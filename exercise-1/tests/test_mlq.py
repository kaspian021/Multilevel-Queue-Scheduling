import json, os, sys
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from mlq import QueueConfig, InputError, simulate, metrics, load_config, main

BASE = os.path.join(os.path.dirname(__file__), "..", "code", "scenarios", "baseline.json")


def run(path):
    procs, cfgs, aging = load_config(json.load(open(path)))
    return metrics(simulate(procs, cfgs, aging)[0])


def test_baseline_hand_computed_gantt():
    procs, cfgs, aging = load_config(json.load(open(BASE)))
    _, g = simulate(procs, cfgs, aging)
    assert g == [(0, 1, "P1"), (1, 3, "P2"), (3, 5, "P4"), (5, 7, "P2"), (7, 8, "P5"), (8, 11, "P3"), (11, 15, "P1")]


def test_baseline_metrics():
    rows, avg = run(BASE)
    by = {r["pid"]: r for r in rows}
    assert (by["P1"]["waiting"], by["P1"]["turnaround"], by["P1"]["response"]) == (10, 15, 0)
    assert (by["P3"]["waiting"], by["P3"]["response"]) == (6, 6)
    assert avg["waiting"] == pytest.approx(4.2) and avg["turnaround"] == pytest.approx(7.2)


def test_waiting_equals_turnaround_minus_burst_and_work_conserved():
    procs, cfgs, _ = load_config(json.load(open(BASE)))
    pl, g = simulate(procs, cfgs)
    assert sum(e - s for s, e, n in g if n != "IDLE") == sum(p.burst for p in pl)
    for r in metrics(pl)[0]:
        assert r["waiting"] == r["turnaround"] - r["burst"]


def test_idle_gap():
    cfg = {1: QueueConfig("FCFS")}
    _, g = simulate([{"pid": "A", "arrival": 3, "burst": 2, "queue": 1}], cfg)
    assert g == [(0, 3, "IDLE"), (3, 5, "A")]


def test_sjf_picks_shortest_nonpreemptive():
    cfg = {1: QueueConfig("SJF")}
    ps = [{"pid": "A", "arrival": 0, "burst": 5, "queue": 1}, {"pid": "B", "arrival": 1, "burst": 1, "queue": 1},
          {"pid": "C", "arrival": 1, "burst": 2, "queue": 1}]
    _, g = simulate(ps, cfg)
    assert [n for _, _, n in g] == ["A", "B", "C"]


def test_starvation_without_and_with_aging():
    cfg = {1: QueueConfig("FCFS"), 2: QueueConfig("FCFS")}
    ps = [{"pid": f"H{i}", "arrival": 2 * i, "burst": 2, "queue": 1} for i in range(10)]
    ps.append({"pid": "L", "arrival": 0, "burst": 1, "queue": 2})
    no_age = {r["pid"]: r for r in metrics(simulate(ps, cfg)[0])[0]}
    aged = {r["pid"]: r for r in metrics(simulate(ps, cfg, aging=4)[0])[0]}
    assert no_age["L"]["finish"] == 21          # waits for the whole high-priority stream
    assert aged["L"]["finish"] < no_age["L"]["finish"]


@pytest.mark.parametrize("bad", [
    [],
    [{"pid": "A", "arrival": 0, "burst": 0, "queue": 1}],
    [{"pid": "A", "arrival": -1, "burst": 1, "queue": 1}],
    [{"pid": "A", "arrival": 0, "burst": 1, "queue": 9}],
    [{"pid": "A", "arrival": 0, "burst": "x", "queue": 1}],
    [{"pid": "A", "arrival": 0, "burst": 1}],
    [{"pid": "A", "arrival": 0, "burst": 1, "queue": 1}, {"pid": "A", "arrival": 0, "burst": 1, "queue": 1}],
])
def test_invalid_input_rejected(bad):
    with pytest.raises(InputError):
        simulate(bad, {1: QueueConfig()})


def test_bad_policy_and_quantum():
    with pytest.raises(InputError):
        simulate([{"pid": "A", "arrival": 0, "burst": 1, "queue": 1}], {1: QueueConfig("XYZ")})
    with pytest.raises(InputError):
        simulate([{"pid": "A", "arrival": 0, "burst": 1, "queue": 1}], {1: QueueConfig("RR", 0)})


def test_cli_ok_and_missing_file(capsys, tmp_path):
    assert main([BASE, "--png", str(tmp_path / "g.png")]) == 0
    assert (tmp_path / "g.png").exists()
    assert main([str(tmp_path / "nope.json")]) == 2
