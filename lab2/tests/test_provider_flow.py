import os
import socket
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from common.protocol import SocketConnection, parse_response


def test_provider_flow(host: str, port: int):
    print("\n--- [TEST] Python Provider -> Go Server Flow ---")

    # 1. Connect Provider
    sp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sp.connect((host, port))
    p_conn = SocketConnection(sp)

    p_conn.send_line("ROLE provider")
    resp = p_conn.read_line()
    assert resp == "OK role_accepted", f"Provider handshake failed: {resp}"
    print("  [✓] Provider Handshake: OK role_accepted")

    # 2. Check initial menu via client
    sc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sc.connect((host, port))
    c_conn = SocketConnection(sc)
    c_conn.send_line("ROLE client")
    c_conn.read_line()
    c_conn.send_line("GET_MENU")
    _, initial_menu = parse_response(c_conn.read_line() or "")
    init_coffee = int(initial_menu.get("coffee", 0))

    # 3. Provider delivers 20 coffee
    p_conn.send_line("DELIVER coffee=20")
    deliv_resp = p_conn.read_line()
    cmd, attrs = parse_response(deliv_resp or "")
    assert cmd == "DELIVERY_OK", f"Expected DELIVERY_OK, got: {deliv_resp}"
    new_coffee = int(attrs.get("coffee", 0))
    assert new_coffee == init_coffee + 20, f"Stock mismatch after delivery: {new_coffee} vs {init_coffee + 20}"
    print(f"  [✓] Delivery Accepted: {deliv_resp}")

    # 4. Drain stock below 5 to trigger push alert to connected provider
    # Order so remaining coffee is 3
    to_order = new_coffee - 3
    c_conn.send_line(f"ORDER coffee={to_order}")
    c_conn.read_line()  # ORDER_ACCEPTED

    # Provider should immediately receive ALERT_LOW_STOCK push
    alert = p_conn.read_line()
    cmd, attrs = parse_response(alert or "")
    assert cmd == "ALERT_LOW_STOCK", f"Expected ALERT_LOW_STOCK, got: {alert}"
    assert attrs.get("product") == "coffee", f"Expected coffee alert, got: {alert}"
    assert int(attrs.get("count", -1)) == 3, f"Expected remaining 3, got: {alert}"
    print(f"  [✓] Live Alert Pushed to Connected Provider: {alert}")

    # 5. Offline Provider Alert Test
    # Provider disconnects
    p_conn.close()
    time.sleep(0.5)

    # Client drains tea below 5 (to 2)
    c_conn.send_line("GET_MENU")
    _, menu = parse_response(c_conn.read_line() or "")
    tea_current = int(menu.get("tea", 0))
    c_conn.send_line(f"ORDER tea={tea_current - 2}")
    c_conn.read_line()  # ORDER_ACCEPTED

    # Reconnect Provider: Go server must deliver queued alert on connect!
    sp2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sp2.connect((host, port))
    p_conn2 = SocketConnection(sp2)
    p_conn2.send_line("ROLE provider")
    resp = p_conn2.read_line()
    assert resp == "OK role_accepted"

    # Queued alert must arrive immediately
    queued_alert = p_conn2.read_line()
    cmd, attrs = parse_response(queued_alert or "")
    assert cmd == "ALERT_LOW_STOCK", f"Expected queued ALERT_LOW_STOCK, got: {queued_alert}"
    print(f"  [✓] Queued Alert Delivered Upon Reconnect: {queued_alert}")

    p_conn2.close()
    c_conn.close()
    print("\033[92m[PASS] Provider Flow Test Succeeded!\033[0m")


if __name__ == "__main__":
    from server_manager import managed_go_server
    with managed_go_server() as (h, p):
        test_provider_flow(h, p)
