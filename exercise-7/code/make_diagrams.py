"""Regenerate every Exercise-7 figure into ../diagrams.

    python3 code/make_diagrams.py

Every number comes from ``output/experiments.json``, never from a literal in
this file, so a figure cannot drift away from the run that produced it. Figure
labels are in Latin script on purpose: the same images go into the Persian
report, and Vazirmatn is not registered with matplotlib here.
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

DIA = os.path.join(ROOT, "diagrams")
OUT = os.path.join(ROOT, "output")
os.makedirs(DIA, exist_ok=True)

BLUE = "#2f6fb3"
ORANGE = "#d9812b"
GREEN = "#3f8f5f"
RED = "#b5372f"
GREY = "#8a8a8a"
PURPLE = "#7a5aa8"

# Short names, because the solution keys are longer than the axis can hold.
LABEL = {
    "semaphore_mutex": "sem mutex",
    "semaphore_mutex_fast": "sem mutex (no queue)",
    "monitor_mesa_mutex": "monitor mesa",
    "monitor_fifo_mutex": "monitor fifo",
    "monitor_mutex": "monitor mutex",
    "dekker_mutex": "dekker",
    "peterson_mutex": "peterson",
    "readers_pref": "readers pref",
    "readers_pref_fast": "readers pref (no queue)",
    "writers_pref": "writers pref",
    "fair_fifo": "fair fifo",
    "fair_fifo_fast": "fair fifo (no queue)",
    "barrier": "writer barrier",
    "monitor_mesa": "monitor mesa rw",
    "monitor_fifo": "monitor fifo rw",
    "dekker_rw": "dekker rw",
    "peterson_rw": "peterson rw",
    "rw_readers_pref": "readers pref",
    "rw_writers_pref": "writers pref (1w)",
    "rw_writers_pref_2w": "writers pref (2w)",
    "rw_fair": "fair fifo",
    "rw_barrier": "writer barrier",
    "rw_monitor_mesa": "monitor mesa",
    "rw_monitor_fifo": "monitor fifo",
    "rw_dekker": "dekker rw",
    "rw_dekker_2readers": "dekker rw (2r)",
    "rw_peterson": "peterson rw",
    "rw_peterson_2readers": "peterson rw (2r)",
    "rw_broken_count": "broken (off by one)",
}


def _name(key: str) -> str:
    return LABEL.get(key, key)


def _save(fig, name):
    path = os.path.join(DIA, name)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("wrote", path)


def _load():
    with open(os.path.join(OUT, "experiments.json"), encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------- 1. the verdicts
def fig_verdicts(model):
    """The model-checking table as a picture: one row per solution, one column
    per property, green where it holds and red where it does not."""
    order = ["semaphore_mutex", "monitor_mesa_mutex", "monitor_fifo_mutex",
             "dekker_mutex", "peterson_mutex",
             "rw_readers_pref", "rw_writers_pref", "rw_writers_pref_2w",
             "rw_fair", "rw_barrier", "rw_monitor_mesa", "rw_monitor_fifo",
             "rw_dekker", "rw_dekker_2readers", "rw_peterson",
             "rw_peterson_2readers", "rw_broken_count"]
    rows = []
    for key in order:
        r = model[key]
        starv = r["starvation_free"]
        rows.append([
            _name(key),
            "".join(r["roles"]),
            r["states"],
            r["rw_safety"],
            r["deadlock_free"],
            "all" if all(starv.values()) else
            ("none" if not any(starv.values()) else
             ",".join(f"P{k}" for k, v in sorted(starv.items()) if not v)),
            r["concurrent_reads_admitted"],
        ])
    cols = ["solution", "roles", "states", "safe", "deadlock\nfree",
            "starves", "concurrent\nreads"]
    fig, ax = plt.subplots(figsize=(9.6, 6.4))
    ax.axis("off")
    table = ax.table(cellText=[[str(c) for c in row] for row in rows],
                     colLabels=cols, cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1, 1.35)
    for j in range(len(cols)):
        table[0, j].set_facecolor("#dddddd")
    for i, row in enumerate(rows, start=1):
        for j, ok in ((3, row[3]), (4, row[4])):
            table[i, j].set_facecolor(GREEN if ok else RED)
            table[i, j].set_color("white")
        starved = row[5]
        table[i, 5].set_facecolor(GREEN if starved == "all" else
                                  (RED if starved == "none" else ORANGE))
        table[i, 5].set_color("white")
        table[i, 6].set_facecolor(GREEN if row[6] else GREY)
        table[i, 6].set_color("white")
        if row[0].startswith("broken"):
            for j in range(len(cols)):
                table[i, j].set_facecolor("#f2c9c5")
    ax.set_title("Exhaustive model checking: every verdict, 2-3 processes",
                 fontsize=11, pad=10)
    _save(fig, "fig_verdicts.png")


def fig_states(model):
    order = [k for k in model if k != "rw_broken_count"]
    order.sort(key=lambda k: model[k]["states"])
    names = [_name(k) for k in order]
    states = [model[k]["states"] for k in order]
    trans = [model[k]["transitions"] for k in order]
    y = range(len(order))
    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.barh(list(y), states, color=BLUE, label="reachable states")
    ax.barh([i + 0.0 for i in y], trans, color=ORANGE, alpha=0.55,
            height=0.45, label="transitions")
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("count (log scale)")
    ax.set_title("How big each proof was")
    ax.legend(loc="lower right", fontsize=8)
    for i, v in enumerate(states):
        ax.text(v * 1.15, i, f"{v:,}", va="center", fontsize=7)
    _save(fig, "fig_states.png")


# --------------------------------------------------------------- 2. throughput
def fig_throughput(e1):
    keys = sorted(e1, key=lambda k: e1[k]["ops_per_s"])
    names = [_name(k) for k in keys]
    vals = [e1[k]["ops_per_s"] for k in keys]
    spread = [e1[k].get("ops_per_s_spread", 0) for k in keys]
    colours = []
    for k in keys:
        if "fast" in k:
            colours.append(PURPLE)
        elif k.startswith(("dekker", "peterson")):
            colours.append(ORANGE)
        elif k.startswith("monitor"):
            colours.append(GREEN)
        else:
            colours.append(BLUE)
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    ax.barh(names, vals, xerr=spread, color=colours,
            error_kw={"ecolor": GREY, "capsize": 2, "lw": 0.8})
    ax.set_xlabel("operations per second (median of "
                  f"{e1[keys[0]]['reps']} runs, whiskers = spread)")
    ax.set_title("Cost: 4 readers + 2 writers, empty critical section")
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(vals):
        ax.text(v * 1.05, i, f"{v:,.0f}", va="center", fontsize=7)
    ax.set_xlim(0, max(vals + spread) * 1.35)
    _save(fig, "fig_throughput.png")


def fig_queue_cost(e1):
    """The price of the FIFO queue the fairness proof assumes."""
    pairs = [("semaphore_mutex", "semaphore_mutex_fast"),
             ("readers_pref", "readers_pref_fast"),
             ("fair_fifo", "fair_fifo_fast")]
    pairs = [(a, b) for a, b in pairs if a in e1 and b in e1]
    labels = [_name(a).replace(" (no queue)", "") for a, _ in pairs]
    fifo = [e1[a]["ops_per_s"] for a, _ in pairs]
    fast = [e1[b]["ops_per_s"] for _, b in pairs]
    x = range(len(pairs))
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.bar([i - 0.2 for i in x], fifo, width=0.4, color=BLUE,
           label="strict FIFO semaphore")
    ax.bar([i + 0.2 for i in x], fast, width=0.4, color=PURPLE,
           label="threading.Semaphore")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_ylabel("operations per second")
    ax.set_title("What the no-barging queue costs")
    ax.legend(fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    for i, (a, b) in enumerate(zip(fifo, fast)):
        ax.text(i - 0.2, a, f"{a:,.0f}", ha="center", va="bottom", fontsize=7)
        ax.text(i + 0.2, b, f"{b:,.0f}", ha="center", va="bottom", fontsize=7)
        if a:
            ax.text(i, max(a, b) * 1.12, f"{b / a:.1f}x", ha="center",
                    fontsize=8, color=RED)
    _save(fig, "fig_queue_cost.png")


# ------------------------------------------------------------ 3. concurrency
def fig_concurrency(e2):
    keys = sorted(e2, key=lambda k: -e2[k]["max_concurrent_readers"])
    names = [_name(k) for k in keys]
    vals = [e2[k]["max_concurrent_readers"] for k in keys]
    colours = [GREEN if v >= 2 else RED for v in vals]
    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    ax.bar(names, vals, color=colours)
    ax.axhline(1, color=GREY, ls="--", lw=0.9)
    ax.text(0.01, 1.12, "the most any mutex can do", fontsize=7, color=GREY)
    ax.set_ylabel("most readers inside at once")
    ax.set_ylim(0, max(vals) + 1.2)
    ax.set_title("The property the problem exists for: 6 readers, 1 writer, "
                 "work inside the section")
    ax.tick_params(axis="x", labelrotation=32, labelsize=8)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.12, str(v), ha="center", fontsize=8)
    _save(fig, "fig_concurrency.png")


# -------------------------------------------------------------- 4. starvation
def fig_starvation(e3):
    keys = list(e3)
    keys.sort(key=lambda k: e3[k]["write_share"])
    names = [_name(k) for k in keys]
    fig, ax = plt.subplots(figsize=(9.4, 5.2))
    for i, k in enumerate(keys):
        shares = e3[k]["write_share_sorted"]
        ax.scatter([i] * len(shares), shares, s=46, color=BLUE, zorder=3,
                   alpha=0.85)
        ax.plot([i - 0.16, i + 0.16],
                [e3[k]["write_share"]] * 2, color=RED, lw=2, zorder=4)
    ax.axhline(1 / 7, color=GREEN, ls="--", lw=1)
    ax.text(len(keys) - 0.4, 1 / 7 + 0.012, "1 writer of 7 threads",
            fontsize=7, color=GREEN, ha="right")
    ax.set_xticks(range(len(keys)))
    ax.set_xticklabels(names, rotation=32, ha="right", fontsize=8)
    ax.set_ylabel("share of the traffic that was writes")
    ax.set_ylim(-0.03, 1.05)
    ax.set_title("Each dot is one 0.6 s trial (9 per lock), the bar is the "
                 "median\nBimodal outcomes are the point, not noise")
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_starvation.png")


def fig_reader_starvation(e4):
    keys = sorted(e4, key=lambda k: e4[k]["reads"])
    names = [_name(k) for k in keys]
    vals = [e4[k]["reads"] for k in keys]
    colours = [RED if v < 0.05 * max(vals) else BLUE for v in vals]
    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    ax.bar(names, vals, color=colours)
    ax.set_ylabel("reads completed (max of "
                  f"{e4[keys[0]]['reps']} runs)")
    ax.set_title("The mirror image: 1 reader against 3 writers")
    ax.tick_params(axis="x", labelrotation=32, labelsize=8)
    ax.grid(axis="y", alpha=0.25)
    _save(fig, "fig_reader_starvation.png")


# ---------------------------------------------------------------- 5. scaling
def fig_scaling(e5):
    fig, ax = plt.subplots(figsize=(8.6, 4.8))
    markers = {"semaphore_mutex": "o", "readers_pref": "s",
               "writers_pref": "^", "fair_fifo": "D", "barrier": "v",
               "monitor_mesa": "P", "monitor_fifo": "X"}
    for name, row in e5.items():
        xs = sorted(int(k) for k in row)
        ys = [row[str(x)]["ops_per_s"] for x in xs]
        ax.plot(xs, ys, marker=markers.get(name, "o"), label=_name(name),
                lw=1.4, ms=6)
    ax.set_xlabel("number of reader threads (plus 1 writer)")
    ax.set_ylabel("operations per second")
    ax.set_title("Does adding readers actually help?")
    ax.legend(fontsize=7.5, ncol=2)
    ax.grid(alpha=0.25)
    ax.set_xticks([1, 2, 4, 6, 8])
    _save(fig, "fig_scaling.png")


# ------------------------------------------------------------ 6. the pattern
def fig_pattern():
    """What the four families do, drawn as the phases of one run each."""
    fig, axes = plt.subplots(4, 1, figsize=(9.2, 6.0), sharex=True)
    plan = [
        ("plain mutex", [(0, 3, "R"), (3, 5, "W"), (5, 8, "R"), (8, 10, "W"),
                         (10, 12, "R")], "one at a time, always"),
        ("readers preference", [(0, 4, "R"), (4, 6, "R"), (6, 7, "R"),
                                (7, 8, "R"), (8, 9, "R")],
         "a read phase that need never end"),
        ("writers preference", [(0, 2, "W"), (2, 4, "W"), (4, 5, "R"),
                                (5, 7, "W"), (7, 9, "W")],
         "the reader door stays shut"),
        ("fair / barrier", [(0, 3, "R"), (3, 5, "W"), (5, 8, "R"),
                            (8, 10, "W"), (10, 13, "R")],
         "the phases take turns"),
    ]
    colour = {"R": BLUE, "W": ORANGE}
    for ax, (title, spans, note) in zip(axes, plan):
        for i, (a, b, kind) in enumerate(spans):
            ax.barh(0, b - a, left=a, color=colour[kind], edgecolor="white",
                    height=0.55)
            ax.text((a + b) / 2, 0, kind, ha="center", va="center",
                    color="white", fontsize=8)
        ax.set_yticks([])
        ax.set_xlim(0, 13)
        ax.set_ylim(-0.6, 0.6)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.set_ylabel(title, fontsize=8.5, rotation=0, ha="right",
                      va="center", labelpad=64)
        ax.text(13.05, 0, note, fontsize=7, va="center", color=GREY)
    axes[-1].set_xlabel("time (one read phase = one bar, R = reader, "
                        "W = writer)")
    axes[0].set_title("What each family looks like when it runs", fontsize=11)
    _save(fig, "fig_pattern.png")


def main() -> int:
    data = _load()
    model = data["e6_model"]
    fig_verdicts(model)
    fig_states(model)
    fig_throughput(data["e1_throughput"])
    fig_queue_cost(data["e1_throughput"])
    fig_concurrency(data["e2_concurrency"])
    fig_starvation(data["e3_writer_starvation"])
    fig_reader_starvation(data["e4_reader_starvation"])
    fig_scaling(data["e5_scaling"])
    fig_pattern()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
