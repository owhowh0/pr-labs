# Network Programming — Laboratory Work 1: Concurrency in Practice

This repository contains the laboratory works for the **Network Programming (PR)** course at the **Technical University of Moldova (UTM)**, Faculty of Computers, Informatics and Microelectronics (FCIM).

- **Student:** Ilie Covali
- **Group:** FAF-243
- **Verified by:** asist. univ. Cristofor Fistic

---

## Laboratory Work 1: Concurrency in Practice

This project explores multithreaded concurrency in Python with the **Global Interpreter Lock (GIL) disabled** using the newly introduced free-threaded CPython 3.13 runtime (`cpython-3.13.16+freethreaded`), managed via `uv`.

### Implemented Tasks

1. **Task 1a: File Partitioning & Counting with Threads (`main.py 1a`)**
   - Partitioning a 50,000,000 random integer file (`numbers.txt`, ~352 MB) into $T$ parts ($T \in \{1, 2, 4, 8, 16, 32, 64\}$).
   - Each thread seeks to its nominal byte offset and uses preceding-byte boundary inspection (`prev_char == b'\n'`) so that lines spanning boundaries are never double counted or skipped.
   - Measures execution time and peak resident memory (RSS).
   - Evaluates parallel speed-up across hardware cores and shows plateau/overhead beyond physical cores.

2. **Task 1b: Three Synchronization Strategies (`main.py 1b`)**
   - Preloads all 50,000,000 numbers into a contiguous 32-bit integer array (`array.array('i')`, ~191 MB).
   - Evaluates 3 synchronization approaches across 4 logical threads (matching CPU core count):
     - **Version 1 (Unsynchronized Shared Counters):** Demonstrates real data races and non-deterministic lost updates (loses ~23% of increments) under free-threaded Python.
     - **Version 2 (Lock-Protected Counters):** Mutual exclusion via `threading.Lock()` guarantees correctness but suffers an ~8x slowdown due to heavy lock contention.
     - **Version 3 (Thread-Local Counters):** Separate local variables per thread aggregated after join; achieves maximum speed-up and 100% correctness.

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
│   ├── main.py                  # CLI implementation for Tasks 1a, 1b, and generator
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
