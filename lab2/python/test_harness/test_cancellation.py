import argparse
import os
import socket
import sys
import time

# Ensure common can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import SocketConnection, parse_response


def get_stock(host: str, port: int) -> dict:
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


def run_cancellation_test(host: str, port: int):
    print(f"\n=======================================================")
    print(f" Task 4 Fault Tolerance Test: Abrupt Client Disconnection")
    print(f"=======================================================")

    initial_stock = get_stock(host, port)
    initial_coffee = initial_stock.get("coffee", 0)
    print(f"[*] Initial coffee stock: {initial_coffee}")

    if initial_coffee < 3:
        print("[*] Stock too low. Restocking via provider first...")
        sp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sp.connect((host, port))
        cp = SocketConnection(sp)
        cp.send_line("ROLE provider")
        cp.read_line()
        cp.send_line("DELIVER coffee=10")
        cp.read_line()
        cp.close()
        initial_stock = get_stock(host, port)
        initial_coffee = initial_stock.get("coffee", 0)
        print(f"[*] Updated initial coffee stock: {initial_coffee}")

    order_qty = 3
    print(f"[*] Connecting client and ordering {order_qty} coffees (Total prep time: {order_qty * 4}s)...")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    conn = SocketConnection(s)
    conn.send_line("ROLE client")
    conn.read_line()

    conn.send_line(f"ORDER coffee={order_qty}")
    resp = conn.read_line()
    print(f"[*] Immediate server response: {resp}")

    if not resp or not resp.startswith("ORDER_ACCEPTED"):
        print(f"[FAIL] Expected ORDER_ACCEPTED, got: {resp}")
        sys.exit(1)

    # Let the worker start preparing the order for 1.5 seconds
    time.sleep(1.5)

    print(f"[*] Simulating abrupt client crash / disconnect (closing socket directly)...")
    s.close()

    # Allow server to detect disconnection, abort worker, and restore stock
    print(f"[*] Waiting 2.0s for server cleanup and worker abort...")
    time.sleep(2.0)

    # Check stock via independent connection
    recovered_stock = get_stock(host, port)
    recovered_coffee = recovered_stock.get("coffee", -1)

    print(f"[*] Stock after disconnect recovery: coffee = {recovered_coffee}")

    if recovered_coffee == initial_coffee:
        print(f"\n\033[92;1m[PASS] CANCELLATION & STOCK ROLLBACK TEST PASSED!\033[0m")
        print(f"Worker stopped, order aborted, and {order_qty} coffees restored to inventory.\n")
    else:
        print(f"\n\033[91;1m[FAIL] STOCK NOT RESTORED!\033[0m Expected: {initial_coffee}, got: {recovered_coffee}\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Task 4 Cancellation & Rollback Test")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Server host")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Server port")
    args = parser.parse_args()

    run_cancellation_test(args.host, args.port)


if __name__ == "__main__":
    main()
