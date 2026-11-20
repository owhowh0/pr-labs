# Lab 2: Coffee Shop — Python Client & Provider

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
- Background listener thread prints asynchronous server notifications (`ORDER_READY`, stock updates) immediately while user is typing without clobbering input.
- Automatically handles server disconnect and clean exit.

```bash
uv run python client.py [port]
# Example:
uv run python client.py 8080
```

### Commands:
- `menu` — View available products and remaining stock.
- `order coffee=2 tea=1` — Place an order (prep times: coffee=4s, tea=3s, croissant=2s).
- `help` — Show command options.
- `exit` / `quit` — Disconnect cleanly.

---

## 3. Interactive Provider (`provider.py`)

Interactive restocker console.
- Identifies as `ROLE provider`.
- Asynchronously receives `ALERT_LOW_STOCK` pushes from server whenever stock falls below 5.

```bash
uv run python provider.py [port]
# Example:
uv run python provider.py 8080
```

### Commands:
- `deliver coffee=20 croissant=10` — Restock inventory.
- `stock` / `menu` — Inspect current stock levels.
- `exit` / `quit` — Disconnect cleanly.

---

## 4. Cross-Language Integration Test Suite

All automated tests for race conditions, disconnect rollback, fuzzing, and flow validation are located in the top-level `tests/` directory:

```bash
cd ../tests
python3 run_all.py
```
