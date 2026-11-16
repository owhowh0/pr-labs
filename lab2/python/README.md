# Lab 2: Coffee Shop — Python Client, Provider & Test Harness

Member 2 implementation for Lab 2: Coffee Shop Server.
Uses raw TCP sockets with newline-delimited stream framing. Managed via `uv`.

---

## 1. Prerequisites & Setup

Ensure `uv` is installed:
```bash
cd lab2/python
uv sync
```

---

## 2. Interactive Client (`client.py`)

Interactive console client. Uses dual-threading:
- Background listener thread prints asynchronous server notifications (`ORDER_READY`, stock updates) immediately while the user is typing without clobbering input.
- Automatically handles server disconnect and clean exit.

```bash
uv run python client.py [host] [port]
# Example:
uv run python client.py 127.0.0.1 8080
```

### Commands:
- `menu` — View available products and remaining stock.
- `order coffee=2 tea=1` — Place an order (prep times: coffee=4s, tea=3s, croissant=2s).
- `help` — Show command options.
- `exit` — Disconnect cleanly.

---

## 3. Interactive Provider (`provider.py`)

Interactive restocker console.
- Identifies as `ROLE provider`.
- Asynchronously receives `ALERT_LOW_STOCK` pushes from server whenever stock falls below 5.

```bash
uv run python provider.py [host] [port]
# Example:
uv run python provider.py 127.0.0.1 8080
```

### Commands:
- `deliver coffee=20 croissant=10` — Restock inventory.
- `stock` / `menu` — Inspect current stock levels.
- `exit` — Disconnect cleanly.

---

## 4. Defense & Automation Test Suite (`test_harness/`)

Scripts designed specifically to demonstrate lab requirements and control questions at the defense.

### 4.1 Race Condition Demo (Task 2)
Proves stock lock safety under high concurrency (more clients than workers).
Synchronizes 40+ concurrent clients with a barrier to order the remaining items simultaneously:
```bash
uv run python test_harness/test_race.py [host] [port]
```

### 4.2 Disconnect Cancellation & Rollback Demo (Task 4)
Places an order with long preparation time, then abruptly kills the client connection. Demonstrates:
1. Server detects disconnect (`recv() == 0` / reset).
2. Active worker aborts simulated preparation immediately.
3. Reserved products are restored back to stock inventory.
```bash
uv run python test_harness/test_cancellation.py [host] [port]
```

### 4.3 Robustness & Fuzzing Suite (Task 4)
Floods server with malformed lines, negative quantities, unknown products, binary noise, and 64KB buffers to prove the server never crashes or deadlocks:
```bash
uv run python test_harness/fuzzer.py [host] [port]
```

---

## 5. Mock Server (`test_harness/mock_server.py`)

A full reference server implemented in Python with raw sockets, `os.cpu_count()` worker pool, and cancellation events. Used for local testing while Member 1 implements the Go server:
```bash
uv run python test_harness/mock_server.py [port]
```
