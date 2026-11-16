"""Tests for the Exercise-2 comparison harness (MLQ / EDF / RM)."""
from __future__ import annotations

import json
import math
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(HERE, "..", "code"))

from rt_sched import (Task, Job, InputError, build_jobs, hyperperiod, rule_edf,   # noqa: E402
                      rule_rm, rule_dm, simulate, metrics, total_utilization,
                      liu_layland_bound, rm_response_time_analysis, dbf,
                      edf_processor_demand_test, feasibility_report,
                      tasks_from_spec, format_gantt, format_metrics)

SCN = os.path.join(ROOT, "code", "scenarios")


def load(name):
    with open(os.path.join(SCN, name), encoding="utf-8") as f:
        spec = json.load(f)
    return spec, tasks_from_spec(spec), int(spec["horizon"])


# --------------------------------------------------------------------------
# model and validation
# --------------------------------------------------------------------------

def test_task_defaults_and_validation():
    t = Task("A", 2, 5)
    assert t.D == 5 and t.offset == 0
    for bad in [(0, 5, None), (-1, 5, None), (2, 0, None), (6, 5, None)]:
        with pytest.raises(InputError):
            Task("X", bad[0], bad[1], bad[2])
    with pytest.raises(InputError):          # constrained deadlines only
        Task("X", 2, 5, 9)
    with pytest.raises(InputError):
        Task("X", 2, 5, 0)


def test_build_jobs_counts_and_deadlines():
    ts = [Task("A", 1, 5), Task("B", 2, 7)]
    jobs = build_jobs(ts, 20)
    assert len(jobs) == 4 + 3
    assert min(j.release for j in jobs) == 0
    for j in jobs:
        assert j.abs_deadline == j.release + j.task.D
        assert j.remaining == j.task.C


def test_build_jobs_respects_the_offset():
    ts = [Task("A", 1, 5, offset=3)]
    assert [j.release for j in build_jobs(ts, 20)] == [3, 8, 13, 18]


def test_hyperperiod_is_the_lcm():
    assert hyperperiod([Task("A", 1, 4), Task("B", 1, 6)]) == 12
    assert hyperperiod([Task("A", 1, 5), Task("B", 1, 7)]) == 35
    assert hyperperiod([Task("A", 1, 3), Task("B", 1, 6), Task("C", 1, 9)]) == 18


# --------------------------------------------------------------------------
# priority rules
# --------------------------------------------------------------------------

def test_edf_picks_the_earliest_absolute_deadline():
    t1, t2 = Task("far", 1, 10), Task("near", 1, 10)
    j1, j2 = Job(t1, 0, 0, 10), Job(t2, 1, 5, 9)
    assert rule_edf([j1, j2]) is j2


def test_rm_picks_the_shortest_period():
    t_short, t_long = Task("s", 1, 4), Task("l", 1, 9)
    js = Job(t_short, 0, 0, 4), Job(t_long, 1, 0, 9)
    assert rule_rm(list(js)) is js[0]


def test_dm_picks_the_shortest_relative_deadline():
    t1, t2 = Task("a", 1, 10, 9), Task("b", 1, 12, 4)
    js = Job(t1, 0, 0, 9), Job(t2, 1, 0, 4)
    assert rule_dm(list(js)) is js[1]


# --------------------------------------------------------------------------
# analytic tests
# --------------------------------------------------------------------------

def test_liu_layland_bound_values_and_limit():
    assert liu_layland_bound(1) == pytest.approx(1.0)
    assert liu_layland_bound(2) == pytest.approx(0.8284271, abs=1e-6)
    assert liu_layland_bound(3) == pytest.approx(0.7797631, abs=1e-6)
    assert liu_layland_bound(10000) == pytest.approx(math.log(2), abs=1e-3)


def test_rm_rta_matches_the_classic_hand_computation():
    """tau1: C=2,T=5 ; tau2: C=4,T=7  ->  R2 = 8 > D2 = 7, so RM fails."""
    ts = [Task("A", 2, 5), Task("B", 4, 7)]
    res = rm_response_time_analysis(ts)
    assert res["response_times"]["A"]["R"] == 2
    assert res["response_times"]["B"]["R"] == 8
    assert res["feasible"] is False
    assert total_utilization(ts) == pytest.approx(2 / 5 + 4 / 7)


def test_rm_rta_finds_a_feasible_set_above_the_liu_layland_bound():
    """U = 0.80 > 0.7568, so the bound says nothing, yet RM is feasible."""
    ts = [Task("T1", 1, 5), Task("T2", 2, 8), Task("T3", 2, 10), Task("T4", 3, 20)]
    res = rm_response_time_analysis(ts)
    assert total_utilization(ts) > res["bound"]
    assert res["feasible"] is True


def test_dbf_values():
    ts = [Task("A", 2, 5)]
    assert dbf(ts, 4) == 0
    assert dbf(ts, 5) == 2
    assert dbf(ts, 10) == 4
    assert dbf(ts, 15) == 6


def test_edf_test_rejects_utilisation_above_one():
    ts = [Task("A", 4, 8), Task("B", 4, 10), Task("C", 4, 12)]
    res = edf_processor_demand_test(ts)
    assert res["feasible"] is False and "utilization > 1" in res["reason"]


def test_edf_test_accepts_every_set_with_implicit_deadlines_below_one():
    ts = [Task("A", 2, 5), Task("B", 4, 7)]
    res = edf_processor_demand_test(ts)
    assert res["feasible"] is True
    assert "U <= 1" in res["method"]


def test_edf_demand_criterion_detects_a_constrained_deadline_failure():
    # two jobs released together, each needs 3 ticks, both deadlines at 5
    ts = [Task("A", 3, 100, 5), Task("B", 3, 100, 5)]
    res = edf_processor_demand_test(ts)
    assert res["feasible"] is False
    assert res["method"] == "processor demand criterion"


def test_feasibility_report_structure():
    ts = [Task("T1", 1, 5), Task("T2", 2, 8)]
    fr = feasibility_report(ts)
    assert set(fr) == {"utilization", "n", "liu_layland_bound", "rm", "edf", "notes"}
    assert "sufficient only" in fr["notes"]["liu_layland"]


# --------------------------------------------------------------------------
# simulator
# --------------------------------------------------------------------------

def test_simulator_is_work_conserving():
    ts = [Task("A", 2, 5, queue=1), Task("B", 2, 7, queue=2)]
    for a in ("EDF", "RM", "MLQ"):
        res = simulate(ts, 35, a)
        demand = sum(t.C * (35 // t.T) for t in ts)
        assert res.busy == min(demand, 35)
        assert res.busy + res.idle == 35


def test_gantt_covers_the_whole_horizon_and_conserves_work():
    ts = [Task("A", 1, 5, queue=1), Task("B", 2, 8, queue=2), Task("C", 3, 20, queue=3)]
    res = simulate(ts, 40, "EDF")
    assert sum(e - s for s, e, n in res.gantt) == 40
    assert sum(e - s for s, e, n in res.gantt if n != "IDLE") == res.busy


def test_edf_meets_every_deadline_of_the_fair_scenario():
    _, ts, horizon = load("scenario_A_fair.json")
    assert metrics(simulate(ts, horizon, "EDF"))["deadline_misses"] == 0
    assert metrics(simulate(ts, horizon, "RM"))["deadline_misses"] == 0


def test_measurement_agrees_with_the_analytic_verdict_on_the_stress_scenario():
    _, ts, horizon = load("scenario_B_stress.json")
    fr = feasibility_report(ts)
    m_edf = metrics(simulate(ts, horizon, "EDF"))
    m_rm = metrics(simulate(ts, horizon, "RM"))
    assert fr["rm"]["feasible"] is False and m_rm["deadline_misses"] > 0
    assert fr["edf"]["feasible"] is True and m_edf["deadline_misses"] == 0


def test_overload_produces_misses_under_every_algorithm():
    _, ts, horizon = load("scenario_D_overload.json")
    for a in ("EDF", "RM", "MLQ"):
        assert metrics(simulate(ts, horizon, a))["deadline_misses"] > 0


def test_under_overload_rm_starves_the_lowest_priority_task():
    _, ts, horizon = load("scenario_D_overload.json")
    m = metrics(simulate(ts, horizon, "RM"))
    per = m["per_task"]
    z_miss_ratio = per["Z"]["misses"] / per["Z"]["jobs"]
    x_miss_ratio = per["X"]["misses"] / per["X"]["jobs"]
    assert x_miss_ratio == 0 and z_miss_ratio > 0.5


def test_unknown_algorithm_and_bad_mlq_settings_raise():
    ts = [Task("A", 1, 5, queue=1)]
    with pytest.raises(InputError):
        simulate(ts, 10, "FIFO")
    with pytest.raises(InputError):
        simulate(ts, 10, "MLQ", mlq_policy="SJF")
    with pytest.raises(InputError):
        simulate(ts, 10, "MLQ", mlq_quantum=0)
    with pytest.raises(InputError):
        simulate([Task("A", 1, 5)], 10, "EDF")      # no queue level


def test_default_queue_assignment_follows_the_period():
    spec = {"tasks": [{"name": "slow", "C": 1, "T": 20},
                      {"name": "fast", "C": 1, "T": 5},
                      {"name": "mid", "C": 1, "T": 10}]}
    ts = tasks_from_spec(spec)
    q = {t.name: t.queue for t in ts}
    assert q == {"fast": 1, "mid": 2, "slow": 3}


def test_metrics_detect_a_missed_deadline_and_tardiness():
    ts = [Task("A", 3, 100, 5, queue=1), Task("B", 3, 100, 5, queue=1)]
    res = simulate(ts, 10, "EDF")
    m = metrics(res)
    assert m["deadline_misses"] == 1
    for j in res.jobs:
        if j.finish is not None and j.finish > j.abs_deadline:
            assert j.name in res.late_tardiness
            assert res.late_tardiness[j.name] == j.finish - j.abs_deadline


def test_mlq_rr_rotation_changes_the_schedule():
    ts = [Task("A", 4, 20, queue=1), Task("B", 4, 20, queue=1)]
    fcfs = simulate(ts, 20, "MLQ", mlq_policy="FCFS")
    rr = simulate(ts, 20, "MLQ", mlq_policy="RR", mlq_quantum=2)
    assert [n for _, _, n in fcfs.gantt][:2] == ["A#0", "B#0"]
    assert [n for _, _, n in rr.gantt][:4] == ["A#0", "B#0", "A#0", "B#0"]


def test_formatters_produce_non_empty_text():
    ts = [Task("A", 1, 5, queue=1), Task("B", 2, 7, queue=2)]
    res = simulate(ts, 35, "EDF")
    assert "|" in format_gantt(res)
    assert "algorithm: EDF" in format_metrics(metrics(res))


# --------------------------------------------------------------------------
# regression locks on the recorded numbers
# --------------------------------------------------------------------------

EXPECTED = {
    ("scenario_A_fair.json", "EDF"): {"misses": 0, "avg": 3.0, "ctx": 54},
    ("scenario_A_fair.json", "RM"): {"misses": 0, "avg": 3.105, "ctx": 57},
    ("scenario_A_fair.json", "MLQ"): {"misses": 0, "avg": 3.105, "ctx": 54},
    ("scenario_B_stress.json", "EDF"): {"misses": 0, "avg": 3.833, "ctx": 36},
    ("scenario_B_stress.json", "RM"): {"misses": 3, "avg": 4.0, "ctx": 48},
    ("scenario_B_stress.json", "MLQ"): {"misses": 3, "avg": 4.0, "ctx": 48},
    ("scenario_C_aperiodic.json", "EDF"): {"misses": 0, "avg": 10.857, "ctx": 6},
    ("scenario_C_aperiodic.json", "RM"): {"misses": 3, "avg": 13.0, "ctx": 6},
    ("scenario_C_aperiodic.json", "MLQ"): {"misses": 0, "avg": 10.857, "ctx": 7},
    ("scenario_D_overload.json", "EDF"): {"misses": 31, "avg": 18.2, "ctx": 29},
    ("scenario_D_overload.json", "RM"): {"misses": 10, "avg": 11.4, "ctx": 35},
    ("scenario_D_overload.json", "MLQ"): {"misses": 10, "avg": 11.4, "ctx": 35},
}


@pytest.mark.parametrize("key", sorted(EXPECTED))
def test_recorded_results_are_reproducible(key):
    name, algo = key
    _, ts, horizon = load(name)
    m = metrics(simulate(ts, horizon, algo))
    exp = EXPECTED[key]
    assert m["deadline_misses"] == exp["misses"]
    assert m["avg_response"] == pytest.approx(exp["avg"], abs=0.001)
    assert m["context_switches"] == exp["ctx"]
