"""Generate Gantt charts (EDF, RM) for the Exercise-3 task set from the simulator."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from edf_rm import Task, simulate, segments

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
    ax.set_xlabel("time")
    ax.set_title(f"{algo} schedule over the hyperperiod [0,{H}) - dotted = deadline, red = missed, arrow = release")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "diagrams")
    os.makedirs(out, exist_ok=True)
    gantt("EDF", os.path.join(out, "gantt_edf.png"))
    gantt("RM", os.path.join(out, "gantt_rm.png"))
    print("figures written")
