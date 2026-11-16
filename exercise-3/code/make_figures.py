"""Generate Gantt charts (EDF, RM) for the Exercise-3 task set from the simulator."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from edf_rm import (Task, simulate, segments, summarize, rm_schedulability,
                    utilization)

TASKS = [Task("T1", 1, 4, 4), Task("T2", 3, 8, 8), Task("T3", 4, 12, 12)]
COL = {0: "#4C78A8", 1: "#F58518", 2: "#54A24B"}


def gantt(algo, path):
    tl, jobs, miss = simulate(TASKS, algo)
    H = len(tl)
    fig, ax = plt.subplots(figsize=(11, 3.2))
    for s, e, x in segments(tl):
        if x is not None:
            ax.barh(x, e - s, left=s, color=COL[x], edgecolor="black", height=0.6)
    for j in jobs:
        ax.annotate("", xy=(j.release, j.task + 0.32), xytext=(j.release, j.task + 0.55),
                    arrowprops=dict(arrowstyle="->", color="gray"))
        bad = j in miss
        ax.plot([j.deadline, j.deadline], [j.task - 0.4, j.task + 0.4], color="red" if bad else "black",
                lw=2.5 if bad else 1, ls="-" if bad else ":")
    ax.set_yticks(range(len(TASKS)))
    ax.set_yticklabels([t.name for t in TASKS])
    ax.invert_yaxis()
    ax.set_xticks(range(0, H + 1))
    ax.set_xlim(0, H)
    ax.grid(axis="x", alpha=0.3)
    ax.set_xlabel("time (ticks)")
    ax.set_title(f"{algo} schedule over the hyperperiod [0,{H}): "
                 f"dotted = deadline, red = missed, arrow = release")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def chart_response(out):
    """Per-task response times measured under EDF and RM."""
    edf = summarize(TASKS, "EDF")
    rm = summarize(TASKS, "RM")
    names = list(edf["per_task"])
    import numpy as np
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    w = 0.2
    for i, (key, colour, label) in enumerate(
            [("min_response", "#9ecae1", "min"), ("avg_response", "#4c72b0", "average"),
             ("max_response", "#c44e52", "max")]):
        ax.bar(x * 2 + (i - 1) * w, [edf["per_task"][n][key] for n in names], w,
               color=colour, label=f"EDF {label}")
        ax.bar(x * 2 + 0.9 + (i - 1) * w, [rm["per_task"][n][key] for n in names], w,
               color=colour, hatch="//", label=f"RM {label}")
    ax.set_xticks(x * 2 + 0.45)
    ax.set_xticklabels(names)
    ax.set_ylabel("ticks")
    ax.set_title("Measured job response times over one hyperperiod (24 ticks)")
    ax.legend(fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "chart_response.png"), dpi=160)
    plt.close(fig)


def chart_utilization(out):
    s = summarize(TASKS, "EDF")
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.bar(["busy"], [s["busy"]], color="#55a868", label="busy")
    ax.bar(["busy"], [s["idle"]], bottom=[s["busy"]], color="#dddddd",
           edgecolor="black", hatch="//", label="idle")
    ax.set_ylabel("ticks")
    ax.set_ylim(0, 26)
    ax.set_title(f"CPU occupancy in [0,24): busy={s['busy']}, idle={s['idle']}, "
                 f"U={s['utilization'] * 100:.2f}%")
    ax.legend()
    for i, v in enumerate([s["busy"], s["idle"]]):
        ax.text(0, (s["busy"] if i else 0) + v / 2, str(v), ha="center", va="center")
    fig.tight_layout()
    fig.savefig(os.path.join(out, "chart_utilization.png"), dpi=160)
    plt.close(fig)


def chart_rta(out):
    """Response-time analysis: computed worst-case R against the deadline D."""
    rta = rm_schedulability(TASKS)
    names = list(rta["response_times"])
    R = [rta["response_times"][n]["R"] for n in names]
    D = [rta["response_times"][n]["D"] for n in names]
    import numpy as np
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    ax.bar(x - 0.2, R, 0.4, label="worst-case response time R",
           color=["#c44e52" if r > d else "#55a868" for r, d in zip(R, D)])
    ax.bar(x + 0.2, D, 0.4, label="deadline D", color="#9fb2cc")
    for i, (r, d) in enumerate(zip(R, D)):
        ax.text(i - 0.2, r, str(r), ha="center", va="bottom", fontsize=8)
        ax.text(i + 0.2, d, str(d), ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.set_ylabel("ticks")
    ax.set_title("RM response-time analysis under RM priorities")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(out, "chart_rta.png"), dpi=160)
    plt.close(fig)


def fig_release_pattern(out):
    """Release instants and deadlines of every job inside the hyperperiod."""
    H = 24
    fig, ax = plt.subplots(figsize=(9.5, 3.0))
    colours = {0: "#4C78A8", 1: "#F58518", 2: "#54A24B"}
    for i, t in enumerate(TASKS):
        k = 0
        while k * t.T < H:
            r = k * t.T
            ax.arrow(r, i, 0, 0.3, head_width=0.18, head_length=0.12,
                     fc=colours[i], ec=colours[i])
            ax.plot([r + t.D, r + t.D], [i - 0.3, i + 0.3], color=colours[i],
                    linestyle="--", linewidth=1.2)
            ax.text(r + 0.15, i + 0.36, f"D={r + t.D}", fontsize=7, color=colours[i])
            k += 1
    ax.set_yticks(range(len(TASKS)))
    ax.set_yticklabels([t.name for t in TASKS])
    ax.set_xticks(range(0, H + 1))
    ax.set_xlabel("time (ticks)")
    ax.set_title("Release instants (arrows) and deadlines (dashed) in [0,24)")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(out, "fig_release_pattern.png"), dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "diagrams")
    os.makedirs(out, exist_ok=True)
    gantt("EDF", os.path.join(out, "gantt_edf.png"))
    gantt("RM", os.path.join(out, "gantt_rm.png"))
    chart_response(out)
    chart_utilization(out)
    chart_rta(out)
    fig_release_pattern(out)
    print("figures written")
