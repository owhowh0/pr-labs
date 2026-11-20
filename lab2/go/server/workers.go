package server

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// Order represents a customer order in the system.
type Order struct {
	ID        int
	ClientID  string
	Items     map[string]int
	TotalTime time.Duration
	Conn      *Connection

	Ctx       context.Context
	Cancel    context.CancelFunc
	Completed bool
	Mu        sync.Mutex
}

// nextOrderID generates a monotonically increasing order ID.
func (s *Server) nextOrderID() int {
	s.orderIDMu.Lock()
	defer s.orderIDMu.Unlock()
	s.orderIDCounter++
	return s.orderIDCounter
}

// workerLoop represents a single worker thread running concurrently.
// It continuously pulls orders from the FIFO orderQueue channel.
func (s *Server) workerLoop(workerID int) {
	for order := range s.orderQueue {
		// Check if the order was already cancelled while waiting in the queue
		if order.Ctx.Err() != nil {
			log.Printf("[Worker-%d] Order #%d was cancelled before preparation started\n", workerID, order.ID)
			s.removeClientOrder(order)
			continue
		}

		log.Printf("[Worker-%d] Preparing order #%d for %s (wait %v)...\n",
			workerID, order.ID, order.ClientID, order.TotalTime)

		// Wait for preparation duration or until cancelled mid-prep
		select {
		case <-time.After(order.TotalTime):
			// Preparation completed successfully!
			order.Mu.Lock()
			order.Completed = true
			order.Mu.Unlock()

			log.Printf("[Worker-%d] Order #%d READY\n", workerID, order.ID)
			// Asynchronously push notification to client
			_ = order.Conn.WriteLine(fmt.Sprintf("ORDER_READY id=%d", order.ID))

		case <-order.Ctx.Done():
			// Client disconnected while order was being prepared
			log.Printf("[Worker-%d] Order #%d CANCELLED mid-prep. Preparation discarded.\n",
				workerID, order.ID)
		}

		// Remove from client's active orders tracking
		s.removeClientOrder(order)
	}
}
