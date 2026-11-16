import argparse
import os
import queue
import random
import socket
import sys
import threading
import time
from typing import Dict, Optional, Set

# Ensure common can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.protocol import SocketConnection, PREPARATION_TIMES, parse_response


class Order:
    def __init__(self, order_id: int, client_id: str, items: Dict[str, int], client_conn: SocketConnection):
        self.order_id = order_id
        self.client_id = client_id
        self.items = items
        self.client_conn = client_conn
        self.total_time = sum(PREPARATION_TIMES.get(prod, 0) * qty for prod, qty in items.items())
        self.cancel_event = threading.Event()
        self.completed = False


class MockCoffeeServer:
    """
    Mock Coffee Shop Server using raw TCP sockets directly.
    Demonstrates all requirements of Lab 2 (Tasks 1-4) in Python.
    Serves as test baseline for Member 2 and reference for Go server implementation.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self.host = host
        self.port = port
        self.server_sock: socket.socket = None
        self.running = threading.Event()

        # Shared State & Synchronization (Task 1 & 2)
        self.stock_lock = threading.Lock()
        self.stock: Dict[str, int] = {
            "coffee": random.randint(10, 50),
            "tea": random.randint(10, 50),
            "croissant": random.randint(10, 50),
        }

        self.order_id_counter = 0
        self.counter_lock = threading.Lock()

        # Producer-Consumer Order Queue & Workers (Task 2)
        self.order_queue: queue.Queue = queue.Queue()
        self.num_workers = os.cpu_count() or 4
        self.workers: list = []

        # Tracking active orders per client for cancellation (Task 4)
        self.orders_lock = threading.Lock()
        self.active_orders_by_client: Dict[str, Set[Order]] = {}

        # Provider tracking (Task 3)
        self.provider_lock = threading.Lock()
        self.provider_conn: Optional[SocketConnection] = None
        self.pending_provider_alerts: list = []

    def log(self, endpoint: str, message: str) -> None:
        print(f"[{time.strftime('%X')}] [{endpoint}] {message}")

    def start(self) -> None:
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((self.host, self.port))
        self.server_sock.listen(128)
        self.running.set()

        print(f"=== Coffee Shop Server Running at {self.host}:{self.port} ===")
        print(f"Workers spawned: {self.num_workers} (CPU cores)")
        print(f"Initial Stock: {self.stock}\n")

        # Start CPU core worker threads
        for i in range(self.num_workers):
            t = threading.Thread(target=self._worker_loop, args=(i + 1,), daemon=True)
            t.start()
            self.workers.append(t)

        # Accept loop
        while self.running.is_set():
            try:
                client_sock, addr = self.server_sock.accept()
                endpoint = f"{addr[0]}:{addr[1]}"
                self.log(endpoint, "Connection accepted")
                t = threading.Thread(target=self._handle_client, args=(client_sock, endpoint), daemon=True)
                t.start()
            except OSError:
                break

    def _worker_loop(self, worker_id: int) -> None:
        """Worker thread executing simulated order preparation."""
        while self.running.is_set():
            try:
                order: Order = self.order_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self.log(f"Worker-{worker_id}", f"Preparing order #{order.order_id} (wait {order.total_time}s)")
            
            # Simulated preparation wait with responsive cancellation check
            elapsed = 0.0
            cancelled = False
            while elapsed < order.total_time:
                if order.cancel_event.is_set():
                    cancelled = True
                    break
                sleep_chunk = min(0.1, order.total_time - elapsed)
                time.sleep(sleep_chunk)
                elapsed += sleep_chunk

            if cancelled:
                self.log(f"Worker-{worker_id}", f"Order #{order.order_id} CANCELLED mid-prep. Preparation discarded.")
            else:
                order.completed = True
                self.log(f"Worker-{worker_id}", f"Order #{order.order_id} READY")
                try:
                    order.client_conn.send_line(f"ORDER_READY id={order.order_id}")
                except Exception:
                    pass

            with self.orders_lock:
                client_orders = self.active_orders_by_client.get(order.client_id)
                if client_orders and order in client_orders:
                    client_orders.remove(order)

            self.order_queue.task_done()

    def _check_low_stock_and_alert(self) -> None:
        """Checks for stock < 5 and alerts provider immediately or queues alert."""
        low_items = []
        with self.stock_lock:
            for prod, count in self.stock.items():
                if count < 5:
                    low_items.append((prod, count))

        for prod, count in low_items:
            alert_msg = f"ALERT_LOW_STOCK product={prod} count={count}"
            with self.provider_lock:
                if self.provider_conn and not self.provider_conn.is_closed:
                    try:
                        self.provider_conn.send_line(alert_msg)
                        self.log("Provider", f"Dispatched alert: {alert_msg}")
                    except Exception:
                        self.pending_provider_alerts.append(alert_msg)
                else:
                    if alert_msg not in self.pending_provider_alerts:
                        self.pending_provider_alerts.append(alert_msg)

    def _handle_client(self, sock: socket.socket, endpoint: str) -> None:
        conn = SocketConnection(sock)
        role: Optional[str] = None
        client_id = endpoint

        with self.orders_lock:
            self.active_orders_by_client[client_id] = set()

        try:
            # 1. Handshake
            handshake = conn.read_line()
            if not handshake or not handshake.startswith("ROLE "):
                conn.send_line("ERROR expected_role_handshake")
                conn.close()
                return

            role = handshake.split()[1].lower()
            if role not in ("client", "provider"):
                conn.send_line("ERROR invalid_role")
                conn.close()
                return

            conn.send_line("OK role_accepted")
            self.log(endpoint, f"Identified as role: {role}")

            if role == "provider":
                with self.provider_lock:
                    self.provider_conn = conn
                    # Send any pending low stock alerts accumulated while offline
                    while self.pending_provider_alerts:
                        alert = self.pending_provider_alerts.pop(0)
                        conn.send_line(alert)
                # Also check existing stock immediately
                self._check_low_stock_and_alert()

            # 2. Main command loop
            while self.running.is_set():
                line = conn.read_line()
                if line is None:
                    break

                if not line.strip():
                    continue

                tokens = line.strip().split()
                cmd = tokens[0].upper()

                if cmd == "GET_MENU":
                    with self.stock_lock:
                        menu_str = " ".join(f"{p}={qty}" for p, qty in self.stock.items())
                    conn.send_line(f"MENU {menu_str}")

                elif cmd == "ORDER":
                    if role != "client":
                        conn.send_line("ERROR role_cannot_order")
                        continue
                    self._handle_order_cmd(conn, client_id, tokens[1:], endpoint)

                elif cmd == "DELIVER":
                    if role != "provider":
                        conn.send_line("ERROR unauthorized_role")
                        continue
                    self._handle_deliver_cmd(conn, tokens[1:], endpoint)

                else:
                    conn.send_line(f"ERROR unknown_command:{cmd}")

        except Exception as e:
            self.log(endpoint, f"Exception occurred: {e}")
        finally:
            self.log(endpoint, "Connection closed/lost")
            if role == "client":
                self._cleanup_client(client_id)
            elif role == "provider":
                with self.provider_lock:
                    if self.provider_conn == conn:
                        self.provider_conn = None
            conn.close()

    def _handle_order_cmd(self, conn: SocketConnection, client_id: str, item_tokens: list, endpoint: str) -> None:
        if not item_tokens:
            conn.send_line("ERROR empty_order")
            return

        requested: Dict[str, int] = {}
        for tok in item_tokens:
            if "=" not in tok:
                conn.send_line(f"ERROR invalid_format:{tok}")
                return
            prod, qty_str = tok.split("=", 1)
            prod = prod.lower()
            if prod not in PREPARATION_TIMES:
                conn.send_line(f"ERROR unknown_product:{prod}")
                return
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError()
            except ValueError:
                conn.send_line(f"ERROR invalid_quantity:{qty_str}")
                return
            requested[prod] = requested.get(prod, 0) + qty

        # Atomic stock verification and deduction
        with self.stock_lock:
            for prod, qty in requested.items():
                if self.stock[prod] < qty:
                    # Refusal: tell client how many are left
                    left_str = " ".join(f"{p}_left={q}" for p, q in self.stock.items())
                    conn.send_line(f"ORDER_REFUSED reason=insufficient_stock {left_str}")
                    self.log(endpoint, f"Order refused: requested {requested}, stock {self.stock}")
                    return

            # Deduct stock
            for prod, qty in requested.items():
                self.stock[prod] -= qty

        # Check for low-stock triggers (<5)
        self._check_low_stock_and_alert()

        # Generate order
        with self.counter_lock:
            self.order_id_counter += 1
            order_id = self.order_id_counter

        order = Order(order_id, client_id, requested, conn)

        with self.orders_lock:
            self.active_orders_by_client[client_id].add(order)

        self.order_queue.put(order)
        self.log(endpoint, f"Order #{order_id} accepted: {requested} (Wait: {order.total_time}s)")
        conn.send_line(f"ORDER_ACCEPTED id={order_id} wait_time={order.total_time}")

    def _handle_deliver_cmd(self, conn: SocketConnection, item_tokens: list, endpoint: str) -> None:
        if not item_tokens:
            conn.send_line("ERROR empty_delivery")
            return

        delivered: Dict[str, int] = {}
        for tok in item_tokens:
            if "=" not in tok:
                conn.send_line(f"ERROR invalid_format:{tok}")
                return
            prod, qty_str = tok.split("=", 1)
            prod = prod.lower()
            if prod not in PREPARATION_TIMES:
                conn.send_line(f"ERROR unknown_product:{prod}")
                return
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError()
            except ValueError:
                conn.send_line(f"ERROR invalid_quantity:{qty_str}")
                return
            delivered[prod] = delivered.get(prod, 0) + qty

        # Add to stock atomically
        with self.stock_lock:
            for prod, qty in delivered.items():
                self.stock[prod] += qty
            stock_str = " ".join(f"{p}={q}" for p, q in self.stock.items())

        self.log(endpoint, f"Delivery accepted: {delivered}. New stock: {self.stock}")
        conn.send_line(f"DELIVERY_OK {stock_str}")

    def _cleanup_client(self, client_id: str) -> None:
        """
        Task 4: Disconnection handling.
        Cancels all pending/active orders of the client and restores items to stock.
        """
        with self.orders_lock:
            client_orders = self.active_orders_by_client.pop(client_id, set())

        if not client_orders:
            return

        restored_stock: Dict[str, int] = {}
        for order in client_orders:
            if not order.completed:
                order.cancel_event.set()
                for prod, qty in order.items.items():
                    restored_stock[prod] = restored_stock.get(prod, 0) + qty

        if restored_stock:
            with self.stock_lock:
                for prod, qty in restored_stock.items():
                    self.stock[prod] += qty
            self.log(client_id, f"Client disappeared. Cancelled orders, restored to stock: {restored_stock}")

    def stop(self) -> None:
        self.running.clear()
        if self.server_sock:
            try:
                self.server_sock.close()
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description="Lab 2 Coffee Shop Mock Server")
    parser.add_argument("port", nargs="?", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    args = parser.parse_args()

    server = MockCoffeeServer(args.host, args.port)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
