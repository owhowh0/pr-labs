import contextlib
import os
import socket
import subprocess
import sys
import time

GO_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "go"))


def get_free_port() -> int:
    """Finds an unused ephemeral TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_port(host: str, port: int, timeout: float = 5.0) -> bool:
    """Polls until port is accepting connections."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)
    return False


@contextlib.contextmanager
def managed_go_server(port: int = None, verbose: bool = False):
    """
    Context manager that starts the Go server, yields (host, port),
    and terminates it upon exit.
    """
    if port is None:
        port = get_free_port()

    host = "127.0.0.1"
    cmd = ["go", "run", "main.go", "--port", str(port)]
    stdout = None if verbose else subprocess.DEVNULL
    stderr = None if verbose else subprocess.DEVNULL

    proc = subprocess.Popen(cmd, cwd=GO_DIR, stdout=stdout, stderr=stderr)
    try:
        ready = wait_for_port(host, port, timeout=6.0)
        if not ready:
            proc.kill()
            raise RuntimeError(f"Go server failed to start on {host}:{port} within timeout.")

        yield host, port
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
