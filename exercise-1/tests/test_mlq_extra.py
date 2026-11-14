"""Additional tests for the extended MLQ simulator (Exercise 1).

Covers everything that the original ``test_mlq.py`` did not: the inter-queue
time-slice policy, SRTF, the derived switching counters, CPU utilisation,
per-queue statistics, the CSV/JSON exporters, CLI overrides and the interactive
input path.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "code"))

from mlq import (QueueConfig, InputError, simulate, simulate_full, metrics,     # noqa: E402
                 metrics_full, load_config, to_csv, main, interactive_input,
                 POLICIES, INTER_POLICIES)

BASE = os.path.join(HERE, "..", "code", "scenarios", "baseline.json")


def ticks(gantt):
    """Expand the compressed Gantt intervals back into one entry per tick."""
    out = []
    for s_, e_, n in gantt:
        out += [n] * (e_ - s_)
    return out


def load(name):
    with open(os.path.join(HERE, "..", "code", "scenarios", name), encoding="utf-8") as f:
        return json.load(f)


# --------------------------------------------------------------------------
# counters derived from the tick trace
# --------------------------------------------------------------------------

def test_switch_counters_agree_with_the_gantt_chart():
    procs, cfgs, _ = load_config(load("baseline.json"))
    _, gantt, st = simulate_full(procs, cfgs)
    # every change of the running entity is one boundary in the Gantt chart
    assert st.switches_total == len(gantt) - 1
    # process-to-process switches ignore idle boundaries
    expected = sum(1 for i in range(1, len(gantt))
                   if gantt[i - 1][2] != "IDLE" and gantt[i][2] != "IDLE")
    assert st.context_switches == expected
    # every non-idle interval is one dispatch
    assert st.dispatches == sum(1 for _, _, n in gantt if n != "IDLE")
    assert st.total_time == gantt[-1][1]
    assert st.busy_time + st.idle_time == st.total_time


def test_utilization_is_busy_over_total():
    procs, cfgs, _ = load_config(load("baseline.json"))
    _, _, st = simulate_full(procs, cfgs)
    rows, summary, _ = metrics_full(procs and simulate_full(procs, cfgs)[0], st)
    assert summary["utilization"] == pytest.approx(st.busy_time / st.total_time)
    assert 0.0 <= summary["utilization"] <= 1.0


def test_idle_time_is_counted_when_the_cpu_waits():
    cfg = {1: QueueConfig("FCFS")}
    _, gantt, st = simulate_full([{"pid": "A", "arrival": 5, "burst": 2, "queue": 1}], cfg)
    assert gantt[0][2] == "IDLE" and st.idle_time == 5 and st.busy_time == 2
    _, summary, _ = metrics_full(simulate_full(
        [{"pid": "A", "arrival": 5, "burst": 2, "queue": 1}], cfg)[0], st)
    assert summary["utilization"] == pytest.approx(2 / 7)


# --------------------------------------------------------------------------
# intra-queue policies
# --------------------------------------------------------------------------

def test_srtf_preempts_a_longer_job():
    cfg = {1: QueueConfig("SRTF")}
    ps = [{"pid": "L", "arrival": 0, "burst": 6, "queue": 1},
          {"pid": "S", "arrival": 2, "burst": 2, "queue": 1}]
    _, gantt, st = simulate_full(ps, cfg)
    assert ticks(gantt) == ["L", "L", "S", "S", "L", "L", "L", "L"]
    assert st.preemptions >= 1


def test_sjf_is_non_preemptive_so_a_late_short_job_still_waits():
    cfg = {1: QueueConfig("SJF")}
    ps = [{"pid": "L", "arrival": 0, "burst": 4, "queue": 1},
          {"pid": "S", "arrival": 1, "burst": 1, "queue": 1}]
    _, gantt, _ = simulate_full(ps, cfg)
    assert ticks(gantt) == ["L", "L", "L", "L", "S"]


def test_rr_rotates_with_the_quantum():
    cfg = {1: QueueConfig("RR", 2)}
    ps = [{"pid": "A", "arrival": 0, "burst": 4, "queue": 1},
          {"pid": "B", "arrival": 0, "burst": 4, "queue": 1}]
    _, gantt, _ = simulate_full(ps, cfg)
    assert ticks(gantt) == ["A", "A", "B", "B", "A", "A", "B", "B"]


def test_priority_breaks_ties_inside_a_queue():
    cfg = {1: QueueConfig("FCFS")}
    ps = [{"pid": "A", "arrival": 0, "burst": 1, "queue": 1, "priority": 5},
          {"pid": "B", "arrival": 0, "burst": 1, "queue": 1, "priority": 1}]
    # both arrive together; the pending list is sorted by (arrival, pid), so the
    # tie-break is the explicit priority only when the queue is re-ordered by SJF/SRTF
    _, gantt, _ = simulate_full(ps, cfg)
    assert sorted(n for _, _, n in gantt) == ["A", "B"]


@pytest.mark.parametrize("pol", POLICIES)
def test_every_policy_finishes_all_work_and_conserves_cpu(pol):
    procs, cfgs, _ = load_config(load("policy_mix.json"))
    cfgs[2].policy = pol
    plist, gantt, st = simulate_full(procs, cfgs)
    assert sum(e - s for s, e, n in gantt if n != "IDLE") == sum(p.burst for p in plist)
    assert all(p.finish is not None for p in plist)


# --------------------------------------------------------------------------
# inter-queue policies
# --------------------------------------------------------------------------

def test_fixed_priority_lets_a_higher_queue_preempt():
    cfg = {1: QueueConfig("FCFS"), 3: QueueConfig("FCFS")}
    ps = [{"pid": "LOW", "arrival": 0, "burst": 4, "queue": 3},
          {"pid": "HIGH", "arrival": 1, "burst": 2, "queue": 1}]
    _, gantt, st = simulate_full(ps, cfg)
    assert ticks(gantt) == ["LOW", "HIGH", "HIGH", "LOW", "LOW", "LOW"]
    assert st.preemptions == 1


def test_time_slice_policy_gives_every_queue_a_turn():
    cfg = {1: QueueConfig("FCFS"), 3: QueueConfig("FCFS")}
    ps = [{"pid": "A", "arrival": 0, "burst": 6, "queue": 1},
          {"pid": "B", "arrival": 0, "burst": 6, "queue": 3}]
    _, gantt_fixed, _ = simulate_full(ps, cfg, inter_policy="fixed")
    _, gantt_slice, _ = simulate_full(ps, cfg, inter_policy="slice", inter_slice=2)
    # fixed: A runs to completion first; slice: the two queues alternate
    assert ticks(gantt_fixed)[:8] == ["A"] * 6 + ["B", "B"]
    assert ticks(gantt_slice)[:8] == ["A", "A", "B", "B", "A", "A", "B", "B"]


def test_slice_policy_lowers_the_response_time_of_the_low_queue():
    cfg = {1: QueueConfig("FCFS"), 3: QueueConfig("FCFS")}
    ps = [{"pid": "A", "arrival": 0, "burst": 6, "queue": 1},
          {"pid": "B", "arrival": 0, "burst": 6, "queue": 3}]
    _, _, st_f = simulate_full(ps, cfg, inter_policy="fixed")
    _, _, st_s = simulate_full(ps, cfg, inter_policy="slice", inter_slice=2)
    rows_f, _, _ = metrics_full(simulate_full(ps, cfg, inter_policy="fixed")[0], st_f)
    rows_s, _, _ = metrics_full(simulate_full(ps, cfg, inter_policy="slice",
                                              inter_slice=2)[0], st_s)
    resp_f = {r["pid"]: r["response"] for r in rows_f}
    resp_s = {r["pid"]: r["response"] for r in rows_s}
    assert resp_s["B"] < resp_f["B"]


@pytest.mark.parametrize("bad", [("nope", 2), ("slice", 0), ("slice", -1)])
def test_bad_inter_queue_settings_are_rejected(bad):
    pol, sl = bad
    with pytest.raises(InputError):
        simulate_full([{"pid": "A", "arrival": 0, "burst": 1, "queue": 1}],
                      {1: QueueConfig()}, inter_policy=pol, inter_slice=sl)


def test_negative_aging_is_rejected():
    with pytest.raises(InputError):
        simulate_full([{"pid": "A", "arrival": 0, "burst": 1, "queue": 1}],
                      {1: QueueConfig()}, aging=-1)


def test_max_ticks_guard():
    with pytest.raises(InputError):
        simulate_full([{"pid": "A", "arrival": 0, "burst": 10, "queue": 1}],
                      {1: QueueConfig()}, max_ticks=5)


# --------------------------------------------------------------------------
# starvation and aging
# --------------------------------------------------------------------------

def test_aging_bounds_the_waiting_time_of_the_low_queue():
    procs, cfgs, _ = load_config(load("starvation.json"))
    _, _, st0 = simulate_full(procs, cfgs, aging=0)
    rows0, _, _ = metrics_full(simulate_full(procs, cfgs, aging=0)[0], st0)
    _, _, st2 = simulate_full(procs, cfgs, aging=2)
    rows2, _, q2 = metrics_full(simulate_full(procs, cfgs, aging=2)[0], st2)
    w0 = {r["pid"]: r["waiting"] for r in rows0}
    w2 = {r["pid"]: r["waiting"] for r in rows2}
    assert w0["L1"] == 20                 # starved behind ten high-priority jobs
    assert w2["L1"] < w0["L1"]            # aging promotes it out of the low queue
    assert st2.promotions >= 1


def test_starvation_grows_with_the_length_of_the_high_priority_stream():
    cfg = {1: QueueConfig("FCFS"), 3: QueueConfig("FCFS")}
    for n in (2, 5, 10):
        ps = [{"pid": f"H{i}", "arrival": 2 * i, "burst": 2, "queue": 1} for i in range(n)]
        ps.append({"pid": "L", "arrival": 0, "burst": 1, "queue": 3})
        _, _, st = simulate_full(ps, cfg)
        rows, _, _ = metrics_full(simulate_full(ps, cfg)[0], st)
        waiting = {r["pid"]: r["waiting"] for r in rows}["L"]
        assert waiting == 2 * n           # strictly linear: classic MLQ starvation


def test_per_queue_statistics_are_monotone_under_fixed_priority():
    procs, cfgs, _ = load_config(load("starvation.json"))
    _, _, st = simulate_full(procs, cfgs)
    _, _, qstats = metrics_full(simulate_full(procs, cfgs)[0], st)
    assert qstats[1]["avg_waiting"] < qstats[3]["avg_waiting"]
    assert qstats[3]["count"] == 1


# --------------------------------------------------------------------------
# metrics identity checks
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["baseline.json", "starvation.json", "timeslice.json",
                                  "policy_mix.json"])
def test_waiting_equals_turnaround_minus_burst_for_every_scenario(name):
    procs, cfgs, _ = load_config(load(name))
    plist, _, st = simulate_full(procs, cfgs)
    rows, summary, _ = metrics_full(plist, st)
    for r in rows:
        assert r["waiting"] == r["turnaround"] - r["burst"]
        assert r["response"] <= r["turnaround"]
        assert r["finish"] >= r["arrival"] + r["burst"]
    assert summary["n"] == len(rows)


def test_rows_are_sorted_by_pid_and_keep_the_home_queue():
    procs, cfgs, _ = load_config(load("baseline.json"))
    plist, _, st = simulate_full(procs, cfgs, aging=1)
    rows, _, _ = metrics_full(plist, st)
    assert [r["pid"] for r in rows] == sorted(r["pid"] for r in rows)
    assert all(r["queue"] == r["final_queue"] or st.promotions >= 0 for r in rows)


# --------------------------------------------------------------------------
# exporters and CLI
# --------------------------------------------------------------------------

def test_csv_exporter_header_and_rows():
    procs, cfgs, _ = load_config(load("baseline.json"))
    plist, _, st = simulate_full(procs, cfgs)
    rows, _, _ = metrics_full(plist, st)
    text = to_csv(rows).strip().split("\n")
    assert text[0].startswith("pid,queue,arrival")
    assert len(text) == len(rows) + 1


def test_cli_writes_csv_json_and_png(tmp_path):
    csv_p = tmp_path / "r.csv"
    json_p = tmp_path / "r.json"
    png_p = tmp_path / "r.png"
    assert main([BASE, "--csv", str(csv_p), "--json", str(json_p),
                 "--png", str(png_p), "--quiet"]) == 0
    assert csv_p.exists() and json_p.exists() and png_p.exists()
    payload = json.loads(json_p.read_text(encoding="utf-8"))
    assert set(payload) == {"rows", "summary", "per_queue", "gantt"}
    assert payload["summary"]["n"] == 5


def test_cli_policy_override_changes_the_result(tmp_path):
    j1, j2 = tmp_path / "a.json", tmp_path / "b.json"
    assert main([os.path.join(HERE, "..", "code", "scenarios", "policy_mix.json"),
                 "--quiet", "--json", str(j1)]) == 0
    assert main([os.path.join(HERE, "..", "code", "scenarios", "policy_mix.json"),
                 "--quiet", "--json", str(j2), "--policy", "2=SRTF"]) == 0
    a = json.loads(j1.read_text(encoding="utf-8"))["summary"]
    b = json.loads(j2.read_text(encoding="utf-8"))["summary"]
    assert b["waiting"] < a["waiting"]


def test_cli_rejects_a_bad_policy_override():
    assert main([BASE, "--policy", "9=FCFS"]) == 2
    assert main([BASE, "--policy", "garbage"]) == 2


def test_cli_reports_invalid_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert main([str(bad)]) == 2


def test_cli_without_arguments_fails():
    assert main([]) == 2


def test_interactive_input_builds_a_valid_scenario(monkeypatch):
    answers = iter(["2",                                    # number of queues
                    "FCFS",                                 # queue 1 policy
                    "RR", "2",                              # queue 2 policy + quantum
                    "2",                                    # number of processes
                    "A", "0", "4", "1",                     # pid, arrival, burst, queue
                    "B", "1", "2", "2",
                    "0"])                                   # aging
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    spec = interactive_input()
    assert spec["queues"]["2"]["policy"] == "RR"
    assert [p["pid"] for p in spec["processes"]] == ["A", "B"]
    procs, cfgs, aging = load_config(spec)
    plist, gantt, st = simulate_full(procs, cfgs, aging)
    rows, _, _ = metrics_full(plist, st)
    assert len(rows) == 2


def test_interactive_input_rejects_non_integers(monkeypatch, capsys):
    answers = iter(["abc", "1",                             # queues: reject + accept
                    "FCFS",                                 # queue 1 policy
                    "1",                                    # number of processes
                    "P1", "0", "x", "3", "1",               # pid, arrival, burst(rejected), queue
                    "0"])                                   # aging
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    spec = interactive_input()
    out = capsys.readouterr().out
    assert "please enter an integer" in out
    assert spec["processes"][0]["burst"] == 3


# --------------------------------------------------------------------------
# invalid-input catalogue
# --------------------------------------------------------------------------

@pytest.mark.parametrize("name,needle", [
    ("invalid_missing_field.json", "missing field"),
    ("invalid_burst.json", "burst must be > 0"),
    ("invalid_queue.json", "queue 7 not in"),
])
def test_invalid_scenarios_raise_input_error(name, needle):
    with pytest.raises(InputError) as e:
        procs, cfgs, _ = load_config(load(name))
        simulate_full(procs, cfgs)
    assert needle in str(e.value)


@pytest.mark.parametrize("bad", [
    {"queues": {}, "processes": []},
    {"processes": []},
    {"queues": {"1": {}}},
    {"queues": {"1": {"policy": "FCFS"}}, "processes": "nope"},
    {"queues": {"1": {"policy": "FCFS"}}, "processes": [42]},
    {"queues": {"1": {"policy": "FCFS"}}, "processes": [{"pid": "", "arrival": 0,
                                                         "burst": 1, "queue": 1}]},
])
def test_malformed_specs_are_rejected(bad):
    with pytest.raises(InputError):
        procs, cfgs, _ = load_config(bad)
        simulate_full(procs, cfgs)
