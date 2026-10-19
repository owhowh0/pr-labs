"""
Dataset Generation Module

Generates a large dataset of pseudo-random integers within [-1_000_000, 1_000_000]
written one integer per line.

Uses multiple threads writing independent temporary chunks in parallel,
which are then merged into the final numbers file.
"""

import os
import threading
import time


def _gen_worker(count: int, seed: int, filepath: str) -> None:
    """
    Generate `count` random integers using a fast Linear Congruential Generator (LCG)
    and write them in batches to `filepath`.
    """
    s = seed
    chunk_size = 50_000
    with open(filepath, "w") as f:
        for _ in range(count // chunk_size):
            buf = []
            for _ in range(chunk_size):
                # Standard POSIX lrand48-like LCG formula
                s = (s * 1103515245 + 12345) & 0x7FFFFFFF
                buf.append(str((s % 2000001) - 1000000))
            f.write("\n".join(buf) + "\n")


def generate_numbers_file(filepath: str, total_count: int = 50_000_000, num_workers: int = 4) -> None:
    """
    Generate `total_count` random integers into `filepath` using `num_workers` threads.

    Each worker produces an equal chunk in a temporary file. When all workers finish,
    the chunks are concatenated into the target file in binary mode for optimal speed.
    """
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

    # Merge parts sequentially into final file
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
