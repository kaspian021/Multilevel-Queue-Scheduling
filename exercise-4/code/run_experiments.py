"""Run every Exercise-4 experiment and write all artefacts to output/.

Usage (from the exercise folder)::

    python code/run_experiments.py
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import sync_algorithms as sa          # noqa: E402
import sync_model as sm               # noqa: E402

OUT = os.path.join(ROOT, "output")


def _fmt(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)


def benchmark_reps(make_lock, threads: int, iterations: int, name: str,
                   reps: int = 7) -> dict:
    """Run one benchmark `reps` times and report the median.

    Timings on a shared machine are noisy: a single run of the same workload
    varied by more than an order of magnitude, so every cost figure in this
    exercise is a median over repeated trials, with the spread reported too.
    """
    runs = [sa.benchmark(make_lock, threads=threads, iterations=iterations,
                         name=name) for _ in range(reps)]
    thr = sorted(r["throughput_ops_per_s"] for r in runs)
    el = sorted(r["elapsed_s"] for r in runs)
    spins = [r["spins"] for r in runs if isinstance(r["spins"], int)]
    last = runs[-1]
    return {
        "name": name,
        "class": type(make_lock()).__name__,
        "threads": threads,
        "iterations": iterations,
        "reps": reps,
        "expected_counter": last["expected_counter"],
        "counter": last["counter"],
        "correct": all(r["correct"] for r in runs),
        "max_concurrent": max(r["max_concurrent"] for r in runs),
        "mutual_exclusion_observed": all(r["mutual_exclusion_observed"]
                                         for r in runs),
        "entries": last["entries"],
        "fairness_pstdev": last["fairness_pstdev"],
        "elapsed_s_median": round(el[len(el) // 2], 5),
        "elapsed_s_min": round(el[0], 5),
        "elapsed_s_max": round(el[-1], 5),
        "throughput_median": round(thr[len(thr) // 2], 1),
        "throughput_min": round(thr[0], 1),
        "throughput_max": round(thr[-1], 1),
        "spins_median": (sorted(spins)[len(spins) // 2] if spins else None),
        "spins_max": (max(spins) if spins else None),
    }


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    data: dict = {}
    lines: list = ["Exercise 4 — experiment results (code/run_experiments.py)", ""]

    # ---------------------------------------------------------- model checker
    data["model"] = sm.check_all()
    lines.append(sm.format_report(data["model"]))
    with open(os.path.join(OUT, "model_check.txt"), "w", encoding="utf-8") as f:
        f.write(sm.format_report(data["model"]) + "\n")

    # --------------------------------------------------------------- benchmark
    locks = [("dekker", sa.DekkerLock), ("peterson", sa.PetersonLock),
             ("tas", sa.TasLock), ("semaphore", sa.SemaphoreLock),
             ("monitor", sa.MonitorLock)]
    data["benchmark"] = {}
    lines.append("=== mutual-exclusion mechanisms (2 threads x 5000 sections, "
                 "median of 7)")
    for name, cls in locks:
        res = benchmark_reps(cls, threads=2, iterations=5000, name=name)
        data["benchmark"][name] = res
        lines.append("  " + json.dumps(res, sort_keys=True))
    lines.append("")

    # ------------------------------------------------------- contention sweep
    data["contention"] = {}
    lines.append("=== contention sweep (5000 sections per thread, median of 5)")
    for n in (2, 4, 8):
        for name, cls in (("tas", sa.TasLock), ("semaphore", sa.SemaphoreLock),
                          ("monitor", sa.MonitorLock)):
            key = f"{name}_{n}t"
            res = benchmark_reps(cls, threads=n, iterations=5000, name=key,
                                 reps=5)
            data["contention"][key] = res
            lines.append("  " + json.dumps(res, sort_keys=True))
    lines.append("")

    # ------------------------------------------------------ producer/consumer
    data["producer_consumer"] = {}
    lines.append("=== monitor: bounded buffer producer/consumer")
    for cap in (1, 4, 16):
        best = None
        for _ in range(5):                 # take the fastest of five runs
            mon = sa.BoundedBufferMonitor(cap)
            res = sa.producer_consumer(mon, n_producers=2, n_consumers=2,
                                       items=800)
            if best is None or res["elapsed_s"] < best["elapsed_s"]:
                best = res
        data["producer_consumer"][f"capacity_{cap}"] = best
        lines.append(f"  capacity={cap}: " + json.dumps(res, sort_keys=True))
    lines.append("")

    # -------------------------------------------------------- readers/writers
    data["readers_writers"] = {}
    lines.append("=== readers/writers (6 readers, 1 writer, 5 x 0.6 s)")
    for cls in (sa.ReadersPreferenceRW, sa.WritersPreferenceRW, sa.FairRW):
        res = sa.readers_writers_benchmark(cls, n_readers=6, n_writers=1,
                                           duration=0.6, reps=5)
        data["readers_writers"][cls.__name__] = res
        lines.append(f"  {cls.__name__}: " + json.dumps(res, sort_keys=True))
    lines.append("")

    # ---------------------------------------------------------------- deadlock
    data["deadlock"] = sa.deadlock_demo(1.0)
    lines.append("=== circular wait (two locks, two threads)")
    lines.append("  " + json.dumps(data["deadlock"], sort_keys=True))

    text = "\n".join(lines) + "\n"
    with open(os.path.join(OUT, "experiments.json"), "w", encoding="utf-8") as f:
        f.write(_fmt(data) + "\n")
    with open(os.path.join(OUT, "experiments_summary.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)

    # a compact Markdown table the report can quote verbatim
    md = ["| Algorithm | family | states | mutual exclusion | deadlock-free | "
          "starvation-free |", "|---|---|---:|---|---|---|"]
    for name, r in data["model"].items():
        sf = "yes" if all(r["starvation_free"].values()) else "**no**"
        md.append(f"| `{name}` | {r['family']} | {r['states']} | "
                  f"{'holds' if r['mutual_exclusion'] else '**VIOLATED**'} | "
                  f"{'yes' if r['deadlock_free'] else '**no**'} | {sf} |")
    with open(os.path.join(OUT, "model_table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
