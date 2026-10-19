"""
Task 1b: Three Synchronization Strategies for Sign Counting

Goal:
Preload all integers into contiguous in-memory array (`array.array('i')`) and evaluate
three synchronization strategies across logical CPU cores:

  1. Version 1 (Unsynchronized Shared Counters):
     Multiple threads increment the exact same attributes (`neg`, `pos`, `zero`)
     without synchronization. Under free-threaded Python, this produces genuine
     data races (lost updates) because `count += 1` is not atomic.

  2. Version 2 (Shared Counters Protected by Mutex Lock):
     Every single counter increment is wrapped in `with lock:`. Guarantees 100%
     correctness, but suffers severe lock contention overhead (waiting in queue).

  3. Version 3 (Thread-Local Counters):
     Each thread increments its own private local counters. When all threads join,
     the parent aggregates the totals. Maximum speed-up and zero synchronization overhead.
"""

import array
import threading
import time
from typing import Dict, List, Tuple

from tasks.utils import get_peak_memory_mb


class SharedCountersUnsync:
    """Unprotected shared counters to observe race conditions and lost updates."""
    __slots__ = ("neg", "pos", "zero")

    def __init__(self):
        self.neg = 0
        self.pos = 0
        self.zero = 0


class SharedCountersLocked:
    """Shared counters protected by a standard mutex lock (`threading.Lock`)."""
    __slots__ = ("neg", "pos", "zero", "lock")

    def __init__(self):
        self.neg = 0
        self.pos = 0
        self.zero = 0
        self.lock = threading.Lock()


def _worker_1b_v1(arr: array.array, start_idx: int, end_idx: int, shared: SharedCountersUnsync) -> None:
    """Worker for V1: increments shared counter without any synchronization."""
    for i in range(start_idx, end_idx):
        val = arr[i]
        if val < 0:
            shared.neg += 1
        elif val > 0:
            shared.pos += 1
        else:
            shared.zero += 1


def _worker_1b_v2(arr: array.array, start_idx: int, end_idx: int, shared: SharedCountersLocked) -> None:
    """Worker for V2: acquires mutex lock on every single increment."""
    lock = shared.lock
    for i in range(start_idx, end_idx):
        val = arr[i]
        if val < 0:
            with lock:
                shared.neg += 1
        elif val > 0:
            with lock:
                shared.pos += 1
        else:
            with lock:
                shared.zero += 1


def _worker_1b_v3(
    arr: array.array,
    start_idx: int,
    end_idx: int,
    results: List[Tuple[int, int, int]],
    idx: int,
) -> None:
    """Worker for V3: uses private thread-local counters, saving result at the end."""
    neg = 0
    pos = 0
    zero = 0
    for i in range(start_idx, end_idx):
        val = arr[i]
        if val < 0:
            neg += 1
        elif val > 0:
            pos += 1
        else:
            zero += 1
    results[idx] = (neg, pos, zero)


def load_array_from_file(filepath: str) -> array.array:
    """
    Preload all integers from file into a contiguous 32-bit signed integer array.
    This time is not measured as part of the benchmark.
    """
    print(f"Loading '{filepath}' into contiguous memory array.array('i')...")
    t0 = time.perf_counter()
    arr = array.array("i")
    with open(filepath, "r", encoding="utf-8") as f:
        arr.extend(int(line) for line in f)
    t1 = time.perf_counter()
    size_mb = (len(arr) * 4) / (1024.0 * 1024.0)
    print(f"Loaded {len(arr):,} integers in {t1 - t0:.2f}s ({size_mb:.1f} MB array).")
    return arr


def run_task_1b_v1(arr: array.array, num_threads: int) -> Dict[str, float]:
    """Execute Version 1: Unsynchronized shared counters."""
    total_len = len(arr)
    shared = SharedCountersUnsync()
    threads = []
    chunk = total_len // num_threads

    t0 = time.perf_counter()
    for i in range(num_threads):
        s = i * chunk
        e = total_len if i == num_threads - 1 else (i + 1) * chunk
        t = threading.Thread(target=_worker_1b_v1, args=(arr, s, e, shared))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    t1 = time.perf_counter()

    tot = shared.neg + shared.pos + shared.zero
    return {
        "time_ms": (t1 - t0) * 1000.0,
        "neg": shared.neg,
        "pos": shared.pos,
        "zero": shared.zero,
        "total": tot,
        "correct": tot == total_len,
    }


def run_task_1b_v2(arr: array.array, num_threads: int) -> Dict[str, float]:
    """Execute Version 2: Shared counters protected by mutex lock."""
    total_len = len(arr)
    shared = SharedCountersLocked()
    threads = []
    chunk = total_len // num_threads

    t0 = time.perf_counter()
    for i in range(num_threads):
        s = i * chunk
        e = total_len if i == num_threads - 1 else (i + 1) * chunk
        t = threading.Thread(target=_worker_1b_v2, args=(arr, s, e, shared))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    t1 = time.perf_counter()

    tot = shared.neg + shared.pos + shared.zero
    return {
        "time_ms": (t1 - t0) * 1000.0,
        "neg": shared.neg,
        "pos": shared.pos,
        "zero": shared.zero,
        "total": tot,
        "correct": tot == total_len,
    }


def run_task_1b_v3(arr: array.array, num_threads: int) -> Dict[str, float]:
    """Execute Version 3: Thread-local counters aggregated after join."""
    total_len = len(arr)
    results: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_threads
    threads = []
    chunk = total_len // num_threads

    t0 = time.perf_counter()
    for i in range(num_threads):
        s = i * chunk
        e = total_len if i == num_threads - 1 else (i + 1) * chunk
        t = threading.Thread(target=_worker_1b_v3, args=(arr, s, e, results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()
    t1 = time.perf_counter()

    total_neg = sum(r[0] for r in results)
    total_pos = sum(r[1] for r in results)
    total_zero = sum(r[2] for r in results)
    tot = total_neg + total_pos + total_zero

    return {
        "time_ms": (t1 - t0) * 1000.0,
        "neg": total_neg,
        "pos": total_pos,
        "zero": total_zero,
        "total": tot,
        "correct": tot == total_len,
    }


def run_task_1b_suite(filepath: str, threads: int = 4) -> Dict:
    """
    Run Task 1b across the three synchronization approaches and display results.
    Version 1 is executed 3 times to observe non-deterministic lost update rates.
    """
    print("\n" + "=" * 70)
    print(f"TASK 1b: THREE WAYS TO COUNT ({threads} Threads = Logical Cores)")
    print("=" * 70)

    arr = load_array_from_file(filepath)
    peak_mem_mb = get_peak_memory_mb()

    # Version 1 (Unsync): run 3 times
    v1_runs = []
    for run_idx in range(1, 4):
        res_v1 = run_task_1b_v1(arr, threads)
        v1_runs.append(res_v1)
        print(f"V1 (Unsync) Run {run_idx}: {res_v1['time_ms']:7.1f} ms | Counted: {res_v1['total']:,} | Correct: {res_v1['correct']}")

    # Version 2 (Lock)
    res_v2 = run_task_1b_v2(arr, threads)
    print(f"V2 (Lock)   Run 1: {res_v2['time_ms']:7.1f} ms | Counted: {res_v2['total']:,} | Correct: {res_v2['correct']}")

    # Version 3 (Thread-local)
    res_v3 = run_task_1b_v3(arr, threads)
    print(f"V3 (Local)  Run 1: {res_v3['time_ms']:7.1f} ms | Counted: {res_v3['total']:,} | Correct: {res_v3['correct']}")

    return {
        "v1_runs": v1_runs,
        "v2": res_v2,
        "v3": res_v3,
        "peak_ram_mb": peak_mem_mb,
    }
