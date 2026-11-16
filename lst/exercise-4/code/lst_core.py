"""A deterministic, integer-time model of Least-Slack-Time scheduling.

This is the canonical copy of the simulation core.  It is vendored into every
exercise folder by ``tools/vendor_core.py`` so that each exercise branch is
self-contained and no branch depends on a sibling.

Model
-----
* One processor, preemptive, no overhead for a preemption (the cost is
  *counted*, not charged to the timeline, so that a hand-worked schedule and
  the simulator agree digit for digit).
* A task set is a list of periodic tasks ``(name, period, wcet, deadline,
  phase)`` where ``deadline`` is relative and defaults to the period and
  ``phase`` defaults to 0.
* Actual execution time equals WCET.  Every quantity is an **integer** number
  of time units: no floats anywhere, so results are bit-for-bit reproducible
  and a schedule computed by hand can be compared to the simulator's output
  without any tolerance.
* A job's *laxity* (slack) at time ``t`` is ``deadline - t - remaining``.
  Least Slack Time runs the ready job with the smallest laxity.

Scheduling policies
-------------------
``lst``            pure LST, ties resolved by lowest task index
``lst:edf``        LST, ties resolved by earliest absolute deadline
``lst:rm``         LST, ties resolved by shortest period
``lst:stay``       LST, ties resolved by keeping the job that just ran
``lst:lzs``        LST with the laxity-zero switch: when the minimum laxity is
                   0, run the earliest-deadline job among those at zero
``edf``            earliest deadline first
``rm``             rate monotonic
``dm``             deadline monotonic
``fifo``           earliest release first

The tie-breaking policy of LST is *not* an implementation detail.  Whether it
changes optimality, and how much it changes the preemption count, is one of the
questions the exercises ask -- so it is a parameter here, never a constant.

Optimality
----------
``exhaustive_feasible`` decides feasibility by depth-first search over every
work-conserving schedule, memoised on ``(time, remaining vector)``.  Idling is
not enumerated: with preemption free, independent jobs and known execution
times, no feasible schedule is lost by staying work-conserving.  That claim is
a lemma of the classical optimality proofs and is checked, not assumed, by
``--check-idle``.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from math import gcd
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "Task", "Job", "POLICIES", "DEFAULT_POLICY",
    "hyperperiod", "utilisation", "make_jobs", "simulate", "laxity",
    "gantt_rows", "exhaustive_feasible", "compare_policies",
]

DEFAULT_POLICY = "lst"


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Task:
    name: str
    period: int
    wcet: int
    deadline: Optional[int] = None   # relative; defaults to the period
    phase: int = 0

    @property
    def rel_deadline(self) -> int:
        return self.deadline if self.deadline is not None else self.period

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError(f"period must be positive: {self.name}")
        if self.wcet <= 0:
            raise ValueError(f"wcet must be positive: {self.name}")
        if self.wcet > self.rel_deadline:
            raise ValueError(
                f"wcet {self.wcet} exceeds relative deadline "
                f"{self.rel_deadline}: {self.name}")
        if not 0 <= self.phase < self.period:
            raise ValueError(f"phase must be in [0, period): {self.name}")


@dataclass(frozen=True)
class Job:
    index: int          # position in the job list
    task: int           # index of the owning task
    name: str           # e.g. "T1#2"
    release: int
    deadline: int       # absolute
    wcet: int


def hyperperiod(tasks: Sequence[Task]) -> int:
    """The least common multiple of the periods (with phases ignored)."""
    h = 1
    for t in tasks:
        h = h * t.period // gcd(h, t.period)
    return h


def utilisation(tasks: Sequence[Task]) -> float:
    """Total utilisation.  A float, and only ever used for reporting."""
    return sum(t.wcet / t.period for t in tasks)


def make_jobs(tasks: Sequence[Task], horizon: int) -> List[Job]:
    """Every job released strictly before ``horizon``, sorted by release."""
    jobs: List[Job] = []
    for ti, t in enumerate(tasks):
        k = 0
        while True:
            release = t.phase + k * t.period
            k += 1
            if release >= horizon:
                break
            jobs.append(Job(index=-1, task=ti, name=f"{t.name}#{k - 1}",
                            release=release,
                            deadline=release + t.rel_deadline,
                            wcet=t.wcet))
    jobs.sort(key=lambda j: (j.release, j.task))
    return [Job(i, j.task, j.name, j.release, j.deadline, j.wcet)
            for i, j in enumerate(jobs)]


def laxity(job: Job, now: int, remaining: int) -> int:
    """Slack: how long this job could still wait and still meet its deadline."""
    return job.deadline - now - remaining


# --------------------------------------------------------------------------
# policies
# --------------------------------------------------------------------------

POLICY_TIES = ("index", "edf", "rm", "stay", "lzs")
POLICIES = ("lst", "lst:edf", "lst:rm", "lst:stay", "lst:lzs",
            "edf", "rm", "dm", "fifo")


def _parse_policy(policy: str) -> Tuple[str, str]:
    if ":" in policy:
        base, _, tie = policy.partition(":")
    else:
        base, tie = policy, ("index" if policy == "lst" else "")
    if base not in ("lst", "edf", "rm", "dm", "fifo"):
        raise ValueError(f"unknown policy: {policy}")
    if base == "lst":
        if tie not in POLICY_TIES:
            raise ValueError(f"unknown LST tie-break: {tie}")
    elif tie:
        raise ValueError(f"policy {base} takes no tie-break")
    return base, tie


def _choose(tasks: Sequence[Task], jobs: Sequence[Job],
            candidates: Sequence[int], now: int, remaining: Sequence[int],
            policy: str, previous: Optional[int]) -> int:
    base, tie = _parse_policy(policy)

    if base == "fifo":
        return min(candidates, key=lambda i: (jobs[i].release, i))
    if base == "edf":
        return min(candidates, key=lambda i: (jobs[i].deadline, i))
    if base == "rm":
        return min(candidates, key=lambda i: (tasks[jobs[i].task].period, i))
    if base == "dm":
        return min(candidates,
                   key=lambda i: (tasks[jobs[i].task].rel_deadline,
                                  tasks[jobs[i].task].period, i))

    # --- least slack time -------------------------------------------------
    lax = {i: laxity(jobs[i], now, remaining[i]) for i in candidates}
    if tie == "stay" and previous is not None and previous in lax:
        if lax[previous] == min(lax.values()):
            return previous
    best = min(lax.values())
    if tie == "lzs" and best == 0:
        zeros = [i for i in candidates if lax[i] == 0]
        return min(zeros, key=lambda i: (jobs[i].deadline, i))
    if tie == "edf":
        return min((i for i in candidates if lax[i] == best),
                   key=lambda i: (jobs[i].deadline, i))
    if tie == "rm":
        return min((i for i in candidates if lax[i] == best),
                   key=lambda i: (tasks[jobs[i].task].period, i))
    return min(i for i in candidates if lax[i] == best)


# --------------------------------------------------------------------------
# simulation
# --------------------------------------------------------------------------

@dataclass
class Result:
    policy: str
    tasks: List[Task]
    horizon: int
    timeline: List[Tuple[int, Optional[str]]] = field(default_factory=list)
    jobs: List[Job] = field(default_factory=list)
    released: int = 0
    completed: int = 0
    missed: int = 0
    miss_rate: float = 0.0
    preemptions: int = 0
    context_switches: int = 0
    laxity_zero_switches: int = 0
    idle: int = 0
    busy: int = 0
    min_laxity: Optional[int] = None
    first_miss: Optional[int] = None
    responses: List[int] = field(default_factory=list)
    worst_response: Optional[int] = None
    mean_response: Optional[float] = None
    jitter: Optional[int] = None
    tie_events: int = 0

    def as_dict(self, keep_timeline: bool = True) -> dict:
        d = {k: v for k, v in self.__dict__.items()
             if k not in ("tasks", "jobs", "timeline")}
        d["tasks"] = [t.__dict__ for t in self.tasks]
        if keep_timeline:
            d["timeline"] = [[t, n] for t, n in self.timeline]
            d["jobs"] = [j.__dict__ for j in self.jobs]
        return d


def simulate(tasks: Sequence[Task], policy: str = DEFAULT_POLICY,
             horizon: Optional[int] = None,
             cycles: int = 2,
             drop_on_miss: bool = False,
             release_window: Optional[int] = None) -> Result:
    """Run one policy over ``cycles`` hyperperiods and count everything.

    ``horizon`` overrides the run length.  Only jobs released strictly before
    the horizon exist; a job whose deadline passes with work left is counted
    as missed once, and by default keeps running (an overloaded system is
    still a system worth measuring).

    ``release_window`` cuts the release window loose from the run length: with
    ``release_window=hp, horizon=hp + max_deadline`` the simulator sees exactly
    the jobs the exhaustive checker generates over one hyperperiod, plus the
    time they need to finish.  That is what makes an optimality claim
    checkable -- the two instruments must be looking at the same job set.
    """
    tasks = [Task(*t) if isinstance(t, tuple) else t for t in tasks]
    hp = hyperperiod(tasks)
    if horizon is None:
        horizon = hp * cycles
    if release_window is None:
        release_window = horizon
    jobs = make_jobs(tasks, release_window)
    n = len(jobs)

    remaining = [j.wcet for j in jobs]
    released = [False] * n
    missed = [False] * n
    finished_at = [None] * n          # type: List[Optional[int]]

    res = Result(policy=policy, tasks=list(tasks), horizon=horizon, jobs=jobs)

    previous: Optional[int] = None
    for t in range(horizon):
        for i, j in enumerate(jobs):
            if j.release <= t and not released[i]:
                released[i] = True
                res.released += 1

        # deadlines are checked before anything runs at this instant
        for i, j in enumerate(jobs):
            if released[i] and remaining[i] > 0 and t >= j.deadline \
                    and not missed[i]:
                missed[i] = True
                res.missed += 1
                if res.first_miss is None:
                    res.first_miss = t
                if drop_on_miss:
                    remaining[i] = 0

        candidates = [i for i in range(n)
                      if released[i] and remaining[i] > 0]
        if not candidates:
            res.timeline.append((t, None))
            res.idle += 1
            previous = None
            continue

        if len(candidates) > 1:
            lax = [laxity(jobs[i], t, remaining[i]) for i in candidates]
            if lax.count(min(lax)) > 1:
                res.tie_events += 1

        chosen = _choose(tasks, jobs, candidates, t, remaining, policy,
                         previous)
        lax_now = laxity(jobs[chosen], t, remaining[chosen])
        res.min_laxity = lax_now if res.min_laxity is None \
            else min(res.min_laxity, lax_now)

        if previous is not None and previous != chosen:
            if remaining[previous] > 0:
                res.preemptions += 1
            res.context_switches += 1
            if laxity(jobs[previous], t, remaining[previous]) == 0 \
                    and lax_now == 0:
                res.laxity_zero_switches += 1
        elif previous is None:
            res.context_switches += 1

        res.timeline.append((t, jobs[chosen].name))
        res.busy += 1
        remaining[chosen] -= 1
        if remaining[chosen] == 0:
            finished_at[chosen] = t + 1
            res.completed += 1
            res.responses.append(t + 1 - jobs[chosen].release)
        previous = chosen

    res.miss_rate = (res.missed / res.released) if res.released else 0.0
    if res.responses:
        res.worst_response = max(res.responses)
        res.mean_response = sum(res.responses) / len(res.responses)
        res.jitter = max(res.responses) - min(res.responses)
    return res


def gantt_rows(res: Result) -> List[Tuple[str, int, int]]:
    """Collapse the timeline into ``(job name, start, end)`` runs."""
    rows: List[Tuple[str, int, int]] = []
    for t, name in res.timeline:
        if name is None:
            continue
        if rows and rows[-1][0] == name and rows[-1][2] == t:
            rows[-1] = (name, rows[-1][1], t + 1)
        else:
            rows.append((name, t, t + 1))
    return rows


# --------------------------------------------------------------------------
# exhaustive feasibility
# --------------------------------------------------------------------------

def exhaustive_feasible(tasks: Sequence[Task], horizon: Optional[int] = None,
                        allow_idle: bool = False,
                        limit: int = 4_000_000
                        ) -> Tuple[bool, Optional[List[Optional[int]]], Dict]:
    """Is there *any* schedule that meets every deadline?

    Depth-first search over schedules, memoised on ``(time, remaining
    vector)``.  Returns ``(feasible, schedule, stats)``; the schedule is one
    entry per time unit -- a job index, or ``None`` when nothing runs.

    Two kinds of idle step exist and the difference matters:

    * **forced** -- nothing has been released yet, so the processor has no
      choice.  Always enumerated.
    * **optional** -- a job is ready and we choose to wait.  Enumerated only
      when ``allow_idle`` is set, because the exchange argument says it never
      helps: in any feasible schedule, run the ready job in the idle slot and
      idle instead at the slot the job used.  That argument is *checked*, not
      trusted -- ``lst_core.py --check-idle`` tries to refute it.
    """
    hp = hyperperiod(tasks)
    horizon = horizon if horizon is not None else hp
    jobs = make_jobs(tasks, horizon)
    n = len(jobs)
    rel = [j.release for j in jobs]
    ddl = [j.deadline for j in jobs]
    start_rem = tuple(j.wcet for j in jobs)

    memo: Dict[Tuple[int, Tuple[int, ...]], Tuple[bool, Optional[int]]] = {}
    stats = {"states": 0, "pruned": 0, "truncated": False, "limit": limit,
             "jobs": n, "horizon": horizon}

    def rec(t: int, rem: Tuple[int, ...]) -> bool:
        stats["states"] += 1
        if stats["states"] > limit:
            stats["truncated"] = True
            return False
        key = (t, rem)
        if key in memo:
            return memo[key][0]

        if all(r == 0 for r in rem):
            memo[key] = (True, None)
            return True

        # a job already past its deadline with work left kills this branch
        for i in range(n):
            if rem[i] > 0 and rel[i] <= t and rem[i] > ddl[i] - t:
                stats["pruned"] += 1
                memo[key] = (False, None)
                return False

        opts = [i for i in range(n) if rem[i] > 0 and rel[i] <= t]
        if not opts:                                  # forced idle
            ok = rec(t + 1, rem)
            memo[key] = (ok, None)
            return ok

        if allow_idle and rec(t + 1, rem):            # optional idle
            memo[key] = (True, None)
            return True

        for i in opts:
            nrem = list(rem)
            nrem[i] -= 1
            nrem_t = tuple(nrem)
            # every job still alive must remain able to meet its deadline
            bad = False
            for j in range(n):
                if nrem_t[j] > 0 and rel[j] <= t + 1 \
                        and nrem_t[j] > ddl[j] - (t + 1):
                    bad = True
                    break
            if bad:
                stats["pruned"] += 1
                continue
            if rec(t + 1, nrem_t):
                memo[key] = (True, i)
                return True

        memo[key] = (False, None)
        return False

    ok = rec(0, start_rem)
    if not ok:
        return False, None, stats

    # replay the memo forward so the returned schedule is the real one
    sched: List[Optional[int]] = []
    t, rem = 0, start_rem
    while any(r > 0 for r in rem):
        choice = memo[(t, rem)][1]
        sched.append(choice)
        if choice is not None:
            lst = list(rem)
            lst[choice] -= 1
            rem = tuple(lst)
        t += 1
        if t > sum(j.wcet for j in jobs) + horizon + 1:   # safety net
            break
    return True, sched, stats


def compare_policies(tasks: Sequence[Task],
                     policies: Sequence[str] = POLICIES,
                     horizon: Optional[int] = None,
                     cycles: int = 2) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for p in policies:
        r = simulate(tasks, p, horizon=horizon, cycles=cycles)
        d = r.as_dict(keep_timeline=False)
        d.pop("tasks", None)
        out[p] = d
    return out


# --------------------------------------------------------------------------
# command line
# --------------------------------------------------------------------------

def _demo() -> int:
    demo = [Task("T1", 6, 2), Task("T2", 8, 2), Task("T3", 12, 3)]
    print(f"task set: {[(t.name, t.period, t.wcet) for t in demo]}")
    print(f"hyperperiod {hyperperiod(demo)}, utilisation "
          f"{utilisation(demo):.3f}")
    print()
    ok, sched, stats = exhaustive_feasible(demo)
    print(f"exhaustive feasibility: {ok}  "
          f"({stats['states']} states, {stats['pruned']} pruned)")
    print()
    hdr = f"{'policy':10s} {'miss':>5s} {'pre':>5s} {'sw':>5s} {'lzs':>5s} {'minlax':>7s}"
    print(hdr)
    print("-" * len(hdr))
    for p in POLICIES:
        r = simulate(demo, p)
        print(f"{p:10s} {r.missed:5d} {r.preemptions:5d} "
              f"{r.context_switches:5d} {r.laxity_zero_switches:5d} "
              f"{r.min_laxity:7d}")
    print()
    r = simulate(demo, "lst")
    print("LST gantt (job, start, end):")
    for row in gantt_rows(r):
        print("   ", row)
    return 0


def _check_idle() -> int:
    """Verify that enumerating idle steps never adds a feasible task set."""
    import itertools
    import random
    rng = random.Random(20250101)
    checked = 0
    for _ in range(60):
        n = rng.choice([2, 3])
        tasks = []
        for i in range(n):
            p = rng.choice([3, 4, 5, 6, 8, 10, 12])
            w = rng.randint(1, max(1, p - 1))
            if sum(t.wcet for t in tasks) + w > 0 and w <= p:
                tasks.append(Task(f"T{i + 1}", p, w))
        if not tasks:
            continue
        if utilisation(tasks) > 1.0:
            continue
        hp = hyperperiod(tasks)
        if hp > 40:
            continue
        a, _, _ = exhaustive_feasible(tasks, allow_idle=False)
        b, _, _ = exhaustive_feasible(tasks, allow_idle=True)
        checked += 1
        if a != b:
            print(f"MISMATCH: {[(t.name, t.period, t.wcet) for t in tasks]} "
                  f"work-conserving={a} with-idle={b}")
            return 1
    print(f"idle enumeration changes nothing on {checked} task sets")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--demo", action="store_true", help="run the built-in demo")
    ap.add_argument("--check-idle", action="store_true",
                    help="check that enumerating idle steps never helps")
    ap.add_argument("--json", metavar="PATH",
                    help="with --demo, dump every policy's metrics here")
    args = ap.parse_args(argv)

    if args.check_idle:
        return _check_idle()
    if args.json:
        demo = [Task("T1", 6, 2), Task("T2", 8, 2), Task("T3", 12, 3)]
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(compare_policies(demo), f, indent=2, sort_keys=True)
    return _demo()


if __name__ == "__main__":
    sys.exit(main())
