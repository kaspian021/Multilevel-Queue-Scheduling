"""Draw the static Exercise-1 diagrams (structure, flowchart, metric timeline).

Everything is drawn with matplotlib primitives so the figures are reproducible
from a clean checkout without any extra system package (graphviz is not
required).

Usage::

    python code/make_diagrams.py
"""
from __future__ import annotations

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIG = os.path.join(ROOT, "diagrams")

plt.rcParams.update({"font.size": 9})

BLUE = "#4c72b0"
GREEN = "#55a868"
RED = "#c44e52"
GREY = "#7f7f7f"
LBLUE = "#dce6f1"
LGREEN = "#d8ecd8"
LRED = "#f6d8d8"


def _box(ax, x, y, w, h, text, fc=LBLUE, ec=BLUE, fs=9, bold=False, tc="black"):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.06",
                       linewidth=1.2, edgecolor=ec, facecolor=fc, zorder=2)
    ax.add_patch(b)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            color=tc, zorder=3, fontweight="bold" if bold else "normal",
            linespacing=1.35)
    return b


def _arrow(ax, x1, y1, x2, y2, color=GREY, style="-|>", lw=1.2, ls="-", rad=0.0,
           lw_=None):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=12, linewidth=lw_ or lw,
                                 color=color, linestyle=ls, zorder=1,
                                 connectionstyle=f"arc3,rad={rad}"))


def _canvas(w=11, h=6.5, xlim=(0, 11), ylim=(0, 6.5)):
    fig, ax = plt.subplots(figsize=(w, h))
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.axis("off")
    return fig, ax


# --------------------------------------------------------------------------

def fig_structure():
    fig, ax = _canvas(10.5, 5.2, (0, 10.5), (0, 5.2))
    ax.text(5.25, 5.0, "Multilevel Queue structure", ha="center", fontsize=12,
            fontweight="bold")

    qdata = [("Queue 1  (highest priority)", "system / interactive", "RR, quantum = 2",
              LRED, RED, 4.0),
             ("Queue 2  (medium priority)", "user interactive", "SJF", LGREEN, GREEN, 2.9),
             ("Queue 3  (lowest priority)", "batch", "FCFS", LBLUE, BLUE, 1.8)]

    for title, kind, pol, fc, ec, y in qdata:
        ax.add_patch(FancyBboxPatch((0.35, y), 6.6, 0.85,
                                    boxstyle="round,pad=0.02,rounding_size=0.08",
                                    linewidth=1.3, edgecolor=ec, facecolor=fc, zorder=2))
        ax.text(0.6, y + 0.58, title, fontsize=9.5, fontweight="bold", zorder=3)
        ax.text(0.6, y + 0.22, f"{kind}  |  intra-queue policy: {pol}", fontsize=8,
                color="#333333", zorder=3)

    # process boxes inside the queues
    for i in range(4):
        ax.add_patch(Rectangle((2.6 + i * 0.85, 4.12), 0.6, 0.42, facecolor="white",
                               edgecolor=RED, zorder=4, linewidth=1))
        ax.text(2.9 + i * 0.85, 4.33, f"P{i + 1}", ha="center", va="center",
                fontsize=7.5, zorder=5)
    for i in range(3):
        ax.add_patch(Rectangle((3.9 + i * 0.85, 3.02), 0.6, 0.42, facecolor="white",
                               edgecolor=GREEN, zorder=4, linewidth=1))
        ax.text(4.2 + i * 0.85, 3.23, f"Q{i + 1}", ha="center", va="center",
                fontsize=7.5, zorder=5)
    for i in range(2):
        ax.add_patch(Rectangle((4.6 + i * 0.85, 1.92), 0.6, 0.42, facecolor="white",
                               edgecolor=BLUE, zorder=4, linewidth=1))
        ax.text(4.9 + i * 0.85, 2.13, f"B{i + 1}", ha="center", va="center",
                fontsize=7.5, zorder=5)

    # CPU box
    _box(ax, 8.0, 2.4, 1.9, 1.8, "CPU\n(1 tick at a time)", fc="#fdf3d8", ec="#b58900",
         fs=9.5, bold=True)
    for y in (4.42, 3.32, 2.22):
        _arrow(ax, 6.95, y, 7.95, 3.3, color=GREY)

    # scheduler / dispatcher
    _box(ax, 8.0, 0.5, 1.9, 1.4, "dispatcher /\ninter-queue\narbitrator", fc="#eeeeee",
         ec=GREY, fs=8.5)
    _arrow(ax, 8.95, 2.4, 8.95, 1.95, color=GREY)
    _arrow(ax, 8.95, 0.5, 8.95, 0.15, color=GREY)
    _arrow(ax, 8.95, 0.15, 0.4, 0.15, color=GREY)
    _arrow(ax, 0.4, 0.15, 0.4, 1.75, color=GREY)
    ax.text(4.6, 0.32, "new and preempted processes return to their queue",
            fontsize=7.5, color="#444444")

    ax.text(8.95, 4.55, "preempt / dispatch", fontsize=7.5, ha="center", color="#444444")
    fig.tight_layout()
    p = os.path.join(FIG, "fig_mlq_structure.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    return p


def fig_flowchart():
    fig, ax = _canvas(9.5, 9.4, (0, 9.5), (0, 9.4))
    ax.text(4.75, 9.1, "Multilevel Queue Scheduling — control flow of one tick",
            ha="center", fontsize=12, fontweight="bold")

    X, W = 3.0, 3.5
    _box(ax, X, 8.4, W, 0.55, "START  t = 0", fc="#eeeeee", ec=GREY, bold=True)
    _box(ax, X, 7.55, W, 0.6, "admit every process with\narrival <= t into its queue",
         fc=LBLUE, ec=BLUE, fs=8.5)
    _box(ax, X, 6.55, W, 0.72, "aging enabled?\npromote processes that waited\n>= threshold",
         fc=LGREEN, ec=GREEN, fs=8.2)
    _box(ax, X, 5.55, W, 0.72, "inter-queue arbitration\nfixed: highest non-empty queue\nslice: next queue after N ticks",
         fc=LBLUE, ec=BLUE, fs=8.2)
    _box(ax, X, 4.55, W, 0.72, "intra-queue selection\nFCFS / RR / SJF / SRTF\n(+ priority tie-break)",
         fc=LBLUE, ec=BLUE, fs=8.2)
    _box(ax, X, 3.55, W, 0.72, "run the selected process for 1 tick\nremaining--,  t++\nrecord the tick in the Gantt trace",
         fc=LBLUE, ec=BLUE, fs=8.2)
    _box(ax, X, 2.5, W, 0.75, "remaining == 0 ?", fc="#fdf3d8", ec="#b58900", fs=9, bold=True)
    _box(ax, X, 1.5, W, 0.72, "record finish time; compute\nwaiting / turnaround / response",
         fc=LGREEN, ec=GREEN, fs=8.2)
    _box(ax, X, 0.55, W, 0.72, "all processes finished?\nno -> next tick\nyes -> print tables and Gantt",
         fc="#fdf3d8", ec="#b58900", fs=8.4, bold=True)

    for y in (8.4, 7.55, 6.55, 5.55, 4.55, 3.55, 3.25, 2.25):
        _arrow(ax, X + W / 2, y, X + W / 2, y - 0.28, color=GREY)

    # "yes" branch to finish
    _arrow(ax, X + W, 2.87, 7.6, 2.87, color=GREEN)
    ax.text(7.65, 2.95, "yes", fontsize=8, color=GREEN, fontweight="bold")
    _arrow(ax, 7.6, 2.87, 7.6, 1.86, color=GREEN)
    _arrow(ax, 7.6, 1.86, X + W, 1.86, color=GREEN)
    # "no" branch loops back
    _arrow(ax, X, 2.87, 1.2, 2.87, color=RED)
    ax.text(0.35, 2.95, "no", fontsize=8, color=RED, fontweight="bold")
    _arrow(ax, 1.2, 2.87, 1.2, 6.95, color=RED)
    _arrow(ax, 1.2, 6.95, X, 6.95, color=RED)
    ax.text(1.28, 5.0, "return to its queue\n(FCFS/RR tail or SJF/SRTF order)",
            fontsize=7.5, color=RED, rotation=90, va="center")

    _arrow(ax, X + W / 2, 1.5, X + W / 2, 1.29, color=GREY)
    _box(ax, X, 0.02, W, 0.42, "END", fc="#eeeeee", ec=GREY, bold=True)
    _arrow(ax, X + W / 2, 0.55, X + W / 2, 0.46, color=GREY)
    fig.tight_layout()
    p = os.path.join(FIG, "fig_flowchart.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    return p


def fig_metrics_timeline():
    """Illustration of burst / waiting / turnaround / response on one process."""
    fig, ax = _canvas(9.5, 3.0, (0, 9.5), (0, 3.0))
    ax.set_ylim(0, 3.0)
    arrival, start, end, run = 1.0, 2.5, 6.5, [3.0, 4.5]
    ax.add_patch(Rectangle((arrival, 1.55), start - arrival, 0.6, facecolor=LRED,
                           edgecolor=RED, linewidth=1.2))
    ax.text((arrival + start) / 2, 1.85, "waiting", ha="center", va="center", fontsize=8.5)
    ax.add_patch(Rectangle((start, 1.55), end - start, 0.6, facecolor=LGREEN,
                           edgecolor=GREEN, linewidth=1.2))
    for s in run:                      # preempted gap inside the execution
        ax.add_patch(Rectangle((s, 1.55), 0.5, 0.6, facecolor="white",
                               edgecolor=GREY, hatch="//", linewidth=1))
    ax.text((start + end) / 2, 1.85, "running (burst time, may be split)", ha="center",
            va="center", fontsize=8.5)
    ax.annotate("", xy=(arrival, 2.35), xytext=(end, 2.35),
                arrowprops=dict(arrowstyle="<|-|>", color=BLUE, linewidth=1.3))
    ax.text((arrival + end) / 2, 2.45, "turnaround time = finish - arrival", ha="center",
            fontsize=8.5, color=BLUE)
    ax.annotate("", xy=(arrival, 1.25), xytext=(start, 1.25),
                arrowprops=dict(arrowstyle="<|-|>", color="#b58900", linewidth=1.3))
    ax.text((arrival + start) / 2, 0.95, "response = first start - arrival", ha="center",
            fontsize=8.5, color="#8a6d00")
    for x, lab in [(arrival, "arrival"), (start, "first start"), (end, "finish")]:
        ax.plot([x, x], [1.4, 2.3], color="black", linewidth=0.8, linestyle=":")
        ax.text(x, 0.6, lab, ha="center", fontsize=8)
    ax.text(4.75, 2.85, "Per-process timing definitions", ha="center", fontsize=11,
            fontweight="bold")
    fig.tight_layout()
    p = os.path.join(FIG, "fig_metrics_timeline.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    return p


def fig_queue_waiting():
    """Conceptual sketch: how strict priority shapes waiting time per queue."""
    fig, ax = _canvas(9.0, 3.4, (0, 9.0), (0, 3.4))
    ax.set_ylim(0, 3.4)
    data = [(1, 1.0, LRED, RED), (2, 4.5, LGREEN, GREEN), (3, 10.0, LBLUE, BLUE)]
    for i, (q, w, fc, ec) in enumerate(data):
        ax.barh(2 - i * 0.7, w, height=0.42, color=fc, edgecolor=ec, linewidth=1.2)
        ax.text(w + 0.15, 2 - i * 0.7, f"{w:.1f} ticks", va="center", fontsize=8.5)
        ax.text(-0.15, 2 - i * 0.7, f"queue {q}", va="center", ha="right", fontsize=9,
                fontweight="bold")
    ax.set_xlim(-0.2, 12)
    ax.set_ylim(0.2, 2.6)
    ax.set_xlabel("average waiting time (ticks)")
    ax.set_title("Strict fixed priority: waiting time grows as the queue level drops",
                 fontsize=10)
    ax.set_yticks([])
    ax.set_yticklabels([])
    fig.tight_layout()
    p = os.path.join(FIG, "fig_queue_waiting.png")
    fig.savefig(p, dpi=170)
    plt.close(fig)
    return p


def main():
    os.makedirs(FIG, exist_ok=True)
    made = [fig_structure(), fig_flowchart(), fig_metrics_timeline(), fig_queue_waiting()]
    for p in made:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
