# Network Programming — Laboratory Work 1: Concurrency in Practice

This repository contains the laboratory works for the **Network Programming (PR)** course at the **Technical University of Moldova (UTM)**, Faculty of Computers, Informatics and Microelectronics (FCIM).

- **Students:** Poiata Calin, Covali Ilie
- **Group:** FAF-243
- **Verified by:** asist. univ. Cristofor Fistic

---

## Laboratory Work 1: Concurrency in Practice

This project explores multithreaded concurrency in Python with the **Global Interpreter Lock (GIL) disabled** using the newly introduced free-threaded CPython 3.13 runtime (`cpython-3.13t`), managed via `uv`.

### Implemented Tasks

1. **Task 1a: File Partitioning & Counting with Threads (`main.py 1a`)**
   - Partitioning a 50,000,000 random integer file (`numbers.txt`, ~352 MB) into $T$ parts ($T \in \{1, 2, 4, 8, 16, 32, 64\}$).
   - Preceding-byte boundary inspection (`prev_char == b'\n'`) guarantees zero skipped or double-counted lines.
   - Measures execution time and peak resident memory (RSS).

2. **Task 1b: Three Synchronization Strategies (`main.py 1b`)**
   - Preloads all 50,000,000 numbers into a contiguous 32-bit integer array (`array.array('i')`, ~191 MB).
   - Evaluates 3 synchronization approaches across 4 logical threads:
     - **Version 1 (Unsynchronized Shared Counters):** Real data races losing ~23% of updates under free-threaded Python.
     - **Version 2 (Lock-Protected Counters):** Mutual exclusion via `threading.Lock()` guarantees correctness but suffers an ~8x slowdown due to lock contention.
     - **Version 3 (Thread-Local Counters):** Separate local variables per thread aggregated after join; achieves maximum speed-up and 100% correctness.

3. **Task 1c: Producer--Consumer with Bounded Queue (`main.py 1c`)**
   - 1 reader thread (producer) reading batches of 10,000 lines into a bounded `queue.Queue(maxsize=100)`.
   - Evaluated across 1 to 64 worker threads (consumers).
   - Demonstrates producer-bottleneck dynamics and worker idle states.

4. **Task 2: Multi-File Processing on Slow Storage (`main.py split` and `main.py 2`)**
   - Slices `numbers.txt` into 8 files of 6,250,000 numbers each placed on a USB flash drive.
   - Evaluated across 1, 2, and 4 threads reading full files into byte buffers (`f.read()`).
   - Evicts OS page cache before each run using filesystem unmount/remount (`udisksctl`) and `posix_fadvise(POSIX_FADV_DONTNEED)`.
   - Demonstrates negative scaling (slowdown) due to concurrent random seek contention on a single half-duplex USB controller.

3. **Automation & Reporting:**
   - `generate_graphs.py`: Generates publication-quality charts for execution time, speed-up factor, peak RAM, and race condition data losses.
   - `report/`: Full LaTeX report utilizing `labreport.cls` and `titlesec.sty`.

---

## Project Structure

```
.
├── .gitignore
├── lab1/
│   ├── .python-version          # Pinned to 3.13t
│   ├── pyproject.toml           # uv project configuration
│   ├── main.py                  # CLI entry point dispatcher
│   ├── tasks/                   # Modular task implementations
│   │   ├── __init__.py          # Package re-exports
│   │   ├── utils.py             # Memory RSS profiling utilities
│   │   ├── generator.py         # Parallel random numbers generator
│   │   ├── task1a.py            # File partitioning & multithreaded counting
│   │   ├── task1b.py            # 3 synchronization strategies (unsync, lock, local)
│   │   └── benchmark.py         # Suite orchestrator & hardware detection
│   ├── generate_graphs.py       # Matplotlib visualization script
│   ├── results.json             # Benchmark measurements
│   ├── README.md                # Lab documentation
│   └── report/
│       ├── labreport.cls        # Custom UTM lab report document class
│       ├── titlesec.sty         # LaTeX styling dependency
│       ├── report.tex           # LaTeX report source
│       ├── report.pdf           # Compiled lab report (verified by Cristofor Fistic)
│       └── images/
│           ├── fig1_task1a.png  # Task 1a benchmark charts
│           └── fig2_task1b.png  # Task 1b benchmark charts
└── lab2/
    └── .gitkeep                 # Folder structure for subsequent labs
```

---

## How to Set Up and Run

### 1. Requirements & Free-Threaded Python Setup
Install `uv` (if not already installed) and install the free-threaded Python runtime:
```bash
# Install Python 3.13 free-threaded (GIL disabled)
uv python install 3.13t

# Create and activate virtual environment in lab1
cd lab1
uv venv --python 3.13t .venv
source .venv/bin/activate
```

Verify GIL is disabled:
```bash
python3 -c "import sys; print('GIL active:', sys._is_gil_enabled())"
# Output should show: GIL active: False
```

### 2. Generating the Input Dataset
Generate 50,000,000 integers into `numbers.txt` using 4 parallel generator threads:
```bash
python3 main.py gen --file numbers.txt --count 50000000
```

### 3. Running Task 1a
Run with a specific thread count (e.g. 4 threads):
```bash
python3 main.py 1a --file numbers.txt --threads 4
```
Or run the full thread suite (1, 2, 4, 8, 16, 32, 64):
```bash
python3 main.py 1a --file numbers.txt
```

### 4. Running Task 1b
Run all three counting versions across logical cores:
```bash
python3 main.py 1b --file numbers.txt --threads 4
```

### 5. Running Full Benchmark Suite & Generating Graphs
```bash
python3 main.py benchmark --file numbers.txt --out results.json
python3 generate_graphs.py results.json
```

### 6. Compiling the LaTeX Report
```bash
cd report
pdflatex -interaction=nonstopmode report.tex
pdflatex -interaction=nonstopmode report.tex
```
Output report: `lab1/report/report.pdf`.
