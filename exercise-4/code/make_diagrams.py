"""Regenerate every Exercise-4 figure into ../diagrams.

    python code/make_diagrams.py

All numbers are read from the experiment functions themselves, never
hard-coded, so the figures cannot drift away from ``output/experiments.json``.
Figure labels are in Latin script on purpose: the Persian report uses the same
images, and Vazirmatn is not registered with matplotlib here.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import matplotlib                                        # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                          # noqa: E402

import sync_algorithms as sa                             # noqa: E402
import sync_model as sm                                  # noqa: E402

DIA = os.path.join(ROOT, "diagrams")
os.makedirs(DIA, exist_ok=True)

BLUE = "#2f6fb3"
ORANGE = "#d9812b"
GREEN = "#3f8f5f"
RED = "#b5372f"
GREY = "#8a8a8a"


def _save(fig, name):
    path = os.path.join(DIA, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path)


def _load_results():
    return sm.check_all()


# --------------------------------------------------------------- state spaces
def fig_state_spaces(res):
    names = list(res)
    states = [res[n]["states"] for n in names]
    trans = [res[n]["transitions"] for n in names]
    x = range(len(names))
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.bar([i - 0.2 for i in x], states, width=0.4, color=BLUE,
           label="reachable states")
    ax.bar([i + 0.2 for i in x], trans, width=0.4, color=ORANGE,
           label="transitions")
    for i, (s, t) in enumerate(zip(states, trans)):
        ax.text(i - 0.2, s + 6, str(s), ha="center", fontsize=7)
        ax.text(i + 0.2, t + 6, str(t), ha="center", fontsize=7)
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=28, ha="right", fontsize=8)
    ax.set_ylabel("count")
    ax.set_title("Exhaustive state spaces: every interleaving is enumerated")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "fig_state_spaces.png")


# ------------------------------------------------------------ property matrix
def fig_property_matrix(res):
    names = list(res)
    props = ["mutual\nexclusion", "deadlock\nfree", "starvation\nfree"]
    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.set_xlim(0, len(props))
    ax.set_ylim(0, len(names))
    for r, name in enumerate(names):
        for c, p in enumerate(props):
            ok = res[name][{"mutual\nexclusion": "mutual_exclusion",
                            "deadlock\nfree": "deadlock_free",
                            "starvation\nfree": "starvation_free"}[p]]
            if p == "starvation\nfree":
                ok = all(ok.values())
            ax.add_patch(plt.Rectangle((c, len(names) - 1 - r), 1, 1,
                                       facecolor=GREEN if ok else RED,
                                       edgecolor="white"))
            ax.text(c + 0.5, len(names) - 1 - r + 0.5,
                    "yes" if ok else "NO", ha="center", va="center",
                    color="white", fontsize=10, fontweight="bold")
    ax.set_xticks([i + 0.5 for i in range(len(props))])
    ax.set_xticklabels(props, fontsize=9)
    ax.set_yticks([i + 0.5 for i in range(len(names))])
    ax.set_yticklabels(list(reversed(names)), fontsize=9)
    ax.set_title("Verified properties (exhaustive, not sampled)", fontsize=10)
    ax.set_axisbelow(True)
    _save(fig, "fig_property_matrix.png")


# ----------------------------------------------------------------- throughput
def fig_throughput():
    locks = [("dekker", sa.DekkerLock), ("peterson", sa.PetersonLock),
             ("tas", sa.TasLock), ("semaphore", sa.SemaphoreLock),
             ("monitor", sa.MonitorLock)]
    names, thr = [], []
    for label, cls in locks:
        r = sa.benchmark(cls, threads=2, iterations=8000, name=label)
        names.append(label)
        thr.append(r["throughput_ops_per_s"] / 1000.0)
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    bars = ax.bar(names, thr, color=[GREY, GREY, ORANGE, BLUE, GREEN])
    for b, v in zip(bars, thr):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, f"{v:.0f}k",
                ha="center", fontsize=8)
    ax.set_ylabel("critical sections per second (thousands)")
    ax.set_title("Cost of mutual exclusion, 2 threads x 8000 sections")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "chart_throughput.png")


# ----------------------------------------------------------------- contention
def fig_contention():
    counts = [2, 4, 8]
    series = {}
    for label, cls in (("tas", sa.TasLock), ("semaphore", sa.SemaphoreLock),
                       ("monitor", sa.MonitorLock)):
        series[label] = [sa.benchmark(cls, threads=n, iterations=5000,
                                      name=f"{label}{n}")["throughput_ops_per_s"]
                         / 1000.0 for n in counts]
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    for (label, vals), colour in zip(series.items(), (ORANGE, BLUE, GREEN)):
        ax.plot(counts, vals, marker="o", color=colour, label=label)
    ax.set_xlabel("threads competing for one lock")
    ax.set_ylabel("critical sections per second (thousands)")
    ax.set_title("Throughput under contention (5000 sections per thread)")
    ax.set_xticks(counts)
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    _save(fig, "chart_contention.png")


# ---------------------------------------------------------------------- spins
def fig_spins():
    counts = [2, 4, 8]
    spins = [sa.benchmark(sa.TasLock, threads=n, iterations=5000,
                          name=f"tas{n}")["spins"] for n in counts]
    fig, ax = plt.subplots(figsize=(7.6, 4.0))
    ax.bar([str(c) for c in counts], spins, color=ORANGE)
    for i, v in enumerate(spins):
        ax.text(i, v + max(spins) * 0.02, f"{v:,}", ha="center", fontsize=9)
    ax.set_xlabel("threads competing for one test-and-set lock")
    ax.set_ylabel("failed acquire attempts (wasted CPU)")
    ax.set_title("Busy-wait cost: spins grow with contention")
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "chart_spins.png")


# ------------------------------------------------------------ readers/writers
def fig_readers_writers():
    variants = [("readers\npreference", sa.ReadersPreferenceRW),
                ("writers\npreference", sa.WritersPreferenceRW),
                ("fair\n(FIFO)", sa.FairRW)]
    labels, reads, writes = [], [], []
    for label, cls in variants:
        r = sa.readers_writers_benchmark(cls, n_readers=6, n_writers=1,
                                         duration=0.6, reps=3)
        labels.append(label)
        reads.append(r["reads_total"] / r["reps"])
        writes.append(r["writes_total"] / r["reps"])
    fig, ax = plt.subplots(figsize=(8.0, 4.2))
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], reads, width=0.4, color=BLUE,
           label="reads completed")
    ax.bar([i + 0.2 for i in x], writes, width=0.4, color=ORANGE,
           label="writes completed")
    ax.set_yscale("log")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("operations completed per 0.6 s trial (log scale)")
    ax.set_title("Readers/writers: 6 reader threads against 1 writer")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    _save(fig, "chart_readers_writers.png")


# ------------------------------------------------------------------- deadlock
def fig_deadlock():
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.text(5, 4.6, "Circular wait: two locks, two threads, opposite orders",
            ha="center", fontsize=11, fontweight="bold")

    def box(x, y, text, colour):
        ax.add_patch(plt.Rectangle((x, y), 2.0, 0.9, facecolor=colour,
                                   edgecolor="black"))
        ax.text(x + 1.0, y + 0.45, text, ha="center", va="center",
                fontsize=8.5)

    def arrow(x1, y1, x2, y2, text, colour):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=colour, lw=1.8))
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.15, text, ha="center",
                fontsize=8, color=colour)

    box(0.6, 2.6, "Thread 0", "#dbe7f4")
    box(6.6, 2.6, "Thread 1", "#dbe7f4")
    box(0.6, 0.6, "Lock A", "#f6e0d2")
    box(6.6, 0.6, "Lock B", "#f6e0d2")

    arrow(2.6, 3.05, 6.6, 3.05, "waits for B (held by T1)", RED)
    arrow(6.6, 2.75, 2.6, 2.75, "waits for A (held by T0)", RED)
    arrow(1.6, 2.6, 1.6, 1.5, "holds", GREEN)
    arrow(7.6, 2.6, 7.6, 1.5, "holds", GREEN)
    ax.text(5, 1.05, "the wait-for graph contains a cycle -> deadlock",
            ha="center", fontsize=9, color=RED, style="italic")
    _save(fig, "fig_deadlock.png")


# ----------------------------------------------------------- monitor timeline
def fig_monitor_timeline():
    caps = [1, 4, 16]
    fig, axes = plt.subplots(1, 3, figsize=(12.4, 3.6), sharey=True)
    for ax, cap in zip(axes, caps):
        mon = sa.BoundedBufferMonitor(cap)
        res = sa.producer_consumer(mon, n_producers=2, n_consumers=2,
                                   items=800)
        ax.axhline(cap, color=RED, linestyle="--", linewidth=1)
        ax.text(0, cap + 0.4, f"capacity {cap}", color=RED, fontsize=8)
        ax.bar([0], [mon.max_observed], color=BLUE)
        ax.bar([1], [res["re_waits_after_signal"] / max(1, mon.produced)],
               color=ORANGE)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["max\noccupancy", "re-waits\nper item"], fontsize=8)
        ax.set_title(f"capacity = {cap}", fontsize=9)
        ax.grid(axis="y", alpha=0.3)
    axes[0].set_ylabel("items")
    fig.suptitle("Monitor bounded buffer: capacity, occupancy and re-checked "
                 "waits", fontsize=10)
    _save(fig, "fig_monitor_timeline.png")


def main():
    res = _load_results()
    fig_state_spaces(res)
    fig_property_matrix(res)
    fig_throughput()
    fig_contention()
    fig_spins()
    fig_readers_writers()
    fig_deadlock()
    fig_monitor_timeline()
    with open(os.path.join(ROOT, "output", "figures.json"), "w",
              encoding="utf-8") as f:
        json.dump(sorted(os.listdir(DIA)), f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
