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


# ---------------------------------------------------------------- extensions
def test_rm_schedulability_is_false_and_shows_rta():
    r = rm_schedulability(TS)
    assert r["feasible"] is False
    assert r["concluded_by_bound"] is False
    assert r["response_times"]["T1"] == {"R": 1, "D": 4, "ok": True}
    assert r["response_times"]["T2"] == {"R": 4, "D": 8, "ok": True}
    assert r["response_times"]["T3"] == {"R": 14, "D": 12, "ok": False}
    assert r["liu_layland_bound"] == pytest.approx(0.7798, abs=1e-4)


def test_rm_schedulability_true_when_bound_satisfied():
    ts = [Task("A", 1, 5, 5)]
    assert rm_schedulability(ts)["feasible"] is True
    assert rm_schedulability(ts)["concluded_by_bound"] is True


def test_edf_schedulability():
    assert edf_schedulability(TS)["feasible"] is True
    assert edf_schedulability(TS)["implicit_deadlines"] is True
    over = [Task("A", 3, 4, 4), Task("B", 3, 4, 4)]
    assert edf_schedulability(over)["feasible"] is False


@pytest.mark.parametrize("algo", ["EDF", "RM"])
def test_summarize_matches_simulation(algo):
    s = summarize(TS, algo)
    assert s["horizon"] == 24
    assert s["job_count"] == 11
    assert s["busy"] == 23 and s["idle"] == 1
    assert s["total_demand"] == 23
    assert s["utilization"] == pytest.approx(23 / 24, abs=1e-6)
    assert s["timeline"] == " ".join(EDF_HAND if algo == "EDF" else RM_HAND)
    assert s["deadline_misses"] == (0 if algo == "EDF" else 1)
    assert s["missed_jobs"] == ([] if algo == "EDF"
                                else [("T3", 0, 0, 12, 14)])


def test_summarize_per_task():
    e = summarize(TS, "EDF")["per_task"]
    assert e["T1"]["avg_response"] == pytest.approx(1.0)
    assert e["T2"]["min_response"] == 4 and e["T2"]["max_response"] == 6
    assert e["T3"]["min_response"] == 10 and e["T3"]["max_response"] == 11
    m = summarize(TS, "RM")["per_task"]
    assert m["T2"]["avg_response"] == pytest.approx(4.0)
    assert m["T3"]["max_response"] == 14 and m["T3"]["misses"] == 1


@pytest.mark.parametrize("algo", ["EDF", "RM"])
def test_step_rows_cover_one_hyperperiod(algo):
    rows = step_rows(TS, algo)
    assert len(rows) == 24
    expected = EDF_HAND if algo == "EDF" else RM_HAND
    got = ["-" if r["ran"] == "IDLE" else r["ran"].split("_")[0] for r in rows]
    assert got == expected
    for r in rows:
        assert r["interval"].count("-") == 1
        assert r["reason"]


def test_step_rows_language_and_idle_reason():
    fa = step_rows(TS, "EDF", "fa")[-1]
    en = step_rows(TS, "EDF", "en")[-1]
    assert fa["ran"] == "IDLE" and "هیچ کار" in fa["reason"]
    assert "no ready job" in en["reason"]


def test_step_rows_ready_detail_mentions_job_and_deadline():
    rows = step_rows(TS, "EDF", "en")
    assert "T1_0(d=4,rem=1)" in rows[0]["ready_detail"]
    assert "T3_0(d=12,rem=4)" in rows[0]["ready_detail"]


def test_format_summary_is_stable():
    for algo in ("EDF", "RM"):
        text = format_summary(summarize(TS, algo))
        assert text.startswith(f"algorithm: {algo}")
        assert "deadline misses:" in text
        assert "timeline:" in text


def test_cli_writes_json_and_table(tmp_path):
    jf = tmp_path / "out.json"
    tf = tmp_path / "table.txt"
    rc = main_cli(["--tasks", "T1:1:4:4,T2:3:8:8,T3:4:12:12",
                   "--json", str(jf), "--table", str(tf), "--lang", "en"])
    assert rc == 0
    data = json.loads(jf.read_text(encoding="utf-8"))
    assert data["hyperperiod"] == 24
    assert data["edf"]["feasible"] is True and data["rm"]["feasible"] is False
    assert data["measured"]["RM"]["deadline_misses"] == 1
    body = tf.read_text(encoding="utf-8")
    assert "=== EDF ===" in body and "=== RM ===" in body
    assert "T1_0" in body


def test_cli_accepts_phase():
    rc = main_cli(["--tasks", "T1:1:4:4:2", "--lang", "fa"])
    assert rc == 0
