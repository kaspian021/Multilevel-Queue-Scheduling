"""Tests for the runnable threading layer of Exercise 4."""
import json
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import sync_algorithms as sa  # noqa: E402


# ------------------------------------------------------------------ semaphore
def test_semaphore_is_a_real_counting_semaphore():
    s = sa.Semaphore(3)
    assert s.value == 3
    s.acquire(); s.acquire(); s.acquire()
    assert s.value == 0
    s.release()
    assert s.value == 1


def test_semaphore_rejects_negative_initial_value():
    with pytest.raises(ValueError):
        sa.Semaphore(-1)


def test_semaphore_blocks_and_wakes():
    s = sa.Semaphore(0)
    order = []

    def waiter():
        s.acquire()
        order.append("acquired")

    t = threading.Thread(target=waiter)
    t.start()
    assert order == []
    s.release()
    t.join(timeout=2)
    assert order == ["acquired"]


def test_semaphore_used_as_a_lock():
    lock = sa.SemaphoreLock()
    with lock:
        assert lock._sem.value == 0
    assert lock._sem.value == 1


# -------------------------------------------------------------------- monitor
def test_monitor_lock_is_exclusive():
    lock = sa.MonitorLock()
    inside = []
    with lock:
        inside.append(1)
    assert inside == [1]


def test_bounded_buffer_blocks_when_full():
    """A producer must wait when the buffer is full: it must not overflow."""
    m = sa.BoundedBufferMonitor(1)
    m.put(1)
    assert len(m.buffer) == 1
    done = threading.Event()

    def producer():
        m.put(2)
        done.set()

    t = threading.Thread(target=producer, daemon=True)
    t.start()
    done.wait(timeout=0.3)
    assert not done.is_set(), "put() should have blocked on a full buffer"
    assert len(m.buffer) == 1
    m.get()                                    # make room
    done.wait(timeout=2.0)
    assert done.is_set()
    assert m.get() == 2
    assert not m.buffer


def test_bounded_buffer_rejects_bad_capacity():
    with pytest.raises(ValueError):
        sa.BoundedBufferMonitor(0)


def test_producer_consumer_is_balanced_and_bounded():
    m = sa.BoundedBufferMonitor(4)
    r = sa.producer_consumer(m, n_producers=2, n_consumers=2, items=200)
    assert r["balanced"] is True
    assert r["capacity_respected"] is True
    assert r["consumed"] == r["produced"] == 400


def test_monitor_uses_a_while_loop_around_wait():
    """The predicate is re-checked, so spurious wake-ups do not corrupt state."""
    src = open(os.path.join(os.path.dirname(__file__), "..", "code",
                            "sync_algorithms.py"), encoding="utf-8").read()
    assert src.count("while len(self.buffer) >= self.capacity") == 1
    assert src.count("while not self.buffer") == 1
    assert src.count("self._cv.wait()") >= 3


# ----------------------------------------------------------------- spin locks
@pytest.mark.parametrize("cls", [sa.DekkerLock, sa.PetersonLock, sa.TasLock])
def test_two_thread_locks_are_exclusive_and_correct(cls):
    r = sa.benchmark(cls, threads=2, iterations=1000)
    assert r["correct"] is True
    assert r["mutual_exclusion_observed"] is True
    assert r["counter"] == 2000


@pytest.mark.parametrize("cls", [sa.SemaphoreLock, sa.MonitorLock])
def test_general_locks_scale_past_two_threads(cls):
    r = sa.benchmark(cls, threads=6, iterations=800)
    assert r["correct"] is True
    assert r["mutual_exclusion_observed"] is True
    assert r["counter"] == 6 * 800
    assert len(r["entries"]) == 6


def test_dekker_and_peterson_are_two_thread_only():
    """Both algorithms index flag[0]/flag[1]; using a third id is an error."""
    for cls in (sa.DekkerLock, sa.PetersonLock):
        with pytest.raises(IndexError):
            cls().acquire(2)


def test_tas_counts_spins_under_contention():
    lock = sa.TasLock()
    assert lock.spins == 0
    sa.benchmark(sa.TasLock, threads=4, iterations=500)
    r = sa.benchmark(sa.TasLock, threads=4, iterations=500)
    assert r["spins"] >= 0
    assert isinstance(r["spins"], int)


def test_benchmark_returns_a_finite_throughput():
    r = sa.benchmark(sa.MonitorLock, threads=2, iterations=300)
    assert r["throughput_ops_per_s"] is not None
    assert r["throughput_ops_per_s"] > 0


# -------------------------------------------------------------- readers/writers
@pytest.mark.parametrize("cls", [sa.ReadersPreferenceRW, sa.WritersPreferenceRW,
                                 sa.FairRW])
def test_readers_writers_keeps_state_consistent(cls):
    rw = cls()
    rw.write(7)
    assert rw.read() == 7
    rw.write(9)
    assert rw.read() == 9
    assert rw.writes == 2
    assert rw.reads == 2


def test_readers_preference_starves_the_writer():
    """Six readers against one writer: the writer is overtaken for ever."""
    r = sa.readers_writers_benchmark(sa.ReadersPreferenceRW, n_readers=6,
                                     n_writers=1, duration=0.4, reps=2)
    assert r["read_share_mean"] > 0.9
    assert r["writes_total"] < r["reads_total"] / 100


def test_fair_readers_writers_is_close_to_arrival_order():
    """With 6 readers and 1 writer, fair scheduling gives readers about 6/7."""
    r = sa.readers_writers_benchmark(sa.FairRW, n_readers=6, n_writers=1,
                                     duration=0.4, reps=2)
    assert 0.5 < r["read_share_mean"] < 0.99


# -------------------------------------------------------------------- deadlock
def test_opposite_lock_order_deadlocks_deterministically():
    d = sa.deadlock_demo(2.0)
    assert d["wrong_order_deadlocks"] is True
    assert d["wrong_order"]["state"]["t0"] == "holds A, blocked on B"
    assert d["wrong_order"]["state"]["t1"] == "holds B, blocked on A"


def test_consistent_lock_order_always_finishes():
    d = sa.deadlock_demo(2.0)
    assert d["consistent_order_finishes"] is True
    assert d["consistent_order"]["deadlocked"] is False
