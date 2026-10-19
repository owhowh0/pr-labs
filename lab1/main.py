"""
Network Programming - Laboratory Work 1: Concurrency in Practice
Command-line Entry Point

This CLI dispatches subcommands to modular task packages:
  - gen: Generate pseudo-random numbers dataset.
  - 1a: File partitioning and multithreaded sign counting.
  - 1b: In-memory sign counting using 3 synchronization strategies.
  - 1c: Producer-consumer sign counting with bounded queue.
  - split: Split numbers.txt into 8 parts for Task 2.
  - 2: Multi-file sign counting on slow storage (USB).
  - benchmark: Execute full test suite and output JSON report.

Runs under free-threaded Python (GIL disabled) to ensure real OS thread concurrency.
"""

import argparse
import json
import os
import sys

from tasks.generator import generate_numbers_file
from tasks.task1a import run_isolated_1a, run_task_1a_single, run_task_1a_suite
from tasks.task1b import run_task_1b_suite
from tasks.task1c import run_isolated_1c, run_task_1c_single, run_task_1c_suite
from tasks.task2 import split_numbers_file, run_isolated_2, run_task_2_single, run_task_2_suite
from tasks.benchmark import run_full_benchmark


def build_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser and subcommands."""
    parser = argparse.ArgumentParser(
        description="Network Programming Lab 1 - Concurrency in Practice",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command")

    # Command: gen
    p_gen = subparsers.add_parser("gen", help="Generate random numbers dataset")
    p_gen.add_argument("--file", default="numbers.txt", help="Target output file path")
    p_gen.add_argument("--count", type=int, default=50_000_000, help="Total random integers to generate")
    p_gen.add_argument("--workers", type=int, default=4, help="Worker threads for generation")

    # Command: 1a
    p_1a = subparsers.add_parser("1a", help="Run Task 1a: File Partitioning & Counting")
    p_1a.add_argument("--file", default="numbers.txt", help="Input numbers file path")
    p_1a.add_argument("--threads", type=int, default=0, help="Thread count (0 to run full suite 1..64)")

    # Command: 1b
    p_1b = subparsers.add_parser("1b", help="Run Task 1b: 3 Synchronization Strategies")
    p_1b.add_argument("--file", default="numbers.txt", help="Input numbers file path")
    p_1b.add_argument("--threads", type=int, default=os.cpu_count() or 4, help="Thread count")

    # Command: 1c
    p_1c = subparsers.add_parser("1c", help="Run Task 1c: Producer-Consumer Bounded Queue")
    p_1c.add_argument("--file", default="numbers.txt", help="Input numbers file path")
    p_1c.add_argument("--workers", type=int, default=0, help="Worker threads count (0 to run full suite 1..64)")

    # Command: split (for Task 2)
    p_split = subparsers.add_parser("split", help="Split numbers.txt into 8 parts for Task 2")
    p_split.add_argument("--file", default="numbers.txt", help="Input source file")
    p_split.add_argument("--dir", default="/run/media/calin/Ventoy/lab1_files", help="Target directory (e.g., USB drive)")

    # Command: 2
    p_2 = subparsers.add_parser("2", help="Run Task 2: Multi-file Processing on Storage")
    p_2.add_argument("--dir", default="/run/media/calin/Ventoy/lab1_files", help="Directory containing the 8 part files")
    p_2.add_argument("--threads", type=int, default=0, help="Thread count (1, 2, 4, or 0 for full suite)")

    # Command: benchmark
    p_bm = subparsers.add_parser("benchmark", help="Run full benchmark suite and save JSON")
    p_bm.add_argument("--file", default="numbers.txt", help="Input numbers file path")
    p_bm.add_argument("--task2-dir", default=None, help="Directory of 8 files for Task 2 benchmark")
    p_bm.add_argument("--out", default="results.json", help="Output JSON results file")

    # Helper commands for isolated subprocess memory measurement
    p_single_1a = subparsers.add_parser("run_single_1a", help=argparse.SUPPRESS)
    p_single_1a.add_argument("--file", required=True)
    p_single_1a.add_argument("--threads", type=int, required=True)

    p_single_1c = subparsers.add_parser("run_single_1c", help=argparse.SUPPRESS)
    p_single_1c.add_argument("--file", required=True)
    p_single_1c.add_argument("--workers", type=int, required=True)

    p_single_2 = subparsers.add_parser("run_single_2", help=argparse.SUPPRESS)
    p_single_2.add_argument("--dir", required=True)
    p_single_2.add_argument("--threads", type=int, required=True)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "gen":
        generate_numbers_file(args.file, args.count, args.workers)

    elif args.command == "run_single_1a":
        res = run_task_1a_single(args.file, args.threads)
        print(json.dumps(res))

    elif args.command == "run_single_1c":
        res = run_task_1c_single(args.file, args.workers)
        print(json.dumps(res))

    elif args.command == "run_single_2":
        res = run_task_2_single(args.dir, args.threads)
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

    elif args.command == "1c":
        if args.workers > 0:
            res = run_isolated_1c(args.file, args.workers)
            print(
                f"Task 1c ({args.workers} workers): {res['time_ms']:.1f} ms | "
                f"Peak RAM: {res['peak_ram_mb']:.1f} MB | "
                f"Neg: {res['neg']:,}, Pos: {res['pos']:,}, Zero: {res['zero']:,}, Total: {res['total']:,}"
            )
        else:
            run_task_1c_suite(args.file)

    elif args.command == "split":
        split_numbers_file(args.file, args.dir)

    elif args.command == "2":
        if args.threads > 0:
            res = run_isolated_2(args.dir, args.threads)
            print(
                f"Task 2 ({args.threads} threads): {res['time_ms']:.1f} ms | "
                f"Peak RAM: {res['peak_ram_mb']:.1f} MB | "
                f"Neg: {res['neg']:,}, Pos: {res['pos']:,}, Zero: {res['zero']:,}, Total: {res['total']:,}"
            )
        else:
            run_task_2_suite(args.dir)

    elif args.command == "benchmark":
        run_full_benchmark(args.file, args.out, task2_dir=args.task2_dir)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
