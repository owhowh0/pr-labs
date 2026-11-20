import os
import socket
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))
from common.protocol import SocketConnection, parse_response


def test_payload(host: str, port: int, payload: bytes, desc: str):
    print(f"  [*] Fuzzing: {desc}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))
        s.sendall(b"ROLE client\n")
        resp = s.recv(1024)

        s.sendall(payload if payload.endswith(b"\n") else payload + b"\n")
        reply = s.recv(1024)
        print(f"      Go reply: {reply.decode('utf-8', errors='replace').strip()[:60]}")
        s.close()
    except Exception as e:
        print(f"      Connection handled exception cleanly: {e}")


def test_cross_fuzz(host: str, port: int):
    print("\n--- [TEST] Task 4: Robustness & Fuzzing on Go Server ---")
    payloads = [
        (b"UNKNOWN_COMMAND_FOOBAR", "Unknown command"),
        (b"ORDER", "Missing order parameters"),
        (b"ORDER coffee=-5", "Negative quantity"),
        (b"ORDER coffee=abc", "Non-numeric quantity"),
        (b"ORDER beer=2", "Unknown product"),
        (b"DELIVER tea=10", "Unauthorized delivery attempt from client"),
        (b"A" * 65536, "Oversized 64KB line"),
        (os.urandom(256), "Random raw binary bytes"),
    ]

    for p, desc in payloads:
        test_payload(host, port, p, desc)
        time.sleep(0.1)

    # Health check: verify Go server is alive and functioning normally
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    conn = SocketConnection(s)
    conn.send_line("ROLE client")
    assert conn.read_line() == "OK role_accepted", "Server unresponsive after fuzzing"
    conn.send_line("GET_MENU")
    menu = conn.read_line()
    assert menu and menu.startswith("MENU"), "Server returned bad menu after fuzzing"
    conn.close()

    print("\033[92m[PASS] Go Server Robustness Verified! (Zero Crashes)\033[0m")


if __name__ == "__main__":
    from server_manager import managed_go_server
    with managed_go_server() as (h, p):
        test_cross_fuzz(h, p)
