package server

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strconv"
	"strings"
	"time"
)

// Known products and their preparation times in seconds (from PDF section 2).
var productPrepTimes = map[string]int{
	"coffee":    4,
	"tea":       3,
	"croissant": 2,
}

// handleHandshake performs the initial protocol handshake.
// Clients and providers must identify their role as the first message.
func handleHandshake(c *Connection) (string, error) {
	line, err := c.ReadLine()
	if err != nil {
		log.Printf("[%s] Client closed connection before handshake: %v\n", c.RemoteAddr(), err)
		return "", err
	}

	parts := strings.Fields(line)
	if len(parts) != 2 {
		c.WriteLine("ERROR expected_role_handshake")
		return "", errors.New("malformed handshake")
	}

	cmd := strings.ToUpper(parts[0])
	role := strings.ToLower(parts[1])

	if cmd != "ROLE" {
		log.Printf("[%s] Expected role handshake, got: %s\n", c.RemoteAddr(), cmd)
		c.WriteLine("ERROR expected_role_handshake")
		return "", errors.New("expected role handshake")
	}

	if role != "client" && role != "provider" {
		log.Printf("[%s] Invalid role: %s\n", c.RemoteAddr(), role)
		c.WriteLine("ERROR invalid_role")
		return "", errors.New("invalid role")
	}

	log.Printf("[%s] Identified as role: %s\n", c.RemoteAddr(), role)
	if err := c.WriteLine("OK role_accepted"); err != nil {
		return "", err
	}
	return role, nil
}

// handleClientLoop runs the main command loop for an established connection.
func (s *Server) handleClientLoop(c *Connection, role string) {
	for {
		line, err := c.ReadLine()
		if err != nil {
			log.Printf("[%s] Connection closed/lost\n", c.RemoteAddr())
			return
		}

		trimmed := strings.TrimSpace(line)
		if len(trimmed) == 0 {
			continue
		}

		parts := strings.Fields(trimmed)
		cmd := strings.ToUpper(parts[0])
		args := parts[1:]

		switch cmd {
		case "GET_MENU":
			s.handleGetMenu(c)

		case "DELIVER":
			if role != "provider" {
				c.WriteLine("ERROR unauthorized_role")
				continue
			}
			s.handleDeliver(c, args)

		case "ORDER":
			if role != "client" {
				c.WriteLine("ERROR role_cannot_order")
				continue
			}
			s.handleOrder(c, args)

		default:
			log.Printf("[%s] Unknown command: %s\n", c.RemoteAddr(), cmd)
			c.WriteLine(fmt.Sprintf("ERROR unknown_command:%s", cmd))
		}
	}
}

// handleGetMenu responds with current stock for all items.
func (s *Server) handleGetMenu(c *Connection) {
	menu := s.stock.GetMenu()
	msg := fmt.Sprintf("MENU coffee=%d tea=%d croissant=%d",
		menu["coffee"], menu["tea"], menu["croissant"])

	if err := c.WriteLine(msg); err != nil {
		log.Printf("[%s] Error sending menu: %v\n", c.RemoteAddr(), err)
	}
}

// handleDeliver processes delivery of items from a provider.
func (s *Server) handleDeliver(c *Connection, tokens []string) {
	if len(tokens) == 0 {
		c.WriteLine("ERROR empty_delivery")
		return
	}

	items, errMsg := parseItemTokens(tokens)
	if errMsg != "" {
		c.WriteLine(errMsg)
		return
	}

	// Atomically add to stock
	newStock := s.stock.AddStock(items)
	log.Printf("[%s] Delivery accepted: %v. New stock: %v\n", c.RemoteAddr(), items, newStock)

	msg := fmt.Sprintf("DELIVERY_OK coffee=%d tea=%d croissant=%d",
		newStock["coffee"], newStock["tea"], newStock["croissant"])
	c.WriteLine(msg)
}

// handleOrder processes client orders and enqueues them for worker preparation.
func (s *Server) handleOrder(c *Connection, tokens []string) {
	if len(tokens) == 0 {
		c.WriteLine("ERROR empty_order")
		return
	}

	items, errMsg := parseItemTokens(tokens)
	if errMsg != "" {
		c.WriteLine(errMsg)
		return
	}

	// Atomic stock deduction
	success, stockSnapshot := s.stock.TryDeduct(items)
	if !success {
		refusal := fmt.Sprintf("ORDER_REFUSED reason=insufficient_stock coffee_left=%d tea_left=%d croissant_left=%d",
			stockSnapshot["coffee"], stockSnapshot["tea"], stockSnapshot["croissant"])
		log.Printf("[%s] Order refused (insufficient stock): %v\n", c.RemoteAddr(), items)
		c.WriteLine(refusal)
		return
	}

	// Check if any product dropped below 5 and alert provider
	s.checkLowStockAndAlert()

	// Calculate total preparation time
	totalSeconds := 0
	for prod, qty := range items {
		totalSeconds += productPrepTimes[prod] * qty
	}
	prepDuration := time.Duration(totalSeconds) * time.Second

	orderID := s.nextOrderID()
	ctx, cancel := context.WithCancel(context.Background())

	order := &Order{
		ID:        orderID,
		ClientID:  c.RemoteAddr(),
		Items:     items,
		TotalTime: prepDuration,
		Conn:      c,
		Ctx:       ctx,
		Cancel:    cancel,
	}

	// Track order for cancellation support
	s.registerClientOrder(order)

	log.Printf("[%s] Order #%d accepted: %v (wait %ds)\n", c.RemoteAddr(), orderID, items, totalSeconds)
	c.WriteLine(fmt.Sprintf("ORDER_ACCEPTED id=%d wait_time=%d", orderID, totalSeconds))

	// Enqueue into FIFO channel for workers
	s.orderQueue <- order
}

// parseItemTokens parses key=value tokens like ["coffee=2", "tea=1"] into a map.
func parseItemTokens(tokens []string) (map[string]int, string) {
	items := make(map[string]int)

	for _, tok := range tokens {
		parts := strings.SplitN(tok, "=", 2)
		if len(parts) != 2 {
			return nil, fmt.Sprintf("ERROR invalid_format:%s", tok)
		}

		prod := strings.ToLower(parts[0])
		if _, ok := productPrepTimes[prod]; !ok {
			return nil, fmt.Sprintf("ERROR unknown_product:%s", prod)
		}

		qty, err := strconv.Atoi(parts[1])
		if err != nil || qty <= 0 {
			return nil, fmt.Sprintf("ERROR invalid_quantity:%s", parts[1])
		}

		items[prod] += qty
	}

	return items, ""
}
