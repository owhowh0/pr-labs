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
    parse_response,
    format_deliver,
)

PROMPT = "provider> "


def print_async(message: str) -> None:
    """Prints server alerts cleanly while user is typing."""
    sys.stdout.write(f"\r\033[K{message}\n{PROMPT}")
    sys.stdout.flush()


class CoffeeProvider:
    """
    Interactive Coffee Shop Provider.
    Answers Defense Questions:
    - 'How does your server know which connection is the provider?'
      The connection explicitly registers with 'ROLE provider' in initial handshake.
    - 'Which thread sends the alert to the provider, and when?'
      Whenever an order decrements stock below 5, or upon provider connect if already below 5.
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
            self.conn.send_line("ROLE provider")
            resp = self.conn.read_line()
            if not resp or not resp.startswith("OK"):
                print(f"[ERROR] Provider handshake failed: {resp}")
                self.conn.close()
                return False
        except (OSError, ConnectionError) as e:
            print(f"[ERROR] Handshake failed: {e}")
            return False

        self.running.set()
        self.receiver_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.receiver_thread.start()
        print(f"[CONNECTED] Provider connected to Coffee Shop at {self.host}:{self.port}")
        return True

    def _listen_loop(self) -> None:
        """Dedicated background thread for receiving incoming push notifications and delivery confirmations."""
        while self.running.is_set():
            line = self.conn.read_line()
            if line is None:
                if self.running.is_set():
                    sys.stdout.write("\r\033[K[DISCONNECTED] Server closed connection.\n")
                    sys.stdout.flush()
                    self.running.clear()
                    os._exit(0)
                break

            cmd, attrs = parse_response(line)
            if cmd == "ALERT_LOW_STOCK":
                product = attrs.get("product", "unknown")
                count = attrs.get("count", "?")
                print_async(f"\033[93;1m[URGENT RESTOCK ALERT]\033[0m Product '{product}' is critically low! Remaining in stock: {count}")
            elif cmd == "DELIVERY_OK":
                items = [f"{k}: {v}" for k, v in attrs.items()]
                print_async(f"\033[92m[RESTOCKED]\033[0m Delivery accepted! Current stock: {', '.join(items)}")
            elif cmd == "MENU":
                items = [f"{k}: {v}" for k, v in attrs.items()]
                print_async(f"\033[96m[STOCK]\033[0m Current Shop Stock: {', '.join(items)}")
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
                    break
                user_input = user_input.strip()
                if not user_input:
                    continue

                if user_input.lower() in ("exit", "quit"):
                    break
                elif user_input.lower() in ("help", "?"):
                    self._print_help()
                elif user_input.lower() == "stock" or user_input.lower() == "menu":
                    self.conn.send_line("GET_MENU")
                elif user_input.lower().startswith("deliver"):
                    self._handle_deliver_cmd(user_input[7:].strip())
                else:
                    self.conn.send_line(user_input)

            except (KeyboardInterrupt, EOFError):
                break
            except Exception as e:
                print(f"[PROVIDER ERROR] {e}")

        self.close()
        sys.exit(0)

    def _handle_deliver_cmd(self, args: str) -> None:
        """
        Parses delivery arguments:
        'deliver coffee=20 croissant=10' or 'coffee:20 croissant:10'
        """
        if not args:
            print("[USAGE] deliver coffee=20 croissant=10 [tea=15]")
            return

        tokens = args.replace(":", "=").replace(",", " ").split()
        items: Dict[str, int] = {}
        idx = 0
        while idx < len(tokens):
            token = tokens[idx]
            if "=" in token:
                k, v = token.split("=", 1)
                try:
                    items[k.lower()] = int(v)
                except ValueError:
                    print(f"[ERROR] Invalid quantity in: {token}")
                    return
                idx += 1
            elif idx + 1 < len(tokens) and tokens[idx + 1].isdigit():
                items[token.lower()] = int(tokens[idx + 1])
                idx += 2
            else:
                print(f"[ERROR] Cannot parse item: '{token}'. Use item=qty")
                return

        if not items:
            print("[ERROR] No valid items to deliver.")
            return

        self.conn.send_line(format_deliver(items))

    def _print_help(self) -> None:
        print("\n--- Provider Commands ---")
        print("  deliver <item>=<qty> - Restock shop inventory (e.g. 'deliver coffee=20 croissant=10')")
        print("  stock / menu         - Check current shop stock levels")
        print("  exit / quit          - Disconnect and exit\n")

    def close(self) -> None:
        self.running.clear()
        if self.conn:
            self.conn.close()
        print("\n[PROVIDER] Disconnected. Bye!")


def main():
    parser = argparse.ArgumentParser(description="Interactive Coffee Shop Provider")
    parser.add_argument("host", nargs="?", default="127.0.0.1", help="Server IP address (default: 127.0.0.1)")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Server port (default: 8080)")
    args = parser.parse_args()

    # If user provided a single numeric argument (e.g. `provider.py 8080`), treat it as the port
    if args.host.isdigit() and args.port == 8080:
        args.port = int(args.host)
        args.host = "127.0.0.1"

    provider = CoffeeProvider(args.host, args.port)
    if provider.connect():
        provider.run_interactive()


if __name__ == "__main__":
    main()
