# Lab 2: Cross-Language Integration Test Suite (Go Server + Python Clients)

This test suite automatically starts the **Go server** (`lab2/go/main.go`) and validates it against the **Python Client and Provider implementations** (`lab2/python/`).

---

## 1. Quick Run

To run all integration tests in one command:

```bash
cd lab2/tests
python3 run_all.py
```
*(Or with uv: `uv run python run_all.py` from `lab2/python`)*

---

## 2. Test Breakdown

| Test File | Target Requirement | Description |
| :--- | :--- | :--- |
| `test_client_flow.py` | Task 1 | Connects Python client, verifies handshake, requests menu, orders items, waits for async `ORDER_READY` from Go worker. |
| `test_provider_flow.py` | Task 3 | Connects Python provider, tests stock restocking (`DELIVER`), live `ALERT_LOW_STOCK` pushes when items `< 5`, and offline alert delivery upon reconnect. |
| `test_cross_cancellation.py` | Task 4 | Python client places 3-coffee order (12s prep), crashes abruptly. Verifies Go worker aborts and restores stock. |
| `test_cross_fuzz.py` | Task 4 | Floods Go server with malformed commands, negative quantities, 64KB buffers, and raw binary noise. Verifies zero crashes. |
| `test_cross_race.py` | Task 2 | Spawns 30+ barrier-synchronized Python clients ordering the last croissant simultaneously. Verifies Go mutex lock prevents overselling. |

---

## 3. Individual Test Runs

Each test can be run individually against an auto-booted Go server:

```bash
python3 test_client_flow.py
python3 test_provider_flow.py
python3 test_cross_cancellation.py
python3 test_cross_fuzz.py
python3 test_cross_race.py
```

Or against an already running server by passing host and port:
```bash
python3 test_client_flow.py 127.0.0.1 8080
```
