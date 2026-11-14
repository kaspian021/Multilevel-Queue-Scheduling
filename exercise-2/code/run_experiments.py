"""Run every Exercise-2 experiment and regenerate all numbers and charts.

Usage (from ``exercise-2``)::

    python code/run_experiments.py

Outputs
-------
* ``output/<scenario>_<ALGO>.txt``  — Gantt chart and metrics per run
* ``output/experiments.json``       — every number, machine readable
* ``output/experiments_summary.txt``— the text block pasted into the report
* ``diagrams/gantt_*.png``          — Gantt charts
* ``diagrams/chart_*.png``          — comparison charts

Nothing is hard-coded: the analytic verdicts come from response-time analysis
and from the processor-demand criterion, the measured numbers come from
``rt_sched.simulate``.
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import matplotlib                                            # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt                              # noqa: E402

from rt_sched import (Task, simulate, metrics, format_gantt, format_metrics,    # noqa: E402
                      tasks_from_spec, total_utilization, liu_layland_bound,
                      rm_response_time_analysis, edf_processor_demand_test,
                      feasibility_report, hyperperiod, dbf)

OUT = os.path.join(ROOT, "output")
FIG = os.path.join(ROOT, "diagrams")
SCN = os.path.join(HERE, "scenarios")

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.35,
                     "grid.linestyle": ":", "axes.axisbelow": True})

ALGOS = ("EDF", "RM", "MLQ")
COLOR = {"EDF": "#55a868", "RM": "#4c72b0", "MLQ": "#c44e52"}
SCENARIOS = ["scenario_A_fair.json", "scenario_B_stress.json",
             "scenario_C_aperiodic.json", "scenario_D_overload.json"]


def load(name):
    with open(os.path.join(SCN, name), encoding="utf-8") as f:
        spec = json.load(f)
    return spec, tasks_from_spec(spec), int(spec["horizon"])


def plot_gantt(res, path, title, limit=None):
    """One row per TASK (not per job) so that the chart stays readable.

    Only the first ``limit`` ticks are drawn; the caption of the report states
    the value of ``limit`` so that nothing is implied beyond the drawn window.
    """
    intervals = res.gantt if limit is None else [(s_, min(e, limit), n)
                                                 for s_, e, n in res.gantt if s_ < limit]
    rows = sorted({n.split("#")[0] for _, _, n in intervals if n != "IDLE"})
    cmap = plt.get_cmap("tab10")
    colour = {r: cmap(i % 10) for i, r in enumerate(rows)}
    fig, ax = plt.subplots(figsize=(11, 0.75 + 0.44 * len(rows)))
    idle_row = len(rows) + 0.35
    for s_, e, n in intervals:
        if n == "IDLE":
            ax.barh(idle_row, e - s_, left=s_, height=0.28, color="#cccccc",
                    edgecolor="black", hatch="//")
        else:
            task = n.split("#")[0]
            ax.barh(rows.index(task), e - s_, left=s_, height=0.5,
                    color=colour[task], edgecolor="black", linewidth=0.5)
            if e - s_ >= 3:
                ax.text((s_ + e) / 2, rows.index(task), n.split("#")[1],
                        ha="center", va="center", fontsize=6.5, color="white")
    ax.set_yticks(list(range(len(rows))))
    ax.set_yticklabels(rows)
    ax.set_xlim(0, (intervals[-1][1] if intervals else 1))
    ax.set_xlabel("time (ticks)")
    ax.set_title(title)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.set_ylim(-0.6, len(rows) + 0.7)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def chart_grouped(per_scenario, key, title, ylabel, fname, pct=False):
    labels = [s.replace("scenario_", "").replace(".json", "") for s in per_scenario]
    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    import numpy as np
    x = np.arange(len(labels))
    w = 0.26
    for i, a in enumerate(ALGOS):
        vals = [per_scenario[s][a][key] * (100 if pct else 1) for s in per_scenario]
        b = ax.bar(x + (i - 1) * w, vals, w, label=a, color=COLOR[a])
        for r, v in zip(b, vals):
            ax.text(r.get_x() + r.get_width() / 2, v, f"{v:.2f}", ha="center",
                    va="bottom", fontsize=7.5)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, fname), dpi=160)
    plt.close(fig)


def chart_rm_bound():
    ns = list(range(1, 21))
    bounds = [liu_layland_bound(n) for n in ns]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    ax.plot(ns, bounds, "o-", color="#4c72b0")
    ax.axhline(1.0, color="#c44e52", linestyle="--",
               label="EDF bound: U <= 1 (necessary and sufficient when D = T)")
    ax.axhline(0.6931, color="#55a868", linestyle=":",
               label="limit of the RM bound: ln 2 = 0.6931")
    ax.set_xlabel("number of tasks n")
    ax.set_ylabel("utilisation bound")
    ax.set_title("Liu and Layland RM bound n(2^(1/n) - 1) compared with the EDF bound")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_rm_bound.png"), dpi=160)
    plt.close(fig)


def random_feasibility_study(n_sets=3000, seed=20250101):
    """How often is a random task set feasible under RM and under EDF?

    Deterministic: the seed is fixed, so the numbers are reproducible.
    """
    rng = random.Random(seed)
    buckets = [(0.00, 0.25), (0.25, 0.50), (0.50, 0.70), (0.70, 0.80),
               (0.80, 0.90), (0.90, 1.00)]
    counts = {b: {"n": 0, "rm": 0, "edf": 0} for b in buckets}
    for _ in range(n_sets):
        n = rng.choice((3, 4, 5))
        periods = sorted(rng.randint(5, 40) for _ in range(n))
        if len(set(periods)) != n:
            continue
        target = rng.uniform(0.35, 1.05)
        # choose C values whose utilisation lands near the target
        tasks = []
        for i, T in enumerate(periods):
            C = max(1, int(round(target * T / n)))
            C = min(C, T)
            tasks.append(Task(f"t{i}", C, T))
        U = total_utilization(tasks)
        if U > 1.0:
            continue
        b = next((b for b in buckets if b[0] <= U < b[1]), None)
        if b is None:
            continue
        counts[b]["n"] += 1
        counts[b]["rm"] += 1 if rm_response_time_analysis(tasks)["feasible"] else 0
        counts[b]["edf"] += 1 if edf_processor_demand_test(tasks)["feasible"] else 0

    labels = [f"{a:.2f}-{b:.2f}" for a, b in buckets]
    ns = [counts[b]["n"] for b in buckets]
    rm_pct = [100 * counts[b]["rm"] / counts[b]["n"] if counts[b]["n"] else 0
              for b in buckets]
    edf_pct = [100 * counts[b]["edf"] / counts[b]["n"] if counts[b]["n"] else 0
              for b in buckets]

    fig, ax = plt.subplots(figsize=(9.5, 3.8))
    import numpy as np
    x = np.arange(len(labels))
    ax.bar(x - 0.2, rm_pct, 0.4, label="feasible under RM (exact RTA)",
           color=COLOR["RM"])
    ax.bar(x + 0.2, edf_pct, 0.4, label="feasible under EDF (demand criterion)",
           color=COLOR["EDF"])
    for i, (r, e, c) in enumerate(zip(rm_pct, edf_pct, ns)):
        ax.text(i - 0.2, r, f"{r:.0f}", ha="center", va="bottom", fontsize=7.5)
        ax.text(i + 0.2, e, f"{e:.0f}", ha="center", va="bottom", fontsize=7.5)
        ax.text(i, 2, f"n={c}", ha="center", va="bottom", fontsize=7, color="#444444")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("total utilisation U")
    ax.set_ylabel("share of feasible task sets (%)")
    ax.set_title(f"Random feasibility study: {sum(ns)} task sets, seed {seed}")
    ax.set_ylim(0, 118)
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_feasibility_study.png"), dpi=160)
    plt.close(fig)
    return {"seed": seed, "sets": sum(ns),
            "buckets": {f"{a:.2f}-{b:.2f}": {"n": counts[(a, b)]["n"],
                                             "rm": counts[(a, b)]["rm"],
                                             "edf": counts[(a, b)]["edf"]}
                        for a, b in buckets}}


def chart_dbf(scenario_file):
    """Demand bound function of one scenario, to show how the EDF test works."""
    _, tasks, horizon = load(scenario_file)
    ts = list(range(1, min(horizon, 60) + 1))
    d = [dbf(tasks, t) for t in ts]
    fig, ax = plt.subplots(figsize=(8.5, 3.4))
    ax.step(ts, d, where="post", color="#4c72b0", label="dbf(t) — cumulative demand")
    ax.plot(ts, ts, "--", color="#c44e52", label="available capacity t")
    ax.set_xlabel("interval length t")
    ax.set_ylabel("execution demand (ticks)")
    ax.set_title(f"Processor-demand criterion for {scenario_file}")
    ax.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "chart_dbf.png"), dpi=160)
    plt.close(fig)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FIG, exist_ok=True)
    data = {"scenarios": {}, "measured": {}, "analytic": {}}

    per_scenario = {}
    summary_lines = ["Exercise 2 — experiment summary (code/run_experiments.py)", ""]

    for name in SCENARIOS:
        spec, tasks, horizon = load(name)
        key = name.replace("scenario_", "").replace(".json", "")
        data["scenarios"][key] = {
            "tasks": [{"name": t.name, "C": t.C, "T": t.T, "D": t.D,
                       "offset": t.offset, "queue": t.queue} for t in tasks],
            "horizon": horizon,
            "hyperperiod": hyperperiod(tasks),
        }
        fr = feasibility_report(tasks)
        data["analytic"][key] = fr
        summary_lines.append(f"[{key}]  U={fr['utilization']:.4f}  n={fr['n']}"
                             f"  Liu&Layland bound={fr['liu_layland_bound']:.4f}")
        summary_lines.append(f"   RM  exact test (response-time analysis): "
                             f"{'FEASIBLE' if fr['rm']['feasible'] else 'NOT feasible'}")
        summary_lines.append(f"   EDF exact test (processor demand):        "
                             f"{'FEASIBLE' if fr['edf']['feasible'] else 'NOT feasible'}"
                             f"  {fr['edf'].get('reason', '')}")
        per_scenario[name] = {}
        for a in ALGOS:
            res = simulate(tasks, horizon, a)
            m = metrics(res)
            per_scenario[name][a] = m
            data["measured"][f"{key}|{a}"] = m
            with open(os.path.join(OUT, f"{key}_{a}.txt"), "w", encoding="utf-8") as f:
                f.write(f"scenario: {name}\nalgorithm: {a}\n\n")
                f.write(format_gantt(res) + "\n\n")
                f.write(format_metrics(m) + "\n")
            plot_gantt(res, os.path.join(FIG, f"gantt_{key}_{a}.png"),
                       f"{a} — {key} (first {min(hyperperiod(tasks), horizon)} ticks)",
                       limit=min(hyperperiod(tasks), horizon))
            summary_lines.append(
                f"   {a:3s} measured: misses={m['deadline_misses']:3d}  "
                f"util={m['utilization'] * 100:6.2f}%  avgR={m['avg_response']:7.3f}  "
                f"jitter={m['jitter']:7.3f}  ctx={m['context_switches']:3d}  "
                f"preemptions={m['preemptions']:3d}")
        summary_lines.append("")

    chart_grouped(per_scenario, "deadline_misses", "Deadline misses per scenario",
                  "missed jobs", "chart_misses.png")
    chart_grouped(per_scenario, "avg_response", "Average job response time",
                  "ticks", "chart_response.png")
    chart_grouped(per_scenario, "jitter", "Response-time jitter (standard deviation)",
                  "ticks", "chart_jitter.png")
    chart_grouped(per_scenario, "context_switches", "Context switches (overhead proxy)",
                  "count", "chart_overhead.png")
    chart_grouped(per_scenario, "utilization", "Achieved CPU utilisation",
                  "%", "chart_utilization.png", pct=True)
    chart_rm_bound()
    chart_dbf("scenario_A_fair.json")
    data["feasibility_study"] = random_feasibility_study()

    fs = data["feasibility_study"]
    summary_lines.append(f"Random feasibility study: {fs['sets']} task sets (seed {fs['seed']})")
    for bucket, c in fs["buckets"].items():
        if not c["n"]:
            continue
        summary_lines.append(f"   U in {bucket}: n={c['n']:4d}  RM feasible="
                             f"{100 * c['rm'] / c['n']:5.1f}%  EDF feasible="
                             f"{100 * c['edf'] / c['n']:5.1f}%")
    summary_lines.append("")

    with open(os.path.join(OUT, "experiments.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    with open(os.path.join(OUT, "experiments_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines) + "\n")

    print("\n".join(summary_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
