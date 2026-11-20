package server

import (
	"fmt"
	"log"
	"net"
	"runtime"
	"sync"
)

type Server struct {
	port  int
	stock *Stock

	// Concurrency & Worker Pool (Task 2)
	orderQueue     chan *Order
	orderIDCounter int
	orderIDMu      sync.Mutex

	// Client Order Tracking & Cancellation (Task 4)
	ordersMu     sync.Mutex
	activeOrders map[string]map[*Order]struct{}

	// Provider Connection & Alerts (Task 3)
	providerMu    sync.Mutex
	providerConn  *Connection
	pendingAlerts []string
}

func NewServer(port int) *Server {
	return &Server{
		port:         port,
		stock:        NewStock(),
		orderQueue:   make(chan *Order, 1000),
		activeOrders: make(map[string]map[*Order]struct{}),
	}
}

func (s *Server) Start() error {
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", s.port))
	if err != nil {
		return err
	}
	defer listener.Close()

	numWorkers := runtime.NumCPU()
	log.Printf("Server listening on port %d with %d workers\n", s.port, numWorkers)
	log.Printf("Initial Stock: %v\n", s.stock.GetMenu())

	// Spawn CPU-pinned worker pool
	for i := 1; i <= numWorkers; i++ {
		go s.workerLoop(i)
	}

	for {
		conn, err := listener.Accept()
		if err != nil {
			log.Printf("Accept error: %v\n", err)
			continue
		}
		c := NewConnection(conn)
		go s.handleConnection(c)
	}
}

func (s *Server) handleConnection(c *Connection) {
	defer c.Close()
	endpoint := c.RemoteAddr()
	log.Printf("[%s] Connection accepted\n", endpoint)

	// Handshake
	role, err := handleHandshake(c)
	if err != nil {
		return
	}

	if role == "provider" {
		s.setProvider(c)
		defer s.unsetProvider(c)
	} else if role == "client" {
		defer s.cleanupClient(endpoint)
	}

	// Command loop
	s.handleClientLoop(c, role)
}

// registerClientOrder tracks an in-flight order for cancellation support.
func (s *Server) registerClientOrder(order *Order) {
	s.ordersMu.Lock()
	defer s.ordersMu.Unlock()

	orders, ok := s.activeOrders[order.ClientID]
	if !ok {
		orders = make(map[*Order]struct{})
		s.activeOrders[order.ClientID] = orders
	}
	orders[order] = struct{}{}
}

// removeClientOrder removes a completed or cancelled order from tracking.
func (s *Server) removeClientOrder(order *Order) {
	s.ordersMu.Lock()
	defer s.ordersMu.Unlock()

	if orders, ok := s.activeOrders[order.ClientID]; ok {
		delete(orders, order)
		if len(orders) == 0 {
			delete(s.activeOrders, order.ClientID)
		}
	}
}

// cleanupClient handles client disconnection: cancels queued & active orders and restores stock.
func (s *Server) cleanupClient(clientID string) {
	s.ordersMu.Lock()
	clientOrders, exists := s.activeOrders[clientID]
	if exists {
		delete(s.activeOrders, clientID)
	}
	s.ordersMu.Unlock()

	if !exists || len(clientOrders) == 0 {
		return
	}

	restoredStock := make(map[string]int)

	for order := range clientOrders {
		order.Mu.Lock()
		if !order.Completed {
			// Signal cancellation to worker
			order.Cancel()
			for prod, qty := range order.Items {
				restoredStock[prod] += qty
			}
		}
		order.Mu.Unlock()
	}

	if len(restoredStock) > 0 {
		s.stock.RestoreStock(restoredStock)
		log.Printf("[%s] Disconnected. Cancelled orders, restored to stock: %v\n",
			clientID, restoredStock)
	}
}

// setProvider registers the active provider and delivers queued or immediate low-stock alerts.
func (s *Server) setProvider(c *Connection) {
	s.providerMu.Lock()
	s.providerConn = c

	// Send any pending alerts accumulated while provider was offline
	for _, alert := range s.pendingAlerts {
		_ = c.WriteLine(alert)
		log.Printf("[Provider] Dispatched queued alert: %s\n", alert)
	}
	s.pendingAlerts = nil
	s.providerMu.Unlock()

	// Check if any product is currently low
	s.checkLowStockAndAlert()
}

// unsetProvider unregisters the provider connection when it disconnects.
func (s *Server) unsetProvider(c *Connection) {
	s.providerMu.Lock()
	defer s.providerMu.Unlock()
	if s.providerConn == c {
		s.providerConn = nil
		log.Printf("[Provider] Provider disconnected\n")
	}
}

// checkLowStockAndAlert checks for items < 5 and sends ALERT_LOW_STOCK to provider.
func (s *Server) checkLowStockAndAlert() {
	lowStock := s.stock.CheckLowStock(5)
	if len(lowStock) == 0 {
		return
	}

	s.providerMu.Lock()
	defer s.providerMu.Unlock()

	for prod, count := range lowStock {
		alertMsg := fmt.Sprintf("ALERT_LOW_STOCK product=%s count=%d", prod, count)
		if s.providerConn != nil {
			if err := s.providerConn.WriteLine(alertMsg); err != nil {
				// Failed to send, queue it
				s.pendingAlerts = append(s.pendingAlerts, alertMsg)
			} else {
				log.Printf("[Provider] Dispatched alert: %s\n", alertMsg)
			}
		} else {
			// Provider not connected: queue alert if not already queued
			alreadyQueued := false
			for _, a := range s.pendingAlerts {
				if a == alertMsg {
					alreadyQueued = true
					break
				}
			}
			if !alreadyQueued {
				s.pendingAlerts = append(s.pendingAlerts, alertMsg)
				log.Printf("[Stock] Low stock queued for provider: %s\n", alertMsg)
			}
		}
	}
}
