"""Tests for Exercise 7: readers and writers.

    python3 -m pytest tests -q       (from the exercise folder)

The tests come in three layers, and they are meant to disagree with each other
in an informative way when something is wrong:

1. the **model checker**, which proves statements about every interleaving of
   a two- or three-process protocol;
2. the **locks**, run on real threads and checked continuously, which is where
   an implementation bug shows up as a violation within a second;
3. the **primitives** underneath both, whose properties the verdicts above
   depend on -- a semaphore that lets a newcomer barge would quietly
   invalidate every fairness result, so it is tested directly.
"""

from __future__ import annotations

import os
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CODE = os.path.join(ROOT, "code")
sys.path.insert(0, CODE)
sys.path.insert(0, HERE)

import rw_model as rm        # noqa: E402
import rw_sync as rs         # noqa: E402


# =========================================================== the model checker

def _verdicts(name: str) -> dict:
    sol = rm.SOLUTIONS[name]
    return rm.explore(sol, max_states=600_000,
                      stop_on_violation=(sol.family == "broken"))


@pytest.mark.parametrize("name", sorted(rm.SOLUTIONS))
def test_model_is_exhaustive(name):
    """No verdict may rest on a truncated state space. A truncated run can
    only prove a property false, never true, so every row in the report has to
    be complete. The broken solution is the one exception, and it is an
    exception by design: it stops at its first witness, which is a proof that
    the invariant fails, not a survey of what happens afterwards."""
    r = _verdicts(name)
    if name == "rw_broken_count":
        assert r["truncated"], "the broken solution should stop at its witness"
        return
    assert not r["truncated"], f"{name} was truncated at {r['states']} states"


@pytest.mark.parametrize("name", [
    "semaphore_mutex", "monitor_mesa_mutex", "monitor_fifo_mutex",
    "dekker_mutex", "peterson_mutex",
    "rw_readers_pref", "rw_writers_pref", "rw_writers_pref_2w", "rw_fair",
    "rw_barrier", "rw_monitor_mesa", "rw_monitor_fifo",
    "rw_dekker", "rw_dekker_2readers", "rw_peterson", "rw_peterson_2readers",
])
def test_model_solutions_are_safe(name):
    r = _verdicts(name)
    assert r["rw_safety"], f"{name} let a writer in beside somebody else"
    assert r["deadlock_free"], f"{name} deadlocked"


def test_broken_solution_is_caught():
    """The negative control: one comparison away from the correct solution and
    the invariant collapses. If this ever passes, the checker is not looking."""
    r = _verdicts("rw_broken_count")
    assert not r["rw_safety"]
    assert r["rw_safety_witness"], "a violation must come with a witness"


@pytest.mark.parametrize("name", [
    "semaphore_mutex", "dekker_mutex", "peterson_mutex", "monitor_fifo_mutex",
    "rw_writers_pref", "rw_fair", "rw_barrier",
    "rw_dekker", "rw_dekker_2readers", "rw_peterson", "rw_peterson_2readers",
])
def test_model_starvation_free(name):
    r = _verdicts(name)
    assert all(r["starvation_free"].values()), (
        f"{name} starves {[k for k, v in r['starvation_free'].items() if not v]}")


def test_readers_preference_starves_the_writer():
    """Two readers can keep the count above zero for ever, so the writer never
    gets in. The starved process is the writer; the readers are fine."""
    r = _verdicts("rw_readers_pref")
    roles = r["roles"]
    starved = {k for k, v in r["starvation_free"].items() if not v}
    assert starved == {str(i) for i, role in enumerate(roles) if role == "W"}
    assert r["concurrent_reads_admitted"]


def test_writers_preference_needs_two_writers_to_starve_a_reader():
    """With one writer the reader door reopens every time, so nothing starves;
    add a second writer and the reader is the one that never gets in."""
    one = _verdicts("rw_writers_pref")
    assert all(one["starvation_free"].values())
    two = _verdicts("rw_writers_pref_2w")
    starved = {k for k, v in two["starvation_free"].items() if not v}
    assert starved == {str(i) for i, role in enumerate(two["roles"])
                       if role == "R"}


def test_mesa_monitor_does_not_bound_waiting():
    """A notified thread has to re-compete for the monitor lock and a newcomer
    can overtake it, so the plain Mesa monitor starves everybody. Handing the
    woken thread a place in the entry queue is what fixes it."""
    mesa = _verdicts("rw_monitor_mesa")
    assert not all(mesa["starvation_free"].values())
    fifo = _verdicts("rw_monitor_fifo")
    starved = {k for k, v in fifo["starvation_free"].items() if not v}
    assert starved == {str(i) for i, role in enumerate(fifo["roles"])
                       if role == "W"}


@pytest.mark.parametrize("name", [
    "semaphore_mutex", "monitor_mesa_mutex", "monitor_fifo_mutex",
    "dekker_mutex", "peterson_mutex", "rw_dekker", "rw_peterson",
])
def test_mutexes_never_admit_two_at_once(name):
    """The whole reason the problem is interesting: every plain mutual
    exclusion solution satisfies the safety properties and still fails the one
    that matters."""
    r = _verdicts(name)
    assert not r["concurrent_reads_admitted"]


@pytest.mark.parametrize("name", [
    "rw_readers_pref", "rw_writers_pref", "rw_fair", "rw_barrier",
    "rw_monitor_mesa", "rw_monitor_fifo",
    "rw_dekker_2readers", "rw_peterson_2readers",
])
def test_readers_writers_solutions_admit_concurrent_reads(name):
    r = _verdicts(name)
    assert r["concurrent_reads_admitted"], f"{name} never let two readers in"


def test_two_process_locks_can_still_host_the_pattern():
    """Dekker and Peterson are written for two participants, and that is the
    whole limitation -- not that they cannot carry the readers pattern, but
    that two is all they have."""
    for name in ("rw_dekker_2readers", "rw_peterson_2readers"):
        r = _verdicts(name)
        assert r["roles"] == ["R", "R"]
        assert r["concurrent_reads_admitted"]
        assert r["rw_safety"]
        assert r["deadlock_free"]


def test_duplicate_labels_are_refused():
    """A label declared twice silently rebinds every earlier jump. That is not
    a hypothetical mistake: it is the bug the spliced-in Dekker snippet had,
    and it cost an afternoon."""
    with pytest.raises(AssertionError):
        rm.asm(["top:", ("JUMP", "top"), "top:", ("REM",)])


def test_every_solution_has_a_program_that_parses():
    for name, sol in rm.SOLUTIONS.items():
        for pid in range(sol.nproc):
            prog = sol.pid_programs[pid]
            assert prog, f"{name}: P{pid} has no program"
            ops = [ins[0] for ins in prog]
            assert "ENTER" in ops and "EXIT" in ops, f"{name}: no section"
            assert sol._cs[pid], f"{name}: P{pid} has no critical section"


# ============================================================== the primitives

def test_fifo_semaphore_does_not_let_a_newcomer_barge():
    """The fairness proofs assume a no-barging semaphore: a thread that has
    never queued may take a permit only when the queue is empty. Three threads
    queue in a known order, so they must be released in that order -- with
    `threading.Semaphore` they are not, and the turnstile solution quietly
    stops being fair."""
    sem = rs.FifoSemaphore(0)
    order = []

    def waiter(i: int) -> None:
        sem.acquire()
        order.append(i)

    threads = []
    for i in range(3):
        t = threading.Thread(target=waiter, args=(i,), daemon=True)
        t.start()
        time.sleep(0.08)            # let it reach acquire() before the next
        threads.append(t)
    assert order == [], "nobody may pass while the value is zero"
    for _ in range(3):
        sem.release()
        time.sleep(0.08)
    for t in threads:
        t.join(timeout=5)
    assert order == [0, 1, 2], f"served out of order: {order}"


def test_fifo_semaphore_hands_out_at_most_one_permit():
    sem = rs.FifoSemaphore(1)
    inside = [0]
    worst = [0]
    lock = threading.Lock()

    def worker() -> None:
        for _ in range(500):
            sem.acquire()
            with lock:
                inside[0] += 1
                worst[0] = max(worst[0], inside[0])
            inside[0] -= 1
            sem.release()

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)
    assert worst[0] == 1


def test_validator_catches_a_writer_beside_a_reader():
    v = rs.Validator()
    v.enter("R")
    v.enter("W")            # a writer walking in on a reader
    assert not v.report()["safe"]
    assert "writer entered" in v.report()["violations"][0]


def test_validator_catches_two_writers():
    v = rs.Validator()
    v.enter("W")
    v.enter("W")
    assert not v.report()["safe"]


def test_validator_accepts_readers_together():
    v = rs.Validator()
    v.enter("R")
    v.enter("R")
    v.enter("R")
    rep = v.report()
    assert rep["safe"]
    assert rep["max_concurrent_readers"] == 3


# ==================================================================== the locks

@pytest.mark.parametrize("name", sorted(rs.LOCKS))
def test_locks_are_safe_under_load(name):
    res = rs.benchmark(rs.LOCKS[name], n_readers=4, n_writers=2, seconds=0.25)
    assert res["safe"], f"{name}: {res['violations']}"
    assert res["ops"] > 0, f"{name} made no progress"


@pytest.mark.parametrize("name", [
    "readers_pref", "writers_pref", "fair_fifo", "barrier",
    "monitor_mesa", "monitor_fifo",
])
def test_readers_writers_locks_let_readers_overlap(name):
    """With real work inside the section, at least two readers must be inside
    at once. A lock that never manages it is a mutex wearing a label.

    Three runs and the best of them: how often readers overlap depends on how
    quickly they happen to arrive, and the barrier solution caps overlap on
    purpose, so one unlucky run proves nothing.
    """
    best = 0
    for _ in range(3):
        res = rs.benchmark(rs.LOCKS[name], n_readers=6, n_writers=1,
                           seconds=0.5, work=3000)
        assert res["safe"], f"{name}: {res['violations']}"
        best = max(best, res["max_concurrent_readers"])
    assert best >= 2, f"{name}: never more than {best} reader(s) inside"


@pytest.mark.parametrize("name", ["semaphore_mutex", "monitor_mutex",
                                  "dekker_mutex", "peterson_mutex"])
def test_mutexes_never_let_anybody_overlap(name):
    res = rs.benchmark(rs.LOCKS[name], n_readers=4, n_writers=2,
                       seconds=0.3, work=3000)
    assert res["safe"]
    assert res["max_concurrent_readers"] == 1


def test_readers_preference_starves_the_writer_in_practice():
    """The model says it can happen; this says it does happen, in under a
    second, with six readers and one writer."""
    res = rs.starvation_probe(rs.LOCKS["readers_pref"], n_readers=6,
                              n_writers=1, seconds=0.6)
    assert res["safe"]
    assert res["write_share"] < 0.05, f"writer got {res['write_share']:.3f}"


def test_fair_and_barrier_do_not_starve_the_writer():
    for name in ("fair_fifo", "barrier"):
        res = rs.starvation_probe(rs.LOCKS[name], n_readers=6, n_writers=1,
                                  seconds=0.6)
        assert res["safe"]
        assert res["write_share"] > 0.02, (
            f"{name}: writer got only {res['write_share']:.4f}")


def test_writers_preference_shuts_the_reader_door_for_long_stretches():
    """One reader against four writers: writers preference keeps the reader
    door shut for thousands of consecutive writes, where a FIFO-semaphore
    solution alternates every few operations.

    The share of the traffic is *not* a usable statistic here and the test
    deliberately does not use it: measured over a second it is dominated by who
    wins the opening race, and Python's own monitor lock turns out to be less
    fair at this timescale than writers preference is. The unbroken run is the
    honest measurement, and the proof that the reader can be shut out for good
    is the model checker's, not this one's.
    """
    def best(name: str) -> int:
        return max(rs.starvation_probe(rs.LOCKS[name], n_readers=1,
                                       n_writers=4, seconds=0.5
                                       )["longest_write_run"]
                   for _ in range(3))
    assert best("writers_pref") > 2000, "the reader door never stayed shut"
    assert best("fair_fifo") < best("writers_pref")


def test_two_process_locks_are_capped_at_two_threads():
    for name in ("dekker_mutex", "peterson_mutex", "dekker_rw", "peterson_rw"):
        assert rs.LOCKS[name]().max_threads == 2
    res = rs.benchmark(rs.LOCKS["dekker_mutex"], n_readers=4, n_writers=2,
                       seconds=0.2)
    assert res["thread_limited"] and res["readers"] == 1 and res["writers"] == 1


def test_fast_semaphore_breaks_the_proof_not_the_lock():
    """`threading.Semaphore` is faster and does not queue. The lock stays
    safe -- the invariant does not depend on the order -- but the fairness
    argument does, which is why the report measures both."""
    res = rs.benchmark(rs.LOCKS["readers_pref_fast"], n_readers=4,
                       n_writers=2, seconds=0.3)
    assert res["safe"]


# ============================================================== the artefacts

def test_experiments_are_recorded():
    path = os.path.join(ROOT, "output", "experiments.json")
    if not os.path.exists(path):
        pytest.skip("run code/run_experiments.py first")
    import json
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    for key in ("e1_throughput", "e2_concurrency", "e3_writer_starvation",
                "e4_reader_starvation", "e5_scaling", "e6_model"):
        assert key in data and data[key]
    for name, row in data["e1_throughput"].items():
        assert row["safe"], f"{name} was unsafe in the recorded run"
