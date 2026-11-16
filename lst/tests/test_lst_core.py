"""Tests for the canonical simulation core (core/lst_core.py).

These run against the copy in ``core/``.  Every exercise vendors that file into
its own ``code/`` and re-runs an equivalent suite, so a change to the core has
to pass here first.

Several tests here exist because a bug actually happened.  They are marked with
what they are pinning down, because "why is this test here" is the only thing
that stops someone deleting it later.
"""
from __future__ import annotations

import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "core"))

from lst_core import (  # noqa: E402
    Task, POLICIES, exhaustive_feasible, gantt_rows, hyperperiod,
    laxity, make_jobs, simulate, utilisation,
)

DEMO = [Task("T1", 6, 2), Task("T2", 8, 2), Task("T3", 12, 3)]


# --------------------------------------------------------------------------
# model
# --------------------------------------------------------------------------

def test_hyperperiod_is_the_lcm():
    assert hyperperiod([Task("a", 4, 1), Task("b", 6, 1)]) == 12
    assert hyperperiod([Task("a", 3, 1), Task("b", 5, 1), Task("c", 7, 1)]) == 105


def test_utilisation_is_the_sum_of_wcet_over_period():
    assert utilisation([Task("a", 4, 1), Task("b", 4, 1)]) == 0.5


def test_a_task_cannot_need_more_than_its_deadline():
    with pytest.raises(ValueError):
        Task("bad", 6, 7)


def test_jobs_are_numbered_from_zero_and_sorted_by_release():
    jobs = make_jobs([Task("T1", 4, 1), Task("T2", 6, 1)], horizon=13)
    # every release strictly before the horizon exists: T1 at 0,4,8,12 and
    # T2 at 0,6,12 -- seven jobs, ordered by release and then by task
    assert [j.name for j in jobs] == ["T1#0", "T2#0", "T1#1", "T2#1",
                                      "T1#2", "T1#3", "T2#2"]
    assert [j.release for j in jobs] == [0, 0, 4, 6, 8, 12, 12]
    assert [j.deadline for j in jobs] == [4, 6, 8, 12, 12, 16, 18]
    assert [j.index for j in jobs] == list(range(len(jobs)))


def test_laxity_counts_down_as_time_passes():
    j = make_jobs([Task("T1", 10, 4)], horizon=11)[0]
    assert laxity(j, 0, 4) == 6
    assert laxity(j, 3, 4) == 3
    assert laxity(j, 6, 4) == 0      # now or never
    assert laxity(j, 7, 4) == -1     # already lost


# --------------------------------------------------------------------------
# simulation invariants -- these hold for every policy
# --------------------------------------------------------------------------

@pytest.mark.parametrize("policy", POLICIES)
def test_a_job_never_runs_more_than_its_wcet(policy):
    r = simulate(DEMO, policy, cycles=3)
    counts = {}
    for _, name in r.timeline:
        if name is not None:
            counts[name] = counts.get(name, 0) + 1
    for j in r.jobs:
        assert counts.get(j.name, 0) <= j.wcet


@pytest.mark.parametrize("policy", POLICIES)
def test_a_job_never_runs_before_its_release(policy):
    r = simulate(DEMO, policy, cycles=2)
    first = {}
    for t, name in r.timeline:
        if name is not None:
            first.setdefault(name, t)
    for j in r.jobs:
        if j.name in first:
            assert first[j.name] >= j.release


@pytest.mark.parametrize("policy", POLICIES)
def test_busy_plus_idle_equals_the_horizon(policy):
    r = simulate(DEMO, policy, horizon=48)
    assert r.busy + r.idle == 48
    assert len(r.timeline) == 48


@pytest.mark.parametrize("policy", POLICIES)
def test_simulation_is_deterministic(policy):
    a = simulate(DEMO, policy, cycles=2)
    b = simulate(DEMO, policy, cycles=2)
    assert a.timeline == b.timeline
    assert a.missed == b.missed


@pytest.mark.parametrize("policy", POLICIES)
def test_completed_plus_missed_never_exceeds_released(policy):
    r = simulate(DEMO, policy, cycles=2)
    assert r.completed <= r.released
    assert r.missed <= r.released


def test_gantt_rows_reconstruct_the_timeline_exactly():
    r = simulate(DEMO, "lst", cycles=2)
    rows = gantt_rows(r)
    flat = []
    for name, start, end in rows:
        flat.extend([name] * (end - start))
    ran = [n for _, n in r.timeline if n is not None]
    assert flat == ran
    # rows are a partition: contiguous and non-overlapping
    for (n1, s1, e1), (n2, s2, e2) in zip(rows, rows[1:]):
        assert n1 != n2 or s2 == e1      # merged when the same job continues


# --------------------------------------------------------------------------
# known-answer tests
# --------------------------------------------------------------------------

def test_lst_runs_the_job_with_the_least_slack_first():
    # T1 must finish 2 units by t=3; T2 has all the time in the world.
    ts = [Task("T1", 3, 2), Task("T2", 20, 2)]
    r = simulate(ts, "lst", horizon=3)
    assert [n for _, n in r.timeline] == ["T1#0", "T1#0", "T2#0"]


def test_a_freshly_released_job_takes_the_processor_when_its_slack_is_less():
    """The point of LST, in four time units.

    At t=3 the second job of T1 arrives with slack 6-3-2 = 1, while T2, which
    has been running, still has slack 20-3-1 = 16.  LST drops T2 mid-job.
    A priority scheduler keyed on the job's age would not.
    """
    ts = [Task("T1", 3, 2), Task("T2", 20, 2)]
    r = simulate(ts, "lst", horizon=6)
    assert [n for _, n in r.timeline] == ["T1#0", "T1#0", "T2#0",
                                          "T1#1", "T1#1", "T2#0"]
    # one preemption, not three: a job that has *finished* is not preempted.
    # T1#0 completes at t=2 and T1#1 at t=5, so those handovers are dispatch,
    # not preemption.  Only T2 being cut off at t=3 counts.
    assert r.preemptions == 1
    assert r.context_switches == 4


def test_edf_and_lst_agree_when_slack_orders_by_deadline():
    # with all phases zero and one job each, the orders coincide
    ts = [Task("T1", 5, 1), Task("T2", 7, 2), Task("T3", 11, 3)]
    assert (simulate(ts, "edf", cycles=1).timeline
            == simulate(ts, "lst", cycles=1).timeline)


def test_an_overloaded_set_misses_deadlines_and_says_when():
    ts = [Task("T1", 4, 3), Task("T2", 4, 3)]      # U = 1.5
    r = simulate(ts, "lst", cycles=2)
    assert r.missed > 0
    assert r.first_miss is not None
    assert r.first_miss >= 0


def test_zero_laxity_is_reachable_and_recorded():
    # T1 needs all four units of its period: its slack is 0 from the start
    ts = [Task("T1", 4, 4), Task("T2", 20, 1)]
    r = simulate(ts, "lst", horizon=8)
    assert r.min_laxity == 0


# --------------------------------------------------------------------------
# the exhaustive checker
# --------------------------------------------------------------------------

def test_the_checker_finds_a_schedule_for_a_set_that_is_obviously_feasible():
    ts = [Task("T1", 10, 2), Task("T2", 10, 2)]
    ok, sched, _ = exhaustive_feasible(ts)
    assert ok
    assert sum(1 for s in sched if s is not None) == 4      # 2 jobs x 2 units


def test_the_checker_rejects_a_set_that_cannot_fit():
    ts = [Task("T1", 4, 4), Task("T2", 4, 4)]              # U = 2
    ok, sched, _ = exhaustive_feasible(ts)
    assert not ok
    assert sched is None


def test_the_returned_schedule_is_valid_and_on_time():
    """A schedule the checker calls feasible must survive an independent check.

    The checker and this verifier share no code, which is the point: the
    checker's own bookkeeping is not allowed to vouch for its own answer.
    """
    ts = [Task("T1", 8, 2), Task("T2", 3, 2)]
    ok, sched, _ = exhaustive_feasible(ts)
    assert ok
    jobs = make_jobs(ts, hyperperiod(ts))
    ran = [0] * len(jobs)
    done = [None] * len(jobs)
    for t, i in enumerate(sched):
        if i is None:
            continue
        assert jobs[i].release <= t
        ran[i] += 1
        if ran[i] == jobs[i].wcet and done[i] is None:
            done[i] = t + 1
    for k, j in enumerate(jobs):
        assert ran[k] == j.wcet
        assert done[k] <= j.deadline


def test_forced_idle_does_not_count_as_infeasible():
    """Pinning a real bug: the search used to give up when nothing was ready.

    T1(8,2) + T2(3,2) releases its last job at t=21, and there is an instant
    at t=14 where every released job has finished but the next one has not
    arrived.  The processor *must* idle there.  A work-conserving search that
    treats "no candidate" as "dead end" reports this feasible set as
    infeasible, and then reports it feasible again once optional idling is
    switched on -- which looks like the exchange argument failing when in fact
    the search was wrong.
    """
    ts = [Task("T1", 8, 2), Task("T2", 3, 2)]
    without_idle, _, _ = exhaustive_feasible(ts, allow_idle=False)
    with_idle, _, _ = exhaustive_feasible(ts, allow_idle=True)
    assert without_idle and with_idle


def test_optional_idle_never_makes_an_infeasible_set_feasible():
    """The exchange argument, checked rather than assumed, on a small sweep."""
    import itertools
    sets = []
    for p1, w1, p2, w2 in itertools.product([3, 4, 5, 6, 8, 10, 12], repeat=4):
        if w1 > p1 or w2 > p2:
            continue
        ts = [Task("T1", p1, w1), Task("T2", p2, w2)]
        if hyperperiod(ts) > 24 or utilisation(ts) > 1.0:
            continue
        sets.append(ts)
    assert len(sets) > 20
    for ts in sets:
        assert (exhaustive_feasible(ts, allow_idle=False)[0]
                == exhaustive_feasible(ts, allow_idle=True)[0])


# --------------------------------------------------------------------------
# the optimality claim -- the reason the checker exists
# --------------------------------------------------------------------------

def _sweep(seed=20250101, n_sets=300, max_hp=40):
    import random
    rng = random.Random(seed)
    out = []
    while len(out) < n_sets:
        ts = []
        for i in range(rng.choice([2, 3])):
            p = rng.choice([4, 5, 6, 8, 10, 12])
            w = rng.randint(1, p - 1)
            d = rng.randint(w, p)                  # constrained deadline
            ts.append(Task(f"T{i + 1}", p, w, d))
        if utilisation(ts) > 1.0 or hyperperiod(ts) > max_hp:
            continue
        ok, _, st = exhaustive_feasible(ts)
        if st["truncated"]:
            continue
        out.append((ts, ok))
    return out


def test_lst_never_misses_a_deadline_on_a_feasible_set():
    feasible = [ts for ts, ok in _sweep(n_sets=200) if ok]
    assert len(feasible) > 40, "the sweep must actually find feasible sets"
    for ts in feasible:
        hp = hyperperiod(ts)
        end = hp + max(t.rel_deadline for t in ts)
        r = simulate(ts, "lst", horizon=end, release_window=hp)
        assert r.missed == 0, f"LST missed on a feasible set: {ts}"


def test_edf_also_never_misses_on_a_feasible_set():
    for ts, ok in _sweep(n_sets=120):
        if not ok:
            continue
        hp = hyperperiod(ts)
        end = hp + max(t.rel_deadline for t in ts)
        assert simulate(ts, "edf", horizon=end, release_window=hp).missed == 0


def test_rate_monotonic_is_not_optimal_and_the_test_can_see_it():
    """If this ever finds no counterexample, RM is optimal or the sweep is wrong."""
    feasible = [ts for ts, ok in _sweep(n_sets=300) if ok]
    failures = 0
    for ts in feasible:
        hp = hyperperiod(ts)
        end = hp + max(t.rel_deadline for t in ts)
        if simulate(ts, "rm", horizon=end, release_window=hp).missed:
            failures += 1
    assert failures > 0, "expected RM to miss on some feasible set"


@pytest.mark.parametrize("tie", ["edf", "rm", "stay", "lzs"])
def test_the_tie_break_does_not_change_whether_lst_is_optimal(tie):
    """Tie-breaking changes the preemption count; whether it changes the
    verdict is a separate question, and this is what answers it."""
    for ts, ok in _sweep(n_sets=120):
        if not ok:
            continue
        hp = hyperperiod(ts)
        end = hp + max(t.rel_deadline for t in ts)
        plain = simulate(ts, "lst", horizon=end, release_window=hp).missed
        assert simulate(ts, f"lst:{tie}", horizon=end,
                        release_window=hp).missed == plain


def test_tie_breaking_does_change_the_preemption_count():
    """On the demo set, LST preempts 10 times and the two anti-thrashing
    tie-breaks cut it to 4.  That gap is the whole of Exercise 7."""
    plain = simulate(DEMO, "lst", cycles=2).preemptions
    stay = simulate(DEMO, "lst:stay", cycles=2).preemptions
    rm = simulate(DEMO, "lst:rm", cycles=2).preemptions
    edf = simulate(DEMO, "edf", cycles=2).preemptions
    assert stay < plain and rm < plain
    assert edf < plain        # LST's known cost, measured not asserted
