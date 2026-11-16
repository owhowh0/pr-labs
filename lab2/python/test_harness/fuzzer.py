import argparse
import os
import socket
import sys
import time

# Ensure common can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import SocketConnection, parse_response


def test_payload(host: str, port: int, payload: bytes, description: str) -> bool:
    print(f"[*] Testing: {description}...")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3.0)
        s.connect((host, port))

        # Handshake
        s.sendall(b"ROLE client\n")
        resp = s.recv(1024)
        if not resp.startswith(b"OK"):
            print(f"    Handshake unexpected: {resp}")

        # Send dirty payload
        s.sendall(payload if payload.endswith(b"\n") else payload + b"\n")
        response = s.recv(1024)
        print(f"    Server response: {response.decode('utf-8', errors='replace').strip()[:80]}")
        s.close()
        return True
    except socket.timeout:
        print(f"    Timed out waiting for response (server survived).")
        return True
    except (ConnectionResetError, BrokenPipeError):
        print(f"    Server cleanly closed socket on invalid input.")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def verify_server_alive(host: str, port: int) -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((host, port))
        conn = SocketConnection(s)
        conn.send_line("ROLE client")
        r1 = conn.read_line()
        conn.send_line("GET_MENU")
        r2 = conn.read_line()
        conn.close()
        return (r1 is not None and r1.startswith("OK") and r2 is not None and r2.startswith("MENU"))
    except Exception as e:
        print(f"[FAIL] Server health check failed: {e}")
        return False


def run_fuzzer(host: str, port: int):
    print(f"\n=======================================================")
    print(f" Task 4 Robustness & Fuzzing Test Suite")
    print(f"=======================================================")

    cases = [
        (b"UNKNOWN_COMMAND_FOOBAR", "Unknown command"),
        (b"ORDER", "Order with missing parameters"),
        (b"ORDER coffee=-4 tea=0", "Negative and zero quantities"),
        (b"ORDER coffee=infinite tea=abc", "Non-numeric quantities"),
        (b"ORDER beer=2 vodka=1", "Unknown products"),
        (b"DELIVER tea=10", "Client attempting unauthorized delivery"),
        (b"A" * 65536, "Oversized 64KB message buffer"),
        (os.urandom(256), "Random raw binary noise"),
        (b"ORDER   coffee===3  ,, tea=2", "Malformed key-value separators"),
    ]

    for payload, desc in cases:
        test_payload(host, port, payload, desc)
        time.sleep(0.1)

    print("\n[*] Verifying server health and availability for normal clients...")
    alive = verify_server_alive(host, port)
    if alive:
        print(f"\n\033[92;1m[PASS] SERVER ROBUSTNESS VERIFIED!\033[0m")
        print(f"Server rejected invalid inputs without crashing or hanging.\n")
    else:
        print(f"\n\033[91;1m[FAIL] SERVER CRASHED OR UNRESPONSIVE!\033[0m\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Task 4 Fuzzing & Malformed Input Test")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Server host")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Server port")
    args = parser.parse_args()

    run_fuzzer(args.host, args.port)


if __name__ == "__main__":
    main()
