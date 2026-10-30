"""
Benchmark Orchestration and Hardware Profiling Module

Coordinates full benchmark runs across Task 1a, 1b, 1c, and Task 2,
collects environment and hardware specifications, and saves results to JSON.
"""

import json
import os
import sys
from typing import Any, Dict, Optional

from tasks.task1a import run_task_1a_suite
from tasks.task1b import run_task_1b_suite
from tasks.task1c import run_task_1c_suite
from tasks.task2 import run_task_2_suite


def get_hardware_info() -> Dict[str, Any]:
    """
    Retrieve hardware and runtime environment metadata.
    """
    cpu_cores = os.cpu_count() or 8
    gil_active = getattr(sys, "_is_gil_enabled", lambda: True)()
    gil_status = "GIL disabled" if not gil_active else "GIL active"

    return {
        "cpu": "AMD Ryzen 7 4700U with Radeon Graphics",
        "physical_cores": 8,
        "logical_processors": cpu_cores,
        "ram_gb": 16.0,
        "os": "Arch Linux (Kernel 7.2.11-arch1-1)",
        "disk": "SAMSUNG MZALQ512HALU-000L1 NVMe SSD 512GB",
        "usb": "Ventoy USB Flash Drive 32GB (USB 3.0)",
        "runtime": f"Python {sys.version.split()[0]} (free-threaded, {gil_status})",
        "gil_enabled": gil_active,
    }


def run_full_benchmark(
    filepath: str,
    out_file: str = "results.json",
    task2_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the entire benchmark suite:
      1. Task 1a: File partitioning across [1, 2, 4, 8, 16, 32, 64] threads
      2. Task 1b: 3 synchronization strategies across logical CPU cores
      3. Task 1c: Producer-consumer queue across [1, 2, 4, 8, 16, 32, 64] workers
      4. Task 2: (Optional if task2_dir provided) multi-file processing across [1, 2, 4] threads
      5. Export compiled benchmark data and system specs to `out_file`
    """
    existing_data: Dict[str, Any] = {}
    if os.path.exists(out_file):
        try:
            with open(out_file, "r") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    cpu_cores = os.cpu_count() or 8
    t1a_results = run_task_1a_suite(filepath)
    t1b_results = run_task_1b_suite(filepath, threads=cpu_cores)
    t1c_results = run_task_1c_suite(filepath)

    benchmark_data: Dict[str, Any] = {
        "task_1a": t1a_results,
        "task_1b": t1b_results,
        "hardware": get_hardware_info(),
        "task_1c": t1c_results,
    }

    if task2_dir and os.path.exists(task2_dir):
        t2_results = run_task_2_suite(task2_dir)
        benchmark_data["task_2"] = t2_results
    elif "task_2" in existing_data:
        benchmark_data["task_2"] = existing_data["task_2"]

    with open(out_file, "w") as f:
        json.dump(benchmark_data, f, indent=2)

    print(f"\nAll benchmark data saved to '{out_file}'.")
    return benchmark_data
