"""Exhaustive model checker for two-process mutual-exclusion algorithms.

Why a model checker and not just threads
----------------------------------------
Running Dekker's or Peterson's algorithm on real threads proves nothing: the
outcome depends on scheduling luck, the interpreter's memory model and the GIL.
What *can* be proved is a statement about **all possible interleavings** of the
atomic steps of the algorithm. That is exactly what this module does.

Model
-----
Time is discrete and memory is sequentially consistent. A global state is::

    (shared, (pc0, loc0), (pc1, loc1))

``shared`` is a small tuple of integers (flags, turn, semaphores, queues, ...),
``pc`` is the program counter of a process and ``loc`` is a tuple holding that
process's private registers. Each algorithm exposes a ``step`` function::

    step(pid, pc, loc, shared) -> (pc2, loc2, shared2, action)

``action`` is ``None``, ``"enter"`` (the process just entered its critical
section) or ``"exit"``. A process that is *blocked* is modelled by a transition
that returns the state unchanged; the explorer prunes such self-loops, so a
blocked process simply has no useful successor.

Properties checked
------------------
1. **Mutual exclusion** — no reachable state has two processes in their critical
   section. A violating path is reported as a witness.
2. **Deadlock / lockout freedom** — no reachable state in which the system can
   never again reach an ``enter`` action while some process is still trying.
3. **Starvation freedom (bounded waiting)** — for each process P, there is no
   reachable lasso in which P never enters while the other process enters at
   least twice.
4. **Progress** — from every reachable state, some ``enter`` is reachable
   unless all processes are in their remainder section.

The state spaces here are tiny (a few thousand states at most), so every answer
below is exhaustive, not sampled.
"""

from __future__ import annotations

from collections import deque
from typing import Callable, Dict, List, Optional, Tuple

State = Tuple[Tuple[int, ...], Tuple[int, Tuple[int, ...]], Tuple[int, Tuple[int, ...]]]

ALGORITHMS: Dict[str, "Algorithm"] = {}


class Algorithm:
    """One mutual-exclusion algorithm, described as a state machine."""

    def __init__(self, name: str, npc: int, init_shared, init_loc,
                 step: Callable, in_cs: Callable, trying: Callable,
                 family: str, procs: int = 2, doc: str = ""):
        self.name = name
        self.npc = npc
        self.init_shared = init_shared
        self.init_loc = init_loc
        self.step = step
        self.in_cs = in_cs
        self.trying = trying
        self.family = family
        self.procs = procs
        self.doc = doc
        ALGORITHMS[name] = self

    # ---------------------------------------------------------------- helpers
    def initial(self) -> State:
        shared = tuple(self.init_shared())
        pcs = tuple(0 for _ in range(self.procs))
        locs = tuple(tuple(self.init_loc(p)) for p in range(self.procs))
        return (shared, pcs, locs)

    def successors(self, st: State):
        """Yield (pid, action, next_state) for every enabled transition."""
        shared, pcs, locs = st
        for pid in range(self.procs):
            pc2, loc2, shared2, action = self.step(pid, pcs[pid], locs[pid], shared)
            npcs = list(pcs)
            nlocs = list(locs)
            npcs[pid] = pc2
            nlocs[pid] = tuple(loc2)
            nxt = (tuple(shared2), tuple(npcs), tuple(nlocs))
            if nxt == st and action is None:
                continue  # a blocked process: self-loop, nothing to explore
            yield pid, action, nxt

    def both_in_cs(self, st: State) -> int:
        return sum(1 for pid in range(self.procs) if self.in_cs(pid, st[1][pid]))


# =============================================================== queues (2 procs)
# The queue of a semaphore holds at most two process ids, so it is encoded as a
# single small integer: 0 = empty, 1 = [0], 2 = [1], 3 = [0,1], 4 = [1,0].

_Q_EMPTY, _Q_P0, _Q_P1, _Q_P0P1, _Q_P1P0 = 0, 1, 2, 3, 4


def _q_head(q: int) -> Optional[int]:
    if q in (_Q_P0, _Q_P0P1):
        return 0
    if q in (_Q_P1, _Q_P1P0):
        return 1
    return None


def _q_pop(q: int) -> int:
    return {_Q_P0: _Q_EMPTY, _Q_P1: _Q_EMPTY, _Q_P0P1: _Q_P1, _Q_P1P0: _Q_P0}.get(q, q)


def _q_push(q: int, pid: int) -> int:
    if q == _Q_EMPTY:
        return _Q_P0 if pid == 0 else _Q_P1
    if q == _Q_P0 and pid == 1:
        return _Q_P0P1
    if q == _Q_P1 and pid == 0:
        return _Q_P1P0
    return q


def _q_has(q: int, pid: int) -> bool:
    return q != _Q_EMPTY and (pid == 0 and q in (_Q_P0, _Q_P0P1, _Q_P1P0)
                              or pid == 1 and q in (_Q_P1, _Q_P0P1, _Q_P1P0))


# ====================================================================== DEKKER
# flag[i]=True; while flag[j] { if turn==j { flag[i]=False;
#                                            while turn==j {}
#                                            flag[i]=True } }
# CS; turn=j; flag[i]=False; remainder
#
# shared = (flag0, flag1, turn);  loc = (rv,)

def _dekker_step(pid, pc, loc, shared):
    f0, f1, turn = shared
    j = 1 - pid
    fl = [f0, f1]
    if pc == 0:
        fl[pid] = 1
        return 1, loc, (fl[0], fl[1], turn), None
    if pc == 1:
        return 2, (fl[j],), (f0, f1, turn), None
    if pc == 2:
        return (3 if loc[0] else 9), loc, shared, None
    if pc == 3:
        return 4, (turn,), shared, None
    if pc == 4:
        return (5 if loc[0] == j else 1), loc, shared, None
    if pc == 5:
        fl[pid] = 0
        return 6, loc, (fl[0], fl[1], turn), None
    if pc == 6:
        return 7, (turn,), shared, None
    if pc == 7:
        return (6 if loc[0] == j else 0), loc, shared, None
    if pc == 9:
        return 10, loc, shared, "enter"
    if pc == 10:
        return 11, loc, (f0, f1, j), None
    if pc == 11:
        fl[pid] = 0
        return 12, loc, (fl[0], fl[1], turn), None
    if pc == 12:                      # remainder section
        return 0, loc, shared, None
    raise AssertionError(f"dekker: bad pc {pc}")


Algorithm("dekker", 13, lambda: (0, 0, 0), lambda p: (0,),
          _dekker_step, lambda pid, pc: pc == 10,
          lambda pid, pc: pc in (0, 1, 2, 3, 4, 5, 6, 7, 9), "software", 2,
          "Dekker's algorithm: two flags plus a turn variable.")


# ==================================================================== PETERSON
# flag[i]=True; turn=j; while (flag[j] && turn==j) {}; CS; flag[i]=False
#
# shared = (flag0, flag1, turn);  loc = (rv,)

def _peterson_step(pid, pc, loc, shared):
    f0, f1, turn = shared
    j = 1 - pid
    fl = [f0, f1]
    if pc == 0:
        fl[pid] = 1
        return 1, loc, (fl[0], fl[1], turn), None
    if pc == 1:
        return 2, loc, (fl[0], fl[1], j), None
    if pc == 2:
        return 3, (fl[j],), shared, None
    if pc == 3:
        return (4 if loc[0] else 6), loc, shared, None
    if pc == 4:
        return 5, (turn,), shared, None
    if pc == 5:
        return (2 if loc[0] == j else 6), loc, shared, None
    if pc == 6:
        return 7, loc, shared, "enter"
    if pc == 7:
        fl[pid] = 0
        return 8, loc, (fl[0], fl[1], turn), None
    if pc == 8:                       # remainder section
        return 0, loc, shared, None
    raise AssertionError(f"peterson: bad pc {pc}")


Algorithm("peterson", 9, lambda: (0, 0, 0), lambda p: (0,),
          _peterson_step, lambda pid, pc: pc == 7,
          lambda pid, pc: pc in (0, 1, 2, 3, 4, 5, 6), "software", 2,
          "Peterson's algorithm: two flags plus a turn variable, simpler loop.")


# ================================================================ LOCK VARIABLE
# The classic broken attempt: test the other flag, then set your own.
#   while flag[j] {}   flag[i]=True   CS   flag[i]=False
# Both processes can read "free" before either writes, so mutual exclusion
# breaks.  shared = (flag0, flag1);  loc = (rv,)

def _lockvar_step(pid, pc, loc, shared):
    f0, f1 = shared
    j = 1 - pid
    fl = [f0, f1]
    if pc == 0:
        return 1, (fl[j],), shared, None
    if pc == 1:
        return (0 if loc[0] else 2), loc, shared, None
    if pc == 2:
        fl[pid] = 1
        return 3, loc, (fl[0], fl[1]), None
    if pc == 3:
        return 4, loc, shared, "enter"
    if pc == 4:
        fl[pid] = 0
        return 5, loc, (fl[0], fl[1]), None
    if pc == 5:
        return 0, loc, shared, None
    raise AssertionError(f"lock_variable: bad pc {pc}")


Algorithm("lock_variable", 6, lambda: (0, 0), lambda p: (0,),
          _lockvar_step, lambda pid, pc: pc == 4,
          lambda pid, pc: pc in (0, 1, 2, 3), "broken", 2,
          "Broken: test-then-set on a single lock variable.")


# ============================================================== FLAG-ONLY SPIN
#   flag[i]=True; while flag[j] {}; CS; flag[i]=False
# Mutual exclusion happens to hold, but if both processes announce interest
# before either looks, both spin forever: the algorithm deadlocks.
# shared = (flag0, flag1);  loc = (rv,)

def _flagspin_step(pid, pc, loc, shared):
    f0, f1 = shared
    j = 1 - pid
    fl = [f0, f1]
    if pc == 0:
        fl[pid] = 1
        return 1, loc, (fl[0], fl[1]), None
    if pc == 1:
        return 2, (fl[j],), shared, None
    if pc == 2:
        return (1 if loc[0] else 3), loc, shared, None
    if pc == 3:
        return 4, loc, shared, "enter"
    if pc == 4:
        fl[pid] = 0
        return 5, loc, (fl[0], fl[1]), None
    if pc == 5:
        return 0, loc, shared, None
    raise AssertionError(f"flag_spin: bad pc {pc}")


Algorithm("flag_spin", 6, lambda: (0, 0), lambda p: (0,),
          _flagspin_step, lambda pid, pc: pc == 4,
          lambda pid, pc: pc in (0, 1, 2, 3), "broken", 2,
          "Broken: announces interest then spins; can deadlock.")


# ============================================================ TEST-AND-SET LOCK
#   while TAS(lock) {}; CS; lock=0
# Correct mutual exclusion, but nothing bounds how often a process can be
# overtaken, so starvation is possible.  shared = (lock,);  loc = (prev,)

def _tas_step(pid, pc, loc, shared):
    (lock,) = shared
    if pc == 0:
        return 1, (lock,), (1,), None          # TAS: read old value, write 1
    if pc == 1:
        return (0 if loc[0] else 2), loc, shared, None
    if pc == 2:
        return 3, loc, shared, "enter"
    if pc == 3:
        return 4, loc, (0,), None
    if pc == 4:
        return 5, loc, shared, None
    if pc == 5:                       # remainder section
        return 0, loc, shared, None
    raise AssertionError(f"tas: bad pc {pc}")


Algorithm("tas", 6, lambda: (0,), lambda p: (0,),
          _tas_step, lambda pid, pc: pc == 3,
          lambda pid, pc: pc in (0, 1, 2), "hardware", 2,
          "Test-and-set spinlock: correct exclusion, no bounded waiting.")


# ==================================================================== SEMAPHORE
# Binary semaphore with a FIFO wait queue.  P0 and P1 run the same program.
# shared = (s, q);  loc = ()

def _sem_step(pid, pc, loc, shared):
    s, q = shared
    if pc == 0:                                     # acquire
        head = _q_head(q)
        if s == 1 and head in (None, pid):
            # Take the permit.  FIFO: only the head of the queue may take it,
            # which is what stops a late arrival from barging in.
            return 1, loc, (0, _q_pop(q) if head == pid else q), None
        # cannot take it: join the queue and stay blocked
        return 0, loc, (s, _q_push(q, pid)), None
    if pc == 1:
        return 2, loc, shared, "enter"
    if pc == 2:                                     # release
        # The permit is handed back; the head of the queue (if any) takes it
        # next, because acquire only lets the head proceed.
        return 3, loc, (1, q), None
    if pc == 3:
        return 0, loc, shared, None
    raise AssertionError(f"semaphore: bad pc {pc}")


Algorithm("semaphore_binary", 4, lambda: (1, _Q_EMPTY), lambda p: (),
          _sem_step, lambda pid, pc: pc == 2,
          lambda pid, pc: pc in (0, 1), "primitive", 2,
          "Binary semaphore with a FIFO wait queue (correct usage).")


# ==================================================== SEMAPHORE, WRONG ORDER
# P0 takes A then B; P1 takes B then A.  The state where P0 holds A and waits
# for B while P1 holds B and waits for A is a deadlock.
# shared = (sA, sB, qA, qB);  loc = ()

def _acquire(st, idx_s, idx_q, pid):
    """Try to take semaphore (s, q) stored at two positions of the tuple."""
    s = st[idx_s]
    q = st[idx_q]
    if s == 1 and (_q_head(q) in (None, pid) or not _q_has(q, pid)):
        if _q_head(q) in (None, pid):
            out = list(st)
            out[idx_s] = 0
            out[idx_q] = _q_pop(q) if _q_head(q) == pid else q
            return tuple(out), True
    out = list(st)
    out[idx_q] = _q_push(q, pid)
    return tuple(out), False


def _release(st, idx_s, idx_q):
    out = list(st)
    if out[idx_q] == _Q_EMPTY:
        out[idx_s] = 1
    return tuple(out), True


def _sem_wrong_step(pid, pc, loc, shared):
    # (A, B) for process 0, (B, A) for process 1
    first, second = (0, 1) if pid == 0 else (1, 0)   # indices of sA, sB
    if pc == 0:
        nxt, ok = _acquire(shared, first, first + 2, pid)
        return (1 if ok else 0), loc, nxt, None
    if pc == 1:
        nxt, ok = _acquire(shared, second, second + 2, pid)
        return (2 if ok else 1), loc, nxt, None
    if pc == 2:
        return 3, loc, shared, "enter"
    if pc == 3:
        nxt, _ = _release(shared, second, second + 2)
        return 4, loc, nxt, None
    if pc == 4:
        nxt, _ = _release(shared, first, first + 2)
        return 5, loc, nxt, None
    if pc == 5:
        return 0, loc, shared, None
    raise AssertionError(f"semaphore_wrong_order: bad pc {pc}")


Algorithm("semaphore_wrong_order", 6, lambda: (1, 1, _Q_EMPTY, _Q_EMPTY),
          lambda p: (), _sem_wrong_step, lambda pid, pc: pc in (2, 3, 4),
          lambda pid, pc: pc in (0, 1), "broken", 2,
          "Broken: two semaphores acquired in opposite orders; deadlocks.")


# ====================================================================== MONITOR
# A Mesa-style monitor guarding a bounded buffer of capacity one.
# Process 0 is the producer, process 1 is the consumer.
#
# shared = (busy, count, wfull, wempty)
#     busy    - 1 while some process is inside the monitor
#     count   - items in the buffer (0 or 1)
#     wfull   - queue of the not_full condition   (0/1/2, see _q_* but only one
#               process can ever wait on it, so a plain pid-slot is enough:
#               0 = nobody, 1 = producer waiting)
#     wempty  - same for not_empty: 0 = nobody, 2 = consumer waiting

def _monitor_step(pid, pc, loc, shared):
    busy, count, wfull, wempty = shared
    if pid == 0:                                   # ---------------- producer
        if pc == 0:                                # try to enter the monitor
            if busy:
                return 0, loc, shared, None
            return 1, loc, (1, count, wfull, wempty), None
        if pc == 1:                                # while full: wait(not_full)
            if count == 1:
                return 2, loc, (0, count, 1, wempty), None
            return 3, loc, shared, None
        if pc == 2:                                # blocked on not_full
            if wfull == 0:
                return 0, loc, shared, None        # signalled: re-acquire
            return 2, loc, shared, None
        if pc == 3:
            return 4, loc, shared, "enter"         # produce
        if pc == 4:
            return 5, loc, (busy, 1, wfull, wempty), None
        if pc == 5:                                # signal(not_empty)
            return 6, loc, (busy, count, wfull, 0), None
        if pc == 6:                                # leave the monitor
            return 7, loc, (0, count, wfull, wempty), None
        if pc == 7:
            return 0, loc, shared, None
        raise AssertionError(f"monitor: bad pc {pc}")
    # --------------------------------------------------------------- consumer
    if pc == 0:
        if busy:
            return 0, loc, shared, None
        return 1, loc, (1, count, wfull, wempty), None
    if pc == 1:
        if count == 0:
            return 2, loc, (0, count, wfull, 2), None
        return 3, loc, shared, None
    if pc == 2:                                    # blocked on not_empty
        if wempty == 0:
            return 0, loc, shared, None
        return 2, loc, shared, None
    if pc == 3:
        return 4, loc, shared, "enter"             # consume
    if pc == 4:
        return 5, loc, (busy, 0, wfull, wempty), None
    if pc == 5:                                    # signal(not_full)
        return 6, loc, (busy, count, 0, wempty), None
    if pc == 6:
        return 7, loc, (0, count, wfull, wempty), None
    if pc == 7:
        return 0, loc, shared, None
    raise AssertionError(f"monitor: bad pc {pc}")


def _monitor_in_cs(pid, pc):
    # Holding the monitor lock: everything except pc 0 (outside), 2 (waiting)
    # and 7 (remainder).
    return pc in (1, 3, 4, 5, 6)


Algorithm("monitor_mesa", 8, lambda: (0, 0, 0, 0), lambda p: (),
          _monitor_step, _monitor_in_cs,
          lambda pid, pc: pc in (0, 2), "monitor", 2,
          "Mesa monitor over a bounded buffer of capacity one.")


# ==================================================================== EXPLORER

def explore(algo: Algorithm, limit: int = 500_000) -> dict:
    """Explore the whole reachable state space of ``algo``."""
    start = algo.initial()
    edges: Dict[State, List[Tuple[int, Optional[str], State]]] = {}
    order: List[State] = []
    seen = {start}
    queue = deque([start])
    truncated = False
    while queue:
        st = queue.popleft()
        order.append(st)
        out = []
        for pid, action, nxt in algo.successors(st):
            out.append((pid, action, nxt))
            if nxt not in seen:
                if len(seen) >= limit:
                    truncated = True
                    break
                seen.add(nxt)
                queue.append(nxt)
        edges[st] = out
        if truncated:
            break

    # ------------------------------------------------------ mutual exclusion
    me_violation = None
    for st in order:
        if algo.both_in_cs(st) > 1:
            me_violation = _witness(algo, start, st, edges)
            break

    # ------------------------- states from which an "enter" is still reachable
    can_enter = _backward_can_enter(algo, edges)
    deadlock = None
    for st in order:
        if st not in can_enter and _someone_is_trying(algo, st):
            deadlock = _witness(algo, start, st, edges)
            break

    # ------------------------------------------------------------- starvation
    starvation = {}
    for victim in range(algo.procs):
        starvation[victim] = _starvation_for(algo, edges, order, victim)

    enters = sum(1 for st in order for (_, a, _) in edges.get(st, ()) if a == "enter")
    return {
        "algorithm": algo.name,
        "family": algo.family,
        "doc": algo.doc,
        "states": len(order),
        "transitions": sum(len(v) for v in edges.values()),
        "truncated": truncated,
        "mutual_exclusion": me_violation is None,
        "mutual_exclusion_witness": me_violation,
        "deadlock_free": deadlock is None,
        "deadlock_witness": deadlock,
        "starvation_free": {str(k): (v is None) for k, v in starvation.items()},
        "starvation_witness": {str(k): v for k, v in starvation.items()},
        "enter_actions": enters,
    }


def _someone_is_trying(algo: Algorithm, st: State) -> bool:
    """True if at least one process is in its entry or waiting section."""
    shared, pcs, _ = st
    return any(algo.trying(pid, pcs[pid]) for pid in range(algo.procs))


def _backward_can_enter(algo, edges):
    """States from which some 'enter' action is reachable."""
    rev: Dict[State, List[State]] = {}
    good = set()
    stack = []
    for st, out in edges.items():
        for _, action, nxt in out:
            rev.setdefault(nxt, []).append(st)
            if action == "enter":
                if st not in good:
                    good.add(st)
                    stack.append(st)
    while stack:
        st = stack.pop()
        for pre in rev.get(st, ()):
            if pre not in good:
                good.add(pre)
                stack.append(pre)
    return good


def _witness(algo, start, target, edges, maxlen=64):
    """Shortest path start -> target, rendered as a readable trace."""
    if target == start:
        return [_render(algo, start, None, None)]
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
                path = []
                cur = nxt
                while cur != start:
                    p, pid_, act = prev[cur]
                    path.append(_render(algo, cur, pid_, act))
                    cur = p
                path.append(_render(algo, start, None, None))
                path.reverse()
                return path[:maxlen]
            queue.append(nxt)
    return None


def _render(algo, st, pid, action):
    shared, pcs, locs = st
    tag = f"P{pid}:" if pid is not None else "  "
    act = f" {action.upper()}" if action else ""
    return f"{tag} pc=({pcs[0]},{pcs[1]}) shared={shared} loc={locs}{act}"


def _starvation_for(algo, edges, order, victim):
    """Look for a reachable lasso in which `victim` stays in its entry/waiting
    section forever (never enters, never gives up) while the other process
    enters its critical section at least twice.

    Requiring the victim to stay inside ``trying`` for the whole cycle is what
    separates real starvation from the trivial case of a process that simply
    never asks for the lock.
    """
    other = 1 - victim
    index = {st: i for i, st in enumerate(order)}
    n = len(order)

    # Restrict the graph: the victim must never enter and must stay trying.
    adj: List[List[int]] = [[] for _ in range(n)]
    enters_by_other: List[List[int]] = [[] for _ in range(n)]
    edge_pid = {}
    for st, out in edges.items():
        i = index[st]
        for pid, action, nxt in out:
            if action == "enter" and pid == victim:
                continue
            j = index.get(nxt)
            if j is None:
                continue
            if not algo.trying(victim, nxt[1][victim]):
                continue                      # victim left the entry section
            adj[i].append(j)
            edge_pid[(i, j)] = pid
            if action == "enter" and pid == other:
                enters_by_other[i].append(j)

    comps = _sccs(adj, n)
    for comp in comps:
        members = set(comp)
        enter_edges = {(i, j) for i in members
                       for j in enters_by_other[i] if j in members}
        if not enter_edges:
            continue
        if not any(adj[i] for i in comp):
            continue                          # no cycle: a single trapped state
        # Weak fairness: a cycle in which the victim never even gets scheduled
        # is not starvation, it is an unfair scheduler.  The walk must contain
        # at least one step taken by the victim.
        path = _walk_with_two_enters(adj, enter_edges, members, comp,
                                     edge_pid, victim)
        if path is None:
            continue
        trace = [_render(algo, order[path[0]], None, None)]
        for a, b in zip(path, path[1:]):
            pid_, act = _edge_label(algo, edges, order[a], order[b])
            trace.append(_render(algo, order[b], pid_, act))
        trace.append(f"(cycle: P{victim} stays in its entry section while "
                     f"P{other} enters at least twice)")
        return trace
    return None


def _edge_label(algo, edges, a, b):
    for pid, action, nxt in edges.get(a, ()):
        if nxt == b:
            return pid, action
    return None, None


def _sccs(adj, n):
    """Tarjan strongly connected components, iterative."""
    disc = [-1] * n
    low = [0] * n
    on_stack = [False] * n
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
                on_stack[v] = True
            recurse = False
            for k in range(pi, len(adj[v])):
                w = adj[v][k]
                if disc[w] == -1:
                    work.append((v, k + 1))
                    work.append((w, 0))
                    recurse = True
                    break
                if on_stack[w]:
                    low[v] = min(low[v], disc[w])
            if recurse:
                continue
            if low[v] == disc[v]:
                comp = []
                while True:
                    w = stack.pop()
                    on_stack[w] = False
                    comp.append(w)
                    if w == v:
                        break
                comps.append(comp)
            if work:
                u = work[-1][0]
                low[u] = min(low[u], low[v])
    return comps


def _walk_with_two_enters(adj, enter_edges, members, comp, edge_pid, victim,
                          depth=48):
    """Depth-limited walk inside `members` that crosses >= 2 enter edges taken
    by the other process, and in which the victim also gets to run."""
    seen_at = {}

    def dfs(node, count, steps, path, moved):
        if count >= 2 and moved:
            return list(path)
        if steps <= 0:
            return None
        key = (node, count, moved)
        if seen_at.get(key, -1) >= steps:
            return None
        seen_at[key] = steps
        for j in adj[node]:
            if j not in members:
                continue
            path.append(j)
            got = dfs(j, count + (1 if (node, j) in enter_edges else 0),
                      steps - 1, path,
                      moved or edge_pid.get((node, j)) == victim)
            if got is not None:
                return got
            path.pop()
        return None

    for start in comp:
        got = dfs(start, 0, depth, [start], False)
        if got is not None:
            return got
    return None


# ====================================================================== REPORT

def check_all() -> Dict[str, dict]:
    return {name: explore(a) for name, a in ALGORITHMS.items()}


def format_report(results: Dict[str, dict]) -> str:
    lines = []
    for name, r in results.items():
        lines.append(f"=== {name}  [{r['family']}]")
        lines.append(f"    {r['doc']}")
        lines.append(f"    states={r['states']}  transitions={r['transitions']}"
                     f"  enter_actions={r['enter_actions']}")
        lines.append(f"    mutual exclusion : "
                     f"{'HOLDS' if r['mutual_exclusion'] else 'VIOLATED'}")
        if r["mutual_exclusion_witness"]:
            lines.append("      witness:")
            for step in r["mutual_exclusion_witness"]:
                lines.append("        " + step)
        lines.append(f"    deadlock free    : "
                     f"{'YES' if r['deadlock_free'] else 'NO'}")
        if r["deadlock_witness"]:
            lines.append("      witness:")
            for step in r["deadlock_witness"]:
                lines.append("        " + step)
        lines.append("    starvation free  : " + ", ".join(
            f"P{k}={'YES' if v else 'NO'}" for k, v in
            sorted(r["starvation_free"].items())))
        for k, w in sorted(r["starvation_witness"].items()):
            if w:
                lines.append(f"      P{k} witness:")
                for step in w:
                    lines.append("        " + step)
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    print(format_report(check_all()))
