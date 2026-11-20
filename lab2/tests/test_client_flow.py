import os
import socket
import sys
import time

# Import common from python package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from common.protocol import SocketConnection, parse_response


def test_client_flow(host: str, port: int):
    print("\n--- [TEST] Python Client -> Go Server Flow ---")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    conn = SocketConnection(s)

    # 1. Handshake
    conn.send_line("ROLE client")
    resp = conn.read_line()
    assert resp == "OK role_accepted", f"Handshake failed: {resp}"
    print("  [✓] Handshake accepted: OK role_accepted")

    # 2. Get Menu
    conn.send_line("GET_MENU")
    menu_resp = conn.read_line()
    cmd, attrs = parse_response(menu_resp or "")
    assert cmd == "MENU", f"Expected MENU, got {menu_resp}"
    initial_croissants = int(attrs.get("croissant", 0))
    assert initial_croissants > 0, "No croissants in stock"
    print(f"  [✓] GET_MENU: {menu_resp}")

    # 3. Order 1 croissant (prep time: 2s)
    conn.send_line("ORDER croissant=1")
    order_resp = conn.read_line()
    cmd, attrs = parse_response(order_resp or "")
    assert cmd == "ORDER_ACCEPTED", f"Expected ORDER_ACCEPTED, got: {order_resp}"
    order_id = attrs.get("id")
    wait_time = int(attrs.get("wait_time", 0))
    assert wait_time == 2, f"Expected 2s wait time for 1 croissant, got: {wait_time}"
    print(f"  [✓] Immediate response: {order_resp}")

    # 4. Wait for Async Server Push (ORDER_READY)
    start_wait = time.time()
    push_msg = conn.read_line()
    elapsed = time.time() - start_wait
    cmd, attrs = parse_response(push_msg or "")
    assert cmd == "ORDER_READY", f"Expected ORDER_READY, got: {push_msg}"
    assert attrs.get("id") == order_id, f"Mismatched order ID: {push_msg}"
    assert elapsed >= 1.8, f"Worker finished too quickly: {elapsed:.2f}s"
    print(f"  [✓] Async Server Push received: {push_msg} (elapsed: {elapsed:.2f}s)")

    # 5. Verify stock decremented
    conn.send_line("GET_MENU")
    updated_menu = conn.read_line()
    _, attrs = parse_response(updated_menu or "")
    updated_croissants = int(attrs.get("croissant", 0))
    assert updated_croissants == initial_croissants - 1, f"Stock mismatch: {updated_croissants} vs {initial_croissants - 1}"
    print(f"  [✓] Stock decremented properly: {initial_croissants} -> {updated_croissants}")

    # 6. Test Out-of-Stock Refusal
    conn.send_line("ORDER croissant=999999")
    refusal = conn.read_line()
    cmd, attrs = parse_response(refusal or "")
    assert cmd == "ORDER_REFUSED", f"Expected ORDER_REFUSED, got: {refusal}"
    print(f"  [✓] Out-of-stock refusal: {refusal}")

    conn.close()
    print("\033[92m[PASS] Client Flow Test Succeeded!\033[0m")


if __name__ == "__main__":
    from server_manager import managed_go_server
    with managed_go_server() as (h, p):
        test_client_flow(h, p)
