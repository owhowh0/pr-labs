"""
Network Programming - Laboratory Work 1: Concurrency in Practice
Task 1a: Direct File Partitioning and Multithreaded Sign Counting
Task 1b: Three Synchronization Strategies for Sign Counting

Runs under free-threaded Python (GIL disabled) to ensure real OS thread concurrency.
"""

import argparse
import array
import os
import resource
import subprocess
import sys
import threading
import time
from typing import Dict, List, Tuple


def get_peak_memory_mb() -> float:
    """Return peak resident memory (RSS) in MB for current process."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    # ru_maxrss is in kilobytes on Linux
    return usage.ru_maxrss / 1024.0


# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------

def _gen_worker(count: int, seed: int, filepath: str) -> None:
    s = seed
    chunk_size = 50_000
    with open(filepath, "w") as f:
        for _ in range(count // chunk_size):
            buf = []
            for _ in range(chunk_size):
                s = (s * 1103515245 + 12345) & 0x7FFFFFFF
                buf.append(str((s % 2000001) - 1000000))
            f.write("\n".join(buf) + "\n")


def generate_numbers_file(filepath: str, total_count: int = 50_000_000, num_workers: int = 4) -> None:
    """Generate numbers.txt in parallel using multiple worker threads."""
    print(f"Generating {total_count:,} random integers into '{filepath}' using {num_workers} threads...")
    t0 = time.perf_counter()
    part_files = []
    threads = []
    count_per_thread = total_count // num_workers

    for i in range(num_workers):
        part_name = f"{filepath}.part_{i}.tmp"
        part_files.append(part_name)
        t = threading.Thread(
            target=_gen_worker,
            args=(count_per_thread, 42 + i * 10007, part_name),
        )
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Merge parts sequentially
    with open(filepath, "wb") as outfile:
        for p in part_files:
            with open(p, "rb") as infile:
                while chunk := infile.read(4 * 1024 * 1024):
                    outfile.write(chunk)
            try:
                os.remove(p)
            except OSError:
                pass

    t1 = time.perf_counter()
    size_mb = os.path.getsize(filepath) / (1024.0 * 1024.0)
    print(f"Done in {t1 - t0:.2f}s! File size: {size_mb:.2f} MB")


# ---------------------------------------------------------------------------
# Task 1a: File Partitioning & Counting with Threads
# ---------------------------------------------------------------------------

def _worker_1a(
    filepath: str,
    start_byte: int,
    end_byte: int,
    is_first: bool,
    is_last: bool,
    results: List[Tuple[int, int, int]],
    idx: int,
) -> None:
    neg = 0
    pos = 0
    zero = 0

    with open(filepath, "rb") as f:
        if not is_first:
            # Check byte immediately before start_byte to see if boundary is exactly on a newline
            f.seek(start_byte - 1)
            prev_b = f.read(1)
            if prev_b == b"\n":
                curr_pos = start_byte
            else:
                discarded = f.readline()
                curr_pos = start_byte + len(discarded)
        else:
            curr_pos = 0

        if is_last:
            while line := f.readline():
                if line[0] == 45:  # b'-'
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
                if line[0] == 45:
                    neg += 1
                elif line == b"0\n" or line == b"0\r\n":
                    zero += 1
                else:
                    pos += 1

    results[idx] = (neg, pos, zero)


def run_task_1a_single(filepath: str, num_threads: int) -> Dict[str, float]:
    """Execute Task 1a for a given thread count, returning time, memory, and counts."""
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


# ---------------------------------------------------------------------------
# Task 1b: Three Synchronization Strategies
# ---------------------------------------------------------------------------

class _SharedCountersUnsync:
    __slots__ = ("neg", "pos", "zero")

    def __init__(self):
        self.neg = 0
        self.pos = 0
        self.zero = 0


class _SharedCountersLocked:
    __slots__ = ("neg", "pos", "zero", "lock")

    def __init__(self):
        self.neg = 0
        self.pos = 0
        self.zero = 0
        self.lock = threading.Lock()


def _worker_1b_v1(arr: array.array, start_idx: int, end_idx: int, shared: _SharedCountersUnsync) -> None:
    for i in range(start_idx, end_idx):
        val = arr[i]
        if val < 0:
            shared.neg += 1
        elif val > 0:
            shared.pos += 1
        else:
            shared.zero += 1


def _worker_1b_v2(arr: array.array, start_idx: int, end_idx: int, shared: _SharedCountersLocked) -> None:
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
    """Preload numbers into in-memory array.array('i'). Not measured."""
    print(f"Loading '{filepath}' into contiguous memory array.array('i')...")
    t0 = time.perf_counter()
    arr = array.array("i")
    with open(filepath, "r", encoding="utf-8") as f:
        arr.extend(int(line) for line in f)
    t1 = time.perf_counter()
    print(f"Loaded {len(arr):,} integers in {t1 - t0:.2f}s ({len(arr)*4/(1024*1024):.1f} MB array).")
    return arr


def run_task_1b_v1(arr: array.array, num_threads: int) -> Dict[str, float]:
    total_len = len(arr)
    shared = _SharedCountersUnsync()
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
    total_len = len(arr)
    shared = _SharedCountersLocked()
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


# ---------------------------------------------------------------------------
# CLI & Subprocess Isolated Execution
# ---------------------------------------------------------------------------

def run_isolated_1a(filepath: str, threads: int) -> Dict[str, float]:
    """Run Task 1a in an isolated subprocess to get true peak RSS."""
    cmd = [
        sys.executable,
        os.path.abspath(__file__),
        "run_single_1a",
        "--file",
        filepath,
        "--threads",
        str(threads),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    # Output is a single line with JSON or comma separated metrics
    line = res.stdout.strip().splitlines()[-1]
    import json
    return json.loads(line)


def run_task_1a_suite(filepath: str, thread_counts: List[int] = [1, 2, 4, 8, 16, 32, 64]) -> List[Dict]:
    print("\n" + "=" * 70)
    print("TASK 1a: COUNTING WITH THREADS (1, 2, 4, 8, 16, 32, 64)")
    print("=" * 70)
    suite_results = []
    base_time = None

    for t in thread_counts:
        # Run 2 passes to get stable measurements
        r1 = run_isolated_1a(filepath, t)
        r2 = run_isolated_1a(filepath, t)
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


def run_task_1b_suite(filepath: str, threads: int = 4) -> Dict:
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


def main():
    parser = argparse.ArgumentParser(description="Network Programming Lab 1 - Concurrency in Practice")
    subparsers = parser.add_subparsers(dest="command")

    # Command: gen
    p_gen = subparsers.add_parser("gen", help="Generate numbers.txt")
    p_gen.add_argument("--file", default="numbers.txt", help="Target output file path")
    p_gen.add_argument("--count", type=int, default=50_000_000, help="Total random integers to generate")
    p_gen.add_argument("--workers", type=int, default=4, help="Worker threads for generation")

    # Command: 1a
    p_1a = subparsers.add_parser("1a", help="Run Task 1a")
    p_1a.add_argument("--file", default="numbers.txt", help="Input file path")
    p_1a.add_argument("--threads", type=int, default=0, help="Threads (0 for full suite 1..64)")

    # Command: 1b
    p_1b = subparsers.add_parser("1b", help="Run Task 1b")
    p_1b.add_argument("--file", default="numbers.txt", help="Input file path")
    p_1b.add_argument("--threads", type=int, default=os.cpu_count() or 4, help="Threads count")

    # Command: benchmark (runs 1a and 1b suites and saves results to JSON)
    p_bm = subparsers.add_parser("benchmark", help="Run full benchmark suite (1a and 1b) and save JSON")
    p_bm.add_argument("--file", default="numbers.txt", help="Input file path")
    p_bm.add_argument("--out", default="results.json", help="Output JSON results file")

    # Hidden worker command for isolated subprocess memory measurement
    p_single = subparsers.add_parser("run_single_1a")
    p_single.add_argument("--file", required=True)
    p_single.add_argument("--threads", type=int, required=True)

    args = parser.parse_args()

    if args.command == "gen":
        generate_numbers_file(args.file, args.count, args.workers)

    elif args.command == "run_single_1a":
        import json
        res = run_task_1a_single(args.file, args.threads)
        print(json.dumps(res))

    elif args.command == "1a":
        if args.threads > 0:
            res = run_isolated_1a(args.file, args.threads)
            print(
                f"Task 1a ({args.threads} threads): {res['time_ms']:.1f} ms | "
                f"Peak RAM: {res['peak_ram_mb']:.1f} MB | "
                f"Neg: {res['neg']:,}, Pos: {res['pos']:,}, Zero: {res['zero']:,}, Total: {res['total']:,}"
            )
        else:
            run_task_1a_suite(args.file)

    elif args.command == "1b":
        run_task_1b_suite(args.file, args.threads)

    elif args.command == "benchmark":
        import json
        t1a = run_task_1a_suite(args.file)
        t1b = run_task_1b_suite(args.file, os.cpu_count() or 4)
        data = {
            "task_1a": t1a,
            "task_1b": t1b,
            "hardware": {
                "cpu": "AMD Ryzen 3 4300U with Radeon Graphics",
                "physical_cores": 4,
                "logical_processors": 4,
                "ram_gb": 19.4,
                "os": "CachyOS Linux (Kernel 7.2.9-2-cachyos)",
                "disk": "WDC PC SN530 NVMe SSD 256GB",
                "runtime": f"Python {sys.version.split()[0]} (free-threaded, GIL disabled)",
                "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
            },
        }
        with open(args.out, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nAll benchmark data saved to '{args.out}'.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
