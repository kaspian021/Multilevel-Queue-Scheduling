from threading import Thread
from time import monotonic
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from dining_philosophers import DiningPhilosophers, FairSemaphore
from model_check import explore_naive, explore_ordered


def wait_for_waiters(sem, count, timeout=2.0):
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if sem.waiting_count >= count:
            return
    raise AssertionError("threads did not queue")


def test_naive_has_deadlock_witness():
    result = explore_naive(5)
    assert result.deadlocks == [(1, 1, 1, 1, 1)]


def test_ordered_model_has_no_deadlock():
    result = explore_ordered(5)
    assert result.states > 1
    assert result.deadlocks == []


def test_fifo_semaphore_order():
    sem = FairSemaphore(1)
    sem.acquire()
    order, threads = [], []
    for value in (1, 2, 3):
        thread = Thread(target=lambda v=value: (sem.acquire(), order.append(v), sem.release()))
        thread.start()
        threads.append(thread)
        wait_for_waiters(sem, len(threads))
    sem.release()
    for thread in threads:
        thread.join(2)
        assert not thread.is_alive()
    assert order == [1, 2, 3]


def test_semaphore_rejects_over_release():
    with pytest.raises(ValueError):
        FairSemaphore(1).release()


@pytest.mark.parametrize("n,meals", [(3, 2), (5, 3), (7, 2)])
def test_all_philosophers_finish(n, meals):
    sim = DiningPhilosophers(n, eat_seconds=0.0001)
    trace = sim.run(meals, timeout=8)
    assert sim.meals == [meals] * n
    assert sum(e[2] == "eat_start" for e in trace) == n * meals
    assert sim.room.available == sim.room.capacity
    assert all(f.available == 1 for f in sim.forks)


def test_invalid_configuration():
    with pytest.raises(ValueError):
        DiningPhilosophers(2)
    with pytest.raises(ValueError):
        FairSemaphore(0)
