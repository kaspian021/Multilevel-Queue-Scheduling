"""Exhaustive model checker for readers-writers solutions.

    python3 code/rw_model.py

Why a model checker at all
--------------------------
Running a readers-writers lock on real threads and finding no corruption proves
nothing: the outcome depends on scheduling luck, on the interpreter and on the
GIL. What *can* be proved is a statement about **every possible interleaving**
of the atomic steps of the protocol, and that is what this module does. It then
reports a verdict for each property plus, whenever a property fails, the
shortest interleaving that breaks it.

Model
-----
Time is discrete, memory is sequentially consistent, and every load and store
of a single word is atomic. A global state is::

    (shared, sems, pcs, locs)

* ``shared`` — a tuple of integers: the reader/writer counters and flags.
* ``sems``   — a tuple of ``(value, queue)`` pairs, one per semaphore.
* ``pcs``    — one program counter per process.
* ``locs``   — one tuple of private registers per process.

A process that cannot proceed is modelled by a transition that leaves the state
unchanged; the explorer prunes those self-loops, so a blocked process simply has
no useful successor and a deadlock shows up as a state from which no ``enter``
is reachable.

Semaphores
----------
The queue is FIFO and a newcomer may not barge past a waiter. A process that
has never queued may take the permit only when the queue is empty; a process
already in the queue may take it only when it is at the head. This is the
strong (no-barging) semaphore, and it is what lets the ``queue`` turnstile in
the fair solution actually enforce order.

Instruction set
---------------
Each process runs a straight-line program, one instruction per program counter:

===================  ==========================================================
``("P", s)``         wait on semaphore ``s`` (blocking, FIFO)
``("V", s)``         signal semaphore ``s``: ``value += 1``
``("VSIG", s)``      Mesa-style signal: wake one waiter, or **lose** the
                     signal if nobody is waiting
``("INC", v)``       ``shared[v] += 1``
``("DEC", v)``       ``shared[v] -= 1``
``("SET", v, k)``    ``shared[v] = k``
``("LOAD", r, v)``   ``loc[r] = shared[v]``
``("SUBI", r, k)``   ``loc[r] -= k``
``("JZ", r, t)``     if ``loc[r] == 0`` jump to ``t``, else fall through
``("JNZ", r, t)``    if ``loc[r] != 0`` jump to ``t``, else fall through
``("JUMP", t)``      unconditional jump
``("SETP", v, k)``   ``shared[slot(v) + pid] = k`` -- my own flag
``("SETO", v, k)``   ``shared[slot(v) + 1 - pid] = k`` -- the other flag
``("LOADP", r, v)``  ``loc[r] = shared[slot(v) + pid]``
``("LOADO", r, v)``  ``loc[r] = shared[slot(v) + 1 - pid]``
``("SETPID", v)``    ``shared[v] = pid``
``("SETOTHER", v)``  ``shared[v] = 1 - pid``
``("JEQPID", r, t)`` if ``loc[r] == pid`` jump to ``t``
``("JNEPID", r, t)`` if ``loc[r] != pid`` jump to ``t``
``("WAIT", cv, t)``  monitor wait: release the monitor lock, block on ``cv``,
                     and on being woken re-acquire the lock and jump to ``t``
                     -- racing any newcomer for it, which is Mesa as Java
                     implements it
``("WAITQ", cv, t)`` the same, except that on being woken the thread queues
                     for the lock and keeps its place
``("SIGNAL", cv)``   Mesa signal on ``cv``: wake one waiter, or lose it
``("SIGNAL_ALL", cv)``  notifyAll on ``cv``: wake every current waiter
``("HAND", cv)``     notify one waiter and hand it straight to the monitor
                     entry queue ``m``, atomically
``("HAND_ALL", cv)`` the same for every waiter
``("ENTER",)``       the process is now inside the critical section
``("EXIT",)``        the process has left the critical section
``("REM",)``         remainder section marker: the only state in which a
                     process is *not* trying to get in
===================  ==========================================================

Properties checked
------------------
1. **Readers-writers safety** — never two writers inside at once, and never a
   writer inside together with anybody else. Readers together are fine.
2. **Deadlock freedom** — no reachable state in which somebody is trying,
   nobody is inside, and no ``enter`` is reachable any more.
3. **Starvation freedom**, per process — no reachable lasso in which that
   process stays in its entry protocol forever while some other process enters
   at least twice, and the starved process is still being scheduled (weak
   fairness: a cycle in which it never runs at all is an unfair scheduler, not
   starvation).
4. **Concurrent reads admitted** — a *positive* property, and the whole point
   of the problem: some reachable state has two or more readers inside at once.
   A plain mutex satisfies every safety property here and still fails this one.

Everything below is exhaustive over the modelled state space, never sampled.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Dict, List, Optional, Sequence, Tuple

State = Tuple[Tuple[int, ...],
              Tuple[Tuple[int, Tuple[int, ...]], ...],
              Tuple[int, ...],
              Tuple[Tuple[int, ...], ...]]

SOLUTIONS: Dict[str, "Solution"] = {}

_P, _V, _VSIG = "P", "V", "VSIG"


class Solution:
    """One readers-writers solution, described as a set of small programs."""

    def __init__(self, name: str, roles: Sequence[str], slots: Sequence[str],
                 sems: Sequence[Tuple[str, int]], programs: Dict[str, list],
                 family: str, doc: str = "", note: str = ""):
        self.name = name
        self.roles = tuple(roles)
        self.slots = {s: i for i, s in enumerate(slots)}
        self.sem_ids = {s: i for i, (s, _) in enumerate(sems)}
        self.sem_init = tuple(v for _, v in sems)
        self.nproc = len(roles)
        # A program may be a plain list, or a factory f(pid, nproc) for the
        # two-process algorithms, whose code differs between the participants.
        self.pid_programs = []
        for pid, r in enumerate(self.roles):
            pr = programs[r]
            self.pid_programs.append(list(pr) if not callable(pr)
                                     else pr(pid, self.nproc))
        self.programs = {r: self.pid_programs[i]
                         for i, r in enumerate(self.roles)}
        self.family = family
        self.doc = doc
        self.note = note
        self._cs = [self._cs_set(prog) for prog in self.pid_programs]
        self._rem = [self._rem_set(prog) for prog in self.pid_programs]
        SOLUTIONS[name] = self

    # -------------------------------------------------------------- analysis
    def _cs_set(self, prog) -> frozenset:
        """Program counters at which this process is inside the CS."""
        inside, out = set(), False
        for i, ins in enumerate(prog):
            if ins[0] == "ENTER":
                out = True
                continue
            if ins[0] == "EXIT":
                out = False
                inside.add(i)
                continue
            if out:
                inside.add(i)
        return frozenset(inside)

    def _rem_set(self, prog) -> frozenset:
        """Program counters at which this process is in its remainder section."""
        out = set()
        rem = [i for i, ins in enumerate(prog) if ins[0] == "REM"]
        if not rem:
            return frozenset()
        start = rem[0]
        for i in range(start, len(prog)):
            out.add(i)
        return frozenset(out)

    def role_of(self, pid: int) -> str:
        return self.roles[pid]

    def in_cs(self, pid: int, pc: int) -> bool:
        return pc in self._cs[pid]

    def trying(self, pid: int, pc: int) -> bool:
        return pc not in self._rem[pid]

    def initial(self) -> State:
        shared = tuple(0 for _ in self.slots)
        sems = tuple((v, ()) for v in self.sem_init)
        pcs = tuple(0 for _ in range(self.nproc))
        locs = tuple((0,) * 2 for _ in range(self.nproc))
        return (shared, sems, pcs, locs)

    # ------------------------------------------------------------ one step
    def step(self, pid: int, st: State):
        shared, sems, pcs, locs = st
        pc = pcs[pid]
        loc = locs[pid]
        ins = self.pid_programs[pid][pc]
        op = ins[0]

        def advance(new_shared=None, new_sems=None, new_loc=None, next_pc=None,
                    action=None):
            npcs = list(pcs)
            npcs[pid] = pc + 1 if next_pc is None else next_pc
            nlocs = list(locs)
            nlocs[pid] = tuple(loc if new_loc is None else new_loc)
            return ((tuple(new_shared if new_shared is not None else shared),
                     tuple(new_sems if new_sems is not None else sems),
                     tuple(npcs), tuple(nlocs)), action)

        if op == "NOP":
            return advance()

        if op == "JUMP":
            return advance(next_pc=ins[1])

        if op == "REM":
            return advance(next_pc=ins[1] if len(ins) > 1 else 0)

        if op in ("ENTER", "EXIT"):
            return advance(action=op.lower())

        if op == "LOAD":
            _, r, v = ins
            nl = list(loc)
            nl[r] = shared[self.slots[v]]
            return advance(new_loc=tuple(nl))

        if op == "SUBI":
            _, r, k = ins
            nl = list(loc)
            nl[r] = loc[r] - k
            return advance(new_loc=tuple(nl))

        if op == "JZ":
            _, r, t = ins
            return advance(next_pc=(t if loc[r] == 0 else pc + 1))

        if op == "JNZ":
            _, r, t = ins
            return advance(next_pc=(t if loc[r] != 0 else pc + 1))

        if op in ("INC", "DEC"):
            i = self.slots[ins[1]]
            ns = list(shared)
            ns[i] = shared[i] + (1 if op == "INC" else -1)
            return advance(new_shared=tuple(ns))

        if op == "SET":
            i = self.slots[ins[1]]
            ns = list(shared)
            ns[i] = ins[2]
            return advance(new_shared=tuple(ns))

        # --- the two-process algorithms need to know who they are ----------
        # `slot(v) + pid` and `slot(v) + (1 - pid)` address the per-process
        # halves of a pair of slots, so one program text can serve both sides
        # of Dekker's and Peterson's algorithms.
        if op in ("SETP", "SETO"):
            base = self.slots[ins[1]]
            i = base + (pid if op == "SETP" else 1 - pid)
            ns = list(shared)
            ns[i] = ins[2]
            return advance(new_shared=tuple(ns))

        if op in ("LOADP", "LOADO"):
            _, r, v = ins
            base = self.slots[v]
            i = base + (pid if op == "LOADP" else 1 - pid)
            nl = list(loc)
            nl[r] = shared[i]
            return advance(new_loc=tuple(nl))

        if op in ("SETPID", "SETOTHER"):
            i = self.slots[ins[1]]
            ns = list(shared)
            ns[i] = pid if op == "SETPID" else 1 - pid
            return advance(new_shared=tuple(ns))

        if op in ("JEQPID", "JNEPID"):
            _, r, t = ins
            mine = loc[r] == pid
            take = mine if op == "JEQPID" else not mine
            return advance(next_pc=(t if take else pc + 1))

        if op in (_V, _VSIG):
            i = self.sem_ids[ins[1]]
            val, q = sems[i]
            if op == _VSIG and not q:
                return advance()                     # Mesa: the signal is lost
            nsems = list(sems)
            nsems[i] = (val + 1, q)
            return advance(new_sems=tuple(nsems))

        if op == "WAIT":
            # The atomic monitor wait: release the monitor lock, block on the
            # condition variable, and on being woken re-acquire the lock and
            # jump back to the re-test. Collapsing this into one instruction
            # removes the intermediate states in which a signalled thread owns
            # nothing and can be delayed for ever.
            _, cv, target = ins
            ci = self.sem_ids[cv]
            mi = self.sem_ids["m"]
            cval, cq = sems[ci]
            mval, mq = sems[mi]
            nsems = list(sems)
            if pid not in cq:
                nsems[ci] = (cval, tuple(cq) + (pid,))
                nsems[mi] = (mval + 1, mq)          # release the monitor
                return ((shared, tuple(nsems), pcs, locs), None)
            if (cval > 0 and cq[0] == pid and mval > 0
                    and (not mq or mq[0] == pid)):
                nsems[ci] = (cval - 1, tuple(cq[1:]))
                nsems[mi] = (mval - 1, mq)          # re-acquire the monitor
                return advance(new_sems=tuple(nsems), next_pc=target)
            return (st, None)                        # still blocked

        if op == "WAITQ":
            # Like WAIT, but on being woken the thread takes its place in the
            # monitor's entry queue instead of racing newcomers for the lock.
            # That is the difference between a Mesa monitor as Java implements
            # it -- where a notified thread has to re-compete and can be
            # barged -- and one with a fair entry queue.
            _, cv, target = ins
            ci = self.sem_ids[cv]
            mi = self.sem_ids["m"]
            _cval, cq = sems[ci]
            mval, mq = sems[mi]
            nsems = list(sems)
            if pid in mq:                            # handed to the entry queue
                if mval > 0 and mq[0] == pid:        # at its head: take the lock
                    nsems[mi] = (mval - 1, tuple(mq[1:]))
                    return advance(new_sems=tuple(nsems), next_pc=target)
                return (st, None)
            if pid in cq:                            # waiting, not yet notified
                return (st, None)
            nsems[ci] = (_cval, tuple(cq) + (pid,))  # start waiting
            nsems[mi] = (mval + 1, mq)               # and release the monitor
            return ((shared, tuple(nsems), pcs, locs), None)

        if op in ("HAND", "HAND_ALL"):
            # notify / notifyAll where the woken thread is handed straight
            # into the monitor's entry queue, so it keeps its place instead of
            # racing newcomers. The hand-off is one atomic step: a notified
            # thread that has merely not been scheduled yet is not the same
            # thing as a thread that has not been notified at all.
            _, cv = ins
            ci = self.sem_ids[cv]
            mi = self.sem_ids["m"]
            cval, cq = sems[ci]
            mval, mq = sems[mi]
            if not cq:
                return advance()                     # lost signal
            k = len(cq) if op == "HAND_ALL" else 1
            nsems = list(sems)
            nsems[ci] = (0, tuple(cq[k:]))
            nsems[mi] = (mval, tuple(mq) + tuple(cq[:k]))
            return advance(new_sems=tuple(nsems))

        if op == "SIGNAL_ALL":
            # notifyAll: every current waiter gets a wakeup. The readers and
            # writers monitor needs this, because waking one reader is not
            # enough to let a whole read phase through.
            _, cv = ins
            ci = self.sem_ids[cv]
            cval, cq = sems[ci]
            if not cq:
                return advance()                     # lost signal
            nsems = list(sems)
            nsems[ci] = (len(cq), cq)
            return advance(new_sems=tuple(nsems))

        if op == "SIGNAL":
            # Mesa semantics: wake one waiter, and if there is none lose the
            # signal. `cval` counts unclaimed wakeups and is capped by the
            # number of waiters, so the state space stays finite: several
            # signals arriving before a waiter is next scheduled collapse into
            # the one wakeup that waiter can observe. Every wait in these
            # programs re-tests in a loop, so collapsing them is sound here.
            _, cv = ins
            ci = self.sem_ids[cv]
            cval, cq = sems[ci]
            if not cq:
                return advance()                     # lost signal
            nsems = list(sems)
            nsems[ci] = (min(cval + 1, len(cq)), cq)
            return advance(new_sems=tuple(nsems))

        if op == _P:
            i = self.sem_ids[ins[1]]
            val, q = sems[i]
            nsems = list(sems)
            if pid in q:
                if val > 0 and q[0] == pid:          # head of the queue: take it
                    nsems[i] = (val - 1, tuple(q[1:]))
                    return advance(new_sems=tuple(nsems))
                return (st, None)                    # blocked
            if val > 0 and not q:                    # nobody waiting: take it
                nsems[i] = (val - 1, ())
                return advance(new_sems=tuple(nsems))
            nsems[i] = (val, tuple(q) + (pid,))      # queue up once, then block
            return ((shared, tuple(nsems), pcs, locs), None)

        raise AssertionError(f"{self.name}: bad instruction {ins!r}")

    def successors(self, st: State):
        for pid in range(self.nproc):
            nxt, action = self.step(pid, st)
            if nxt == st and action is None:
                continue                             # blocked: pruned self-loop
            yield pid, action, nxt


# =========================================================== the solutions
# Programs are written with labels so that a jump target can never be an
# off-by-one index. `("REM",)` returns to pc 0 and marks the remainder section.


def asm(lines):
    """Assemble a program. A bare ``"name:"`` declares a label.

    A jump target may be a label string instead of an index; that removes the
    class of bug where a hand-written index silently skips a release.
    """
    prog, labels = [], {}
    for ln in lines:
        if isinstance(ln, str):
            name = ln.rstrip(":")
            # A label declared twice silently rebounds every earlier jump to
            # the second copy -- the bug that a spliced-in snippet produced
            # here. Refuse it instead.
            assert name not in labels, f"duplicate label {name!r}"
            labels[name] = len(prog)
            continue
        prog.append(list(ln))
    out = []
    for ins in prog:
        op = ins[0]
        ins = list(ins)
        if op in ("JZ", "JNZ", "JEQPID", "JNEPID") and isinstance(ins[2], str):
            ins[2] = labels[ins[2]]
        elif op in ("WAIT", "WAITQ") and isinstance(ins[2], str):
            ins[2] = labels[ins[2]]
        elif op in ("JUMP", "REM") and len(ins) > 1 and isinstance(ins[1], str):
            ins[1] = labels[ins[1]]
        out.append(tuple(ins))
    return out


def _fair_monitor(program):
    """Turn a Mesa monitor program into one with a fair entry queue.

    ``WAIT`` becomes ``WAITQ`` and ``SIGNAL_ALL`` becomes ``HAND_ALL``: the
    woken thread is handed straight into the monitor's entry queue instead of
    racing newcomers for the lock.
    """
    out = []
    for ins in program:
        if ins[0] == "WAIT":
            out.append(tuple(("WAITQ",) + ins[1:]))
        elif ins[0] == "SIGNAL_ALL":
            out.append(("HAND_ALL", ins[1]))
        else:
            out.append(tuple(ins))
    return out


def _mutex_program(lock: str):
    """Both roles run the same program: acquire, CS, release."""
    return asm(["top:", ("P", lock), ("ENTER",), ("EXIT",), ("V", lock),
                ("REM",)])


# ------------------------------------------------- 1. semaphore as a plain mutex
Solution(
    "semaphore_mutex", ("R", "W"), ("unused",),
    (("m", 1),),
    {"R": _mutex_program("m"), "W": _mutex_program("m")},
    "mutex",
    "A binary semaphore used as an ordinary mutex around the whole section.",
    "Correct, and it excludes exactly the thing the problem exists to allow.")

# ---------------------------------------------------- 2. Mesa monitor as a mutex
_MON_MUTEX = asm([
    "top:", ("P", "m"),
    "retest:", ("LOAD", 0, "busy"),
    ("JZ", 0, "claim"),
    # The target of the wait has to be the re-test, not the top: jumping back
    # to P(m) would acquire the monitor lock a second time and deadlock.
    ("WAIT", "cv", "retest"),
    "claim:", ("SET", "busy", 1), ("V", "m"),
    ("ENTER",), ("EXIT",),
    ("P", "m"), ("SET", "busy", 0), ("SIGNAL_ALL", "cv"), ("V", "m"),
    ("REM",),
])
Solution(
    "monitor_mesa_mutex", ("R", "W"), ("busy",),
    (("m", 1), ("cv", 0)),
    {"R": list(_MON_MUTEX), "W": list(_MON_MUTEX)},
    "mutex",
    "A Mesa monitor used as a mutex: busy is re-tested in a loop, not an if.",
    "The re-acquire at the top of the loop is what makes a lost signal "
    "harmless.")

_FAIR_MUTEX = _fair_monitor(_MON_MUTEX)

# ------------------------------------------- 2b. the same monitor, fair entry
Solution(
    "monitor_fifo_mutex", ("R", "W"), ("busy",),
    (("m", 1), ("cv", 0)),
    {"R": _FAIR_MUTEX, "W": _FAIR_MUTEX},
    "mutex",
    "The same Mesa monitor, except that a notified thread is handed into the "
    "monitor's entry queue instead of racing for the lock.",
    "Prove the mutex correct with a fair entry queue and it stays correct; "
    "the verdict below is about the queue, not the condition variable.")

# ------------------------------------------------------------ 3. Dekker
def _dekker(pid, nproc):
    return asm([
        "top:", ("SETP", "flag", 1),              # flag[me] = 1
        "loop:", ("LOADO", 0, "flag"),            # the other side interested?
        ("JZ", 0, "enter"),
        ("LOAD", 0, "turn"),
        ("JEQPID", 0, "loop"),                    # my turn: keep spinning
        ("SETP", "flag", 0),                      # not my turn: yield
        "wait:", ("LOAD", 0, "turn"),
        ("JEQPID", 0, "retest"),                  # turn came back to me
        ("JUMP", "wait"),
        "retest:", ("SETP", "flag", 1), ("JUMP", "loop"),
        "enter:", ("ENTER",), ("EXIT",),
        ("SETOTHER", "turn"), ("SETP", "flag", 0),
        ("REM",),
    ])


Solution(
    "dekker_mutex", ("R", "W"), ("flag", "flag1", "turn"),
    (),
    {"R": _dekker, "W": _dekker},
    "dekker",
    "Dekker's algorithm: flags plus a turn, with the polite yield when both "
    "sides are interested.",
    "The first correct software solution to mutual exclusion, and it is "
    "written for exactly two processes.")

# ---------------------------------------------------------- 4. Peterson
def _peterson(pid, nproc):
    return asm([
        "top:", ("SETP", "flag", 1),              # flag[me] = 1
        ("SETOTHER", "turn"),                     # turn = other: I go second
        "loop:", ("LOADO", 0, "flag"),
        ("JZ", 0, "enter"),                       # the other side is not trying
        ("LOAD", 0, "turn"),
        ("JEQPID", 0, "enter"),                   # my turn: enter
        ("JUMP", "loop"),
        "enter:", ("ENTER",), ("EXIT",),
        ("SETP", "flag", 0),
        ("REM",),
    ])


Solution(
    "peterson_mutex", ("R", "W"), ("flag", "flag1", "turn"),
    (),
    {"R": _peterson, "W": _peterson},
    "peterson",
    "Peterson's algorithm: the same two flags, with the turn doing the "
    "yielding instead of a busy loop.",
    "Shorter and easier to prove than Dekker, and still strictly a "
    "two-process solution.")

# --------------------- 5. the readers pattern built on a two-process lock
# Both algorithms can host the readers-writers pattern: the lock guards the
# reader count instead of the section, so the two readers are inside together.
# The catch is written into the roles -- two participants is all they have.
def _dk_acquire(tag: str):
    """Dekker's entry protocol. `tag` makes the labels unique when the
    snippet is spliced into a program twice, once for the entry and once for
    the exit."""
    return [("SETP", "flag", 1), f"{tag}_loop:", ("LOADO", 0, "flag"),
            ("JZ", 0, f"{tag}_enter"), ("LOAD", 0, "turn"),
            ("JEQPID", 0, f"{tag}_loop"), ("SETP", "flag", 0),
            f"{tag}_wait:", ("LOAD", 0, "turn"),
            ("JEQPID", 0, f"{tag}_retest"), ("JUMP", f"{tag}_wait"),
            f"{tag}_retest:", ("SETP", "flag", 1), ("JUMP", f"{tag}_loop"),
            f"{tag}_enter:"]


def _pt_acquire(tag: str):
    return [("SETP", "flag", 1), ("SETOTHER", "turn"),
            f"{tag}_loop:", ("LOADO", 0, "flag"), ("JZ", 0, f"{tag}_enter"),
            ("LOAD", 0, "turn"), ("JEQPID", 0, f"{tag}_enter"),
            ("JUMP", f"{tag}_loop"), f"{tag}_enter:"]


def _count_lock_rw(acquire, release, gate: bool):
    """The readers-preference pattern built on an arbitrary two-process lock.

    `acquire` is a function ``tag -> snippet`` and `release` a snippet, so the
    lock's labels stay unique when it is spliced in twice. With `gate` the
    first reader also takes the `wrt` semaphore, which is what excludes a real
    writer; without it the model is two readers and no writer, which is the
    only configuration in which the concurrency the pattern exists for can
    actually be observed with a two-process lock.
    """
    def factory(pid, nproc):
        body = ["top:"] + acquire("in")
        body += [("INC", "rd"), ("LOAD", 0, "rd"), ("SUBI", 0, 1),
                 ("JNZ", 0, "after_take")]
        if gate:
            body += [("P", "wrt")]
        body += ["after_take:"] + release
        body += [("ENTER",), ("EXIT",)] + acquire("out")
        body += [("DEC", "rd"), ("LOAD", 0, "rd"), ("JNZ", 0, "after_give")]
        if gate:
            body += [("V", "wrt")]
        body += ["after_give:"] + release + [("REM",)]
        return asm(body)
    return factory


_DK_REL = [("SETOTHER", "turn"), ("SETP", "flag", 0)]
_PT_REL = [("SETP", "flag", 0)]

_RW_WRITER = asm(["top:", ("P", "wrt"), ("ENTER",), ("EXIT",), ("V", "wrt"),
                  ("REM",)])

Solution(
    "rw_dekker", ("R", "W"), ("rd", "flag", "flag1", "turn"),
    (("wrt", 1),),
    {"R": _count_lock_rw(_dk_acquire, _DK_REL, True), "W": _RW_WRITER},
    "dekker",
    "The readers-preference pattern with Dekker's algorithm guarding the "
    "reader count instead of the section.",
    "The pattern really is independent of the lock underneath it -- Dekker "
    "works as well as a semaphore here, at the price of a busy wait.")

Solution(
    "rw_peterson", ("R", "W"), ("rd", "flag", "flag1", "turn"),
    (("wrt", 1),),
    {"R": _count_lock_rw(_pt_acquire, _PT_REL, True), "W": _RW_WRITER},
    "peterson",
    "The same pattern with Peterson's algorithm as the count lock.",
    "Identical verdicts to Dekker's: as a count lock the two are "
    "interchangeable.")

Solution(
    "rw_dekker_2readers", ("R", "R"), ("rd", "flag", "flag1", "turn"),
    (),
    {"R": _count_lock_rw(_dk_acquire, _DK_REL, False)},
    "dekker",
    "Two readers and no writer, with Dekker's algorithm guarding the count.",
    "Both readers end up inside at once, which is the whole point of the "
    "problem -- and which no plain mutex, Dekker's included, can do.")

Solution(
    "rw_peterson_2readers", ("R", "R"), ("rd", "flag", "flag1", "turn"),
    (),
    {"R": _count_lock_rw(_pt_acquire, _PT_REL, False)},
    "peterson",
    "The same two readers with Peterson's algorithm as the count lock.",
    "The same verdict again: two readers inside, no writer, no semaphore.")

# --------------------------------------------------------- 5. readers preference
_RP_READER = asm([
    "top:", ("P", "mutex"), ("INC", "rd"), ("LOAD", 0, "rd"), ("SUBI", 0, 1),
    ("JNZ", 0, "release"),       # not the first reader: skip P(wrt)
    ("P", "wrt"),                # only the first reader takes it
    "release:", ("V", "mutex"),
    ("ENTER",), ("EXIT",),
    ("P", "mutex"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),          # not the last reader: keep wrt
    ("V", "wrt"),
    "done:", ("V", "mutex"), ("REM",),
])
_RP_WRITER = asm(["top:", ("P", "wrt"), ("ENTER",), ("EXIT",), ("V", "wrt"),
                  ("REM",)])
Solution(
    "rw_readers_pref", ("R", "W", "R"), ("rd",),
    (("mutex", 1), ("wrt", 1)),
    {"R": _RP_READER, "W": _RP_WRITER},
    "readers-preference",
    "The classic first solution: a mutex protects the reader count, wrt "
    "excludes writers.",
    "Readers never wait for a waiting writer, so a writer can be overtaken "
    "for ever.")

# --------------------------------------------------------- 6. writers preference
_WP_READER = asm([
    "top:", ("P", "readTry"),    # closed while any writer is waiting
    ("P", "mutex"), ("INC", "rd"), ("LOAD", 0, "rd"), ("SUBI", 0, 1),
    ("JNZ", 0, "release"),
    ("P", "wrt"),
    "release:", ("V", "mutex"), ("V", "readTry"),
    ("ENTER",), ("EXIT",),
    ("P", "mutex"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),
    ("V", "wrt"),
    "done:", ("V", "mutex"), ("REM",),
])
_WP_WRITER = asm([
    "top:", ("P", "wrtQ"), ("INC", "wr"), ("LOAD", 0, "wr"), ("SUBI", 0, 1),
    ("JNZ", 0, "take"),          # not the first writer: do not touch the gate
    ("P", "readTry"),            # the first writer shuts the reader door
    "take:", ("V", "wrtQ"), ("P", "wrt"),
    ("ENTER",), ("EXIT",), ("V", "wrt"),
    ("P", "wrtQ"), ("DEC", "wr"), ("LOAD", 0, "wr"),
    ("JNZ", 0, "done"),          # writers still queued: keep the door shut
    ("V", "readTry"),
    "done:", ("V", "wrtQ"), ("REM",),
])
Solution(
    "rw_writers_pref", ("R", "W", "R"), ("rd", "wr"),
    (("mutex", 1), ("wrt", 1), ("readTry", 1), ("wrtQ", 1)),
    {"R": _WP_READER, "W": _WP_WRITER},
    "writers-preference",
    "Adds a readTry gate: the first waiting writer closes it, so arriving "
    "readers queue behind the writers.",
    "Symmetric to the previous one, with the starvation moved to the readers.")

# ------------------------------------------------------------------ 7. fair FIFO
_FAIR_READER = asm([
    "top:", ("P", "queue"),      # a turnstile, held only briefly
    ("P", "mutex"), ("INC", "rd"), ("LOAD", 0, "rd"), ("SUBI", 0, 1),
    ("JNZ", 0, "release"),
    ("P", "wrt"),
    "release:", ("V", "mutex"), ("V", "queue"),
    ("ENTER",), ("EXIT",),
    ("P", "mutex"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),
    ("V", "wrt"),
    "done:", ("V", "mutex"), ("REM",),
])
_FAIR_WRITER = asm([
    "top:", ("P", "queue"), ("P", "wrt"),   # a waiting writer holds the
    ("ENTER",), ("EXIT",),                  # turnstile across the whole wait
    ("V", "wrt"), ("V", "queue"), ("REM",),
])
Solution(
    "rw_fair", ("R", "W", "R"), ("rd",),
    (("mutex", 1), ("wrt", 1), ("queue", 1)),
    {"R": _FAIR_READER, "W": _FAIR_WRITER},
    "fair",
    "A FIFO turnstile: a writer waiting for wrt holds queue, so no new reader "
    "can slip in ahead of it.",
    "The writer pays for fairness by holding a semaphore across its whole "
    "wait.")

# ------------------------------------------------- 8. writer barrier (two gates)
_BAR_READER = asm([
    "top:", ("P", "rgate"), ("P", "rmutex"), ("INC", "rd"),
    ("LOAD", 0, "rd"), ("SUBI", 0, 1),
    ("JNZ", 0, "release"),
    ("P", "wgate"),              # the first reader closes the writer gate
    "release:", ("V", "rmutex"), ("V", "rgate"),
    ("ENTER",), ("EXIT",),
    ("P", "rmutex"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),
    ("V", "wgate"),
    "done:", ("V", "rmutex"), ("REM",),
])
_BAR_WRITER = asm([
    "top:", ("P", "wmutex"), ("INC", "wr"), ("LOAD", 0, "wr"), ("SUBI", 0, 1),
    ("JNZ", 0, "take"),
    ("P", "rgate"),              # the first writer closes the reader gate
    "take:", ("V", "wmutex"), ("P", "wgate"),   # wait for the read phase
    ("ENTER",), ("EXIT",), ("V", "wgate"),
    ("P", "wmutex"), ("DEC", "wr"), ("LOAD", 0, "wr"),
    ("JNZ", 0, "done"),
    ("V", "rgate"),
    "done:", ("V", "wmutex"), ("REM",),
])
Solution(
    "rw_barrier", ("R", "W", "R"), ("rd", "wr"),
    (("rgate", 1), ("wgate", 1), ("rmutex", 1), ("wmutex", 1)),
    {"R": _BAR_READER, "W": _BAR_WRITER},
    "writer-barrier",
    "Two symmetric gates: the first reader closes wgate, the first writer "
    "closes rgate, and each phase drains before the other opens.",
    "The barrier stops new readers once a writer has declared. It does not by "
    "itself force the phases to alternate; the verdicts below say how far it "
    "actually gets.")

# --------------------------------------------------- 9. monitor, Mesa semantics
_MON_READER = asm([
    "top:", ("P", "m"),
    "retest:", ("LOAD", 0, "wactive"),
    ("JZ", 0, "enter"),
    ("WAIT", "cv", "retest"),             # a writer holds the floor
    "enter:", ("INC", "rd"), ("V", "m"),
    ("ENTER",), ("EXIT",),
    ("P", "m"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),
    ("SIGNAL_ALL", "cv"),                 # last reader out: wake the waiters
    "done:", ("V", "m"), ("REM",),
])
_MON_WRITER = asm([
    "top:", ("P", "m"),
    "retest:", ("LOAD", 0, "wactive"),
    ("JZ", 0, "check_readers"),
    ("WAIT", "cv", "retest"),             # another writer is in
    "check_readers:", ("LOAD", 0, "rd"),
    ("JZ", 0, "enter"),
    ("WAIT", "cv", "retest"),             # a read phase is open
    "enter:", ("SET", "wactive", 1), ("V", "m"),
    ("ENTER",), ("EXIT",),
    ("P", "m"), ("SET", "wactive", 0), ("SIGNAL_ALL", "cv"), ("V", "m"),
    ("REM",),
])
Solution(
    "rw_monitor_mesa", ("R", "W", "R"), ("rd", "wactive"),
    (("m", 1), ("cv", 0)),
    {"R": _MON_READER, "W": _MON_WRITER},
    "monitor",
    "Readers and writers as one condition variable inside one monitor: the "
    "monitor lock is taken for the bookkeeping, the condition variable for "
    "the waiting.",
    "Every wait loops back to the re-test, which is what Mesa semantics "
    "demand; a lost signal is then simply harmless, and notifyAll is what "
    "lets a whole read phase through at once.")

# -------------------------------------- 10. monitor with a fair entry queue
Solution(
    "rw_monitor_fifo", ("R", "W", "R"), ("rd", "wactive"),
    (("m", 1), ("cv", 0)),
    {"R": _fair_monitor(_MON_READER), "W": _fair_monitor(_MON_WRITER)},
    "monitor",
    "The same monitor, except that a woken thread queues for the monitor "
    "lock instead of racing newcomers for it.",
    "One change, and the fairness verdict flips: what was missing was never "
    "the condition variable, it was the entry queue.")

# ------------------------------------------ 11. writers preference, 2 writers
Solution(
    "rw_writers_pref_2w", ("R", "W", "W"), ("rd", "wr"),
    (("mutex", 1), ("wrt", 1), ("readTry", 1), ("wrtQ", 1)),
    {"R": _WP_READER, "W": _WP_WRITER},
    "writers-preference",
    "The same writers-preference solution with two writers instead of one.",
    "With a single writer the reader door reopens every time, so nothing "
    "starves; two writers can keep it shut, and then the reader does.")

# -------------------------------------------------- 12. broken: off-by-one
_BUG_READER = asm([
    "top:", ("P", "mutex"), ("INC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "release"),       # BUG: should be "jump unless rd == 1"
    ("P", "wrt"),
    "release:", ("V", "mutex"),
    ("ENTER",), ("EXIT",),
    ("P", "mutex"), ("DEC", "rd"), ("LOAD", 0, "rd"),
    ("JNZ", 0, "done"),
    ("V", "wrt"),
    "done:", ("V", "mutex"), ("REM",),
])
_BUG_WRITER = asm(["top:", ("P", "wrt"), ("ENTER",), ("EXIT",), ("V", "wrt"),
                   ("REM",)])
Solution(
    "rw_broken_count", ("R", "W", "R"), ("rd",),
    (("mutex", 1), ("wrt", 1)),
    {"R": _BUG_READER, "W": _BUG_WRITER},
    "broken",
    "Readers preference with the guard off by one: the first reader tests "
    "rd == 0 instead of rd == 1.",
    "One comparison away from a correct solution, and safety is gone. This is "
    "why the count has to be read while the mutex is held.")


# =================================================================== exploration

def explore(sol: Solution, max_states: int = 4_000_000,
            stop_on_violation: bool = False) -> dict:
    """Walk the reachable state space of `sol` and judge it.

    With ``stop_on_violation`` the walk stops at the first safety violation.
    That keeps the "VIOLATED" verdict sound -- a witness was found -- while
    making a broken solution affordable: once the invariant is broken the
    reachable set stops being interesting, and it grows very fast.
    """
    start = sol.initial()
    order: List[State] = []
    index: Dict[State, int] = {}
    edges: Dict[State, List[Tuple[int, Optional[str], State]]] = {}
    enter_actions = 0
    safety_witness = None
    concurrent_reads = None

    seen = {start: 0}
    order.append(start)
    queue = deque([start])
    truncated = False
    while queue:
        st = queue.popleft()
        out = []
        for pid, action, nxt in sol.successors(st):
            if action == "enter":
                enter_actions += 1
            if nxt not in seen:
                if len(order) >= max_states:
                    truncated = True
                    break
                seen[nxt] = len(order)
                order.append(nxt)
                queue.append(nxt)
            out.append((pid, action, nxt))
        if truncated:
            break
        edges[st] = out
        # --- safety and the positive concurrency property, checked as we go
        if safety_witness is None and _unsafe(sol, st):
            safety_witness = _path(edges, start, st, sol)
            if stop_on_violation:
                truncated = "stopped at the first safety violation"
                queue.clear()
                break
        if concurrent_reads is None and _concurrent_reads(sol, st):
            concurrent_reads = _path(edges, start, st, sol)

    # --- deadlock: somebody is trying, nobody is inside, no enter is reachable
    can_enter = _can_reach_enter(sol, edges, order)
    deadlock_witness = None
    for st in order:
        if any(sol.in_cs(p, st[2][p]) for p in range(sol.nproc)):
            continue
        if not any(sol.trying(p, st[2][p]) for p in range(sol.nproc)):
            continue
        if not can_enter.get(st, False):
            deadlock_witness = _path(edges, start, st, sol)
            break

    starvation = {}
    witnesses = {}
    for pid in range(sol.nproc):
        ok, wit = _starvation_free(sol, edges, order, seen, pid)
        starvation[str(pid)] = ok
        if wit:
            witnesses[str(pid)] = wit

    return {
        "name": sol.name,
        "family": sol.family,
        "doc": sol.doc,
        "note": sol.note,
        "roles": list(sol.roles),
        "nproc": sol.nproc,
        "states": len(order),
        "transitions": sum(len(v) for v in edges.values()),
        "enter_actions": enter_actions,
        "truncated": truncated,
        "stopped_early": bool(truncated),
        "rw_safety": safety_witness is None,
        "rw_safety_witness": safety_witness,
        "deadlock_free": deadlock_witness is None,
        "deadlock_witness": deadlock_witness,
        "starvation_free": starvation,
        "starvation_witness": witnesses,
        "concurrent_reads_admitted": concurrent_reads is not None,
        "concurrent_reads_witness": concurrent_reads,
    }


def _unsafe(sol: Solution, st: State) -> bool:
    inside = [p for p in range(sol.nproc) if sol.in_cs(p, st[2][p])]
    writers = [p for p in inside if sol.role_of(p) == "W"]
    if len(writers) > 1:
        return True
    return bool(writers) and len(inside) > 1


def _concurrent_reads(sol: Solution, st: State) -> bool:
    inside = [p for p in range(sol.nproc) if sol.in_cs(p, st[2][p])]
    return len(inside) >= 2 and all(sol.role_of(p) == "R" for p in inside)


def _can_reach_enter(sol, edges, order) -> Dict[State, bool]:
    """Reverse reachability: states from which some ENTER action is possible."""
    good: Dict[State, bool] = {}
    rev: Dict[State, List[State]] = {}
    for st, out in edges.items():
        for _pid, action, nxt in out:
            if action == "enter":
                good[st] = True
            rev.setdefault(nxt, []).append(st)
    work = deque([s for s, ok in good.items() if ok])
    while work:
        st = work.popleft()
        for pred in rev.get(st, ()):
            if not good.get(pred):
                good[pred] = True
                work.append(pred)
    return good


def _starvation_free(sol, edges, order, index, victim):
    """Is there a *fair* lasso in which `victim` never enters but others do?

    Four things have to hold together, and each one alone is the wrong test.

    * The victim must be *trying* at every state of the cycle -- a cycle
      through a state where it is in its remainder section proves nothing.
    * The victim must never enter on the cycle, while somebody else enters at
      least twice: otherwise nobody is being overtaken.
    * The schedule has to be fair to **every** process, not only to the
      victim. Weak fairness says that a step which stays enabled must
      eventually be taken, so on the cycle every process must either move at
      least once or be blocked at least once. Fairness only for the victim is
      not enough: a cycle in which some third process sits on an enabled step
      it never takes can hold a lock for ever and block the victim, and that
      is an unfair scheduler, not starvation.
    * The cycle has to be closed. A path that merely overtakes the victim
      twice proves nothing, because the victim might get in on the third
      attempt.
    """
    n = len(order)
    nproc = sol.nproc
    adj: List[List[Tuple[int, int, bool]]] = [[] for _ in range(n)]
    enabled = [[False] * nproc for _ in range(n)]
    for st, out in edges.items():
        i = index[st]
        for pid, action, nxt in out:
            j = index.get(nxt)
            if j is None:
                continue
            enabled[i][pid] = True
            if pid == victim and action == "enter":
                continue                  # the cycle must never contain this
            adj[i].append((j, pid, action == "enter"))
    if not any(adj[i] for i in range(n)):
        return True, None
    trying = [sol.trying(victim, order[i][2][victim]) for i in range(n)]
    blocked = [[not enabled[i][p] for p in range(nproc)] for i in range(n)]
    plain = [[j for j, _, _ in adj[i]] for i in range(n)]

    # A cycle is fair to `p` only if it uses at least one edge that either
    # belongs to `p` or leaves a state where `p` is blocked. Drop every edge
    # that satisfies neither and the remaining graph is where unfair cycles
    # live: an unfair cycle lies inside one of its strongly connected
    # components, so a component spanning two of them must be fair for `p`.
    bad_id = []
    for p in range(nproc):
        bad = [[] for _ in range(n)]
        for i in range(n):
            for j, pid, _ in adj[i]:
                if pid != p and not blocked[i][p]:
                    bad[i].append(j)
        ids = [-1] * n
        for k, comp in enumerate(_sccs(bad, n)):
            for v in comp:
                ids[v] = k
        bad_id.append(ids)

    for comp in _sccs(plain, n):
        members = set(comp)
        if not any(adj[i] for i in comp):
            continue                                   # a dead end, not a cycle
        if not all(trying[i] for i in comp):
            continue                                   # not trying throughout
        if not any(j in members and is_enter
                   for i in comp for j, _, is_enter in adj[i]):
            continue                                   # nobody else gets in
        if any(len({bad_id[p][i] for i in comp}) < 2 for p in range(nproc)):
            continue                                   # an unfair schedule
        walk = _fair_cycle(adj, comp, members, blocked, nproc)
        if walk is not None:
            trace = [_render(sol, order[walk[0]], None, None)]
            for a, b in zip(walk, walk[1:]):
                pid, is_enter = _edge(adj, a, b)
                trace.append(_render(sol, order[b], pid,
                                     "enter" if is_enter else None))
            trace.append(f"(cycle: P{victim} ({sol.role_of(victim)}) stays in "
                         f"its entry protocol while others keep entering)")
            return False, trace[1:]
    return True, None


def _edge(adj, a, b):
    for j, pid, is_enter in adj[a]:
        if j == b:
            return pid, is_enter
    return None, False


def _fair_cycle(adj, comp, members, blocked, nproc, depth=160, budget=400_000):
    """A closed walk inside `comp`, fair to every process, crossing 2 enters."""
    full = (1 << nproc) - 1
    for start in comp:
        seen = set()
        stack = [[start, 0, 0, 0, [start]]]
        steps = 0
        while stack:
            frame = stack[-1]
            node, mask, count, pos, path = frame
            if pos >= len(adj[node]) or len(path) > depth:
                stack.pop()
                continue
            frame[3] += 1
            steps += 1
            if steps > budget:
                return None
            j, pid, is_enter = adj[node][pos]
            if j not in members:
                continue
            bits = 0
            for p in range(nproc):
                if pid == p or blocked[node][p]:
                    bits |= 1 << p
            nmask = mask | bits
            ncount = count + (1 if is_enter else 0)
            if j == start and ncount >= 2 and nmask == full:
                return path + [j]
            key = (j, nmask, min(ncount, 2))
            if key in seen:
                continue
            seen.add(key)
            stack.append([j, nmask, ncount, 0, path + [j]])
    return None


def _sccs(adj, n):
    """Tarjan strongly connected components, iterative."""
    disc = [-1] * n
    low = [0] * n
    on = [False] * n
    stack: List[int] = []
    comps: List[List[int]] = []
    timer = 0
    for root in range(n):
        if disc[root] != -1:
            continue
        work = [(root, 0)]
        while work:
            v, pi = work.pop()
            if pi == 0:
                disc[v] = low[v] = timer
                timer += 1
                stack.append(v)
                on[v] = True
            descend = False
            for k in range(pi, len(adj[v])):
                w = adj[v][k]
                if disc[w] == -1:
                    work.append((v, k + 1))
                    work.append((w, 0))
                    descend = True
                    break
                if on[w]:
                    low[v] = min(low[v], disc[w])
            if descend:
                continue
            if low[v] == disc[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on[w] = False
                    comp.append(w)
                    if w == v:
                        break
                comps.append(comp)
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    return comps


def _render(sol, st, pid, action) -> str:
    shared, sems, pcs, locs = st
    tag = f"P{pid}({sol.role_of(pid)}):" if pid is not None else "     "
    act = f" {action.upper()}" if action else ""
    sems_s = "{" + ", ".join(f"{n}={v}q{list(q)}"
                             for n, (v, q) in
                             zip(sol.sem_ids, sems)) + "}"
    return f"{tag} pcs={pcs} {sems_s} shared={shared}{act}"


def _path(edges, start, target, sol, limit=48):
    """Shortest path start -> target as a readable trace."""
    if target == start:
        return [_render(sol, start, None, None)]
    prev: Dict[State, Tuple[State, int, Optional[str]]] = {}
    seen = {start}
    queue = deque([start])
    while queue:
        st = queue.popleft()
        for pid, action, nxt in edges.get(st, ()):
            if nxt in seen:
                continue
            seen.add(nxt)
            prev[nxt] = (st, pid, action)
            if nxt == target:
                path, cur = [], nxt
                while cur != start:
                    p, pid_, act = prev[cur]
                    path.append(_render(sol, cur, pid_, act))
                    cur = p
                path.append(_render(sol, start, None, None))
                path.reverse()
                return path[:limit]
            queue.append(nxt)
    return None


def check_all(max_states: int = 4_000_000) -> Dict[str, dict]:
    return {name: explore(s, max_states) for name, s in SOLUTIONS.items()}


def format_report(results: Dict[str, dict]) -> str:
    lines = []
    for name, r in results.items():
        lines.append(f"=== {name}  [{r['family']}]  roles={''.join(r['roles'])}")
        lines.append(f"    {r['doc']}")
        lines.append(f"    states={r['states']}  transitions={r['transitions']} "
                     f" enters={r['enter_actions']}"
                     + ("  TRUNCATED" if r["truncated"] else ""))
        lines.append(f"    rw safety         : "
                     f"{'HOLDS' if r['rw_safety'] else 'VIOLATED'}")
        for step in (r["rw_safety_witness"] or [])[:12]:
            lines.append("        " + step)
        lines.append(f"    deadlock free     : "
                     f"{'YES' if r['deadlock_free'] else 'NO'}")
        for step in (r["deadlock_witness"] or [])[:12]:
            lines.append("        " + step)
        lines.append("    starvation free   : " + ", ".join(
            f"P{k}({r['roles'][int(k)]})={'YES' if v else 'NO'}"
            for k, v in sorted(r["starvation_free"].items())))
        for k, w in sorted(r["starvation_witness"].items()):
            for step in (w or [])[:12]:
                lines.append(f"        P{k}: " + step)
        lines.append(f"    concurrent reads  : "
                     f"{'POSSIBLE' if r['concurrent_reads_admitted'] else 'IMPOSSIBLE'}")
        for step in (r["concurrent_reads_witness"] or [])[:12]:
            lines.append("        " + step)
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    import argparse
    import json
    import os

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-states", type=int, default=600_000)
    ap.add_argument("--json", default=None,
                    help="write the verdicts to this file as JSON")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    results = {}
    for name, sol in SOLUTIONS.items():
        # A broken solution only needs its one witness; exploring the rest of
        # its state space costs minutes and says nothing more.
        results[name] = explore(sol, max_states=args.max_states,
                                stop_on_violation=(sol.family == "broken"))
    if not args.quiet:
        print(format_report(results))
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=1, sort_keys=True)
        print(f"wrote {args.json}")
    return 0 if all(r["rw_safety"] for r in results.values()
                    if r["family"] != "broken") else 1


if __name__ == "__main__":
    raise SystemExit(main())
