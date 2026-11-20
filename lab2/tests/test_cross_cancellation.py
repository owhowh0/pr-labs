import os
import socket
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
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


def test_cross_cancellation(host: str, port: int):
    print("\n--- [TEST] Task 4: Abrupt Disconnect & Stock Rollback on Go Server ---")
    initial_stock = get_stock(host, port)
    initial_coffee = initial_stock.get("coffee", 0)
    print(f"  [*] Initial coffee stock: {initial_coffee}")

    order_qty = 3
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    conn = SocketConnection(s)
    conn.send_line("ROLE client")
    conn.read_line()

    conn.send_line(f"ORDER coffee={order_qty}")
    resp = conn.read_line()
    cmd, attrs = parse_response(resp or "")
    assert cmd == "ORDER_ACCEPTED", f"Expected ORDER_ACCEPTED, got: {resp}"
    print(f"  [✓] Go server accepted order: {resp}")

    # Let the Go worker start preparing for 1.5 seconds
    time.sleep(1.5)

    print("  [*] Simulating abrupt client crash (closing TCP socket)...")
    s.close()

    # Wait for Go server cleanupClient() to execute
    time.sleep(2.0)

    recovered_stock = get_stock(host, port)
    recovered_coffee = recovered_stock.get("coffee", -1)
    print(f"  [✓] Coffee stock after recovery: {recovered_coffee} (Expected: {initial_coffee})")

    assert recovered_coffee == initial_coffee, f"Stock rollback failed! Expected {initial_coffee}, got {recovered_coffee}"
    print("\033[92m[PASS] Go Server Task 4 Worker Abort & Stock Rollback Succeeded!\033[0m")


if __name__ == "__main__":
    from server_manager import managed_go_server
    with managed_go_server() as (h, p):
        test_cross_cancellation(h, p)
