"""Run the Exercise-3 experiment and write every artefact.

Usage (from ``exercise-3``)::

    python code/run_experiments.py

Writes ``output/summary_EDF.txt``, ``output/summary_RM.txt``,
``output/step_table_EDF.txt``, ``output/step_table_RM.txt`` and
``output/experiments.json``.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from edf_rm import (Task, hyperperiod, utilization, rm_schedulability,      # noqa: E402
                    edf_schedulability, summarize, step_rows, format_summary,
                    format_timeline, simulate)

TASKS = [Task("T1", 1, 4, 4), Task("T2", 3, 8, 8), Task("T3", 4, 12, 12)]
OUT = os.path.join(ROOT, "output")


def step_table_text(algo, lang="fa"):
    rows = step_rows(TASKS, algo, lang)
    head = f"{'interval':<12}{'ran':<12}{'#ready':<10}reason"
    lines = [f"algorithm: {algo}", head, "-" * len(head)]
    for r in rows:
        lines.append(f"{r['interval']:<12}{r['ran']:<12}{r['ready']:<10}{r['reason']}")
    lines.append("")
    lines.append("ready-set detail (name_job(d=absolute deadline, rem=remaining)):")
    for r in rows:
        if r["ready_detail"]:
            lines.append(f"  [{r['interval']}] {r['ready_detail']}")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    data = {
        "tasks": [{"name": t.name, "C": t.C, "T": t.T, "D": t.D, "phase": t.phase}
                  for t in TASKS],
        "hyperperiod": hyperperiod(TASKS),
        "utilization": utilization(TASKS),
        "demand_in_hyperperiod": sum(t.C * (hyperperiod(TASKS) // t.T) for t in TASKS),
        "rm": rm_schedulability(TASKS),
        "edf": edf_schedulability(TASKS),
        "measured": {},
    }
    lines = ["Exercise 3 — experiment summary (code/run_experiments.py)", ""]
    lines.append(f"task set: " + ", ".join(
        f"{t.name}(C={t.C},T={t.T},D={t.D})" for t in TASKS))
    lines.append(f"utilization U = {data['utilization']:.6f} = "
                 f"{sum(t.C * (24 // t.T) for t in TASKS)}/24")
    lines.append(f"hyperperiod H = {data['hyperperiod']}")
    lines.append(f"total demand in [0,H) = {data['demand_in_hyperperiod']}")
    lines.append("")
    lines.append(f"RM : {json.dumps(data['rm'], ensure_ascii=False, sort_keys=True)}")
    lines.append(f"EDF: {json.dumps(data['edf'], ensure_ascii=False, sort_keys=True)}")
    lines.append("")

    for algo in ("EDF", "RM"):
        s = summarize(TASKS, algo)
        data["measured"][algo] = s
        lines.append(format_summary(s))
        lines.append("")
        with open(os.path.join(OUT, f"summary_{algo}.txt"), "w", encoding="utf-8") as f:
            f.write(format_summary(s) + "\n")
        with open(os.path.join(OUT, f"step_table_{algo}.txt"), "w", encoding="utf-8") as f:
            f.write(step_table_text(algo) + "\n")

    with open(os.path.join(OUT, "experiments.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
    with open(os.path.join(OUT, "experiments_summary.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
