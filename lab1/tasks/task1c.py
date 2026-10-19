"""
Task 1c: Producer-Consumer Model with Bounded Queue

Specification:
  - One reader thread (producer) reads `numbers.txt` line by line.
  - Bundles lines into batches of 10,000 lines.
  - Pushes batches into a thread-safe blocking queue of maxsize=100.
  - When the queue is full (100 batches), the reader waits.
  - Consumer worker threads repeatedly pop batches from the queue and count signs.
  - When empty, worker threads wait.
  - At EOF, reader signals termination (sentinels), and workers stop once queue is empty.
  - Evaluated across 1, 2, 4, 8, 16, 32, and 64 worker threads.
"""

import json
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from tasks.utils import get_peak_memory_mb


def _reader_producer(filepath: str, q: queue.Queue, batch_size: int, num_workers: int) -> None:
    """
    Producer thread:
    Reads file line by line in binary mode, groups lines into batches of `batch_size`,
    and puts them into the thread-safe bounded queue.
    Puts `None` sentinels for each worker when EOF is reached.
    """
    batch = []
    with open(filepath, "rb") as f:
        for line in f:
            batch.append(line)
            if len(batch) >= batch_size:
                q.put(batch)
                batch = []

    if batch:
        q.put(batch)

    # Send termination sentinel for each worker
    for _ in range(num_workers):
        q.put(None)


def _worker_consumer(
    q: queue.Queue,
    results: List[Tuple[int, int, int]],
    worker_idx: int,
) -> None:
    """
    Consumer thread:
    Pops batches from queue, parses lines, and maintains thread-local sign counters.
    """
    neg = 0
    pos = 0
    zero = 0

    while True:
        batch = q.get()
        if batch is None:
            break

        for line in batch:
            if line[0] == 45:  # ASCII for '-'
                neg += 1
            elif line == b"0\n" or line == b"0\r\n":
                zero += 1
            else:
                pos += 1

    results[worker_idx] = (neg, pos, zero)


def run_task_1c_single(
    filepath: str,
    num_workers: int,
    batch_size: int = 10_000,
    queue_capacity: int = 100,
) -> Dict[str, float]:
    """
    Execute Task 1c with 1 reader producer and `num_workers` consumer threads.
    """
    q: queue.Queue = queue.Queue(maxsize=queue_capacity)
    results: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_workers
    worker_threads = []

    t0 = time.perf_counter()

    # Start consumer threads
    for i in range(num_workers):
        t = threading.Thread(
            target=_worker_consumer,
            args=(q, results, i),
        )
        worker_threads.append(t)
        t.start()

    # Start producer thread
    reader_thread = threading.Thread(
        target=_reader_producer,
        args=(filepath, q, batch_size, num_workers),
    )
    reader_thread.start()

    # Wait for producer and all consumers
    reader_thread.join()
    for t in worker_threads:
        t.join()

    t1 = time.perf_counter()
    duration_ms = (t1 - t0) * 1000.0
    peak_mem_mb = get_peak_memory_mb()

    total_neg = sum(r[0] for r in results)
    total_pos = sum(r[1] for r in results)
    total_zero = sum(r[2] for r in results)
    total_all = total_neg + total_pos + total_zero

    return {
        "workers": num_workers,
        "time_ms": duration_ms,
        "peak_ram_mb": peak_mem_mb,
        "neg": total_neg,
        "pos": total_pos,
        "zero": total_zero,
        "total": total_all,
    }


def run_isolated_1c(filepath: str, workers: int, entry_script: Optional[str] = None) -> Dict[str, float]:
    """
    Run Task 1c in an isolated subprocess to measure true peak resident memory (RSS).
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
        "run_single_1c",
        "--file",
        filepath,
        "--workers",
        str(workers),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    line = res.stdout.strip().splitlines()[-1]
    return json.loads(line)


def run_task_1c_suite(
    filepath: str,
    worker_counts: Optional[List[int]] = None,
    entry_script: Optional[str] = None,
) -> List[Dict]:
    """
    Run the full Task 1c benchmark suite across specified worker counts
    (default: 1, 2, 4, 8, 16, 32, 64) and compute speed-up factors.
    """
    if worker_counts is None:
        worker_counts = [1, 2, 4, 8, 16, 32, 64]

    print("\n" + "=" * 70)
    print("TASK 1c: PRODUCER-CONSUMER QUEUE (1, 2, 4, 8, 16, 32, 64 Workers)")
    print("=" * 70)

    suite_results = []
    base_time = None

    for w in worker_counts:
        # Run 2 passes to get stable measurements
        r1 = run_isolated_1c(filepath, w, entry_script=entry_script)
        r2 = run_isolated_1c(filepath, w, entry_script=entry_script)
        avg_time = (r1["time_ms"] + r2["time_ms"]) / 2.0

        if base_time is None:
            base_time = avg_time
        speedup = base_time / avg_time

        item = {
            "workers": w,
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
            f"Workers: {w:2d} | R1: {r1['time_ms']:7.1f} ms | R2: {r2['time_ms']:7.1f} ms | "
            f"Avg: {avg_time:7.1f} ms | Speed-up: {speedup:5.2f}x | RAM: {r1['peak_ram_mb']:5.1f} MB | "
            f"Total: {r1['total']:,}"
        )

    return suite_results


if __name__ == "__main__":
    # Support direct execution for isolated subprocess benchmarking
    import argparse

    parser = argparse.ArgumentParser(description="Task 1c Subprocess Worker")
    parser.add_argument("cmd", choices=["run_single_1c"])
    parser.add_argument("--file", required=True)
    parser.add_argument("--workers", type=int, required=True)
    args = parser.parse_args()

    if args.cmd == "run_single_1c":
        res = run_task_1c_single(args.file, args.workers)
        print(json.dumps(res))
