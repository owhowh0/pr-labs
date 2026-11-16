import argparse
import os
import socket
import sys
import threading
from typing import Dict

# Ensure common can be imported when running as script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.protocol import (
    SocketConnection,
    PREPARATION_TIMES,
    parse_response,
    format_order,
)

PROMPT = "client> "


def print_async(message: str) -> None:
    """Prints server notifications cleanly while the user is typing."""
    sys.stdout.write(f"\r\033[K{message}\n{PROMPT}")
    sys.stdout.flush()


class CoffeeClient:
    """
    Interactive Coffee Shop Client.
    Answers Defense Questions:
    - 'Why must the client receive and read the keyboard at the same time?'
      Because server sends asynchronous notifications (e.g. ORDER_READY) at arbitrary times
      while the user might be typing a new order or asking for the menu.
    - 'How does yours do it?'
      Uses a dedicated receiver thread reading the TCP stream while the main thread blocks on stdin.
    """

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock: socket.socket = None
        self.conn: SocketConnection = None
        self.running = threading.Event()
        self.receiver_thread: threading.Thread = None

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            self.conn = SocketConnection(self.sock)
        except OSError as e:
            print(f"[ERROR] Could not connect to {self.host}:{self.port} - {e}")
            return False

        # Role Handshake
        try:
            self.conn.send_line("ROLE client")
            resp = self.conn.read_line()
            if not resp or not resp.startswith("OK"):
                print(f"[ERROR] Handshake failed: {resp}")
                self.conn.close()
                return False
        except (OSError, ConnectionError) as e:
            print(f"[ERROR] Handshake failed: {e}")
            return False

        self.running.set()
        self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receiver_thread.start()
        print(f"[CONNECTED] Connected to Coffee Shop Server at {self.host}:{self.port}")
        return True

    def _listen_loop(self) -> None:
        """Background thread dedicated to receiving incoming server messages & pushes."""
        while self.running.is_set():
            line = self.conn.read_line()
            if line is None:
                if self.running.is_set():
                    sys.stdout.write("\r\033[K[DISCONNECTED] Server closed the connection.\n")
                    sys.stdout.flush()
                    self.running.clear()
                    os._exit(0)
                break

            cmd, attrs = parse_response(line)
            if cmd == "ORDER_READY":
                order_id = attrs.get("id", "?")
                print_async(f"\033[92m[READY]\033[0m Order #{order_id} is ready for pickup!")
            elif cmd == "ORDER_ACCEPTED":
                order_id = attrs.get("id", "?")
                wait_time = attrs.get("wait_time", "?")
                print_async(f"\033[94m[ACCEPTED]\033[0m Order #{order_id} accepted. Estimated wait: {wait_time}s.")
            elif cmd == "ORDER_REFUSED":
                reason = attrs.get("reason", "unknown")
                remaining = {k: v for k, v in attrs.items() if k != "reason"}
                remaining_str = ", ".join(f"{k}: {v}" for k, v in remaining.items())
                print_async(f"\033[91m[REFUSED]\033[0m Order refused: {reason}. Stock: ({remaining_str})")
            elif cmd == "MENU":
                items = [f"{k}: {v}" for k, v in attrs.items()]
                print_async(f"\033[96m[MENU]\033[0m Available Stock: {', '.join(items)}")
            elif cmd == "ERROR":
                print_async(f"\033[91m[SERVER ERROR]\033[0m {line}")
            else:
                print_async(f"[SERVER] {line}")

    def run_interactive(self) -> None:
        print("Type 'help' for command list or 'exit' to quit.\n")
        while self.running.is_set():
            try:
                sys.stdout.write(PROMPT)
                sys.stdout.flush()
                user_input = sys.stdin.readline()
                if not user_input:
                    # EOF (Ctrl+D)
                    break
                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    break
                elif user_input.lower() in ("help", "?"):
                    self._print_help()
                elif user_input.lower() == "menu":
                    self.conn.send_line("GET_MENU")
                elif user_input.lower().startswith("order"):
                    self._handle_order_cmd(user_input[5:].strip())
                else:
                    # Pass raw text command directly to server for testing
                    self.conn.send_line(user_input)

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"[CLIENT ERROR] {e}")

        self.close()
        sys.exit(0)

    def _handle_order_cmd(self, args: str) -> None:
        """
        Parses order arguments in format:
        'coffee=2 tea=1' or 'coffee:2 tea:1' or 'coffee 2 tea 1'
        """
        if not args:
            print("[USAGE] order coffee=2 tea=1 [croissant=1]")
            return

        tokens = args.replace(":", "=").replace(",", " ").split()
        order_dict: Dict[str, int] = {}

        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            if "=" in token:
                k, v = token.split("=", 1)
                try:
                    order_dict[k.lower()] = int(v)
                except ValueError:
                    print(f"[ERROR] Invalid quantity in: {token}")
                    return
                idx += 1
            elif idx + 1 < len(tokens) and tokens[idx + 1].isdigit():
                order_dict[token.lower()] = int(tokens[idx + 1])
                idx += 2
            else:
                print(f"[ERROR] Cannot parse item: '{token}'. Use item=qty")
                return

        if not order_dict:
            print("[ERROR] No valid items to order.")
            return

        raw_cmd = format_order(order_dict)
        self.conn.send_line(raw_cmd)

    def _print_help(self) -> None:
        print("\n--- Available Commands ---")
        print("  menu                 - Query stock quantities from server")
        print("  order <item>=<qty>   - Place order (e.g. 'order coffee=2 tea=1')")
        print("                         Items & Prep Times: coffee (4s), tea (3s), croissant (2s)")
        print("  exit / quit          - Disconnect and exit\n")

    def close(self) -> None:
        self.running.clear()
        if self.conn:
            self.conn.close()
        print("\n[CLIENT] Disconnected. Bye!")


def main():
    parser = argparse.ArgumentParser(description="Interactive Coffee Shop Client")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Server IP address (default: 127.0.0.1)")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Server port (default: 8080)")
    args = parser.parse_args()

    client = CoffeeClient(args.host, args.port)
    if client.connect():
        client.run_interactive()


if __name__ == "__main__":
    main()
