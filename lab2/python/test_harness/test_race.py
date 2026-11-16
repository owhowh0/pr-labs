import argparse
import os
import socket
import sys
import threading
import time
from typing import List, Dict

# Ensure common can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def run_race_test(host: str, port: int, target_item: str = "croissant"):
    print(f"\n=======================================================")
    print(f" Task 2 Race Condition Test: High-Concurrency Contention")
    print(f"=======================================================")

    initial_stock = get_stock(host, port)
    available_units = initial_stock.get(target_item, 0)

    # Spawn more clients than available stock to guarantee contention and refusals
    num_clients = available_units + 10
    print(f"[*] Available {target_item} stock: {available_units}")
    print(f"[*] Launching {num_clients} concurrent clients simultaneously (Barrier synchronized)...")

    barrier = threading.Barrier(num_clients)
    results: List[str] = []
    results_lock = threading.Lock()

    def client_worker(worker_id: int):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((host, port))
            conn = SocketConnection(s)
            conn.send_line("ROLE client")
            conn.read_line()

            # Synchronize all threads so they fire at the exact same instant
            barrier.wait()

            # Place order for 1 unit
            conn.send_line(f"ORDER {target_item}=1")
            resp = conn.read_line()

            with results_lock:
                results.append(resp or "NONE")

            # If accepted, remain connected until order is prepared so Task 4 cancellation doesn't trigger
            if resp and resp.startswith("ORDER_ACCEPTED"):
                while True:
                    push = conn.read_line()
                    if push is None or push.startswith("ORDER_READY"):
                        break

            conn.close()
        except Exception as e:
            with results_lock:
                results.append(f"EXCEPTION: {e}")

    threads = [threading.Thread(target=client_worker, args=(i,)) for i in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Analyze outcomes
    accepted = [r for r in results if r.startswith("ORDER_ACCEPTED")]
    refused = [r for r in results if r.startswith("ORDER_REFUSED")]
    errors = [r for r in results if not r.startswith("ORDER_ACCEPTED") and not r.startswith("ORDER_REFUSED")]

    final_stock = get_stock(host, port)
    final_units = final_stock.get(target_item, -1)

    print(f"\n--- Results Summary ---")
    print(f"Total concurrent clients : {num_clients}")
    print(f"Initial {target_item} stock      : {available_units}")
    print(f"Orders ACCEPTED          : {len(accepted)}")
    print(f"Orders REFUSED           : {len(refused)}")
    print(f"Errors / Exceptions      : {len(errors)}")
    print(f"Final {target_item} stock        : {final_units}")

    # Defense Criteria Check:
    # 1. Exactly available_units accepted
    # 2. Exactly num_clients - available_units refused
    # 3. Final stock is 0 (never negative)
    success = (len(accepted) == available_units) and (len(refused) == (num_clients - available_units)) and (final_units == 0)

    if success:
        print(f"\n\033[92;1m[PASS] RACE CONDITION TEST PASSED!\033[0m")
        print(f"Locks properly prevent overselling: exactly {available_units} accepted, {len(refused)} refused.\n")
    else:
        print(f"\n\033[91;1m[FAIL] RACE CONDITION DETECTED OR MISMATCH!\033[0m\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Task 2: Multi-client Race Condition Demo")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Server host")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Server port")
    parser.add_argument("-i", "--item", default="croissant", help="Item to test (default: croissant)")
    args = parser.parse_args()

    run_race_test(args.host, args.port, args.item)


if __name__ == "__main__":
    main()
