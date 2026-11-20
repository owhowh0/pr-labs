import os
import socket
import sys
import threading
import time
from typing import List, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from common.protocol import SocketConnection, parse_response


def get_stock(host: str, port: int) -> Dict[str, int]:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    conn = SocketConnection(s)
    conn.send_line("ROLE client")
    conn.read_line()
    conn.send_line("GET_MENU")
    resp = conn.read_line()
    conn.close()
    _, attrs = parse_response(resp or "")
    return {k: int(v) for k, v in attrs.items() if v.isdigit()}


def test_cross_race(host: str, port: int, target_item: str = "croissant"):
    print(f"\n--- [TEST] Task 2: High-Concurrency Race Test on Go Server ---")
    initial_stock = get_stock(host, port)
    available_units = initial_stock.get(target_item, 0)

    # Spawn more concurrent clients than available stock
    num_clients = available_units + 10
    print(f"  [*] Initial {target_item} stock: {available_units}")
    print(f"  [*] Firing {num_clients} concurrent Python clients with Barrier synchronization...")

    barrier = threading.Barrier(num_clients)
    results: List[str] = []
    results_lock = threading.Lock()

    def client_worker():
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            conn = SocketConnection(s)
            conn.send_line("ROLE client")
            conn.read_line()

            # Synchronize all threads so packets hit Go server at the exact same instant
            barrier.wait()

            conn.send_line(f"ORDER {target_item}=1")
            resp = conn.read_line()

            with results_lock:
                results.append(resp or "NONE")

            # Keep connection open until prepared so rollback doesn't trigger
            if resp and resp.startswith("ORDER_ACCEPTED"):
                while True:
                    push = conn.read_line()
                    if push is None or push.startswith("ORDER_READY"):
                        break

            conn.close()
        except Exception as e:
            with results_lock:
                results.append(f"EXCEPTION: {e}")

    threads = [threading.Thread(target=client_worker) for _ in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    accepted = [r for r in results if r.startswith("ORDER_ACCEPTED")]
    refused = [r for r in results if r.startswith("ORDER_REFUSED")]
    errors = [r for r in results if not r.startswith("ORDER_ACCEPTED") and not r.startswith("ORDER_REFUSED")]

    final_stock = get_stock(host, port)
    final_units = final_stock.get(target_item, -1)

    print(f"  [✓] Orders ACCEPTED : {len(accepted)} (Expected: {available_units})")
    print(f"  [✓] Orders REFUSED  : {len(refused)} (Expected: {num_clients - available_units})")
    print(f"  [✓] Errors / Crushes: {len(errors)} (Expected: 0)")
    print(f"  [✓] Final Stock     : {final_units} (Expected: 0)")

    assert len(accepted) == available_units, f"Oversold! Accepted {len(accepted)} for stock {available_units}"
    assert len(refused) == (num_clients - available_units), "Refusal count mismatch"
    assert final_units == 0, f"Stock should be 0, got {final_units}"
    assert len(errors) == 0, f"Encountered connection errors: {errors}"

    print("\033[92m[PASS] Go Server Task 2 Race Protection Verified!\033[0m")


if __name__ == "__main__":
    from server_manager import managed_go_server
    with managed_go_server() as (h, p):
        test_cross_race(h, p)
