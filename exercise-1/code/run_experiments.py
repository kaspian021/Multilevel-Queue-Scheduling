"""Run every Exercise-1 experiment and regenerate all numbers and charts.

Usage (from the ``exercise-1`` directory)::

    python code/run_experiments.py

Outputs
-------
* ``output/scenario_<name>.txt``  — full Gantt + metric table per scenario
* ``output/experiments.json``     — machine-readable metrics for the report
* ``output/experiments_summary.txt`` — the table that is pasted into the report
* ``diagrams/chart_*.png``        — every comparison chart used in the reports
* ``diagrams/gantt_<name>.png``   — Gantt chart per scenario

Nothing in this file invents numbers: every value written out is produced by
``mlq.simulate_full`` from the JSON scenarios in ``code/scenarios/``.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import matplotlib                                            # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402

from mlq import (QueueConfig, InputError, simulate_full, metrics_full,        # noqa: E402
                 format_gantt, format_table, plot_gantt, load_config, POLICIES)

OUT = os.path.join(ROOT, "output")
FIG = os.path.join(ROOT, "diagrams")
SCN = os.path.join(HERE, "scenarios")

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.35,
                     "grid.linestyle": ":", "axes.axisbelow": True})


def _load(name):
    with open(os.path.join(SCN, name), encoding="utf-8") as f:
        return json.load(f)


def run_scenario(name, **over):
    spec = _load(name)
    procs, cfgs, aging = load_config(spec)
    inter = over.pop("inter_policy", spec.get("inter_policy", "fixed"))
    inter_slice = over.pop("inter_slice", int(spec.get("inter_slice", 2)))
    aging = over.pop("aging", aging)
    for q, pol in list(over.pop("policies", {}).items()):
        cfgs[int(q)].policy = pol
    if over:
        raise TypeError(f"unexpected overrides: {over}")
    plist, gantt, st = simulate_full(procs, cfgs, aging, inter, inter_slice)
    rows, summary, qstats = metrics_full(plist, st)
    return rows, summary, qstats, gantt, plist


def write_scenario_report(name, tag=None, **over):
    rows, summary, qstats, gantt, plist = run_scenario(name, **over)
    tag = tag or name.replace(".json", "")
    txt = [f"scenario: {name}"]
    if over:
        txt.append(f"overrides: {json.dumps(over, sort_keys=True)}")
    txt.append("")
    txt.append(format_gantt(gantt))
    txt.append("")
    txt.append(format_table(rows, summary, qstats))
    txt.append("")
    path = os.path.join(OUT, f"scenario_{tag}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(txt) + "\n")
    plot_gantt(gantt, os.path.join(FIG, f"gantt_{tag}.png"),
               title=f"MLQ Gantt chart — {tag}",
               queue_of={p.pid: p.home_queue for p in plist})
    return rows, summary, qstats, gantt


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------

METRIC_KEYS = ["waiting", "turnaround", "response"]
METRIC_LABEL = {"waiting": "avg waiting time (ticks)",
                "turnaround": "avg turnaround time (ticks)",
                "response": "avg response time (ticks)"}


def chart_queue_policy():
    """Same workload, four different intra-queue policies for queue 2."""
    res = {}
    for pol in POLICIES:
        rows, summary, _, _, _ = run_scenario("policy_mix.json", policies={"2": pol})
        res[pol] = summary
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.4))
    for ax, key in zip(axes, METRIC_KEYS):
        vals = [res[p][key] for p in POLICIES]
        bars = ax.bar(POLICIES, vals, color=["#4c72b0", "#55a868", "#c44e52", "#8172b2"])
        ax.set_title(METRIC_LABEL[key])
        ax.set_ylabel("ticks")
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center",
                    va="bottom", fontsize=8)
        ax.set_ylim(0, max(vals) * 1.22)
    fig.suptitle("Queue-2 intra-queue policy comparison (policy_mix.json, 8 processes)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_queue_policy.png"), dpi=160)
    plt.close(fig)
    return res


def chart_aging():
    """Waiting time of the starved low-priority process vs the aging threshold."""
    thresholds = [0, 2, 4, 6, 8, 12]
    low_wait, low_tat, avg_wait, promo = [], [], [], []
    for a in thresholds:
        rows, summary, _, _, _ = run_scenario("starvation.json", aging=a)
        by = {r["pid"]: r for r in rows}
        low_wait.append(by["L1"]["waiting"])
        low_tat.append(by["L1"]["turnaround"])
        avg_wait.append(summary["waiting"])
        promo.append(summary["promotions"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4))
    axes[0].plot(thresholds, low_wait, "o-", color="#c44e52", label="L1 waiting time")
    axes[0].plot(thresholds, low_tat, "s--", color="#4c72b0", label="L1 turnaround time")
    axes[0].set_xlabel("aging threshold (ticks, 0 = no aging)")
    axes[0].set_ylabel("ticks")
    axes[0].set_title("Starvation of the low-priority process")
    axes[0].legend()
    axes[1].bar([str(t) for t in thresholds], avg_wait, color="#55a868")
    axes[1].set_xlabel("aging threshold (ticks)")
    axes[1].set_ylabel("avg waiting time (ticks)")
    axes[1].set_title("System-wide average waiting time")
    for x, v in zip(range(len(thresholds)), avg_wait):
        axes[1].text(x, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    axes[1].set_ylim(0, max(avg_wait) * 1.25)
    fig.suptitle("Effect of aging on starvation (starvation.json)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_aging.png"), dpi=160)
    plt.close(fig)
    return {"thresholds": thresholds, "low_wait": low_wait, "low_tat": low_tat,
            "avg_wait": avg_wait, "promotions": promo}


def chart_interqueue():
    """fixed-priority vs time-slice between queues."""
    res = {}
    for inter, sl in [("fixed", 2), ("slice", 2), ("slice", 3), ("slice", 5)]:
        rows, summary, _, _, _ = run_scenario("timeslice.json", inter_policy=inter,
                                           inter_slice=sl)
        res[f"{inter}/{sl}"] = summary
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.2))
    labels = list(res)
    for ax, key in zip(axes, METRIC_KEYS):
        vals = [res[l][key] for l in labels]
        bars = ax.bar(labels, vals, color="#4c72b0")
        ax.set_title(METRIC_LABEL[key])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center",
                    va="bottom", fontsize=8)
        ax.set_ylim(0, max(vals) * 1.25)
        ax.tick_params(axis="x", labelsize=8)
    fig.suptitle("Inter-queue policy: fixed priority vs time slice (timeslice.json)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_interqueue.png"), dpi=160)
    plt.close(fig)
    return res


def chart_scenarios(names):
    res = {}
    for n in names:
        rows, summary, _, _, _ = run_scenario(n)
        res[n.replace(".json", "")] = summary
    labels = list(res)
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    import numpy as np
    x = np.arange(len(labels))
    w = 0.26
    for i, key in enumerate(METRIC_KEYS):
        vals = [res[l][key] for l in labels]
        b = ax.bar(x + (i - 1) * w, vals, w, label=METRIC_LABEL[key])
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, v, f"{v:.1f}", ha="center",
                    va="bottom", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("ticks")
    ax.legend()
    ax.set_title("Average metrics per scenario (Exercise 1)")
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_scenarios.png"), dpi=160)
    plt.close(fig)
    return res


def chart_overhead():
    """Overhead proxy: context switches and dispatches per scenario."""
    names = ["baseline.json", "starvation.json", "policy_mix.json", "timeslice.json"]
    labels, sw, disp, util = [], [], [], []
    for n in names:
        rows, summary, _, _, _ = run_scenario(n)
        labels.append(n.replace(".json", ""))
        sw.append(summary["context_switches"])
        disp.append(summary["dispatches"])
        util.append(summary["utilization"] * 100)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.2))
    import numpy as np
    x = np.arange(len(labels))
    axes[0].bar(x - 0.2, sw, 0.4, label="context switches", color="#4c72b0")
    axes[0].bar(x + 0.2, disp, 0.4, label="dispatches", color="#c44e52")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, fontsize=8)
    axes[0].set_ylabel("count")
    axes[0].set_title("Scheduling overhead")
    axes[0].legend()
    b = axes[1].bar(labels, util, color="#55a868")
    axes[1].set_ylabel("CPU utilization (%)")
    axes[1].set_title("CPU utilization (work-conserving, no idle)")
    axes[1].set_ylim(0, 115)
    for r, v in zip(b, util):
        axes[1].text(r.get_x() + r.get_width() / 2, v, f"{v:.0f}%", ha="center",
                     va="bottom", fontsize=8)
    axes[1].tick_params(axis="x", labelsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_overhead.png"), dpi=160)
    plt.close(fig)
    return {"labels": labels, "switches": sw, "dispatches": disp, "utilization": util}


def chart_starvation_bars():
    """Per-queue waiting time in the starvation scenario (with and without aging)."""
    out = {}
    for a in (0, 4):
        rows, summary, qstats, _, _ = run_scenario("starvation.json", aging=a)
        out[a] = qstats
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    import numpy as np
    qs = sorted(out[0])
    x = np.arange(len(qs))
    ax.bar(x - 0.2, [out[0][q]["avg_waiting"] for q in qs], 0.4,
           label="no aging", color="#c44e52")
    ax.bar(x + 0.2, [out[4][q]["avg_waiting"] for q in qs], 0.4,
           label="aging = 4", color="#55a868")
    ax.set_xticks(x)
    ax.set_xticklabels([f"queue {q}" for q in qs])
    ax.set_ylabel("avg waiting time (ticks)")
    ax.set_title("Per-queue waiting time with and without aging")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_starvation.png"), dpi=160)
    plt.close(fig)
    return out


# --------------------------------------------------------------------------

def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)

    data = {"scenarios": {}, "experiments": {}}

    for name in ["baseline.json", "starvation.json", "timeslice.json", "policy_mix.json"]:
        rows, summary, qstats, gantt = write_scenario_report(name)
        data["scenarios"][name] = {
            "summary": summary,
            "per_queue": {str(k): v for k, v in qstats.items()},
            "gantt": [list(g) for g in gantt],
            "rows": rows,
        }

    # --- error handling evidence ---------------------------------------
    errors = {}
    for name in ["invalid_missing_field.json", "invalid_burst.json", "invalid_queue.json"]:
        try:
            run_scenario(name)
            errors[name] = "UNEXPECTED: accepted"
        except InputError as e:
            errors[name] = str(e)
    data["errors"] = errors

    data["experiments"]["queue_policy"] = chart_queue_policy()
    data["experiments"]["aging"] = chart_aging()
    data["experiments"]["interqueue"] = chart_interqueue()
    data["experiments"]["scenarios"] = chart_scenarios(
        ["baseline.json", "starvation.json", "timeslice.json", "policy_mix.json"])
    data["experiments"]["overhead"] = chart_overhead()
    data["experiments"]["starvation_bars"] = {str(k): v for k, v in
                                              chart_starvation_bars().items()}

    with open(os.path.join(OUT, "experiments.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)

    # --- human readable summary -----------------------------------------
    lines = ["Exercise 1 — experiment summary (generated by code/run_experiments.py)", ""]
    for name, d in data["scenarios"].items():
        s = d["summary"]
        lines.append(f"{name}: n={s['n']}  avgW={s['waiting']:.2f}  avgTAT={s['turnaround']:.2f}"
                     f"  avgR={s['response']:.2f}  util={s['utilization'] * 100:.1f}%"
                     f"  switches={s['context_switches']}  preemptions={s['preemptions']}")
    lines.append("")
    lines.append("queue-2 policy comparison (policy_mix.json):")
    for pol, s in data["experiments"]["queue_policy"].items():
        lines.append(f"  {pol:5s} avgW={s['waiting']:.2f}  avgTAT={s['turnaround']:.2f}"
                     f"  avgR={s['response']:.2f}")
    lines.append("")
    lines.append("aging sweep (starvation.json): threshold -> L1 waiting / avg waiting")
    ag = data["experiments"]["aging"]
    for t, lw, aw in zip(ag["thresholds"], ag["low_wait"], ag["avg_wait"]):
        lines.append(f"  aging={t:2d}  L1 wait={lw:3d}  avg wait={aw:.2f}"
                     f"  promotions={ag['promotions'][ag['thresholds'].index(t)]}")
    lines.append("")
    lines.append("invalid-input handling:")
    for k, v in errors.items():
        lines.append(f"  {k}: {v}")
    with open(os.path.join(OUT, "experiments_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\nwrote {len(data['scenarios'])} scenario reports, "
          f"6 charts and experiments.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
