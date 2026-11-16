"""Regenerate every Exercise-6 figure into exercise-6/diagrams.

    python3 tools/make_figures_ex6.py          # from the repository root

Every number is read from the ``output/experiments.json`` files of exercises 1,
2, 3 and 4, and the two overload timelines are re-simulated with exercise-2's
own scheduler so that the Gantt chart cannot disagree with the published
figures. The script asserts that agreement before it writes anything.

Labels are in Latin script on purpose: the Persian report uses the same images
and Vazirmatn is not registered with matplotlib here.

Dependencies: ``pip install -r exercise-4/requirements.txt`` (matplotlib only).
"""
from __future__ import annotations

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import importlib.util                                        # noqa: E402
import sys                                                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
DIA = os.path.join(REPO, "exercise-6", "diagrams")


def _load_module(name, path):
    """Import a module from a file path, without touching sys.path forever."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # dataclasses resolves annotations through sys.modules[cls.__module__],
    # so the module must be registered before it is executed.
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


RT = _load_module("rt_sched",
                  os.path.join(REPO, "exercise-2", "code", "rt_sched.py"))
os.makedirs(DIA, exist_ok=True)

BLUE = "#1f365d"
ORANGE = "#d9812b"
GREEN = "#3f8f5f"
RED = "#b5372f"
GREY = "#8a8a8a"


def _load(ex, name="experiments.json"):
    with open(os.path.join(REPO, ex, "output", name), encoding="utf-8") as f:
        return json.load(f)


E1 = _load("exercise-1")
E2 = _load("exercise-2")
E3 = _load("exercise-3")
E4 = _load("exercise-4")


def _save(fig, name):
    fig.tight_layout()
    fig.savefig(os.path.join(DIA, name), dpi=150)
    plt.close(fig)
    print("wrote", os.path.join(DIA, name))


# ----------------------------------------------------------------- figure 1
def fig_utilisation_cliff():
    """The RM/EDF schedulability cliff, straight from the feasibility study."""
    fs = E2["feasibility_study"]
    buckets = [b for b in sorted(fs["buckets"]) if fs["buckets"][b]["n"]]
    centres = [(float(b.split("-")[0]) + float(b.split("-")[1])) / 2
               for b in buckets]
    rm = [100.0 * fs["buckets"][b]["rm"] / fs["buckets"][b]["n"]
          for b in buckets]
    edf = [100.0 * fs["buckets"][b]["edf"] / fs["buckets"][b]["n"]
           for b in buckets]

    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.plot(centres, rm, marker="o", color=ORANGE, linewidth=2,
            label=f"RM ({fs['sets']:,} sets)")
    ax.plot(centres, edf, marker="s", color=BLUE, linewidth=2,
            label="EDF (same sets)")
    ax.axvline(0.7798, color=GREY, linestyle=":", linewidth=1.2)
    ax.annotate("Liu-Layland bound, n = 3", xy=(0.7798, 60),
                xytext=(0.52, 52), fontsize=8, color=GREY,
                arrowprops=dict(arrowstyle="->", color=GREY, linewidth=0.8))
    ax.set_xlabel("task-set utilisation U")
    ax.set_ylabel("% of sets feasible")
    ax.set_ylim(-4, 108)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_title("Where rate monotonic stops working")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(loc="lower left", fontsize=9, frameon=False)
    _save(fig, "fig_utilisation_cliff.png")


# ----------------------------------------------------------------- figure 2
def _overload_schedules():
    """Re-simulate scenario D with exercise-2's own scheduler.

    Returns ``{algorithm: (segments, deadline_misses)}``. The miss counts are
    checked against exercise-2's published ``experiments.json`` so that this
    figure cannot silently disagree with the numbers the paper quotes.
    """
    spec = E2["scenarios"]["D_overload"]
    tasks = RT.tasks_from_spec(spec)
    out = {}
    for algo in ("EDF", "RM"):
        res = RT.simulate(tasks, spec["horizon"], algo)
        published = E2["measured"][f"D_overload|{algo}"]["deadline_misses"]
        assert len(res.deadline_misses) == published, (
            f"{algo}: re-simulation found {len(res.deadline_misses)} misses "
            f"but experiments.json publishes {published}")
        out[algo] = (res.gantt, len(res.deadline_misses))
    return out


def fig_overload_gantt():
    """EDF and RM timelines for the 123.33% overload scenario."""
    tasks = E2["scenarios"]["D_overload"]["tasks"]
    horizon = E2["scenarios"]["D_overload"]["horizon"]
    colours = {"X": BLUE, "Y": ORANGE, "Z": GREEN}
    sched = _overload_schedules()

    fig, axes = plt.subplots(2, 1, figsize=(7.2, 3.2), sharex=True)
    for ax, algo in zip(axes, ("EDF", "RM")):
        segs, misses = sched[algo]
        for a, b, label in segs:
            if label == "IDLE":
                ax.barh(0, b - a, left=a, color="#e8e8e8", height=0.5)
                continue
            task = label.split("#")[0]
            ax.barh(0, b - a, left=a, color=colours[task], height=0.5,
                    edgecolor="white", linewidth=0.6)
            if b - a >= 2.2:
                ax.text((a + b) / 2, 0, task, ha="center", va="center",
                        color="white", fontsize=8)
        for t in tasks:
            j = 0
            while True:
                d = t["offset"] + j * t["T"] + t["D"]
                if d > horizon:
                    break
                ax.plot([d, d], [-0.42, 0.42], color=RED, linewidth=0.7,
                        alpha=0.6)
                j += 1
        ax.set_yticks([])
        ax.set_ylabel(f"{algo}\n{misses} misses", rotation=0, ha="right",
                      va="center", fontsize=9)
        ax.set_xlim(0, horizon)
        ax.tick_params(axis="x", labelsize=8)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
    axes[-1].set_xlabel("time (ticks); red ticks are deadlines")
    axes[0].set_title("Scenario D: 123.33% offered load, achieved U = 100%")
    _save(fig, "fig_overload_gantt.png")


# ----------------------------------------------------------------- figure 3
def fig_contention():
    """Spinning against blocking as the thread count grows."""
    c = E4["contention"]
    ns = [2, 4, 8]
    tas = [c[f"tas_{n}t"]["throughput_median"] for n in ns]
    sem = [c[f"semaphore_{n}t"]["throughput_median"] for n in ns]
    mon = [c[f"monitor_{n}t"]["throughput_median"] for n in ns]
    spins = [c[f"tas_{n}t"]["spins_median"] for n in ns]

    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.plot(ns, tas, marker="o", color=ORANGE, linewidth=2,
            label="test-and-set (spins)")
    ax.plot(ns, sem, marker="s", color=BLUE, linewidth=2, label="semaphore")
    ax.plot(ns, mon, marker="^", color=GREEN, linewidth=2, label="monitor")
    ax.set_xlabel("threads")
    ax.set_ylabel("median ops/s")
    ax.set_xticks(ns)
    ax.set_title("Throughput under contention")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=9, frameon=False, loc="upper right")

    ax2 = ax.twinx()
    ax2.bar(ns, spins, width=0.42, color=RED, alpha=0.20)
    ax2.set_ylabel("wasted spin attempts", color=RED, fontsize=9)
    ax2.tick_params(axis="y", labelcolor=RED, labelsize=8)
    ax2.set_ylim(0, max(spins) * 4.2)
    _save(fig, "fig_contention.png")


# ----------------------------------------------------------------- figure 4
def fig_property_matrix():
    """Which property fails, for each of the eight mutual-exclusion algorithms."""
    m = E4["model"]
    order = ("dekker", "peterson", "lock_variable", "flag_spin", "tas",
             "semaphore_binary", "semaphore_wrong_order", "monitor_mesa")
    props = [("mutual_exclusion", "safety"),
             ("deadlock_free", "no deadlock"),
             ("starvation_free", "no starvation")]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    cell = 1.0
    for yi, name in enumerate(order):
        for xi, (key, label) in enumerate(props):
            if key == "starvation_free":
                ok = all(m[name][key].values())
            else:
                ok = m[name][key]
            colour = GREEN if ok else RED
            ax.add_patch(plt.Rectangle((xi, len(order) - 1 - yi), cell, cell,
                                       facecolor=colour, alpha=0.85,
                                       edgecolor="white"))
            ax.text(xi + cell / 2, len(order) - 1 - yi + cell / 2,
                    "ok" if ok else "FAIL", ha="center", va="center",
                    color="white", fontsize=11 if ok else 10,
                    fontweight="bold")
    ax.set_xlim(0, len(props))
    ax.set_ylim(0, len(order))
    ax.set_xticks([i + 0.5 for i in range(len(props))])
    ax.set_xticklabels([p[1] for p in props], fontsize=10)
    ax.set_yticks([i + 0.5 for i in range(len(order))])
    ax.set_yticklabels(list(reversed(order)), fontsize=9, family="monospace")
    ax.set_title("Exhaustive verdicts: three ways to be wrong")
    ax.set_aspect("equal")
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(False)
    ax.tick_params(length=0)
    _save(fig, "fig_property_matrix.png")


# ----------------------------------------------------------------- figure 5
def fig_aging():
    """The aging threshold sweep from exercise 1."""
    ag = E1["experiments"]["aging"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    ax.plot(ag["thresholds"], ag["low_wait"], marker="o", color=RED,
            linewidth=2, label="lowest queue: waiting time")
    ax.plot(ag["thresholds"], [w * 1.0 for w in ag["avg_wait"]], marker="s",
            color=BLUE, linewidth=2, label="all queues: mean waiting")
    ax.set_xlabel("aging threshold (ticks); 0 = aging disabled")
    ax.set_ylabel("waiting time (ticks)")
    ax.set_xticks(ag["thresholds"])
    ax.set_title("Aging: what the victim gains and everyone else pays")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(fontsize=9, frameon=False)
    _save(fig, "fig_aging.png")


DECK_NUMBERS = os.path.join(REPO, "exercise-6", "output", "deck_numbers.json")


def write_deck_numbers():
    """Publish the numbers the seminar deck quotes.

    ``exercise-6/code/build_deck.py`` must run on the Exercise-6 branch, where
    the other exercises' JSON files are not present. It therefore reads this
    file instead. Regenerating it here, from the same sources the figures use,
    is what keeps the spoken numbers on the slides from drifting away from the
    measurements.
    """
    sched = _overload_schedules()
    fs = E2["feasibility_study"]
    top = fs["buckets"]["0.90-1.00"]
    mid = fs["buckets"]["0.80-0.90"]
    data = {
        "_comment": "Generated by tools/make_figures_ex6.py; do not edit by "
                    "hand. Consumed by exercise-6/code/build_deck.py.",
        "sets": fs["sets"],
        "seed": fs["seed"],
        "rm_top_pct": round(100.0 * top["rm"] / top["n"], 1),
        "rm_mid_pct": round(100.0 * mid["rm"] / mid["n"], 1),
        "liu_layland_n3": round(3 * (2 ** (1.0 / 3) - 1), 4),
        "overload_edf_misses": sched["EDF"][1],
        "overload_rm_misses": sched["RM"][1],
        "aging_low_wait_off": E1["experiments"]["aging"]["low_wait"][0],
        "aging_low_wait_on": E1["experiments"]["aging"]["low_wait"][1],
        "D_load_pct": round(100.0 * (4 / 8 + 4 / 10 + 4 / 12), 2),
        "horizon_D": E2["scenarios"]["D_overload"]["horizon"],
        "model_states_max": max(v["states"] for v in E4["model"].values()),
    }
    os.makedirs(os.path.dirname(DECK_NUMBERS), exist_ok=True)
    with open(DECK_NUMBERS, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("wrote", DECK_NUMBERS)


def main():
    fig_utilisation_cliff()
    fig_overload_gantt()
    fig_contention()
    fig_property_matrix()
    fig_aging()
    write_deck_numbers()


if __name__ == "__main__":
    main()
