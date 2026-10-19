"""
Concurrency in Practice - Modular Tasks Package

This package divides the concurrency laboratory work into clear, modular components:
  - `utils`: Process profiling and peak memory measurement.
  - `generator`: Parallel generation of random numbers dataset.
  - `task1a`: Direct file partitioning, boundary inspection, and multithreaded counting.
  - `task1b`: Three synchronization strategies (unsynchronized, mutex lock, thread-local).
  - `task1c`: Producer-consumer architecture with bounded queue.
  - `task2`: Multi-file partitioned processing on slow storage (USB drive).
  - `benchmark`: Orchestration of the full benchmark suite and hardware reporting.
"""

from tasks.utils import get_peak_memory_mb
from tasks.generator import generate_numbers_file
from tasks.task1a import (
    run_task_1a_single,
    run_isolated_1a,
    run_task_1a_suite,
)
from tasks.task1b import (
    run_task_1b_v1,
    run_task_1b_v2,
    run_task_1b_v3,
    run_task_1b_suite,
    load_array_from_file,
)
from tasks.task1c import (
    run_task_1c_single,
    run_isolated_1c,
    run_task_1c_suite,
)
from tasks.task2 import (
    split_numbers_file,
    run_task_2_single,
    run_isolated_2,
    run_task_2_suite,
)
from tasks.benchmark import (
    get_hardware_info,
    run_full_benchmark,
)

__all__ = [
    "get_peak_memory_mb",
    "generate_numbers_file",
    "run_task_1a_single",
    "run_isolated_1a",
    "run_task_1a_suite",
    "run_task_1b_v1",
    "run_task_1b_v2",
    "run_task_1b_v3",
    "run_task_1b_suite",
    "load_array_from_file",
    "run_task_1c_single",
    "run_isolated_1c",
    "run_task_1c_suite",
    "split_numbers_file",
    "run_task_2_single",
    "run_isolated_2",
    "run_task_2_suite",
    "get_hardware_info",
    "run_full_benchmark",
]
