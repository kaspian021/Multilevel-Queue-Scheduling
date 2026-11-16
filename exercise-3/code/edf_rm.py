"""Unit-time preemptive single-CPU simulator for periodic tasks: EDF and RM.

Task model: (name, C=execution, T=period, D=relative deadline, phase=first release).
Job k of a task is released at phase + k*T with absolute deadline release + D.
Ties: EDF -> earlier absolute deadline, then lower task index.
      RM  -> shorter period (fixed priority), then lower task index.
A job that is still unfinished at its absolute deadline is recorded as a miss and
keeps running (no abort).  Simulation covers [0, horizon).
"""
from __future__ import annotations
from dataclasses import dataclass
from math import gcd
from functools import reduce
from typing import List, Optional


@dataclass(frozen=True)
class Task:
    name: str
    C: int
    T: int
    D: int
    phase: int = 0


@dataclass
class Job:
    task: int
    k: int
    release: int
    deadline: int
    remaining: int
    start: Optional[int] = None
    finish: Optional[int] = None


def validate(tasks: List[Task]):
    if not tasks:
        raise ValueError("no tasks")
    for t in tasks:
        if min(t.C, t.T, t.D) <= 0 or t.phase < 0:
            raise ValueError(f"{t.name}: C,T,D must be >0 and phase >=0")
        if t.C > t.D:
            raise ValueError(f"{t.name}: C > D can never meet its deadline")


def hyperperiod(tasks):
    return reduce(lambda a, b: a * b // gcd(a, b), (t.T for t in tasks))


def utilization(tasks):
    return sum(t.C / t.T for t in tasks)


def rm_bound(n):
    return n * (2 ** (1 / n) - 1)


def simulate(tasks: List[Task], algo: str, horizon: Optional[int] = None):
    """Return (timeline, jobs, misses). timeline[t] = task index or None (idle)."""
    validate(tasks)
    if algo not in ("EDF", "RM"):
        raise ValueError("algo must be EDF or RM")
    H = horizon if horizon is not None else max(t.phase for t in tasks) + hyperperiod(tasks)
    jobs: List[Job] = []
    for i, t in enumerate(tasks):
        k, r = 0, t.phase
        while r < H:
            jobs.append(Job(i, k, r, r + t.D, t.C))
            k, r = k + 1, r + t.T
    timeline: List[Optional[int]] = []
    for now in range(H):
        ready = [j for j in jobs if j.release <= now and j.remaining > 0]
        if not ready:
            timeline.append(None)
            continue
        if algo == "EDF":
            j = min(ready, key=lambda j: (j.deadline, j.task, j.k))
        else:
            j = min(ready, key=lambda j: (tasks[j.task].T, j.task, j.k))
        if j.start is None:
            j.start = now
        j.remaining -= 1
        timeline.append(j.task)
        if j.remaining == 0:
            j.finish = now + 1
    misses = [j for j in jobs if (j.finish is None and j.deadline <= H) or
              (j.finish is not None and j.finish > j.deadline)]
    return timeline, jobs, misses


def segments(timeline):
    segs = []
    for t, x in enumerate(timeline):
        if segs and segs[-1][2] == x:
            segs[-1] = (segs[-1][0], t + 1, x)
        else:
            segs.append((t, t + 1, x))
    return segs


def idle_time(timeline):
    return sum(1 for x in timeline if x is None)


def response_time_analysis(tasks: List[Task]):
    """RM response-time iteration R=C+sum(ceil(R/Tj)*Cj) for the first job of each task
    (synchronous release, fixed priority = shorter period). Compare with D to decide."""
    order = sorted(range(len(tasks)), key=lambda i: (tasks[i].T, i))
    res = {}
    for pos, i in enumerate(order):
        hp = [tasks[j] for j in order[:pos]]
        r = tasks[i].C
        while True:
            nxt = tasks[i].C + sum(-(-r // h.T) * h.C for h in hp)
            if nxt == r or nxt > 100 * tasks[i].T:
                r = nxt
                break
            r = nxt
        res[tasks[i].name] = r
    return res


def format_timeline(tasks, timeline):
    return " ".join(tasks[x].name if x is not None else "-" for x in timeline)


def main():
    tasks = [Task("T1", 2, 5, 5), Task("T2", 4, 7, 7)]
    for a in ("EDF", "RM"):
        tl, _, m = simulate(tasks, a)
        print(a, format_timeline(tasks, tl), "misses:", [(tasks[j.task].name, j.k) for j in m])


if __name__ == "__main__":
    main()


def trace(tasks: List[Task], algo: str):
    """Per-tick decision log: [(t, ready, chosen)] where ready/chosen are
    (task_name, job_index, abs_deadline, remaining_before_tick)."""
    validate(tasks)
    H = max(t.phase for t in tasks) + hyperperiod(tasks)
    jobs = []
    for i, t in enumerate(tasks):
        k, r = 0, t.phase
        while r < H:
            jobs.append(Job(i, k, r, r + t.D, t.C))
            k, r = k + 1, r + t.T
    log = []
    for now in range(H):
        ready = [j for j in jobs if j.release <= now and j.remaining > 0]
        view = lambda j: (tasks[j.task].name, j.k, j.deadline, j.remaining)
        if not ready:
            log.append((now, [], None))
            continue
        if algo == "EDF":
            j = min(ready, key=lambda j: (j.deadline, j.task, j.k))
        else:
            j = min(ready, key=lambda j: (tasks[j.task].T, j.task, j.k))
        log.append((now, sorted(map(view, ready), key=lambda v: (v[0], v[1])), view(j)))
        j.remaining -= 1
    return log


# --------------------------------------------------------------------------
# Exercise-3 extensions: schedulability tests, metrics, step tables, CLI
# --------------------------------------------------------------------------

import argparse                                                     # noqa: E402
import json                                                         # noqa: E402
import statistics                                                   # noqa: E402


def rm_schedulability(tasks: List[Task]) -> dict:
    """Liu and Layland sufficient bound plus the exact response-time test."""
    U = utilization(tasks)
    bound = rm_bound(len(tasks))
    rta = response_time_analysis(tasks)
    verdict = {name: {"R": r, "D": next(t.D for t in tasks if t.name == name),
                      "ok": r <= next(t.D for t in tasks if t.name == name)}
               for name, r in rta.items()}
    return {"utilization": U, "liu_layland_bound": bound,
            "concluded_by_bound": U <= bound,
            "response_times": verdict,
            "feasible": all(v["ok"] for v in verdict.values())}


def edf_schedulability(tasks: List[Task]) -> dict:
    """U <= 1 is necessary and sufficient for EDF with implicit deadlines."""
    U = utilization(tasks)
    implicit = all(t.D == t.T for t in tasks)
    if implicit:
        return {"utilization": U, "implicit_deadlines": True,
                "feasible": U <= 1,
                "method": "U <= 1 (necessary and sufficient for implicit deadlines)"}
    return {"utilization": U, "implicit_deadlines": False,
            "feasible": U <= 1,
            "method": "U <= 1 is necessary but NOT sufficient for constrained deadlines; "
                      "the processor-demand criterion is required"}


def summarize(tasks: List[Task], algo: str) -> dict:
    """All measured numbers for one algorithm over one hyperperiod."""
    validate(tasks)
    H = hyperperiod(tasks)
    tl, jobs, misses = simulate(tasks, algo, H)
    busy = sum(1 for x in tl if x is not None)
    per = {}
    for i, t in enumerate(tasks):
        js = [j for j in jobs if j.task == i]
        fin = [j for j in js if j.finish is not None]
        resp = [j.finish - j.release for j in fin]
        per[t.name] = {
            "C": t.C, "T": t.T, "D": t.D,
            "jobs": len(js),
            "finished": len(fin),
            "misses": sum(1 for j in js
                          if j.finish is None or j.finish > j.deadline),
            "avg_response": round(statistics.fmean(resp), 4) if resp else None,
            "max_response": max(resp) if resp else None,
            "min_response": min(resp) if resp else None,
            "jitter": round(statistics.pstdev(resp), 4) if len(resp) > 1 else 0.0,
        }
    return {
        "algorithm": algo,
        "horizon": H,
        "timeline": format_timeline(tasks, tl),
        "segments": [(s, e, (tasks[x].name if x is not None else "IDLE"))
                     for s, e, x in segments(tl)],
        "busy": busy,
        "idle": H - busy,
        "utilization": round(busy / H, 6),
        "offered_utilization": round(utilization(tasks), 6),
        "total_demand": sum(t.C * (H // t.T) for t in tasks),
        "job_count": len(jobs),
        "deadline_misses": len(misses),
        "missed_jobs": [(tasks[j.task].name, j.k, j.release, j.deadline, j.finish)
                        for j in misses],
        "per_task": per,
    }


REASON_EDF = "کمترین مهلت پایان مطلق"
REASON_RM = "بالاترین اولویت ثابت"


def step_rows(tasks: List[Task], algo: str, lang: str = "fa") -> List[dict]:
    """One row per tick: what was ready, what ran, and why."""
    log = trace(tasks, algo)
    rows = []
    for t, ready, chosen in log:
        if chosen is None:
            rows.append({"interval": f"{t}-{t + 1}", "ready": "-", "ran": "IDLE",
                         "reason": "هیچ کار آماده‌ای وجود ندارد" if lang == "fa"
                                   else "no ready job",
                         "ready_detail": ""})
            continue
        rd = ", ".join(f"{v[0]}_{v[1]}(d={v[2]},rem={v[3]})" for v in ready)
        if algo == "EDF":
            key = chosen[2]
            ties = [v for v in ready if v[2] == key]
            reason = f"d={key}"
            if len(ties) > 1:
                reason += ("؛ تساوی، شاخص وظیفه کوچک‌تر" if lang == "fa"
                           else "; tie, lower task index")
        else:
            T = {tt.name: tt.T for tt in tasks}[chosen[0]]
            reason = f"T={T}" + ("؛ اولویت ثابت" if lang == "fa" else "; fixed priority")
        rows.append({"interval": f"{t}-{t + 1}", "ready": str(len(ready)),
                     "ran": f"{chosen[0]}_{chosen[1]}", "reason": reason,
                     "ready_detail": rd})
    return rows


def format_summary(s: dict) -> str:
    L = [f"algorithm: {s['algorithm']}",
         f"  horizon={s['horizon']}  jobs={s['job_count']}  busy={s['busy']}"
         f"  idle={s['idle']}",
         f"  utilization={s['utilization'] * 100:.2f}%  (offered "
         f"{s['offered_utilization'] * 100:.2f}%)  demand={s['total_demand']}",
         f"  deadline misses: {s['deadline_misses']}"]
    for row in s["missed_jobs"]:
        L.append("    miss -> task={0} job={1} release={2} deadline={3} finish={4}"
                 .format(*row))
    L.append(f"  timeline: {s['timeline']}")
    L.append(f"  {'task':<6}{'C':>3}{'T':>4}{'D':>4}{'jobs':>6}{'miss':>6}"
             f"{'minR':>6}{'avgR':>8}{'maxR':>6}{'jitter':>8}")
    for name, p in s["per_task"].items():
        L.append(f"  {name:<6}{p['C']:>3}{p['T']:>4}{p['D']:>4}{p['jobs']:>6}"
                 f"{p['misses']:>6}{p['min_response']:>6}{p['avg_response']:>8.3f}"
                 f"{p['max_response']:>6}{p['jitter']:>8.3f}")
    return "\n".join(L)


def main_cli(argv=None):
    ap = argparse.ArgumentParser(description="EDF and RM simulator for exercise 3")
    ap.add_argument("--tasks", default="T1:1:4:4,T2:3:8:8,T3:4:12:12",
                    help="comma separated name:C:T:D[:phase]")
    ap.add_argument("--json", dest="json_out", help="write every metric as JSON")
    ap.add_argument("--table", help="write the tick-by-tick decision table")
    ap.add_argument("--lang", default="fa", choices=("fa", "en"))
    a = ap.parse_args(argv)

    tasks = []
    for item in a.tasks.split(","):
        parts = item.split(":")
        name, C, T, D = parts[0], int(parts[1]), int(parts[2]), int(parts[3])
        phase = int(parts[4]) if len(parts) > 4 else 0
        tasks.append(Task(name, C, T, D, phase))

    out = {"tasks": [{"name": t.name, "C": t.C, "T": t.T, "D": t.D, "phase": t.phase}
                     for t in tasks],
           "hyperperiod": hyperperiod(tasks),
           "utilization": utilization(tasks),
           "rm": rm_schedulability(tasks),
           "edf": edf_schedulability(tasks),
           "measured": {alg: summarize(tasks, alg) for alg in ("EDF", "RM")}}

    print(f"U = {out['utilization']:.6f}   H = {out['hyperperiod']}")
    print("RM :", json.dumps(out["rm"], ensure_ascii=False, sort_keys=True))
    print("EDF:", json.dumps(out["edf"], ensure_ascii=False, sort_keys=True))
    for alg in ("EDF", "RM"):
        print()
        print(format_summary(out["measured"][alg]))

    if a.table:
        with open(a.table, "w", encoding="utf-8") as f:
            for alg in ("EDF", "RM"):
                f.write(f"=== {alg} ===\n")
                f.write(f"{'interval':<10}{'ran':<10}{'#ready':<8}reason\n")
                for row in step_rows(tasks, alg, a.lang):
                    f.write(f"{row['interval']:<10}{row['ran']:<10}{row['ready']:<8}"
                            f"{row['reason']}\n")
                f.write("\n")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False, sort_keys=True)
    return 0
