"""Runnable thread-based implementations and benchmarks for Exercise 4.

Honesty note, stated up front
-----------------------------
Everything here *runs*, but a successful run does not *prove* anything about
Dekker's or Peterson's algorithm: CPython's GIL makes the interleavings that
would break them extremely unlikely, and plain Python variables carry no memory
ordering guarantees at all. The proof for those two algorithms is the
exhaustive model checker in :mod:`sync_model`, which examines every reachable
interleaving. What this module measures is therefore **behaviour and cost**:

* whether the mutual-exclusion invariant is *observed* to hold,
* how many critical-section entries each thread obtains (fairness),
* how long the workload takes (cost),
* how many spins a busy-wait lock burns (wasted CPU).

The semaphore and monitor below are built from scratch on top of
``threading.Condition`` (itself a monitor), so they are genuinely implemented
here rather than borrowed from the standard library.
"""

from __future__ import annotations

import statistics
import threading
import time
from typing import Callable, Dict, List

# ============================================================ base interface

class Lock:
    """Minimal lock interface used by the benchmark harness."""

    def acquire(self, tid: int = 0) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def release(self, tid: int = 0) -> None:  # pragma: no cover - overridden
        raise NotImplementedError

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


# ================================================================== DEKKER
class DekkerLock(Lock):
    """Dekker's algorithm for exactly two threads (ids 0 and 1).

    Implemented with plain attributes. Under CPython the GIL makes the
    dangerous interleavings rare, so this class is a *demonstration*, not a
    proof. The proof is ``sync_model.py``.
    """

    def __init__(self) -> None:
        self.flag = [False, False]
        self.turn = 0
        self.spins = [0, 0]

    def acquire(self, tid: int = 0) -> None:
        i = tid
        j = 1 - tid
        self.flag[i] = True
        while self.flag[j]:
            if self.turn == j:
                self.flag[i] = False
                while self.turn == j:
                    self.spins[i] += 1
                self.flag[i] = True

    def release(self, tid: int = 0) -> None:
        i = tid
        j = 1 - tid
        self.turn = j
        self.flag[i] = False


# ================================================================= PETERSON
class PetersonLock(Lock):
    """Peterson's algorithm for exactly two threads (ids 0 and 1)."""

    def __init__(self) -> None:
        self.flag = [False, False]
        self.turn = 0
        self.spins = [0, 0]

    def acquire(self, tid: int = 0) -> None:
        i = tid
        j = 1 - tid
        self.flag[i] = True
        self.turn = j
        while self.flag[j] and self.turn == j:
            self.spins[i] += 1

    def release(self, tid: int = 0) -> None:
        self.flag[tid] = False


# ============================================================ TEST-AND-SET
class TasLock(Lock):
    """A test-and-set spinlock.

    Python has no atomic read-modify-write instruction, so the RMW is emulated
    with a one-instruction-wide critical section guarded by a private mutex.
    That makes the *semantics* of TAS (including the absence of bounded
    waiting, which ``sync_model`` proves) observable, while the emulation
    supplies the atomicity the hardware would.
    """

    def __init__(self) -> None:
        self._locked = False
        self._atomic = threading.Lock()
        self.spins = 0
        self._owner: int | None = None

    def _test_and_set(self) -> bool:
        with self._atomic:
            prev = self._locked
            self._locked = True
            return prev

    def acquire(self, tid: int = 0) -> None:
        while self._test_and_set():
            self.spins += 1
        self._owner = tid

    def release(self, tid: int = 0) -> None:
        with self._atomic:
            self._locked = False
        self._owner = None


# ================================================================= SEMAPHORE
class Semaphore:
    """A counting semaphore built from scratch on a condition variable."""

    def __init__(self, value: int = 1) -> None:
        if value < 0:
            raise ValueError("a semaphore cannot start negative")
        self.value = value
        self._cv = threading.Condition()

    def acquire(self) -> None:
        with self._cv:
            while self.value == 0:
                self._cv.wait()
            self.value -= 1

    def release(self) -> None:
        with self._cv:
            self.value += 1
            self._cv.notify()

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()
        return False


class SemaphoreLock(Lock):
    """Mutual exclusion expressed as a binary semaphore."""

    def __init__(self) -> None:
        self._sem = Semaphore(1)

    def acquire(self, tid: int = 0) -> None:
        self._sem.acquire()

    def release(self, tid: int = 0) -> None:
        self._sem.release()


# =================================================================== MONITOR
class BoundedBufferMonitor:
    """A Mesa-style monitor: one mutex, two condition variables, capacity n.

    Every ``wait`` sits inside a ``while`` loop, because under Mesa semantics a
    signalled thread must re-check the predicate: another thread may have
    entered the monitor first and invalidated it.
    """

    def __init__(self, capacity: int = 4) -> None:
        if capacity < 1:
            raise ValueError("capacity must be at least 1")
        self.capacity = capacity
        self.buffer: List[int] = []
        self._cv = threading.Condition()
        self.produced = 0
        self.consumed = 0
        self.max_observed = 0
        self.spurious_wakeups = 0

    def put(self, item: int) -> None:
        with self._cv:
            checks = 0
            while len(self.buffer) >= self.capacity:
                checks += 1
                self._cv.wait()
            if checks > 1:
                self.spurious_wakeups += checks - 1
            self.buffer.append(item)
            self.produced += 1
            self.max_observed = max(self.max_observed, len(self.buffer))
            self._cv.notify_all()

    def get(self) -> int:
        with self._cv:
            checks = 0
            while not self.buffer:
                checks += 1
                self._cv.wait()
            if checks > 1:
                self.spurious_wakeups += checks - 1
            item = self.buffer.pop(0)
            self.consumed += 1
            self._cv.notify_all()
            return item


class MonitorLock(Lock):
    """Mutual exclusion expressed as a monitor with one condition variable."""

    def __init__(self) -> None:
        self._cv = threading.Condition()
        self._busy = False

    def acquire(self, tid: int = 0) -> None:
        with self._cv:
            while self._busy:
                self._cv.wait()
            self._busy = True

    def release(self, tid: int = 0) -> None:
        with self._cv:
            self._busy = False
            self._cv.notify()


# ========================================================== READERS / WRITERS
class ReadersWriters:
    """Base class: shared state guarded for concurrent readers and writers."""

    def __init__(self) -> None:
        self.value = 0
        self.reads = 0
        self.writes = 0

    def read(self) -> int:
        raise NotImplementedError

    def write(self, v: int) -> None:
        raise NotImplementedError


class ReadersPreferenceRW(ReadersWriters):
    """First readers–writers problem: no reader waits unless a writer is in.

    Consequence, measured below: a steady stream of readers can starve writers.
    """

    def __init__(self) -> None:
        super().__init__()
        self._mutex = threading.Lock()
        self._room = threading.Lock()
        self._readers = 0

    def read(self) -> int:
        with self._mutex:
            self._readers += 1
            if self._readers == 1:
                self._room.acquire()
        try:
            v = self.value
            time.sleep(0)               # yield, widening the overlap window
            with self._mutex:
                self.reads += 1
            return v
        finally:
            with self._mutex:
                self._readers -= 1
                if self._readers == 0:
                    self._room.release()

    def write(self, v: int) -> None:
        with self._room:
            self.value = v
            with self._mutex:
                self.writes += 1


class WritersPreferenceRW(ReadersWriters):
    """Second readers–writers problem: a waiting writer blocks new readers."""

    def __init__(self) -> None:
        super().__init__()
        self._cv = threading.Condition()
        self._readers = 0
        self._writers = 0
        self._waiting_writers = 0

    def read(self) -> int:
        with self._cv:
            while self._writers or self._waiting_writers:
                self._cv.wait()
            self._readers += 1
        try:
            v = self.value
            with self._cv:
                self.reads += 1
            return v
        finally:
            with self._cv:
                self._readers -= 1
                if self._readers == 0:
                    self._cv.notify_all()

    def write(self, v: int) -> None:
        with self._cv:
            self._waiting_writers += 1
            try:
                while self._readers or self._writers:
                    self._cv.wait()
            finally:
                self._waiting_writers -= 1
            self._writers += 1
        try:
            self.value = v
            with self._cv:
                self.writes += 1
        finally:
            with self._cv:
                self._writers -= 1
                self._cv.notify_all()


class FairRW(ReadersWriters):
    """FIFO ticket order: whichever caller arrived first is served first."""

    def __init__(self) -> None:
        super().__init__()
        self._cv = threading.Condition()
        self._ticket = 0
        self._now = 0
        self._readers = 0

    def _take(self) -> int:
        with self._cv:
            t = self._ticket
            self._ticket += 1
            while t != self._now or self._readers:
                self._cv.wait()
            self._readers += 1
            return t

    def _give(self) -> None:
        with self._cv:
            self._readers -= 1
            self._now += 1
            self._cv.notify_all()

    def read(self) -> int:
        self._take()
        try:
            v = self.value
            with self._cv:
                self.reads += 1
            return v
        finally:
            self._give()

    def write(self, v: int) -> None:
        self._take()
        try:
            self.value = v
            with self._cv:
                self.writes += 1
        finally:
            self._give()


# ================================================================== DEADLOCK
def _two_lock_trial(order_t1: tuple, timeout: float = 2.0) -> dict:
    """Two threads each take two locks; `order_t1` is the order for thread 1.

    Thread 0 always takes A then B.  When the orders differ, a barrier sits
    *between* the two acquisitions and the second acquisition is **non-blocking**,
    so the circular wait is produced deterministically instead of depending on
    scheduler luck or on a timeout race.
    """
    a, b = threading.Lock(), threading.Lock()
    consistent = order_t1 == ("A", "B")
    gate = None if consistent else threading.Barrier(2)
    gate2 = None if consistent else threading.Barrier(2)
    state = {"t0": "start", "t1": "start"}

    def run(name: str, first, second, first_label, second_label):
        first.acquire()
        try:
            state[name] = f"holds {first_label}"
            if gate is not None:
                gate.wait(timeout=timeout)      # both now hold one lock each
            if consistent:
                got = second.acquire(timeout=timeout)
            else:
                got = second.acquire(blocking=False)
            if got:
                state[name] = "completed"
                second.release()
            else:
                state[name] = f"holds {first_label}, blocked on {second_label}"
            if gate2 is not None:
                # Neither thread may release its first lock until both have
                # recorded the outcome, otherwise the loser would free its lock
                # just in time for the winner to grab it.
                gate2.wait(timeout=timeout)
        finally:
            first.release()

    if consistent:
        order1 = (a, b, "A", "B")
    else:
        order1 = (b, a, "B", "A")
    ts = [threading.Thread(target=run, args=("t0", a, b, "A", "B"), daemon=True),
          threading.Thread(target=run, args=("t1",) + order1, daemon=True)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=timeout * 3)
    blocked = [v for v in state.values() if "blocked" in v]
    return {"state": state,
            "deadlocked": len(blocked) == 2,
            "both_completed": all(v == "completed" for v in state.values())}


def deadlock_demo(timeout: float = 2.0) -> dict:
    """Reproduce the circular wait, and show that a fixed order avoids it."""
    wrong = _two_lock_trial(("B", "A"), timeout)
    right = _two_lock_trial(("A", "B"), timeout)
    return {
        "wrong_order": wrong,
        "consistent_order": right,
        "wrong_order_deadlocks": wrong["deadlocked"],
        "consistent_order_finishes": right["both_completed"],
        "note": ("with opposite orders both threads hold one lock and wait for "
                 "the other (circular wait); with a consistent order the same "
                 "program always finishes"),
    }


# ================================================================== BENCHMARK
class Harness:
    """Counts how many threads are inside the critical section at once."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.inside = 0
        self.max_inside = 0
        self.entries: Dict[int, int] = {}
        self.counter = 0
        self.wait_samples: List[float] = []

    def enter(self, tid: int) -> float:
        t0 = time.perf_counter()
        with self._lock:
            self.inside += 1
            self.max_inside = max(self.max_inside, self.inside)
            self.entries[tid] = self.entries.get(tid, 0) + 1
        return time.perf_counter() - t0

    def leave(self) -> None:
        with self._lock:
            self.inside -= 1

    @property
    def total_entries(self) -> int:
        return sum(self.entries.values())

    def fairness(self) -> float:
        """Population standard deviation of per-thread entry counts.

        0 means perfectly fair; larger means some thread was overtaken a lot.
        """
        vals = sorted(self.entries.values())
        if len(vals) < 2:
            return 0.0
        return statistics.pstdev(vals)


def benchmark(make_lock: Callable[[], Lock], threads: int = 2,
              iterations: int = 2000, name: str = "") -> dict:
    """Run `threads` threads doing `iterations` critical sections each."""
    lock = make_lock()
    h = Harness()
    barrier = threading.Barrier(threads)

    def worker(tid: int) -> None:
        barrier.wait()
        for _ in range(iterations):
            lock.acquire(tid)
            h.enter(tid)
            h.counter += 1
            h.leave()
            lock.release(tid)

    ts = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    elapsed = time.perf_counter() - t0

    spins = getattr(lock, "spins", None)
    if isinstance(spins, list):
        spins = sum(spins)
    return {
        "name": name or type(lock).__name__,
        "threads": threads,
        "iterations": iterations,
        "expected_counter": threads * iterations,
        "counter": h.counter,
        "correct": h.counter == threads * iterations,
        "max_concurrent": h.max_inside,
        "mutual_exclusion_observed": h.max_inside == 1,
        "entries": dict(sorted(h.entries.items())),
        "fairness_pstdev": round(h.fairness(), 3),
        "elapsed_s": round(elapsed, 4),
        "throughput_ops_per_s": round(threads * iterations / elapsed, 1)
        if elapsed > 0 else None,
        "spins": spins,
    }


def producer_consumer(monitor: BoundedBufferMonitor, n_producers: int = 2,
                      n_consumers: int = 2, items: int = 500) -> dict:
    total = n_producers * items
    barrier = threading.Barrier(n_producers + n_consumers)
    stop = object()

    def produce(pid: int) -> None:
        barrier.wait()
        for k in range(items):
            monitor.put(pid * items + k)

    def consume() -> None:
        barrier.wait()
        for _ in range(items):
            monitor.get()

    ts = ([threading.Thread(target=produce, args=(i,))
           for i in range(n_producers)]
          + [threading.Thread(target=consume) for _ in range(n_consumers)])
    t0 = time.perf_counter()
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    elapsed = time.perf_counter() - t0
    return {
        "producers": n_producers,
        "consumers": n_consumers,
        "items_per_producer": items,
        "expected_items": total,
        "produced": monitor.produced,
        "consumed": monitor.consumed,
        "balanced": monitor.produced == monitor.consumed == total,
        "capacity": monitor.capacity,
        "max_observed_in_buffer": monitor.max_observed,
        "capacity_respected": monitor.max_observed <= monitor.capacity,
        "re_waits_after_signal": monitor.spurious_wakeups,
        "elapsed_s": round(elapsed, 4),
        "throughput_items_per_s": round(total / elapsed, 1) if elapsed else None,
    }


def readers_writers_trial(rw: ReadersWriters, n_readers: int, n_writers: int,
                          duration: float) -> dict:
    """One timed trial with `n_readers` reader threads and `n_writers` writers."""
    stop = threading.Event()

    def reader() -> None:
        while not stop.is_set():
            rw.read()

    def writer() -> None:
        while not stop.is_set():
            rw.write(1)

    ts = ([threading.Thread(target=reader, daemon=True)
           for _ in range(n_readers)]
          + [threading.Thread(target=writer, daemon=True)
             for _ in range(n_writers)])
    for t in ts:
        t.start()
    time.sleep(duration)
    stop.set()
    for t in ts:
        t.join(timeout=3.0)
    reads, writes = rw.reads, rw.writes
    total = reads + writes
    return {
        "reads": reads,
        "writes": writes,
        "read_share": round(reads / total, 4) if total else 0.0,
        "write_share": round(writes / total, 4) if total else 0.0,
        "writer_starved": writes == 0,
        "reader_starved": reads == 0,
    }


def readers_writers_benchmark(make_rw, n_readers: int = 4, n_writers: int = 2,
                              duration: float = 0.6, reps: int = 5) -> dict:
    """Run the same workload several times and aggregate.

    A single trial of a busy-wait workload on CPython is noisy, so the reported
    figures are aggregates over `reps` independent trials; the per-trial numbers
    are kept so the spread is visible.
    """
    trials = [readers_writers_trial(make_rw(), n_readers, n_writers, duration)
              for _ in range(reps)]
    shares = [t["read_share"] for t in trials]
    rd = [t["reads"] for t in trials]
    wr = [t["writes"] for t in trials]
    return {
        "variant": make_rw.__name__,
        "readers": n_readers,
        "writers": n_writers,
        "duration_s": duration,
        "reps": reps,
        "trials": trials,
        "reads_total": sum(rd),
        "writes_total": sum(wr),
        "reads_min": min(rd),
        "reads_max": max(rd),
        "writes_min": min(wr),
        "writes_max": max(wr),
        "read_share_mean": round(sum(shares) / len(shares), 4),
        "read_share_min": min(shares),
        "read_share_max": max(shares),
        "trials_with_writer_starved": sum(1 for t in trials
                                          if t["writer_starved"]),
        "trials_with_reader_starved": sum(1 for t in trials
                                          if t["reader_starved"]),
    }
