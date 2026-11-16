package server

import (
	"math/rand"
	"sync"
)

type Stock struct {
	mu    sync.Mutex
	items map[string]int
}

func NewStock() *Stock {
	return &Stock{
		items: map[string]int{
			"coffee":    10 + rand.Intn(41),
			"tea":       10 + rand.Intn(41),
			"croissant": 10 + rand.Intn(41),
		},
	}
}

// returns copy of items, caller must hold s.mu
func (s *Stock) snapshotLocked() map[string]int {
	snapshot := make(map[string]int, len(s.items))
	for k, v := range s.items {
		snapshot[k] = v
	}
	return snapshot
}

func (s *Stock) GetMenu() map[string]int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.snapshotLocked()
}

func (s *Stock) TryDeduct(requested map[string]int) (bool, map[string]int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	// 1. verify all items are available
	for item, qty := range requested {
		available, exists := s.items[item]
		if !exists || available < qty {
			return false, s.snapshotLocked()
		}
	}

	// 2. deduct each
	for item, qty := range requested {
		s.items[item] -= qty
	}

	return true, s.snapshotLocked()
}

func (s *Stock) AddStock(delivered map[string]int) map[string]int {
	s.mu.Lock()
	defer s.mu.Unlock()

	for item, qty := range delivered {
		s.items[item] += qty
	}

	return s.snapshotLocked()
}

func (s *Stock) RestoreStock(cancelled map[string]int) {
	s.mu.Lock()
	defer s.mu.Unlock()

	for item, qty := range cancelled {
		s.items[item] += qty
	}
}

func (s *Stock) CheckLowStock(threshold int) map[string]int {
	s.mu.Lock()
	defer s.mu.Unlock()

	lowStock := make(map[string]int)

	for item, qty := range s.items {
		if qty < threshold {
			lowStock[item] = qty
		}
	}

	return lowStock
}
