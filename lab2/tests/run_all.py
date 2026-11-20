import argparse
import sys
import time

from server_manager import managed_go_server
from test_client_flow import test_client_flow
from test_provider_flow import test_provider_flow
from test_cross_cancellation import test_cross_cancellation
from test_cross_fuzz import test_cross_fuzz
from test_cross_race import test_cross_race


def run_all(port: int = None):
    print("==================================================================")
    print("  Lab 2: Full Integration Test Suite (Go Server + Python Clients)")
    print("==================================================================")

    start_time = time.time()
    with managed_go_server(port=port) as (host, server_port):
        print(f"[*] Booted Go Server at {host}:{server_port}")

        # 1. Basic Client Flow
        test_client_flow(host, server_port)

        # 2. Provider Restock & Low Stock Alert Flow
        test_provider_flow(host, server_port)

        # 3. Disconnect Cancellation & Rollback (Task 4)
        test_cross_cancellation(host, server_port)

        # 4. Robustness Fuzzer (Task 4)
        test_cross_fuzz(host, server_port)

        # 5. High-Concurrency Race Condition (Task 2)
        test_cross_race(host, server_port)

    elapsed = time.time() - start_time
    print("\n==================================================================")
    print(f"\033[92;1m  ALL CROSS-LANGUAGE INTEGRATION TESTS PASSED in {elapsed:.2f}s!\033[0m")
    print("==================================================================")


def main():
    parser = argparse.ArgumentParser(description="Run all Go Server + Python Client Integration Tests")
    parser.add_argument("--port", type=int, default=None, help="Custom port for Go server (default: random ephemeral)")
    args = parser.parse_args()

    try:
        run_all(port=args.port)
    except AssertionError as e:
        print(f"\n\033[91;1m[TEST FAILURE] {e}\033[0m")
        sys.exit(1)
    except Exception as e:
        print(f"\n\033[91;1m[ERROR] {e}\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()
