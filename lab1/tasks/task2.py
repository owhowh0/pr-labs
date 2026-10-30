"""
Task 2: Many Files on Slow Storage (USB Flash Drive)

Specification:
  - Input: 8 files of 6,250,000 numbers each, split in order from numbers.txt.
  - Storage: Files placed on a USB flash drive (slow external storage).
  - Unit of work: One file per operation.
  - A thread reads a file in a single operation into one byte buffer (`f.read()`),
    parses it, and counts negative, positive, and zero numbers.
  - Files are divided among threads as evenly as possible (e.g. 8 files / T threads).
  - Evaluated across 1, 2, and 4 threads.
  - Goal: Decide whether the workload is CPU-bound or I/O-bound on slow storage.
"""

import glob
import json
import os
import subprocess
import sys
import threading
import time
from typing import Dict, List, Optional, Tuple

from tasks.utils import get_peak_memory_mb


def split_numbers_file(
    source_file: str,
    target_dir: str,
    num_files: int = 8,
    numbers_per_file: int = 6_250_000,
) -> List[str]:
    """
    Split `source_file` (in order) into `num_files` files of `numbers_per_file` lines each.
    Target files are created in `target_dir` as `part_0.txt` ... `part_7.txt`.
    """
    os.makedirs(target_dir, exist_ok=True)
    out_paths = [os.path.join(target_dir, f"part_{i}.txt") for i in range(num_files)]

    print(f"Splitting '{source_file}' into {num_files} files of {numbers_per_file:,} numbers in '{target_dir}'...")
    t0 = time.perf_counter()

    with open(source_file, "rb") as infile:
        for file_idx in range(num_files):
            target_path = out_paths[file_idx]
            count = 0
            with open(target_path, "wb") as outfile:
                while count < numbers_per_file:
                    line = infile.readline()
                    if not line:
                        break
                    outfile.write(line)
                    count += 1
            print(f"  Written {count:,} numbers -> {target_path}")

    t1 = time.perf_counter()
    print(f"Split complete in {t1 - t0:.2f}s!")
    return out_paths


def get_task2_files(target_dir: str) -> List[str]:
    """Retrieve and sort the 8 partition files from the directory."""
    files = sorted(glob.glob(os.path.join(target_dir, "part_*.txt")))
    if not files:
        # Fallback to checking any text files in target_dir if named differently
        files = sorted(glob.glob(os.path.join(target_dir, "*.txt")))
    return files


def _worker_2(file_paths: List[str], results: List[Tuple[int, int, int]], idx: int) -> None:
    """
    Task 2 worker:
    Reads each assigned file in a single operation into one byte buffer (`f.read()`),
    parses the buffer, and counts signs.
    """
    neg = 0
    pos = 0
    zero = 0

    for path in file_paths:
        with open(path, "rb") as f:
            buf = f.read()  # Single operation into one byte buffer

        for line in buf.splitlines():
            if not line:
                continue
            if line[0] == 45:  # ASCII for '-'
                neg += 1
            elif line == b"0":
                zero += 1
            else:
                pos += 1

    results[idx] = (neg, pos, zero)


def run_task_2_single(target_dir: str, num_threads: int) -> Dict[str, float]:
    """
    Execute Task 2 across `num_threads` for files in `target_dir`.
    """
    file_list = get_task2_files(target_dir)
    if not file_list:
        raise FileNotFoundError(f"No part files found in '{target_dir}'. Run 'main.py split' first.")

    total_files = len(file_list)
    results: List[Tuple[int, int, int]] = [(0, 0, 0)] * num_threads
    threads = []

    # Divide files as evenly as possible
    files_per_thread = (total_files + num_threads - 1) // num_threads

    t0 = time.perf_counter()

    for i in range(num_threads):
        chunk_files = file_list[i * files_per_thread : min((i + 1) * files_per_thread, total_files)]
        if not chunk_files:
            continue
        t = threading.Thread(
            target=_worker_2,
            args=(chunk_files, results, i),
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


def run_isolated_2(target_dir: str, threads: int, entry_script: Optional[str] = None) -> Dict[str, float]:
    """
    Run Task 2 in an isolated subprocess for accurate peak RSS profiling.
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
        "run_single_2",
        "--dir",
        target_dir,
        "--threads",
        str(threads),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    line = res.stdout.strip().splitlines()[-1]
    return json.loads(line)


def run_task_2_suite(
    target_dir: str,
    thread_counts: Optional[List[int]] = None,
    entry_script: Optional[str] = None,
) -> List[Dict]:
    """
    Run Task 2 suite across 1, 2, and 4 threads.
    """
    if thread_counts is None:
        thread_counts = [1, 2, 4]

    print("\n" + "=" * 70)
    print(f"TASK 2: FILES ON STORAGE ({target_dir}) - (1, 2, 4 Threads)")
    print("=" * 70)

    suite_results = []
    base_time = None

    for t in thread_counts:
        r = run_isolated_2(target_dir, t, entry_script=entry_script)
        if base_time is None:
            base_time = r["time_ms"]
        speedup = base_time / r["time_ms"] if r["time_ms"] > 0 else 1.0

        item = {
            "threads": t,
            "time_ms": r["time_ms"],
            "speedup": speedup,
            "ram_mb": r["peak_ram_mb"],
            "neg": r["neg"],
            "pos": r["pos"],
            "zero": r["zero"],
            "total": r["total"],
        }
        suite_results.append(item)
        print(
            f"Threads: {t:2d} | Time: {r['time_ms']:7.1f} ms | Speed-up: {speedup:5.2f}x | "
            f"RAM: {r['peak_ram_mb']:5.1f} MB | Total: {r['total']:,}"
        )

    return suite_results


if __name__ == "__main__":
    # Support direct execution for isolated subprocess benchmarking
    import argparse

    parser = argparse.ArgumentParser(description="Task 2 Subprocess Worker")
    parser.add_argument("cmd", choices=["run_single_2"])
    parser.add_argument("--dir", required=True)
    parser.add_argument("--threads", type=int, required=True)
    args = parser.parse_args()

    if args.cmd == "run_single_2":
        res = run_task_2_single(args.dir, args.threads)
        print(json.dumps(res))
