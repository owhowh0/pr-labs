"""
Task 1a: Direct File Partitioning and Multithreaded Sign Counting

Goal:
Measure parallel execution time, speed-up factor, and peak resident memory (RSS)
when counting negative, positive, and zero integers in a large file across
various thread counts (1, 2, 4, 8, 16, 32, 64).

Boundary Handling Algorithm:
When a file is sliced into equal byte ranges, byte boundaries almost never align
with newline boundaries. To guarantee that no number is counted twice or skipped:
  1. If a worker starts at byte 0, it reads from the beginning.
  2. For workers starting at byte > 0, the worker inspects the preceding byte
     (start_byte - 1). If that byte was '\\n', the worker starts exactly at start_byte.
     Otherwise, it reads and discards the remainder of the current line (which the
     previous worker will process to completion), advancing its start position.
  3. The worker stops reading once its file pointer reaches or exceeds end_byte.
"""

import json
import os
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from tasks.utils import get_peak_memory_mb


def _worker_1a(
    filepath: str,
    start_byte: int,
    end_byte: int,
    is_first: bool,
    is_last: bool,
    results: List[Tuple[int, int, int]],
    idx: int,
) -> None:
    """Worker thread that processes a single byte chunk of the numbers file."""
    neg = 0
    pos = 0
    zero = 0

    with open(filepath, "rb") as f:
        if not is_first:
            # Check byte immediately before start_byte to inspect boundary alignment
            f.seek(start_byte - 1)
            prev_b = f.read(1)
            if prev_b == b"\n":
                curr_pos = start_byte
            else:
                # Discard the partial line; the preceding thread will read it
                discarded = f.readline()
                curr_pos = start_byte + len(discarded)
        else:
            curr_pos = 0

        if is_last:
            while line := f.readline():
                if line[0] == 45:  # ASCII for '-'
                    neg += 1
                elif line == b"0\n" or line == b"0\r\n":
                    zero += 1
                else:
                    pos += 1
        else:
            while curr_pos < end_byte:
                line = f.readline()
                if not line:
                    break
                curr_pos += len(line)
                if line[0] == 45:  # ASCII for '-'
                    neg += 1
                elif line == b"0\n" or line == b"0\r\n":
                    zero += 1
                else:
                    pos += 1

    results[idx] = (neg, pos, zero)


def run_task_1a_single(filepath: str, num_threads: int) -> Dict[str, float]:
    """
    Execute Task 1a for a specified number of threads in the current process.

    Returns a dictionary containing duration (ms), peak RAM (MB), and sign counts.
    """
    file_size = os.path.getsize(filepath)
    results: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_threads
    threads = []

    t0 = time.perf_counter()

    for i in range(num_threads):
        start_b = i * file_size // num_threads
        end_b = (i + 1) * file_size // num_threads if i < num_threads - 1 else file_size
        t = threading.Thread(
            target=_worker_1a,
            args=(filepath, start_b, end_b, i == 0, i == num_threads - 1, results, i),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000.0
    peak_mem_mb = get_peak_memory_mb()

    total_neg = sum(r[0] for r in results)
    total_pos = sum(r[1] for r in results)
    total_zero = sum(r[2] for r in results)
    total_all = total_neg + total_pos + total_zero

    return {
        "threads": num_threads,
        "time_ms": duration_ms,
        "peak_ram_mb": peak_mem_mb,
        "neg": total_neg,
        "pos": total_pos,
        "zero": total_zero,
        "total": total_all,
    }


def run_isolated_1a(filepath: str, threads: int, entry_script: Optional[str] = None) -> Dict[str, float]:
    """
    Run Task 1a in an isolated subprocess to measure true peak resident memory (RSS)
    without residual memory allocation from previous benchmark passes.
    """
    if entry_script is None:
        parent_main = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        if os.path.exists(parent_main):
            entry_script = parent_main
        else:
            entry_script = os.path.abspath(__file__)

    cmd = [
        sys.executable,
        entry_script,
        "run_single_1a",
        "--file",
        filepath,
        "--threads",
        str(threads),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    line = res.stdout.strip().splitlines()[-1]
    return json.loads(line)


def run_task_1a_suite(
    filepath: str,
    thread_counts: Optional[List[int]] = None,
    entry_script: Optional[str] = None,
) -> List[Dict]:
    """
    Run the full Task 1a benchmark suite across specified thread counts
    (default: 1, 2, 4, 8, 16, 32, 64) and compute speed-up factors.
    """
    if thread_counts is None:
        thread_counts = [1, 2, 4, 8, 16, 32, 64]

    print("\n" + "=" * 70)
    print("TASK 1a: COUNTING WITH THREADS (1, 2, 4, 8, 16, 32, 64)")
    print("=" * 70)

    suite_results = []
    base_time = None

    for t in thread_counts:
        # Run 2 passes to get stable measurements
        r1 = run_isolated_1a(filepath, t, entry_script=entry_script)
        r2 = run_isolated_1a(filepath, t, entry_script=entry_script)
        avg_time = (r1["time_ms"] + r2["time_ms"]) / 2.0

        if base_time is None:
            base_time = avg_time
        speedup = base_time / avg_time

        item = {
            "threads": t,
            "time_r1": r1["time_ms"],
            "time_r2": r2["time_ms"],
            "avg_time": avg_time,
            "speedup": speedup,
            "ram_r1": r1["peak_ram_mb"],
            "ram_r2": r2["peak_ram_mb"],
            "neg": r1["neg"],
            "pos": r1["pos"],
            "zero": r1["zero"],
            "total": r1["total"],
        }
        suite_results.append(item)
        print(
            f"Threads: {t:2d} | R1: {r1['time_ms']:7.1f} ms | R2: {r2['time_ms']:7.1f} ms | "
            f"Avg: {avg_time:7.1f} ms | Speed-up: {speedup:5.2f}x | RAM: {r1['peak_ram_mb']:5.1f} MB | "
            f"Total: {r1['total']:,}"
        )

    return suite_results


if __name__ == "__main__":
    # Support direct execution for isolated subprocess benchmarking
    import argparse

    parser = argparse.ArgumentParser(description="Task 1a Subprocess Worker")
    parser.add_argument("cmd", choices=["run_single_1a"])
    parser.add_argument("--file", required=True)
    parser.add_argument("--threads", type=int, required=True)
    args = parser.parse_args()

    if args.cmd == "run_single_1a":
        res = run_task_1a_single(args.file, args.threads)
        print(json.dumps(res))
