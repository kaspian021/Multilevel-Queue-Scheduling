"""Threaded readers-writers locks, one per solution, plus a harness.

    python3 code/rw_sync.py

Why this file exists alongside the model checker
------------------------------------------------
`rw_model.py` proves statements about *every interleaving* of a protocol, but
only for two or three participants and only for a handful of atomic steps. This
module asks the other question: what do these solutions actually cost, and do
they stay correct, when real threads run them for a while? The two answers are
complementary and they do not always point the same way -- a solution can be
provably fair and slow, or fast and provably unfair.

The locks
---------
Every lock here offers the same four calls, so the harness can treat them
alike::

    acquire_read() / release_read() / acquire_write() / release_write()

`max_threads` is ``None`` when a lock takes any number of participants and ``2``
for Dekker's and Peterson's algorithms, which are written for exactly two.

Two details are not incidental
------------------------------
* **The semaphore is strictly FIFO.** Python's own `threading.Semaphore` hands
  a permit to whoever gets there first, which would quietly break the fairness
  of the turnstile solution: the model checker proved that solution correct
  *assuming* a no-barging semaphore, so the measurement has to use one too.
* **The harness checks the invariant on every entry, not at the end.** A
  readers-writers lock that lets a writer in beside a reader for a microsecond
  will very likely leave no trace at all in the final counter; the violation
  has to be caught while it is happening.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Callable, Dict, List, Optional

__all__ = [
    "Validator", "FifoCondition", "FifoSemaphore",
    "SemMutex", "MonitorMutex", "DekkerMutex", "PetersonMutex",
    "ReadersPrefSem", "WritersPrefSem", "FairSem", "BarrierSem",
    "MonitorRW", "DekkerRW", "PetersonRW",
    "LOCKS", "benchmark", "starvation_probe",
]


# ============================================================== instrumentation

class Validator:
    """Watches the invariant while the lock is being exercised.

    A readers-writers lock is correct when no two writers are inside at once
    and no writer is ever inside with anybody else. Both are checked on every
    single entry, because a violation that lasts a microsecond leaves no trace
    in any counter read afterwards.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.readers = 0
        self.writers = 0
        self.reads = 0
        self.writes = 0
        self.max_readers = 0
        self.violations: List[str] = []

    def enter(self, kind: str) -> None:
        with self._lock:
            if kind == "R":
                if self.writers:
                    self.violations.append(
                        f"reader entered while {self.writers} writer(s) inside")
                self.readers += 1
                self.reads += 1
                if self.readers > self.max_readers:
                    self.max_readers = self.readers
            else:
                if self.writers:
                    self.violations.append("two writers inside at once")
                if self.readers:
                    self.violations.append(
                        f"writer entered while {self.readers} reader(s) inside")
                self.writers += 1
                self.writes += 1

    def leave(self, kind: str) -> None:
        with self._lock:
            if kind == "R":
                self.readers -= 1
            else:
                self.writers -= 1

    def report(self) -> dict:
        with self._lock:
            return {
                "reads": self.reads,
                "writes": self.writes,
                "max_concurrent_readers": self.max_readers,
                "violations": list(self.violations),
                "safe": not self.violations,
            }


# ================================================================== primitives

class FifoSemaphore:
    """A counting semaphore whose queue is strictly first-in-first-out.

    A thread takes a ticket on arrival and is served in ticket order, so a
    newcomer can never overtake a waiter. That property is what the model
    checker assumed when it proved the turnstile solution fair, so the
    measurement has to use a semaphore that actually has it --
    `threading.Semaphore` does not, and quietly hands a permit to whichever
    thread the OS wakes first.

    The ticket also makes the uncontended case cheap: with a permit available
    and nobody ahead, the caller is served without allocating anything.
    """

    def __init__(self, value: int = 1) -> None:
        self._cv = threading.Condition()
        self._value = value
        self._next = 0
        self._serving = 0

    def acquire(self) -> None:
        with self._cv:
            ticket = self._next
            self._next += 1
            while not (self._value > 0 and ticket == self._serving):
                self._cv.wait()
            self._value -= 1
            self._serving += 1
            self._cv.notify_all()

    def release(self) -> None:
        with self._cv:
            self._value += 1
            self._cv.notify_all()

    def __enter__(self) -> "FifoSemaphore":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


class FastSemaphore:
    """The same semaphore without the queue: `threading.Semaphore` as it comes.

    It is there to be measured against the FIFO one, so the price of the
    fairness the proofs assume is a number rather than an assertion.
    """

    def __init__(self, value: int = 1) -> None:
        self._s = threading.Semaphore(value)

    def acquire(self) -> None:
        self._s.acquire()

    def release(self) -> None:
        self._s.release()

    def __enter__(self) -> "FastSemaphore":
        self.acquire()
        return self

    def __exit__(self, *exc) -> None:
        self.release()


class FifoCondition:
    """A condition variable with a FIFO wait queue and a notify-all.

    `threading.Condition` is good enough as a Mesa monitor, but its waiters are
    served in whatever order the underlying lock wakes them, so the fair
    monitor variant gets its own queue here for the same reason the fair
    semaphore does.
    """

    def __init__(self, lock: threading.Lock) -> None:
        self._lock = lock
        self._queue: deque = deque()
        self._tickets = 0

    def wait(self) -> None:
        gate = threading.Condition(self._lock)
        self._queue.append(gate)
        while True:
            gate.wait()
            if self._tickets > 0 and self._queue and self._queue[0] is gate:
                self._queue.popleft()
                self._tickets -= 1
                if self._tickets > 0 and self._queue:
                    self._queue[0].notify()
                return

    def notify_all(self) -> None:
        self._tickets = len(self._queue)
        if self._queue:
            self._queue[0].notify()


# ===================================================== the plain-mutex baselines

class SemMutex:
    """A semaphore used as an ordinary mutex: correct, and it forbids exactly
    the thing the readers-writers problem exists to allow."""
    max_threads = None

    def __init__(self, make_sem=FifoSemaphore) -> None:
        self._s = make_sem(1)

    def acquire_read(self) -> None:
        self._s.acquire()

    def release_read(self) -> None:
        self._s.release()

    def acquire_write(self) -> None:
        self._s.acquire()

    def release_write(self) -> None:
        self._s.release()


class MonitorMutex:
    """The same mutex as a Mesa monitor: a flag, re-tested in a loop."""
    max_threads = None

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cv = threading.Condition(self._lock)
        self._busy = False

    def _acquire(self) -> None:
        with self._lock:
            while self._busy:
                self._cv.wait()
            self._busy = True

    def _release(self) -> None:
        with self._lock:
            self._busy = False
            self._cv.notify()

    acquire_read = _acquire
    release_read = _release
    acquire_write = _acquire
    release_write = _release


class _Spin:
    """Shared bookkeeping for the two classic two-process spinlocks."""
    max_threads = 2

    def __init__(self) -> None:
        self.flag = [False, False]
        self.turn = 0
        self.spins = 0

    def _done(self) -> None:
        pass


class DekkerMutex(_Spin):
    """Dekker's algorithm: two flags and a turn, with the polite yield."""

    def _acquire(self, tid: int) -> None:
        other = 1 - tid
        self.flag[tid] = True
        while self.flag[other]:
            if self.turn == tid:
                self.spins += 1
                continue
            self.flag[tid] = False
            while self.turn != tid:
                self.spins += 1
            self.flag[tid] = True

    def _release(self, tid: int) -> None:
        self.turn = 1 - tid
        self.flag[tid] = False

    def __init__(self) -> None:
        super().__init__()

    def acquire_read(self, tid: int = 0) -> None:
        self._acquire(tid)

    def release_read(self, tid: int = 0) -> None:
        self._release(tid)

    def acquire_write(self, tid: int = 0) -> None:
        self._acquire(tid)

    def release_write(self, tid: int = 0) -> None:
        self._release(tid)


class PetersonMutex(_Spin):
    """Peterson's algorithm: the turn does the yielding, no loop needed."""

    def _acquire(self, tid: int) -> None:
        other = 1 - tid
        self.flag[tid] = True
        self.turn = other
        while self.flag[other] and self.turn == other:
            self.spins += 1

    def _release(self, tid: int) -> None:
        self.flag[tid] = False

    def __init__(self) -> None:
        super().__init__()

    def acquire_read(self, tid: int = 0) -> None:
        self._acquire(tid)

    def release_read(self, tid: int = 0) -> None:
        self._release(tid)

    def acquire_write(self, tid: int = 0) -> None:
        self._acquire(tid)

    def release_write(self, tid: int = 0) -> None:
        self._release(tid)


# ==================================================== the semaphore-based family

class ReadersPrefSem:
    """Readers preference: the first reader takes `wrt`, the last one gives it
    back. A writer can be overtaken for ever."""
    max_threads = None

    def __init__(self, make_sem=FifoSemaphore) -> None:
        self._mutex = make_sem(1)
        self._wrt = make_sem(1)
        self._readers = 0

    # `wrt` is taken and given *inside* the count mutex. Taking it afterwards
    # opens a window in which a second reader has already raised the count but
    # the first one has not yet taken the writer lock, and then a writer can
    # be inside with a reader. The harness catches this within a second of
    # load, and the model checker proves it is not merely unlikely.
    def acquire_read(self) -> None:
        with self._mutex:
            self._readers += 1
            if self._readers == 1:
                self._wrt.acquire()

    def release_read(self) -> None:
        with self._mutex:
            self._readers -= 1
            if self._readers == 0:
                self._wrt.release()

    def acquire_write(self) -> None:
        self._wrt.acquire()

    def release_write(self) -> None:
        self._wrt.release()


class WritersPrefSem:
    """Writers preference: the first waiting writer shuts the reader door, and
    it stays shut until the last writer is done."""
    max_threads = None

    def __init__(self, make_sem=FifoSemaphore) -> None:
        self._mutex = make_sem(1)            # protects `readers`
        self._wrt = make_sem(1)              # the section itself
        self._read_try = make_sem(1)         # the reader door
        self._wrt_q = make_sem(1)            # protects `writers`
        self._readers = 0
        self._writers = 0

    def acquire_read(self) -> None:
        self._read_try.acquire()
        with self._mutex:
            self._readers += 1
            if self._readers == 1:
                self._wrt.acquire()
        self._read_try.release()

    def release_read(self) -> None:
        with self._mutex:
            self._readers -= 1
            if self._readers == 0:
                self._wrt.release()

    def acquire_write(self) -> None:
        with self._wrt_q:
            self._writers += 1
            if self._writers == 1:
                self._read_try.acquire()
        self._wrt.acquire()

    def release_write(self) -> None:
        self._wrt.release()
        with self._wrt_q:
            self._writers -= 1
            if self._writers == 0:
                self._read_try.release()


class FairSem:
    """A FIFO turnstile: whoever queues first goes in first.

    The writer pays for this by holding the turnstile across its whole wait,
    which is what stops readers banging through the door ahead of it.
    """
    max_threads = None

    def __init__(self, make_sem=FifoSemaphore) -> None:
        self._mutex = make_sem(1)
        self._wrt = make_sem(1)
        self._queue = make_sem(1)
        self._readers = 0

    def acquire_read(self) -> None:
        self._queue.acquire()
        with self._mutex:
            self._readers += 1
            if self._readers == 1:
                self._wrt.acquire()
        self._queue.release()

    def release_read(self) -> None:
        with self._mutex:
            self._readers -= 1
            if self._readers == 0:
                self._wrt.release()

    def acquire_write(self) -> None:
        self._queue.acquire()      # held for the whole wait, not released here
        self._wrt.acquire()

    def release_write(self) -> None:
        self._wrt.release()
        self._queue.release()


class BarrierSem:
    """Two symmetric gates: the first reader closes the writer gate, the first
    writer closes the reader gate, and each phase drains before the next opens.
    """
    max_threads = None

    def __init__(self, make_sem=FifoSemaphore) -> None:
        self._rgate = make_sem(1)
        self._wgate = make_sem(1)
        self._rmutex = make_sem(1)
        self._wmutex = make_sem(1)
        self._readers = 0
        self._writers = 0

    def acquire_read(self) -> None:
        self._rgate.acquire()
        with self._rmutex:
            self._readers += 1
            if self._readers == 1:
                self._wgate.acquire()
        self._rgate.release()

    def release_read(self) -> None:
        with self._rmutex:
            self._readers -= 1
            if self._readers == 0:
                self._wgate.release()

    def acquire_write(self) -> None:
        with self._wmutex:
            self._writers += 1
            if self._writers == 1:
                self._rgate.acquire()
        self._wgate.acquire()

    def release_write(self) -> None:
        self._wgate.release()
        with self._wmutex:
            self._writers -= 1
            if self._writers == 0:
                self._rgate.release()


# ============================================================== the monitor

class MonitorRW:
    """Readers and writers inside one monitor.

    `fair` picks between the two variants the model checker distinguishes: with
    a plain `threading.Condition` a notified thread has to re-compete for the
    monitor lock and can be barged, which is how Java behaves; with a FIFO wait
    queue it keeps its place.
    """
    max_threads = None

    def __init__(self, fair: bool = False) -> None:
        self.fair = fair
        self._lock = threading.Lock()
        self._plain = threading.Condition(self._lock)
        self._fifo = FifoCondition(self._lock)
        self._readers = 0
        self._writer = False

    @property
    def _cv(self):
        return self._fifo if self.fair else self._plain

    def acquire_read(self) -> None:
        with self._lock:
            while self._writer:
                self._cv.wait()
            self._readers += 1

    def release_read(self) -> None:
        with self._lock:
            self._readers -= 1
            if self._readers == 0:
                self._cv.notify_all()

    def acquire_write(self) -> None:
        with self._lock:
            while self._writer or self._readers:
                self._cv.wait()
            self._writer = True

    def release_write(self) -> None:
        with self._lock:
            self._writer = False
            self._cv.notify_all()


# ============================== the readers pattern on a two-process spinlock

class _CountLockRW:
    """The readers-preference pattern with an arbitrary two-process lock
    guarding the reader count instead of the section.

    The lock still excludes writers through `wrt`; what the spinlock protects
    is the bookkeeping. That is enough for two readers to be inside together,
    which no plain mutex can do -- and two participants is all Dekker's and
    Peterson's algorithms have.
    """
    max_threads = 2

    def __init__(self) -> None:
        self._wrt = FifoSemaphore(1)
        self._readers = 0
        self._lock = _Spin()

    def _acquire_lock(self, tid: int) -> None:
        raise NotImplementedError

    def _release_lock(self, tid: int) -> None:
        raise NotImplementedError

    def acquire_read(self, tid: int = 0) -> None:
        self._acquire_lock(tid)
        self._readers += 1
        if self._readers == 1:
            self._wrt.acquire()
        self._release_lock(tid)

    def release_read(self, tid: int = 0) -> None:
        self._acquire_lock(tid)
        self._readers -= 1
        if self._readers == 0:
            self._wrt.release()
        self._release_lock(tid)

    def acquire_write(self, tid: int = 0) -> None:
        self._wrt.acquire()

    def release_write(self, tid: int = 0) -> None:
        self._wrt.release()


class DekkerRW(_CountLockRW):
    """The readers pattern with Dekker's algorithm as the count lock."""

    def _acquire_lock(self, tid: int) -> None:
        other = 1 - tid
        self._lock.flag[tid] = True
        while self._lock.flag[other]:
            if self._lock.turn == tid:
                self._lock.spins += 1
                continue
            self._lock.flag[tid] = False
            while self._lock.turn != tid:
                self._lock.spins += 1
            self._lock.flag[tid] = True

    def _release_lock(self, tid: int) -> None:
        self._lock.turn = 1 - tid
        self._lock.flag[tid] = False


class PetersonRW(_CountLockRW):
    """The readers pattern with Peterson's algorithm as the count lock."""

    def _acquire_lock(self, tid: int) -> None:
        other = 1 - tid
        self._lock.flag[tid] = True
        self._lock.turn = other
        while self._lock.flag[other] and self._lock.turn == other:
            self._lock.spins += 1

    def _release_lock(self, tid: int) -> None:
        self._lock.flag[tid] = False


def _fast(cls):
    return lambda: cls(make_sem=FastSemaphore)


LOCKS: Dict[str, Callable[[], object]] = {
    "semaphore_mutex": SemMutex,
    "semaphore_mutex_fast": _fast(SemMutex),
    "monitor_mutex": MonitorMutex,
    "dekker_mutex": DekkerMutex,
    "peterson_mutex": PetersonMutex,
    "readers_pref": ReadersPrefSem,
    "readers_pref_fast": _fast(ReadersPrefSem),
    "writers_pref": WritersPrefSem,
    "fair_fifo": FairSem,
    "fair_fifo_fast": _fast(FairSem),
    "barrier": BarrierSem,
    "monitor_mesa": lambda: MonitorRW(fair=False),
    "monitor_fifo": lambda: MonitorRW(fair=True),
    "dekker_rw": DekkerRW,
    "peterson_rw": PetersonRW,
}


# ================================================================= the harness

def _needs_tid(lock) -> bool:
    return getattr(type(lock), "max_threads", None) == 2


def _call(fn, tid, needs_tid: bool):
    return fn(tid) if needs_tid else fn()


def benchmark(make_lock: Callable[[], object], n_readers: int, n_writers: int,
              seconds: float = 0.6, work: int = 0) -> dict:
    """Run `n_readers` + `n_writers` threads against one lock for `seconds`.

    Returns the throughput, the share of the traffic that was writes, how many
    readers were ever inside at once, and whether the invariant held. A lock
    limited to two participants is run with one reader and one writer however
    many were asked for, and the report says so.
    """
    lock = make_lock()
    capped = _needs_tid(lock)
    if capped:
        n_readers, n_writers = 1, 1
    val = Validator()
    stop = threading.Event()
    capped = _needs_tid(lock) or _needs_tid(make_lock())
    spins = [0]

    def body(kind: str, tid: int) -> None:
        enter = lock.acquire_read if kind == "R" else lock.acquire_write
        leave = lock.release_read if kind == "R" else lock.release_write
        while not stop.is_set():
            _call(enter, tid, capped)
            val.enter(kind)
            if work:
                _ = sum(range(work))          # a little time inside the section
            val.leave(kind)
            _call(leave, tid, capped)

    threads = []
    for i in range(n_readers):
        threads.append(threading.Thread(target=body, args=("R", i),
                                        daemon=True))
    for i in range(n_writers):
        threads.append(threading.Thread(target=body, args=("W", n_readers + i),
                                        daemon=True))
    start = time.perf_counter()
    for t in threads:
        t.start()
    time.sleep(seconds)
    stop.set()
    for t in threads:
        t.join(timeout=10)
    elapsed = time.perf_counter() - start

    rep = val.report()
    total = rep["reads"] + rep["writes"]
    if hasattr(lock, "spins"):
        spins[0] = lock.spins
    elif hasattr(getattr(lock, "_lock", None), "spins"):
        spins[0] = lock._lock.spins
    return {
        "lock": type(lock).__name__,
        "readers": n_readers,
        "writers": n_writers,
        "thread_limited": capped,
        "elapsed_s": round(elapsed, 4),
        "reads": rep["reads"],
        "writes": rep["writes"],
        "ops": total,
        "ops_per_s": round(total / elapsed, 1) if elapsed > 0 else 0.0,
        "write_share": round(rep["writes"] / total, 4) if total else 0.0,
        "max_concurrent_readers": rep["max_concurrent_readers"],
        "violations": rep["violations"][:10],
        "safe": rep["safe"],
        "spins": spins[0],
    }


def starvation_probe(make_lock: Callable[[], object], n_readers: int = 6,
                     n_writers: int = 1, seconds: float = 0.8) -> dict:
    """The load the preference solutions are supposed to fail: many readers,
    one writer, no work inside the section.

    It reports the share of the traffic that was writes and, more tellingly,
    the longest unbroken run of reads and of writes. A lock that never lets the
    writer in produces one read run as long as the whole trial; a lock that
    never lets a waiting reader in produces one long write run. The share alone
    is a poor statistic for these locks, because several of them are bimodal:
    the outcome depends on who wins the opening race and it stays that way.
    """
    lock = make_lock()
    capped = _needs_tid(lock)
    if capped:
        n_readers, n_writers = 1, 1
    val = Validator()
    seq: List[str] = []
    seq_lock = threading.Lock()
    stop = threading.Event()

    def body(kind: str, tid: int) -> None:
        enter = lock.acquire_read if kind == "R" else lock.acquire_write
        leave = lock.release_read if kind == "R" else lock.release_write
        while not stop.is_set():
            _call(enter, tid, capped)
            val.enter(kind)
            with seq_lock:
                seq.append(kind)
            val.leave(kind)
            _call(leave, tid, capped)

    threads = [threading.Thread(target=body, args=("R", i), daemon=True)
               for i in range(n_readers)]
    threads += [threading.Thread(target=body, args=("W", n_readers + i),
                                 daemon=True)
                for i in range(n_writers)]
    for t in threads:
        t.start()
    time.sleep(seconds)
    stop.set()
    for t in threads:
        t.join(timeout=10)

    longest_read = read_run = 0
    longest_write = write_run = 0
    for k in seq:
        if k == "R":
            read_run += 1
            write_run = 0
        else:
            write_run += 1
            read_run = 0
        longest_read = max(longest_read, read_run)
        longest_write = max(longest_write, write_run)
    rep = val.report()
    total = rep["reads"] + rep["writes"]
    return {
        "lock": type(lock).__name__,
        "readers": n_readers,
        "writers": n_writers,
        "thread_limited": capped,
        "reads": rep["reads"],
        "writes": rep["writes"],
        "write_share": round(rep["writes"] / total, 4) if total else 0.0,
        "longest_read_run": longest_read,
        "longest_write_run": longest_write,
        "traced_ops": len(seq),
        "max_concurrent_readers": rep["max_concurrent_readers"],
        "safe": rep["safe"],
        "violations": rep["violations"][:10],
    }


def self_test() -> dict:
    """Smoke-test every lock: correct under load, and concurrent reads where
    the solution is supposed to allow them."""
    out = {}
    for name, make in LOCKS.items():
        res = benchmark(make, n_readers=4, n_writers=2, seconds=0.25)
        out[name] = res
    return out


if __name__ == "__main__":
    import json
    print(json.dumps(self_test(), indent=2))
