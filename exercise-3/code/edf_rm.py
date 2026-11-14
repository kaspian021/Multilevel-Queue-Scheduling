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
