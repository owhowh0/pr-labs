"""
Generate report figures from benchmark results.
Produces:
- report/images/fig1_task1a.png: Time, speed-up, and memory vs thread count for Task 1a.
- report/images/fig2_task1b.png: Execution time and total numbers counted for Task 1b.
- report/images/fig3_task1c.png: Comparison of Producer-Consumer (1c) vs File Partitioning (1a).
- report/images/fig4_task2.png: Task 2 execution time and peak RAM on USB drive.
"""

import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_graphs(json_path: str = "results.json", out_dir: str = "report/images") -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(json_path, "r") as f:
        data = json.load(f)

    # -------------------------------------------------------------
    # Figure 1: Task 1a (Time, Speed-up, Memory)
    # -------------------------------------------------------------
    t1a = data["task_1a"]
    threads = [x["threads"] for x in t1a]
    avg_times = [x["avg_time"] for x in t1a]
    speedups = [x["speedup"] for x in t1a]
    ram_mb = [x["ram_r1"] for x in t1a]

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(16, 4.5), dpi=300)

    # Subplot 1: Execution Time
    ax1.plot(threads, avg_times, marker="o", color="#1f77b4", linewidth=2, markersize=6, label="Execution Time")
    ax1.set_xscale("log", base=2)
    ax1.set_xticks(threads)
    ax1.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax1.set_xlabel("Number of Threads", fontweight="bold")
    ax1.set_ylabel("Execution Time (ms)", fontweight="bold")
    ax1.set_title("Task 1a: Execution Time vs Threads", fontweight="bold", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.6)
    ax1.axvline(x=4, color="gray", linestyle=":", label="4 Physical Cores")
    ax1.legend(loc="upper right", frameon=True)

    # Subplot 2: Parallel Speed-up
    ideal_speedup = [min(t, 4) for t in threads]
    ax2.plot(threads, speedups, marker="s", color="#2ca02c", linewidth=2, markersize=6, label="Measured Speed-up")
    ax2.plot(threads, ideal_speedup, linestyle="--", color="gray", alpha=0.7, label="Ideal (up to 4 cores)")
    ax2.set_xscale("log", base=2)
    ax2.set_xticks(threads)
    ax2.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax2.set_xlabel("Number of Threads", fontweight="bold")
    ax2.set_ylabel("Speed-up Factor", fontweight="bold")
    ax2.set_title("Task 1a: Speed-up vs Threads", fontweight="bold", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.6)
    ax2.axvline(x=4, color="gray", linestyle=":", label="4 Physical Cores")
    ax2.legend(loc="upper left", frameon=True)

    # Subplot 3: Peak RAM
    ax3.plot(threads, ram_mb, marker="^", color="#d62728", linewidth=2, markersize=6, label="Peak RSS")
    ax3.set_xscale("log", base=2)
    ax3.set_xticks(threads)
    ax3.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax3.set_xlabel("Number of Threads", fontweight="bold")
    ax3.set_ylabel("Peak RAM (MB)", fontweight="bold")
    ax3.set_title("Task 1a: Peak Memory vs Threads", fontweight="bold", fontsize=11)
    ax3.grid(True, linestyle="--", alpha=0.6)
    ax3.set_ylim(0, max(ram_mb) * 1.4)
    ax3.legend(loc="upper left", frameon=True)

    plt.tight_layout()
    fig1_path = os.path.join(out_dir, "fig1_task1a.png")
    fig.savefig(fig1_path)
    plt.close(fig)
    print(f"Saved Figure 1 to: {fig1_path}")

    # -------------------------------------------------------------
    # Figure 2: Task 1b (Execution Time & Totals)
    # -------------------------------------------------------------
    t1b = data["task_1b"]
    v1_avg_time = sum(r["time_ms"] for r in t1b["v1_runs"]) / len(t1b["v1_runs"])
    v2_time = t1b["v2"]["time_ms"]
    v3_time = t1b["v3"]["time_ms"]

    v1_avg_total = sum(r["total"] for r in t1b["v1_runs"]) / len(t1b["v1_runs"])
    v2_total = t1b["v2"]["total"]
    v3_total = t1b["v3"]["total"]

    fig, (bx1, bx2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)

    approaches = ["V1: Unsync\n(Race Condition)", "V2: Lock\n(Mutex)", "V3: Thread-local\n(Separate Counters)"]
    times = [v1_avg_time, v2_time, v3_time]
    colors = ["#ff7f0e", "#d62728", "#2ca02c"]

    # Subplot 1: Execution Time
    bars = bx1.bar(approaches, times, color=colors, width=0.55, edgecolor="black", linewidth=0.8)
    bx1.set_ylabel("Execution Time (ms)", fontweight="bold")
    bx1.set_title("Task 1b: Execution Time Comparison", fontweight="bold", fontsize=11)
    bx1.grid(True, axis="y", linestyle="--", alpha=0.6)
    for bar in bars:
        h = bar.get_height()
        bx1.annotate(f"{h:.1f} ms",
                     xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontweight="bold")

    # Subplot 2: Total Numbers Counted
    totals = [v1_avg_total / 1e6, v2_total / 1e6, v3_total / 1e6]
    bars2 = bx2.bar(approaches, totals, color=colors, width=0.55, edgecolor="black", linewidth=0.8)
    bx2.axhline(y=50.0, color="blue", linestyle="--", alpha=0.7, label="Expected (50.0M)")
    bx2.set_ylabel("Total Counted (Millions)", fontweight="bold")
    bx2.set_title("Task 1b: Counts Accuracy & Race Conditions", fontweight="bold", fontsize=11)
    bx2.set_ylim(0, 60.0)
    bx2.grid(True, axis="y", linestyle="--", alpha=0.6)
    bx2.legend(loc="lower right", frameon=True)
    for bar in bars2:
        h = bar.get_height()
        bx2.annotate(f"{h:.2f}M",
                     xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 4), textcoords="offset points",
                     ha="center", va="bottom", fontweight="bold")

    plt.tight_layout()
    fig2_path = os.path.join(out_dir, "fig2_task1b.png")
    fig.savefig(fig2_path)
    plt.close(fig)
    print(f"Saved Figure 2 to: {fig2_path}")

    # -------------------------------------------------------------
    # Figure 3: Task 1c vs Task 1a Comparison
    # -------------------------------------------------------------
    if "task_1c" in data:
        t1c = data["task_1c"]
        workers = [x["workers"] for x in t1c]
        t1c_times = [x["time_ms"] for x in t1c]
        t1c_ram = [x["ram_mb"] for x in t1c]

        fig, (cx1, cx2) = plt.subplots(1, 2, figsize=(14, 4.5), dpi=300)

        # Subplot 1: Task 1c vs Task 1a Execution Time
        cx1.plot(threads, avg_times, marker="o", color="#1f77b4", linewidth=2, label="Task 1a: File Partitioning (Direct)")
        cx1.plot(workers, t1c_times, marker="s", color="#e377c2", linewidth=2, label="Task 1c: Producer-Consumer Queue")
        cx1.set_xscale("log", base=2)
        cx1.set_xticks(workers)
        cx1.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        cx1.set_xlabel("Number of Workers / Threads", fontweight="bold")
        cx1.set_ylabel("Execution Time (ms)", fontweight="bold")
        cx1.set_title("Task 1c vs Task 1a: Execution Time Comparison", fontweight="bold", fontsize=11)
        cx1.grid(True, linestyle="--", alpha=0.6)
        cx1.legend(loc="center right", frameon=True)

        # Subplot 2: Task 1c Memory vs Workers
        cx2.plot(workers, t1c_ram, marker="^", color="#17becf", linewidth=2, label="Task 1c Peak RAM")
        cx2.set_xscale("log", base=2)
        cx2.set_xticks(workers)
        cx2.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        cx2.set_xlabel("Number of Workers", fontweight="bold")
        cx2.set_ylabel("Peak RAM (MB)", fontweight="bold")
        cx2.set_title("Task 1c: Peak Memory vs Worker Threads", fontweight="bold", fontsize=11)
        cx2.grid(True, linestyle="--", alpha=0.6)
        cx2.set_ylim(0, max(t1c_ram) * 1.4)
        cx2.legend(loc="upper left", frameon=True)

        plt.tight_layout()
        fig3_path = os.path.join(out_dir, "fig3_task1c.png")
        fig.savefig(fig3_path)
        plt.close(fig)
        print(f"Saved Figure 3 to: {fig3_path}")

    # -------------------------------------------------------------
    # Figure 4: Task 2 (Slow Storage / USB Flash Drive)
    # -------------------------------------------------------------
    if "task_2" in data:
        t2 = data["task_2"]
        t2_threads = [x["threads"] for x in t2]
        t2_times = [x["time_ms"] for x in t2]
        t2_ram = [x["ram_mb"] for x in t2]

        fig, (dx1, dx2) = plt.subplots(1, 2, figsize=(12, 4.5), dpi=300)

        # Subplot 1: Task 2 Execution Time
        bars_t2 = dx1.bar([str(t) for t in t2_threads], t2_times, color="#9467bd", width=0.5, edgecolor="black", linewidth=0.8)
        dx1.set_xlabel("Number of Threads", fontweight="bold")
        dx1.set_ylabel("Execution Time (ms)", fontweight="bold")
        dx1.set_title("Task 2: Execution Time on USB Flash Drive", fontweight="bold", fontsize=11)
        dx1.grid(True, axis="y", linestyle="--", alpha=0.6)
        for b in bars_t2:
            h = b.get_height()
            dx1.annotate(f"{h:.1f} ms",
                         xy=(b.get_x() + b.get_width() / 2, h),
                         xytext=(0, 4), textcoords="offset points",
                         ha="center", va="bottom", fontweight="bold")

        # Subplot 2: Task 2 Peak RAM
        bars_ram = dx2.bar([str(t) for t in t2_threads], t2_ram, color="#bcbd22", width=0.5, edgecolor="black", linewidth=0.8)
        dx2.set_xlabel("Number of Threads", fontweight="bold")
        dx2.set_ylabel("Peak RAM (MB)", fontweight="bold")
        dx2.set_title("Task 2: Linear Memory Scaling with Buffer Concurrency", fontweight="bold", fontsize=11)
        dx2.grid(True, axis="y", linestyle="--", alpha=0.6)
        for b in bars_ram:
            h = b.get_height()
            dx2.annotate(f"{h:.1f} MB",
                         xy=(b.get_x() + b.get_width() / 2, h),
                         xytext=(0, 4), textcoords="offset points",
                         ha="center", va="bottom", fontweight="bold")

        plt.tight_layout()
        fig4_path = os.path.join(out_dir, "fig4_task2.png")
        fig.savefig(fig4_path)
        plt.close(fig)
        print(f"Saved Figure 4 to: {fig4_path}")


if __name__ == "__main__":
    import sys
    jpath = sys.argv[1] if len(sys.argv) > 1 else "results.json"
    odir = sys.argv[2] if len(sys.argv) > 2 else "report/images"
    plot_graphs(jpath, odir)
