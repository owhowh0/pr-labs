"""
Memory and runtime profiling utilities for concurrency benchmarks.
"""

import resource


def get_peak_memory_mb() -> float:
    """
    Return peak resident set size (RSS) in megabytes (MB) for the current process.

    On Linux, getrusage().ru_maxrss is reported in kilobytes.
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024.0
