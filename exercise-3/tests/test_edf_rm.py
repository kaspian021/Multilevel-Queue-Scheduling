import os, sys, pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from edf_rm import *

TS = [Task("T1", 1, 4, 4), Task("T2", 3, 8, 8), Task("T3", 4, 12, 12)]
EDF_HAND = "T1 T2 T2 T2 T1 T3 T3 T3 T1 T3 T2 T2 T1 T2 T3 T3 T1 T2 T2 T2 T1 T3 T3 -".split()
RM_HAND = "T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 -".split()


def names(tl):
    return [TS[x].name if x is not None else "-" for x in tl]


def test_basic_numbers():
    assert hyperperiod(TS) == 24
    assert utilization(TS) == pytest.approx(23 / 24)
    assert rm_bound(3) == pytest.approx(0.7798, abs=1e-4)


def test_edf_matches_hand_solution_no_miss():
    tl, _, miss = simulate(TS, "EDF")
    assert names(tl) == EDF_HAND and miss == [] and idle_time(tl) == 1


def test_rm_matches_hand_solution_one_miss():
    tl, jobs, miss = simulate(TS, "RM")
    assert names(tl) == RM_HAND and idle_time(tl) == 1
    assert [(TS[j.task].name, j.k, j.deadline, j.finish) for j in miss] == [("T3", 0, 12, 14)]


def test_rta_agrees_with_simulation():
    assert response_time_analysis(TS) == {"T1": 1, "T2": 4, "T3": 14}


def test_total_busy_time_equals_total_work_both():
    for a in ("EDF", "RM"):
        tl, _, _ = simulate(TS, a)
        assert 24 - idle_time(tl) == 6 * 1 + 3 * 3 + 2 * 4


def test_edf_feasible_when_u_le_1_rm_fails_classic_set():
    ts = [Task("A", 2, 5, 5), Task("B", 4, 7, 7)]
    assert simulate(ts, "EDF")[2] == []
    assert simulate(ts, "RM")[2] != []


def test_segments():
    assert segments([0, 0, None, 1]) == [(0, 2, 0), (2, 3, None), (3, 4, 1)]


@pytest.mark.parametrize("bad", [[], [Task("x", 0, 4, 4)], [Task("x", 5, 4, 4)], [Task("x", 1, 4, 4, -1)]])
def test_invalid(bad):
    with pytest.raises(ValueError):
        simulate(bad, "EDF")


def test_bad_algo():
    with pytest.raises(ValueError):
        simulate(TS, "FOO")


@pytest.mark.parametrize("algo", ["EDF", "RM"])
def test_trace_matches_simulation(algo):
    tl, _, _ = simulate(TS, algo)
    lg = trace(TS, algo)
    got = [None if c is None else c[0] for _, _, c in lg]
    assert got == [None if x is None else TS[x].name for x in tl]
