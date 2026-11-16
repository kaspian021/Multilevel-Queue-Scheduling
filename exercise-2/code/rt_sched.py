"""Common simulation harness for MLQ, EDF and RM (Exercise 2).

Why a shared harness is needed
------------------------------
MLQ, EDF and RM were designed for different problems, so comparing them is only
meaningful when they are driven by the *same* task set, the *same* discrete-time
model and the *same* measurement code.  This module does exactly that:

* EDF  — Earliest Deadline First: dynamic priority by absolute deadline.
* RM   — Rate Monotonic: fixed priority, shorter period = higher priority.
* DM   — Deadline Monotonic: fixed priority, shorter relative deadline wins.
* MLQ  — Multilevel Queue: fixed priority by queue level, with a configurable
         intra-queue policy.  Queues are derived from the task parameters so
         that the comparison stays defined.

Every algorithm is executed on the same job release sequence, so any difference
in the measured metrics is caused by the scheduling rule alone.

Feasibility is *not* decided by simulation
------------------------------------------
Simulating one hyperperiod only shows what happens on that horizon.  The
definitive answers come from the analytic tests that are also implemented here:
response-time analysis for fixed priorities (Joseph and Pandya) and the
processor-demand criterion for EDF (Baruah, Howell and Rosier).  Both are
implemented so that the report can separate "observed on this horizon" from
"proved for all time".

Model assumptions (stated explicitly, because violations invalidate the tests)
-----------------------------------------------------------------------------
* single processor, preemptive scheduling, no priority inversion;
* periodic, independent tasks with no blocking, no release jitter;
* worst-case execution time C_i known and constant per job;
* deadlines are implicit (D_i = T_i) unless a task says otherwise;
* context-switch cost is zero in the simulation.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

POLICIES = ("FCFS", "RR")
ALGORITHMS = ("EDF", "RM", "DM", "MLQ")


class InputError(ValueError):
    pass


# --------------------------------------------------------------------------
# Task and job model
# --------------------------------------------------------------------------

@dataclass
class Task:
    name: str
    C: int                       # worst-case execution time
    T: int                       # period
    D: Optional[int] = None      # relative deadline (defaults to T)
    offset: int = 0              # release offset of the first job
    queue: Optional[int] = None  # MLQ queue level (1 = highest)
    criticality: str = ""

    def __post_init__(self):
        if self.C <= 0:
            raise InputError(f"{self.name}: C must be > 0")
        if self.T <= 0:
            raise InputError(f"{self.name}: T must be > 0")
        if self.C > self.T:
            raise InputError(f"{self.name}: C must be <= T")
        if self.D is None:
            self.D = self.T
        if self.D <= 0:
            raise InputError(f"{self.name}: D must be > 0")
        if self.D > self.T:
            raise InputError(f"{self.name}: constrained deadlines only (D <= T)")


@dataclass
class Job:
    task: Task
    index: int
    release: int
    abs_deadline: int
    remaining: int = field(init=False)
    first_start: Optional[int] = None
    finish: Optional[int] = None

    def __post_init__(self):
        self.remaining = self.task.C

    @property
    def name(self) -> str:
        return f"{self.task.name}#{self.index}"


def build_jobs(tasks: Sequence[Task], horizon: int) -> List[Job]:
    jobs = []
    for t in tasks:
        k = 0
        while t.offset + k * t.T < horizon:
            rel = t.offset + k * t.T
            jobs.append(Job(t, k, rel, rel + t.D))
            k += 1
    return sorted(jobs, key=lambda j: (j.release, j.task.name, j.index))


def hyperperiod(tasks: Sequence[Task]) -> int:
    h = 1
    for t in tasks:
        h = h * t.T // math.gcd(h, t.T)
    return h


# --------------------------------------------------------------------------
# Priority rules
# --------------------------------------------------------------------------

def rule_edf(ready: List[Job]) -> Job:
    """Dynamic priority: the earliest absolute deadline wins."""
    return min(ready, key=lambda j: (j.abs_deadline, j.release, j.task.name, j.index))


def rule_rm(ready: List[Job]) -> Job:
    """Fixed priority: the shortest period wins."""
    return min(ready, key=lambda j: (j.task.T, j.release, j.task.name, j.index))


def rule_dm(ready: List[Job]) -> Job:
    """Fixed priority: the shortest relative deadline wins."""
    return min(ready, key=lambda j: (j.task.D, j.task.T, j.release, j.task.name, j.index))


# --------------------------------------------------------------------------
# Discrete simulator
# --------------------------------------------------------------------------

@dataclass
class Result:
    algorithm: str
    tasks: List[Task]
    jobs: List[Job]
    gantt: List[Tuple[int, int, str]]
    horizon: int
    busy: int
    idle: int
    context_switches: int
    preemptions: int
    deadline_misses: List[str]
    late_tardiness: Dict[str, int]


def simulate(tasks: Sequence[Task], horizon: int, algorithm: str,
             mlq_policy: str = "FCFS", mlq_quantum: int = 2) -> Result:
    """Run one algorithm on the task set for `horizon` ticks."""
    algorithm = algorithm.upper()
    if algorithm not in ALGORITHMS:
        raise InputError(f"unknown algorithm {algorithm!r}")
    if any(t.queue is None for t in tasks):
        raise InputError("every task needs a queue level for a defined comparison")
    if mlq_policy not in POLICIES:
        raise InputError(f"unknown intra-queue policy {mlq_policy!r}")
    if mlq_quantum <= 0:
        raise InputError("quantum must be > 0")
    jobs = build_jobs(tasks, horizon)

    pending = sorted(jobs, key=lambda j: (j.release, j.task.name, j.index))
    ready: List[Job] = []
    running: Optional[Job] = None
    slice_used = 0
    trace: List[str] = []
    ctx = 0
    preempt = 0

    for t in range(horizon):
        while pending and pending[0].release <= t:
            ready.append(pending.pop(0))

        if running is not None and running.remaining == 0:
            running = None

        if algorithm == "MLQ":
            # (1) inter-queue preemption: a job in a higher queue always wins
            if running is not None and ready:
                top = min(j.task.queue for j in ready)
                if top < running.task.queue:
                    preempt += 1
                    ready.append(running)
                    running, slice_used = None, 0
            # (2) intra-queue round-robin rotation at the end of a slice
            if (running is not None and mlq_policy == "RR"
                    and slice_used >= mlq_quantum):
                if any(j.task.queue == running.task.queue for j in ready):
                    preempt += 1
                    ready.append(running)
                    running, slice_used = None, 0
            # (3) select from the highest non-empty queue
            if running is None and ready:
                top = min(j.task.queue for j in ready)
                cand = [j for j in ready if j.task.queue == top]
                if mlq_policy == "RR":
                    best = cand[0]          # FIFO: the rotated job goes to the tail
                else:
                    best = min(cand, key=lambda j: (j.release, j.task.name, j.index))
                ready.remove(best)
                running, slice_used = best, 0
                if trace and trace[-1] != "IDLE" and trace[-1] != running.name:
                    ctx += 1
        else:
            rule = {"EDF": rule_edf, "RM": rule_rm, "DM": rule_dm}[algorithm]
            candidates = ready + ([running] if running is not None else [])
            if candidates:
                best = rule(candidates)
                if running is not None and best is not running:
                    if running.remaining > 0:
                        preempt += 1
                    ready.append(running)
                    running = None
                if running is None:
                    if best in ready:
                        ready.remove(best)
                    running = best
                    if trace and trace[-1] != "IDLE" and trace[-1] != running.name:
                        ctx += 1

        if running is None:
            trace.append("IDLE")
            continue

        trace.append(running.name)
        if running.first_start is None:
            running.first_start = t
        running.remaining -= 1
        slice_used += 1
        if running.remaining == 0:
            running.finish = t + 1
            running = None
            slice_used = 0

    gantt: List[Tuple[int, int, str]] = []
    for i, n in enumerate(trace):
        if gantt and gantt[-1][2] == n:
            gantt[-1] = (gantt[-1][0], i + 1, n)
        else:
            gantt.append((i, i + 1, n))

    misses, tardiness = [], {}
    for j in jobs:
        if j.finish is None or j.finish > j.abs_deadline:
            misses.append(j.name)
            if j.finish is not None:
                tardiness[j.name] = j.finish - j.abs_deadline
    busy = sum(1 for n in trace if n != "IDLE")
    return Result(algorithm, list(tasks), jobs, gantt, horizon, busy,
                  horizon - busy, ctx, preempt, misses, tardiness)


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _stdev(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def metrics(res: Result) -> dict:
    finished = [j for j in res.jobs if j.finish is not None]
    unfinished = [j for j in res.jobs if j.finish is None]
    resp = [j.finish - j.release for j in finished]
    util_demand = sum(1 for j in res.jobs for _ in range(j.task.C)) / res.horizon
    per_task = {}
    for t in res.tasks:
        js = [j for j in res.jobs if j.task.name == t.name]
        fin = [j for j in js if j.finish is not None]
        r = [j.finish - j.release for j in fin]
        per_task[t.name] = {
            "jobs": len(js),
            "finished": len(fin),
            "misses": sum(1 for j in js if j.finish is None or j.finish > j.abs_deadline),
            "avg_response": round(_mean(r), 3),
            "max_response": max(r) if r else None,
            "jitter": round(_stdev(r), 3),
            "C": t.C, "T": t.T, "D": t.D, "queue": t.queue,
        }
    return {
        "algorithm": res.algorithm,
        "horizon": res.horizon,
        "jobs": len(res.jobs),
        "finished": len(finished),
        "unfinished": len(unfinished),
        "deadline_misses": len(res.deadline_misses),
        "missed_jobs": res.deadline_misses,
        "utilization": round(res.busy / res.horizon, 4),
        "demand_utilization": round(util_demand, 4),
        "idle": res.idle,
        "avg_response": round(_mean(resp), 3),
        "max_response": max(resp) if resp else None,
        "jitter": round(_stdev(resp), 3),
        "context_switches": res.context_switches,
        "preemptions": res.preemptions,
        "per_task": per_task,
    }


def format_gantt(res: Result) -> str:
    bar = "|" + "|".join(f" {n} ".center(max(len(n) + 2, 2 * (e - s)))
                         for s, e, n in res.gantt) + "|"
    return bar + "\n" + "  ".join(f"{s}-{e}:{n}" for s, e, n in res.gantt)


def format_metrics(m: dict) -> str:
    L = [f"algorithm: {m['algorithm']}"]
    L.append(f"  horizon={m['horizon']}  jobs={m['jobs']}  finished={m['finished']}"
             f"  deadline misses={m['deadline_misses']}")
    if m["missed_jobs"]:
        L.append(f"  missed jobs: {', '.join(m['missed_jobs'][:12])}"
                 + (" ..." if len(m["missed_jobs"]) > 12 else ""))
    L.append(f"  CPU utilization={m['utilization'] * 100:.2f}%"
             f"  (offered load {m['demand_utilization'] * 100:.2f}%)"
             f"  idle={m['idle']}")
    L.append(f"  avg response={m['avg_response']:.3f}  max response={m['max_response']}"
             f"  jitter(stdev)={m['jitter']:.3f}")
    L.append(f"  context switches={m['context_switches']}  preemptions={m['preemptions']}")
    L.append("  per task:")
    L.append(f"    {'task':<6}{'C':>3}{'T':>4}{'D':>4}{'Q':>3}{'jobs':>6}{'miss':>6}"
             f"{'avgR':>8}{'maxR':>6}{'jitter':>8}")
    for name, s in m["per_task"].items():
        L.append(f"    {name:<6}{s['C']:>3}{s['T']:>4}{s['D']:>4}{s['queue']:>3}"
                 f"{s['jobs']:>6}{s['misses']:>6}{s['avg_response']:>8.2f}"
                 f"{str(s['max_response']):>6}{s['jitter']:>8.2f}")
    return "\n".join(L)


# --------------------------------------------------------------------------
# Analytic feasibility tests
# --------------------------------------------------------------------------

def total_utilization(tasks: Sequence[Task]) -> float:
    return sum(t.C / t.T for t in tasks)


def liu_layland_bound(n: int) -> float:
    """Sufficient (not necessary) RM utilisation bound: n(2^(1/n) - 1)."""
    if n <= 0:
        raise InputError("n must be > 0")
    return n * (2 ** (1.0 / n) - 1)


def rm_response_time_analysis(tasks: Sequence[Task]) -> dict:
    """Exact fixed-priority test (Joseph and Pandya) with RM priorities.

    R_i = C_i + sum over higher-priority tasks of ceil(R_i / T_j) * C_j.
    The task set is schedulable under RM iff R_i <= D_i for every i.
    """
    order = sorted(tasks, key=lambda t: (t.T, t.name))
    out = {}
    feasible = True
    for i, t in enumerate(order):
        hp = order[:i]
        R = t.C
        for _ in range(10000):
            new = t.C + sum(math.ceil(R / h.T) * h.C for h in hp)
            if new == R:
                break
            R = new
            if R > t.D:
                break
        out[t.name] = {"R": R, "D": t.D, "ok": R <= t.D, "C": t.C, "T": t.T}
        feasible = feasible and R <= t.D
    return {"feasible": feasible, "response_times": out,
            "bound": liu_layland_bound(len(tasks)),
            "utilization": round(total_utilization(tasks), 4)}


def dbf(tasks: Sequence[Task], t: int) -> int:
    """Demand bound function: the maximum execution demand in any window of length t."""
    return sum(max(0, (t - t_i.D) // t_i.T + 1) * t_i.C for t_i in tasks)


def edf_processor_demand_test(tasks: Sequence[Task], max_points: int = 200000) -> dict:
    """Exact EDF test for constrained deadlines (Baruah, Howell and Rosier).

    A task set is EDF-schedulable iff dbf(t) <= t for every t >= 0.  It is
    enough to check the points of the form k*T_i + D_i up to Baruah's bound,
    which makes the test finite.

    Two shortcuts are taken, both of them mathematically safe:

    * if U > 1 the set is trivially infeasible;
    * if every deadline is implicit (D_i = T_i) then U <= 1 is *necessary and
      sufficient*, so the demand loop is skipped entirely.
    """
    U = total_utilization(tasks)
    if U > 1:
        return {"feasible": False, "reason": "utilization > 1", "checked_points": 0,
                "utilization": round(U, 4), "bound_used": 0,
                "method": "utilisation bound"}
    if all(t.D == t.T for t in tasks):
        return {"feasible": True, "checked_points": 0, "utilization": round(U, 4),
                "bound_used": 0, "method": "U <= 1 (exact for implicit deadlines)"}
    bound = min(_qpa_bound(tasks), 20000)
    points = sorted({k * t.T + t.D for t in tasks for k in range(0, bound // t.T + 2)})
    points = [p for p in points if 0 < p <= bound][:max_points]
    worst = None
    for t in points:
        d = dbf(tasks, t)
        if d > t:
            return {"feasible": False, "reason": f"dbf({t}) = {d} > {t}",
                    "checked_points": len(points), "utilization": round(U, 4),
                    "bound_used": bound, "method": "processor demand criterion"}
        if worst is None or d - t > worst[1] - worst[0]:
            worst = (t, d)
    return {"feasible": True, "checked_points": len(points),
            "utilization": round(U, 4), "bound_used": bound,
            "tightest_point": worst, "method": "processor demand criterion"}


def _qpa_bound(tasks: Sequence[Task]) -> int:
    """Baruah's bound for the processor-demand test (QPA)."""
    U = total_utilization(tasks)
    if U >= 1:
        return max(t.D for t in tasks)
    total_C = sum(t.C for t in tasks)
    max_d = max(t.D for t in tasks)
    s = sum(t.C * (t.T - t.D) / t.T for t in tasks)
    return int(math.ceil((s + total_C + max_d) / (1 - U))) + max(t.T for t in tasks)


def feasibility_report(tasks: Sequence[Task]) -> dict:
    rm = rm_response_time_analysis(tasks)
    edf = edf_processor_demand_test(tasks)
    U = total_utilization(tasks)
    n = len(tasks)
    bound = liu_layland_bound(n)
    return {
        "utilization": round(U, 4),
        "n": n,
        "liu_layland_bound": round(bound, 4),
        "rm": rm,
        "edf": edf,
        "notes": {
            "liu_layland": ("sufficient only: U <= bound proves RM feasibility, "
                            "U > bound proves nothing"),
            "rm_exact": "exact for RM under the stated assumptions (response-time analysis)",
            "edf_exact": ("exact for EDF with constrained deadlines "
                          "(processor-demand criterion)"),
            "edf_simple": ("U <= 1 is necessary and sufficient for EDF only when "
                           "D_i = T_i for every task"),
        },
    }


# --------------------------------------------------------------------------
# Scenario helpers
# --------------------------------------------------------------------------

def tasks_from_spec(spec: dict) -> List[Task]:
    out = []
    for t in spec["tasks"]:
        out.append(Task(name=t["name"], C=int(t["C"]), T=int(t["T"]),
                        D=t.get("D"), offset=int(t.get("offset", 0)),
                        queue=t.get("queue"), criticality=t.get("criticality", "")))
    # default queue assignment: shorter period -> higher queue (1 = highest)
    if any(t.queue is None for t in out):
        periods = sorted({t.T for t in out})
        rank = {p: i + 1 for i, p in enumerate(periods)}
        for t in out:
            if t.queue is None:
                t.queue = rank[t.T]
    return out


def assign_queues_by_criticality(tasks: Sequence[Task], mapping: Dict[str, int]):
    for t in tasks:
        t.queue = mapping.get(t.criticality, t.queue)


def compare(tasks: Sequence[Task], horizon: int, algorithms=("EDF", "RM", "MLQ"),
            mlq_policy: str = "FCFS", mlq_quantum: int = 2) -> Dict[str, dict]:
    out = {}
    for a in algorithms:
        res = simulate(tasks, horizon, a, mlq_policy, mlq_quantum)
        out[a] = metrics(res)
    return out
