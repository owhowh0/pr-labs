# Lab 2: A Coffee Shop Server — 50/50 Task Breakdown

## 1. Architecture & Language Split

- **Server**: **Go** (Member 1) — High performance, native goroutines, channels, thread-safe sync primitives.
- **Client, Provider & Defense Test Suite**: **Python** (Member 2) — Interactive CLI with dual threading, raw sockets, automated concurrency & chaos test harness.
- **Bonus Achieved**: Satisfies Lab Section 8 bonus (*"the server and the clients written in two different programming languages, working together"*).
- **Protocol**: Raw TCP sockets, newline-delimited (`\n`) text messages.

---

## 2. Work Breakdown

### Member 1: Go Side (Server Engine & Concurrency)

#### Task 1: Single-Client Core
- [ ] Initialize raw TCP listener with `net.ListenTCP` on configurable port.
- [ ] Handle client connection lifecycle and custom newline buffer reader/writer.
- [ ] Stock initialization (random 10–50 for `coffee`, `tea`, `croissant`).
- [ ] Order validation (positive integers, stock availability).
- [ ] Immediate response generator (`ORDER_ACCEPTED id=<id> wait_time=<sec>` or `ORDER_REFUSED`).

#### Task 2: Multi-Client & Worker Pool
- [ ] Thread-safe stock management using `sync.Mutex` / `sync.RWMutex` (prevent race condition on last item).
- [ ] Worker pool sized to `runtime.NumCPU()` logical cores.
- [ ] Producer-consumer FIFO order queue with channel or condition variable.
- [ ] Worker routine: sleep for order duration, dispatch asynchronous `ORDER_READY id=<id>\n` to client connection.

#### Task 3: Provider Server Logic
- [ ] Provider identification (`ROLE provider`).
- [ ] Delivery endpoint (`DELIVER coffee=X ...`) updating stock atomically.
- [ ] Low-stock threshold check (`< 5` units) triggering `ALERT_LOW_STOCK`.
- [ ] Push notification dispatch to provider (immediate if connected, or queued until provider connects).

#### Task 4: Fault Tolerance & Cleanup
- [ ] Disconnection detection (`io.EOF` / broken pipe).
- [ ] Order cancellation: purge client's queued orders and interrupt active worker (via `context.Context`).
- [ ] Stock rollback: return reserved products to inventory when order canceled.
- [ ] Structured logging for every connect, order, delivery, disconnect, and error.

---

### Member 2: Python Side (Client, Provider & Defense Test Suite)

#### Protocol & Framing Utility
- [ ] Shared raw socket helper (`socket.socket`, `recv` buffer accumulator splitting on `\n`).
- [ ] Message serializer & parser for all commands and responses.

#### Interactive Client CLI (Task 1 & 4)
- [ ] Console REPL connecting to server via command-line host/port.
- [ ] Send `ROLE client`, `GET_MENU`, and `ORDER <items>`.
- [ ] **Dual-threaded architecture**: Background listener thread receiving server push events (`ORDER_READY`) printing immediately without blocking active `input()` prompt.
- [ ] Graceful exit on server disconnect or `CTRL+C`.

#### Interactive Provider CLI (Task 3)
- [ ] Console REPL connecting as `ROLE provider`.
- [ ] Send `DELIVER <items>` to restock items.
- [ ] Background listener thread to receive and display `ALERT_LOW_STOCK` pushes asynchronously.

#### Automated Concurrency & Chaos Harness (Task 2 & 4 Defense Demos)
- [ ] **Race Condition Test Script**: Spawns multiple concurrent socket threads ordering the final item simultaneously to prove thread safety for defense.
- [ ] **Queue & Worker Saturation Script**: Floods server with orders exceeding worker count to demonstrate FIFO queuing and worker allocation.
- [ ] **Chaos / Disconnect Test Script**: Connects, places order, disconnects abruptly while worker is preparing to demonstrate worker abort and stock rollback.
- [ ] **Invalid Input Fuzzer**: Sends malformed packets, negative counts, random bytes, oversized buffers to verify server resilience.

---

## 3. Workload Balance Matrix (~50 / 50)

| Metric | Member 1 (Go) | Member 2 (Python) |
| :--- | :--- | :--- |
| **Primary Artifacts** | `server/` (Core, Workers, Stock, Handlers) | `client/`, `provider/`, `tests/` (Harness & Fuzzer) |
| **Core Challenges** | Mutex locking, worker pool lifecycle, cancellation tokens, atomic rollback | Multi-threaded console I/O, async notifications, stress-test harness, protocol fuzzer |
| **Lab Tasks Covered** | Server side of Tasks 1, 2, 3, 4 | Client side of Tasks 1, 3, 4 + Automated Defense verification for Tasks 2 & 4 |
| **Defense Value** | Demonstrates internal concurrency architecture | Drives the live demonstrations and proves edge-case safety |
| **Estimated Effort** | ~50% | ~50% |

---

## 4. Defense Q&A Distribution

### Member 1 (Go Focus):
1. How does the server partition message bytes from TCP streams?
2. Which data is shared between threads/goroutines and how is each protected with mutexes?
3. How does the server detect when a client disappears (`EOF` / reset)?
4. How does the worker cancel an in-flight order and roll back stock atomically?
5. Why is worker pool size pinned to CPU cores?

### Member 2 (Python Focus):
1. Why does the client need concurrent reading (keyboard input vs. socket push)?
2. How does the client/provider handle partial socket reads and TCP framing?
3. Demonstration: Running the multi-client script showing two clients contending for the last croissant.
4. Demonstration: Running the abrupt disconnect test and showing recovery.
5. How does the provider receive async low-stock alerts without polling?

---

## 5. Repository Structure

```text
lab2/
├── tasks.md                    # This work breakdown
├── protocol.md                 # Detailed wire protocol specs
├── go/                         # Member 1 (Server)
│   ├── go.mod
│   ├── main.go
│   ├── server/
│   │   ├── listener.go         # Socket accept loop
│   │   ├── stock.go            # Thread-safe inventory
│   │   ├── workers.go          # Worker pool & queue
│   │   └── handlers.go         # Command dispatcher
└── python/                     # Member 2 (Clients & Harness)
    ├── common/
    │   └── protocol.py         # Framing & socket helpers
    ├── client.py               # Interactive client CLI
    ├── provider.py             # Interactive provider CLI
    └── test_harness/
        ├── test_race.py        # Concurrent race-condition demo
        ├── test_cancellation.py# Disconnect & rollback demo
        └── fuzzer.py           # Malformed input tester
```
