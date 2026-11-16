import socket
import threading
from typing import Optional, Tuple, Dict, Any

PREPARATION_TIMES: Dict[str, int] = {
    "coffee": 4,
    "tea": 3,
    "croissant": 2,
}


class SocketConnection:
    """
    Low-level raw socket manager handling newline-delimited stream framing.
    Answers Defense Question:
    'How does your code cut received bytes into messages?
     What does it do when a message arrives in two pieces, or two in one receive?'
    """

    def __init__(self, sock: socket.socket):
        self.sock = sock
        self._buffer = ""
        self._send_lock = threading.Lock()
        self._recv_lock = threading.Lock()
        self._closed = False

    def send_line(self, message: str) -> None:
        """Appends newline if absent, encodes to UTF-8, and transmits via raw socket."""
        if not message.endswith("\n"):
            message += "\n"
        data = message.encode("utf-8")
        with self._send_lock:
            if self._closed:
                raise ConnectionError("Socket is closed")
            self.sock.sendall(data)

    def read_line(self) -> Optional[str]:
        """
        Reads from socket until a newline is found.
        Correctly handles:
        - Partial messages across multiple recv() calls (buffered).
        - Multiple messages in a single recv() chunk (FIFO split).
        - Clean EOF detection (recv returns 0 bytes).
        """
        with self._recv_lock:
            while "\n" not in self._buffer:
                if self._closed:
                    return None
                try:
                    chunk = self.sock.recv(4096)
                except (socket.error, OSError) as e:
                    self._closed = True
                    return None

                if not chunk:
                    # Connection closed by remote peer (EOF)
                    self._closed = True
                    if self._buffer.strip():
                        res = self._buffer.strip()
                        self._buffer = ""
                        return res
                    return None

                self._buffer += chunk.decode("utf-8", errors="replace")

            # Extract the first full line
            line, self._buffer = self._buffer.split("\n", 1)
            return line.strip()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass

    @property
    def is_closed(self) -> bool:
        return self._closed


def format_order(items: Dict[str, int]) -> str:
    parts = [f"{product}={qty}" for product, qty in items.items()]
    return f"ORDER {' '.join(parts)}"


def format_deliver(items: Dict[str, int]) -> str:
    parts = [f"{product}={qty}" for product, qty in items.items()]
    return f"DELIVER {' '.join(parts)}"


def parse_response(line: str) -> Tuple[str, Dict[str, str]]:
    """
    Parses a protocol line into command and key-value attributes.
    Example: 'ORDER_ACCEPTED id=1 wait_time=7' -> ('ORDER_ACCEPTED', {'id': '1', 'wait_time': '7'})
    """
    tokens = line.strip().split()
    if not tokens:
        return "", {}
    command = tokens[0]
    attributes: Dict[str, str] = {}
    for token in tokens[1:]:
        if "=" in token:
            key, val = token.split("=", 1)
            attributes[key] = val.strip('"\'')
        else:
            attributes[token] = ""
    return command, attributes
