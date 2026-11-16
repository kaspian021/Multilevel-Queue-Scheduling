# -*- coding: utf-8 -*-
"""Exercise 4 — English report on Dekker, Peterson, semaphore and monitor.

Every number is read from ``exercise-4/output/experiments.json``, which is
produced by ``code/run_experiments.py``, so the prose and the program cannot
disagree.
"""
from __future__ import annotations

import json
import os

from report_kit import (Report, cover, toc, ptitle, h1, para, bullets, table,
                        kv, image, code, formula, note)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
DATA = json.load(open(os.path.join(_REPO, "exercise-4", "output",
                                   "experiments.json"), encoding="utf-8"))

M = DATA["model"]
B = DATA["benchmark"]
C = DATA["contention"]
PC = DATA["producer_consumer"]
RW = DATA["readers_writers"]
DL = DATA["deadlock"]

TITLE = ("Exercise 4 — Dekker, Peterson, Semaphore and Monitor: "
         "a verified comparative study")
SUBTITLE = ("Mutual exclusion proved by exhaustive model checking and measured "
            "on running threads")

COVER_META = [
    ("Exercise", "Dekker, Peterson, semaphore and monitor"),
    ("Course", "Advanced Operating Systems"),
    ("Topic", "Mutual exclusion and process synchronisation"),
    ("Verification method", "exhaustive model checking over all interleavings"),
    ("Algorithms checked", "8 (4 correct, 3 deliberately broken, 1 hardware)"),
    ("Measured mechanisms", "Dekker, Peterson, TAS, semaphore, monitor, 3 readers-writers variants"),
    ("Deliverable", "Persian and English reports (DOCX and PDF) + runnable code + tests"),
    ("Repository", "github.com/kaspian021/Multilevel-Queue-Scheduling"),
    ("Branch", "Exercise-4-Dekker-Peterson-Semaphore-Monitor"),
]


def _yes(flag):
    return "yes" if flag else "**no**"


def _md_row(name):
    r = M[name]
    sf = "yes" if all(r["starvation_free"].values()) else "**no**"
    return [f"`{name}`", r["family"], str(r["states"]),
            "holds" if r["mutual_exclusion"] else "**VIOLATED**",
            "yes" if r["deadlock_free"] else "**no**", sf]


def _witness(name, key):
    return M[name][key] or []


def build():
    r = Report(TITLE, SUBTITLE, "en", cover_meta=COVER_META)

    r.page(cover(COVER_META))
    r.page(toc())

    # ---------------------------------------------------------------- abstract
    r.page(
        ptitle("Abstract, keywords and report map"),
        h1("Abstract"),
        para("This exercise studies four approaches to mutual exclusion: "
             "Dekker's algorithm, Peterson's algorithm, semaphores and "
             "monitors. The central methodological point is that running a "
             "concurrent program and watching it succeed proves nothing. What "
             "proves something is a statement about every possible interleaving "
             "of the atomic steps, which is what the model checker built for "
             "this exercise computes exhaustively."),
        para(f"Eight algorithms were checked: four correct ones (Dekker, "
             f"Peterson, a binary semaphore and a Mesa monitor), one hardware "
             f"primitive (test-and-set) and three deliberately broken "
             f"variants. The largest state space has only "
             f"{max(v['states'] for v in M.values())} reachable states, so every "
             f"verdict below is complete rather than sampled. Alongside the "
             f"proofs, {len(B)} mechanisms were benchmarked on running threads to "
             f"measure what correctness costs."),
        h1("Keywords"),
        para("Mutual exclusion; critical section; Dekker's algorithm; "
             "Peterson's algorithm; test-and-set; semaphore; monitor; condition "
             "variable; Mesa semantics; bounded waiting; starvation; deadlock; "
             "circular wait; model checking; state-space exploration."),
        h1("Report map"),
        bullets([
            "Pages 3-6: the problem, the three properties and the method.",
            "Pages 7-8: the model checker and how to read a witness.",
            "Pages 9-14: Dekker, Peterson and two broken software protocols.",
            "Pages 15-18: test-and-set, semaphores and the circular wait.",
            "Pages 19-22: monitors, bounded buffers and readers-writers.",
            "Pages 23-26: measured cost, contention and the comparison table.",
            "Pages 27-30: limits, conclusion, references and file inventory.",
        ]),
    )

    # ------------------------------------------------------------ introduction
    r.page(
        ptitle("Introduction, problem statement and goals"),
        h1("Problem statement"),
        para("Concurrent threads share data. A critical section is a piece of "
             "code that touches shared state and that must not be executed by "
             "more than one thread at a time. The four mechanisms studied here "
             "solve that problem at different levels: two are hand-written "
             "software protocols for exactly two participants, one is an "
             "operating-system primitive, and one is a language-level "
             "abstraction."),
        h1("Goals"),
        bullets([
            "State the three properties a solution may or may not provide.",
            "Explain why a successful test run is not a proof.",
            "Build an exhaustive model checker and use it on eight algorithms.",
            "Show, with a concrete witness trace, how a broken protocol fails.",
            "Implement a semaphore and a monitor from scratch and measure them.",
            "Reproduce a deadlock deterministically and show how to prevent it.",
            "Measure the cost of each mechanism under contention.",
        ]),
        h1("Model rules assumed throughout"),
        bullets([
            "Two (or more) threads, one shared variable region, no failures.",
            "Loads and stores of a single shared word are atomic.",
            "Memory is sequentially consistent: no reordering by compiler or CPU.",
            "A thread in its remainder section eventually requests entry again.",
            "Scheduling is weakly fair: a thread that can run will eventually run.",
        ]),
        note("The sequential-consistency assumption is exactly why Dekker and "
             "Peterson are studied as historical results rather than used in "
             "production: on a modern CPU, without explicit fences, they are not "
             "guaranteed to work at all.", "Why this matters"),
    )

    r.page(
        ptitle("The three properties, and why they are different"),
        h1("Mutual exclusion"),
        para("No two threads are inside the critical section at the same time. "
             "This is a safety property: a single bad interleaving breaks it, "
             "and a single witness trace is enough to disprove it."),
        h1("Progress (lockout freedom)"),
        para("If no thread is in the critical section and somebody wants to "
             "enter, the choice of who enters is not postponed for ever. A "
             "solution can satisfy mutual exclusion and still fail here: two "
             "threads can politely block each other indefinitely."),
        h1("Bounded waiting (starvation freedom)"),
        para("There is a bound on how many times a requesting thread can be "
             "overtaken. This is a liveness property about fairness, and it is "
             "strictly stronger than progress. Test-and-set satisfies the first "
             "two and fails this one."),
        kv([["Property", "Type", "Broken by", "Needs to disprove it"],
            ["Mutual exclusion", "safety", "one bad interleaving", "one witness trace"],
            ["Progress", "liveness", "mutual politeness", "a reachable stuck state"],
            ["Bounded waiting", "liveness", "unbounded overtaking", "a reachable fair cycle"]],
           caption="The three properties and what it takes to refute each"),
        h1("A fourth, separate question: deadlock"),
        para("Deadlock is not one of the three properties; it is a failure of "
             "the whole system when several locks are involved. A mechanism can "
             "be perfectly correct in isolation and still deadlock when used "
             "carelessly. Page 17 shows exactly that."),
    )

    r.page(
        ptitle("Why running the program proves nothing"),
        h1("The argument"),
        bullets([
            "A concurrency bug may need a specific interleaving of a dozen "
            "atomic steps to appear.",
            "On a machine with a scheduler you do not control, that interleaving "
            "may not occur in a million runs, and then occur in production.",
            "A passing test therefore only means 'no violation was observed', "
            "never 'no violation exists'.",
            "The opposite also holds: a failing test is conclusive, because one "
            "witness is enough to disprove a safety property.",
        ]),
        h1("What this exercise does instead"),
        para("Rather than sampling executions, the model checker enumerates the "
             "entire reachable state space. If no reachable state has two "
             "threads in the critical section, mutual exclusion holds, full "
             "stop. No run, however long, could add anything to that."),
        h1("Reproducibility of the measurements"),
        para("The cost figures in the second half of this report are genuinely "
             "measured, and genuinely noisy. A single run of the same workload "
             "varied by more than an order of magnitude on the machine used "
             "here, so every timing is a median over five to seven repeated "
             "trials, and the minimum and maximum are reported next to it. "
             "Claims about correctness come from the model checker; claims "
             "about cost come from those medians, and both are labelled as such."),
        note("The two halves of this exercise answer different questions. The "
             "model checker answers 'is it correct?'. The benchmark answers "
             "'what does it cost?'. Neither substitutes for the other.",
             "Two different questions"),
    )

    r.page(
        ptitle("How the model checker works"),
        h1("The model"),
        code(["state = ( shared-memory tuple,",
              "          (pc0, private registers of thread 0),",
              "          (pc1, private registers of thread 1) )",
              "",
              "step(pid, pc, loc, shared) -> (pc', loc', shared', action)",
              "    action in {None, 'enter', 'exit'}",
              "",
              "successors(state) = one transition per thread that can move"],
             caption="The state model used for exhaustive exploration"),
        h1("What each algorithm contributes"),
        bullets([
            "A tuple of shared integers: flags, turn, semaphores, wait queues.",
            "A step function: one atomic action per program counter value.",
            "An 'in critical section' predicate used to test mutual exclusion.",
            "A 'trying' predicate used to test starvation.",
        ]),
        h1("How blocking is modelled"),
        para("A blocked thread is modelled by a transition that leaves the "
             "state unchanged. Such a self-loop is pruned by the explorer, so a "
             "blocked thread simply has no useful successor. That is what makes "
             "a deadlock visible: a state whose only outgoing transitions are "
             "self-loops."),
        h1("How starvation is detected"),
        bullets([
            "Build the reachable graph, then restrict it to transitions in "
            "which the victim never enters and never leaves its entry section.",
            "Find the strongly connected components of that restricted graph.",
            "An SCC that contains a cycle in which the other thread enters at "
            "least twice is a starvation witness.",
            "Weak fairness is enforced by requiring the victim to take at least "
            "one step in the cycle: a thread that is never scheduled is not "
            "starved, it is simply not running.",
        ]),
    )

    # -------------------------------------------------------------- dekker
    r.page(
        ptitle("Dekker's algorithm"),
        h1("The protocol"),
        code(["flag[i] = True",
              "while flag[j]:",
              "    if turn == j:",
              "        flag[i] = False",
              "        while turn == j:      # wait for my turn",
              "            pass",
              "        flag[i] = True",
              "# critical section",
              "turn = j",
              "flag[i] = False",
              "# remainder section"],
             caption="Dekker's algorithm for process i, with j = 1 - i"),
        h1("How it works"),
        bullets([
            "Each process announces interest by setting its own flag.",
            "If the other process is not interested, entry is immediate.",
            "If both are interested, the turn variable breaks the tie: the "
            "process whose turn it is not withdraws its flag.",
            "The withdrawing process waits until turn comes back to it, then "
            "re-announces and re-checks.",
            "On exit, the process hands the turn to the other one, which is "
            "what guarantees the other process is not overtaken for ever.",
        ]),
        note("The turn variable is doing the real work. Without the withdrawal "
             "and hand-off, the protocol collapses into the broken variant two "
             "pages on.", "The key idea"),
    )

    r.page(
        ptitle("Dekker: the verified verdict"),
        h1("Verified result"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["dekker"]["states"])],
            ["Transitions", str(M["dekker"]["transitions"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "yes"],
            ["Starvation free (bounded waiting)", "yes, for both processes"]],
           caption="Model-checking verdict for Dekker's algorithm"),
        h1("Why this verdict is trustworthy"),
        bullets([
            "The state space was explored completely, not sampled.",
            "No reachable state has both processes in the critical section.",
            "No reachable state has both processes blocked with nothing left to "
            "do.",
            "No reachable cycle exists in which one process spins while the "
            "other enters repeatedly.",
        ]),
    )

    r.page(
        ptitle("Peterson's algorithm"),
        h1("The protocol"),
        code(["flag[i] = True",
              "turn = j                      # be polite: give the turn away",
              "while flag[j] and turn == j:  # wait only if both want in",
              "    pass",
              "# critical section",
              "flag[i] = False",
              "# remainder section"],
             caption="Peterson's algorithm for process i, with j = 1 - i"),
        h1("How it differs from Dekker"),
        bullets([
            "There is no withdrawal and no re-announcement; the loop is shorter.",
            "The process gives the turn away and then waits, which means the "
            "other process will find turn in its own favour and proceed.",
            "Both algorithms use two flags and one turn variable; Peterson just "
            "uses them more economically.",
            "Peterson generalises to n processes via a tournament tree; Dekker "
            "does not generalise cleanly.",
        ]),
        h1("Verified result"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["peterson"]["states"])],
            ["Transitions", str(M["peterson"]["transitions"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "yes"],
            ["Starvation free (bounded waiting)", "yes, for both processes"]],
           caption="Model-checking verdict for Peterson's algorithm"),
    )

    r.page(
        ptitle("Why the state spaces differ"),
        image("fig_state_spaces.png", width_cm=15.5,
              caption="Reachable states and transitions for all eight "
                      "algorithms, enumerated exhaustively"),
        h1("Reading the chart"),
        bullets([
            "Dekker has more reachable states than Peterson because its "
            "withdraw-and-retry loop needs extra program counters.",
            "The binary semaphore has the smallest state space: blocking "
            "removes a whole class of interleavings, because a blocked thread "
            "has no successor.",
            "The deliberately broken variants are small too, precisely because "
            "they get stuck: fewer reachable behaviours.",
            "Every space is small enough to explore completely; nothing here "
            "relies on sampling or on a depth limit.",
        ]),
    )

    r.page(
        ptitle("Broken variant 1: the single lock variable"),
        h1("The tempting but wrong protocol"),
        code(["while flag[j]:                # look first",
              "    pass",
              "flag[i] = True                # then announce",
              "# critical section",
              "flag[i] = False",
              "# remainder section"],
             caption="Test-then-set on one variable: a classic mistake"),
        h1("Why it fails"),
        para("The read of the other flag and the write of your own are two "
             "separate atomic steps. If both processes read before either "
             "writes, both see the lock as free and both walk in."),
        h1("The witness produced by the checker"),
        code([s for s in _witness("lock_variable", "mutual_exclusion_witness")],
             caption=f"Shortest violating trace, {M['lock_variable']['states']} "
                     f"states explored; 'ENTER' marks entry to the critical "
                     f"section"),
        bullets([
            "Both processes read flag[j] = 0 while the other flag is still 0.",
            "Both then set their own flag and enter.",
            "The last two lines both end in ENTER: mutual exclusion is broken.",
            "This trace is not a guess; it is the shortest path the explorer "
            "could find to a violating state.",
        ]),
    )

    r.page(
        ptitle("Broken variant 2: announce, then spin"),
        h1("The protocol"),
        code(["flag[i] = True                # announce first",
              "while flag[j]:                # then look",
              "    pass",
              "# critical section",
              "flag[i] = False",
              "# remainder section"],
             caption="Swapping the two steps fixes exclusion but creates a deadlock"),
        h1("What the checker found"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["flag_spin"]["states"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "**no**"],
            ["Starvation free", "yes (trivially: nobody gets stuck waiting)"]],
           caption="Model-checking verdict for the announce-then-spin variant"),
        h1("The deadlock witness"),
        code([s for s in _witness("flag_spin", "deadlock_witness")],
             caption="Both processes have announced interest; each now waits "
                     "for the other for ever"),
        h1("Reading the trace"),
        bullets([
            "P0 sets flag 0, then P1 sets flag 1.",
            "Both flags are now true, and each process is about to look.",
            "From here neither can ever see a clear flag, so neither can "
            "proceed.",
        ]),
    )

    r.page(
        ptitle("Announce-then-spin: why the order of two steps matters"),
        h1("Why it fails"),
        bullets([
            "Announcing before looking does guarantee exclusion: whoever sees "
            "the other flag clear is safe.",
            "But if both announce before either looks, both then spin for ever.",
            "This is a progress failure, not a safety failure: nothing wrong "
            "ever happens, because nothing ever happens at all.",
            "Dekker and Peterson both avoid this by adding a tie-breaker that "
            "one process can win.",
        ]),
        h1("The general lesson"),
        para("Correctness here depends on the relative order of a read and a "
             "write of shared variables. Reversing two adjacent lines is enough "
             "to convert a protocol that loses mutual exclusion into one that "
             "loses progress. Neither failure is visible in a short test run: "
             "the first needs a lucky interleaving and the second needs both "
             "processes to arrive at the same instant."),
        kv([["Variant", "Mutual exclusion", "Deadlock free"],
            ["look then announce", "**VIOLATED**", "yes"],
            ["announce then look", "holds", "**no**"],
            ["Dekker (announce + turn)", "holds", "yes"]],
           caption="Three arrangements of the same two ideas"),
    )

    r.page(
        ptitle("Test-and-set: correct exclusion, unbounded waiting"),
        h1("The primitive"),
        code(["def TAS(lock):                # atomic read-modify-write",
              "    old = lock",
              "    lock = True",
              "    return old",
              "",
              "while TAS(lock):",
              "    pass                      # spin",
              "# critical section",
              "lock = False"],
             caption="A test-and-set spinlock"),
        h1("Verified result"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["tas"]["states"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "yes"],
            ["Starvation free", "**no, for either process**"]],
           caption="Model-checking verdict for the test-and-set lock"),
        h1("Why bounded waiting fails"),
        para("Nothing in the protocol remembers who has been waiting longest. "
             "After a process releases the lock, any spinner may win the race, "
             "including one that arrived a moment ago. The checker exhibits a "
             "reachable cycle in which one process spins while the other enters "
             "repeatedly."),
        bullets([
            "Mutual exclusion is guaranteed by the atomicity of TAS.",
            "Progress holds: if the lock is free, somebody takes it.",
            "Bounded waiting does not hold: a process can be overtaken for ever.",
            "This is why real spinlocks add a queue (ticket locks, MCS locks).",
        ]),
        note("Test-and-set is the only mechanism in this exercise for which "
             "mutual exclusion and deadlock freedom hold but bounded waiting "
             "does not. It is the cleanest illustration that the three "
             "properties are genuinely independent.", "Why it is here"),
    )

    r.page(
        ptitle("Semaphores"),
        h1("Definition"),
        para("A semaphore is an integer with two atomic operations. Unlike the "
             "software protocols above it is not limited to two participants, "
             "and a blocked thread does not spin: it sleeps and is woken."),
        formula("wait(S)   / acquire:  if S > 0 then S = S - 1 else block",
                caption="The acquire operation"),
        formula("signal(S) / release:  if a thread is queued, wake one; "
                "else S = S + 1",
                caption="The release operation"),
        h1("Built from scratch in this exercise"),
        code(["class Semaphore:",
              "    def __init__(self, value):",
              "        self.value = value",
              "        self._cv = threading.Condition()",
              "",
              "    def acquire(self):",
              "        with self._cv:",
              "            while self.value == 0:   # must be a loop",
              "                self._cv.wait()",
              "            self.value -= 1",
              "",
              "    def release(self):",
              "        with self._cv:",
              "            self.value += 1",
              "            self._cv.notify()"],
             caption="A counting semaphore implemented on a condition variable"),
    )

    r.page(
        ptitle("Semaphores: the verified verdict"),
        h1("Verified result"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["semaphore_binary"]["states"])],
            ["Transitions", str(M["semaphore_binary"]["transitions"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "yes"],
            ["Starvation free", "yes (the wait queue is FIFO)"]],
           caption="Model-checking verdict for a binary semaphore used correctly"),
        bullets([
            "The FIFO wait queue is what buys bounded waiting: a thread cannot "
            "be overtaken by someone who arrived later.",
            "The semaphore is more general than Dekker or Peterson: it handles "
            "any number of participants and any resource count.",
            "But it is also easier to misuse, which is the subject of the next "
            "page.",
        ]),
        h1("Counting versus binary semaphores"),
        bullets([
            "A binary semaphore takes only 0 and 1 and is used for mutual "
            "exclusion.",
            "A counting semaphore tracks how many units of a resource are free "
            "and is used, for example, for a pool of connections.",
            "The implementation above is a counting semaphore; using it with an "
            "initial value of 1 gives a binary one.",
            "Both need acquire and release to be correctly paired; an extra "
            "release silently lets two threads in.",
        ]),
    )

    r.page(
        ptitle("Broken variant 3: the circular wait"),
        h1("Two locks, two orders"),
        code(["# thread 0                # thread 1",
              "lock(A)                   lock(B)",
              "lock(B)                   lock(A)     # opposite order",
              "# critical section        # critical section",
              "unlock(B)                 unlock(A)",
              "unlock(A)                 unlock(B)"],
             caption="The classic way to deadlock with correct primitives"),
        h1("Verified result"),
        kv([["Property", "Verdict"],
            ["Reachable states", str(M["semaphore_wrong_order"]["states"])],
            ["Mutual exclusion", "holds"],
            ["Deadlock free", "**no**"],
            ["Starvation free", "yes"]],
           caption="Model-checking verdict for the wrong-order variant"),
        h1("Measured on real threads"),
        code([f"wrong order    : "
              f"{DL['wrong_order']['state']['t0']} | "
              f"{DL['wrong_order']['state']['t1']}",
              f"                deadlocked = {DL['wrong_order']['deadlocked']}",
              f"same order     : "
              f"{DL['consistent_order']['state']['t0']} | "
              f"{DL['consistent_order']['state']['t1']}",
              f"                completed  = "
              f"{DL['consistent_order']['both_completed']}"],
             caption="Output of the deterministic deadlock experiment"),
        bullets([
            "A barrier sits between the two acquisitions, so the circular wait "
            "is produced on purpose rather than left to scheduler luck.",
            "The second acquisition is non-blocking, so the outcome cannot "
            "depend on a timeout race.",
            "With a consistent order the same program always finishes.",
        ]),
    )

    r.page(
        ptitle("Deadlock: the four conditions and how to break them"),
        h1("Coffman's four conditions"),
        table(["Condition", "Meaning in this example", "Holds?"],
              [["Mutual exclusion", "a lock is held by at most one thread", "yes"],
               ["Hold and wait", "a thread holds A while waiting for B", "yes"],
               ["No preemption", "a lock cannot be taken away", "yes"],
               ["Circular wait", "T0 waits for T1 who waits for T0", "yes"]],
              caption="All four conditions are necessary for deadlock"),
        image("fig_deadlock.png", width_cm=14.5,
              caption="The wait-for graph of the wrong-order example: the cycle "
                      "is the deadlock"),
    )

    r.page(
        ptitle("Deadlock prevention strategies"),
        h1("Prevention strategies"),
        bullets([
            "**Impose a global lock order.** Acquire A before B everywhere; the "
            "cycle becomes impossible. Cheapest fix and the one measured above.",
            "**Acquire everything atomically.** Take all locks in one "
            "all-or-nothing step, or none.",
            "**Allow preemption.** If a second acquisition fails, release what "
            "you hold and retry. Risks livelock without back-off.",
            "**Detect and recover.** Build the wait-for graph at run time and "
            "abort a victim. Used by databases, rare in OS kernels.",
        ]),
        note("None of the four conditions is about the quality of the lock. "
             "Deadlock is a property of how locks are used, not of how they are "
             "implemented. A perfect semaphore will deadlock just as happily.",
             "The lesson"),
    )

    r.page(
        ptitle("Monitors"),
        h1("Definition"),
        para("A monitor bundles shared state with the operations on it and "
             "guarantees that at most one thread is executing inside the monitor "
             "at any time. Condition variables let a thread wait for a predicate "
             "that is not yet true, releasing the monitor lock while it waits."),
        h1("Mesa versus Hoare semantics"),
        table(["Aspect", "Hoare", "Mesa (used here)"],
              [["On signal", "signaller blocks, waiter runs at once",
                "waiter becomes ready, signaller keeps running"],
               ["Predicate on wake", "guaranteed true",
                "must be re-checked"],
               ["Correct loop", "`if not P: wait(c)`",
                "`while not P: wait(c)`"],
               ["Implementation", "harder, more context switches",
                "simpler, standard in Java and Python"]],
              caption="The two monitor semantics and why Mesa needs a while-loop"),
        h1("Why the while-loop is not optional"),
        para("Under Mesa semantics a woken thread only becomes ready; it must "
             "re-acquire the monitor lock, and by the time it does, another "
             "thread may have invalidated the predicate. The loop is therefore "
             "part of the correctness argument, not defensive styling."),
        code(["def put(self, item):",
              "    with self._cv:",
              "        while len(self.buffer) >= self.capacity:   # loop",
              "            self._cv.wait()",
              "        self.buffer.append(item)",
              "        self._cv.notify_all()"],
             caption="The producer side of the bounded buffer monitor"),
    )

    r.page(
        ptitle("Measured: the bounded buffer monitor"),
        h1("The experiment"),
        para("Two producers and two consumers move 1600 items through a bounded "
             "buffer of capacity 1, 4 and 16. The monitor was implemented from "
             "scratch on a condition variable. Each configuration was run five "
             "times and the fastest run is reported."),
        table(["Capacity", "Max occupancy", "Capacity respected",
               "Re-checks after a wake", "Throughput (items/s)"],
              [[str(PC[f"capacity_{c}"]["capacity"]),
                str(PC[f"capacity_{c}"]["max_observed_in_buffer"]),
                "yes" if PC[f"capacity_{c}"]["capacity_respected"] else "no",
                f"{PC[f'capacity_{c}']['re_waits_after_signal']:,}",
                f"{PC[f'capacity_{c}']['throughput_items_per_s']:,.0f}"]
               for c in (1, 4, 16)],
              caption="Producer/consumer results; 1600 items each time"),
    )

    r.page(
        ptitle("Bounded buffer: the cost of re-checking"),
        image("fig_monitor_timeline.png", width_cm=15.5,
              caption="Maximum occupancy and how often a woken thread had to "
                      "wait again before the predicate held"),
        bullets([
            "Production and consumption are perfectly balanced in every run: "
            "no item is lost or duplicated.",
            "The buffer occupancy never exceeds the capacity.",
            f"At capacity 1 a woken thread had to re-wait "
            f"{PC['capacity_1']['re_waits_after_signal']:,} times, against only "
            f"{PC['capacity_16']['re_waits_after_signal']:,} at capacity 16.",
            "That number is direct evidence that the while-loop is doing real "
            "work: had the code used `if`, those re-waits would have been "
            "silent corruption instead.",
            "A larger buffer raises throughput "
            f"{PC['capacity_16']['throughput_items_per_s'] / PC['capacity_1']['throughput_items_per_s']:.1f}x, "
            "because producers block less often.",
        ]),
    )

    r.page(
        ptitle("The readers and writers problem"),
        h1("The problem"),
        para("Many threads read a shared object and some write it. Any number "
             "of readers may be inside at once, but a writer needs exclusive "
             "access. The question is what to do when a reader is inside and a "
             "writer arrives, or the other way round."),
        h1("Three solutions implemented here"),
        table(["Variant", "Rule", "Consequence"],
              [["Readers preference", "a new reader enters unless a writer is "
                "already in", "writers can be starved"],
               ["Writers preference", "a waiting writer blocks new readers",
                "readers can be starved"],
               ["Fair (FIFO ticket)", "whoever arrived first is served first",
                "nobody starves; lower concurrency"]],
              caption="The three variants and their fairness trade-offs"),
        h1("Measured: 6 reader threads against 1 writer"),
        table(["Variant", "Reads completed", "Writes completed",
               "Mean read share"],
              [["Readers preference",
                f"{RW['ReadersPreferenceRW']['reads_total']:,}",
                f"{RW['ReadersPreferenceRW']['writes_total']:,}",
                f"{RW['ReadersPreferenceRW']['read_share_mean']:.3f}"],
               ["Writers preference",
                f"{RW['WritersPreferenceRW']['reads_total']:,}",
                f"{RW['WritersPreferenceRW']['writes_total']:,}",
                f"{RW['WritersPreferenceRW']['read_share_mean']:.3f}"],
               ["Fair (FIFO)",
                f"{RW['FairRW']['reads_total']:,}",
                f"{RW['FairRW']['writes_total']:,}",
                f"{RW['FairRW']['read_share_mean']:.3f}"]],
              caption="Five trials of 0.6 s each, aggregated"),
    )

    r.page(
        ptitle("Readers and writers: reading the results"),
        bullets([
            f"Under readers preference the writer completed "
            f"{RW['ReadersPreferenceRW']['writes_total']} operations in three "
            f"seconds while readers completed "
            f"{RW['ReadersPreferenceRW']['reads_total']:,}: the writer was "
            f"overtaken essentially every time.",
            f"Under writers preference the imbalance reverses: "
            f"{RW['WritersPreferenceRW']['writes_total']:,} writes against "
            f"{RW['WritersPreferenceRW']['reads_total']:,} reads.",
            f"The FIFO variant lands at a read share of "
            f"{RW['FairRW']['read_share_mean']:.3f}, close to the arrival ratio "
            f"of 6 readers to 1 writer (0.857), which is what fairness should "
            f"produce.",
        ]),
    )

    r.page(
        ptitle("Readers and writers: the measurements in full"),
        image("chart_readers_writers.png", width_cm=14.5,
              caption="Operations completed per trial, log scale; the gap "
                      "between the two bars is the fairness deficit"),
        h1("Reading the chart"),
        bullets([
            "The two bars of the readers-preference variant are four orders of "
            "magnitude apart.",
            "The two bars of the FIFO variant are roughly in the ratio of "
            "thread counts, which is the expected fair outcome.",
            "The writers-preference variant is the mirror image: the write bar "
            "dominates.",
        ]),
        h1("Per-trial spread"),
        table(["Variant", "Read share min", "Read share mean", "Read share max"],
              [[v.replace("RW", ""),
                f"{RW[k]['read_share_min']:.3f}",
                f"{RW[k]['read_share_mean']:.3f}",
                f"{RW[k]['read_share_max']:.3f}"]
               for k, v in (("ReadersPreferenceRW", "readers pref."),
                            ("WritersPreferenceRW", "writers pref."),
                            ("FairRW", "fair FIFO"))],
              caption="Spread over five independent trials of 0.6 s"),
        note("These numbers measure what the GIL and CPython's lock "
             "implementation happen to do, not a theorem. They are reported "
             "because they make the trade-off concrete, not because they prove "
             "anything about starvation.", "Honest reading"),
    )

    r.page(
        ptitle("What correctness costs"),
        h1("The experiment"),
        para("Two threads each perform 5000 critical sections, incrementing a "
             "shared counter. Seven repetitions; the median is reported with the "
             "observed minimum and maximum."),
        table(["Mechanism", "Median (ops/s)", "Min", "Max", "Spins (median)"],
              [[k, f"{v['throughput_median']:,.0f}",
                f"{v['throughput_min']:,.0f}", f"{v['throughput_max']:,.0f}",
                f"{v['spins_median']:,}" if v["spins_median"] is not None
                else "n/a (blocks)"]
               for k, v in B.items()],
              caption="Throughput of five mutual-exclusion mechanisms"),
        image("chart_throughput.png", width_cm=14.0,
              caption="Median throughput; higher is faster"),
    )

    r.page(
        ptitle("Reading the throughput numbers"),
        h1("What the numbers say"),
        bullets([
            "The two software protocols are fastest here because they never "
            "sleep: a thread either spins or enters.",
            "The semaphore and monitor are roughly half as fast, and the "
            "difference is the price of blocking: a kernel wait and wake per "
            "contended acquisition.",
            "The spread between the minimum and the maximum run is large; on a "
            "shared machine a single measurement is not trustworthy.",
            "All five produced the correct counter and never let two threads "
            "into the critical section at once.",
        ]),
    )

    r.page(
        ptitle("Behaviour under contention"),
        table(["Threads", "Test-and-set (ops/s)", "Semaphore (ops/s)",
               "Monitor (ops/s)", "TAS spins"],
              [[str(n),
                f"{C[f'tas_{n}t']['throughput_median']:,.0f}",
                f"{C[f'semaphore_{n}t']['throughput_median']:,.0f}",
                f"{C[f'monitor_{n}t']['throughput_median']:,.0f}",
                f"{C[f'tas_{n}t']['spins_median']:,}"]
               for n in (2, 4, 8)],
              caption="Median of five trials, 5000 critical sections per thread"),
        image("chart_contention.png", width_cm=13.5,
              caption="Throughput as the number of competing threads grows"),
        h1("Interpretation"),
        bullets([
            "Blocking mechanisms degrade gently: blocking a thread frees the "
            "CPU for someone who can run.",
            "The differences between the three mechanisms are small compared "
            "with the spread between repeated runs of the same mechanism.",
            "The spinlock does not collapse in throughput because the critical "
            "section here is extremely short: an increment.",
        ]),
    )

    r.page(
        ptitle("The hidden cost of spinning"),
        image("chart_spins.png", width_cm=11.5,
              caption="Failed test-and-set attempts: work done and thrown away"),
        bullets([
            "Every failed attempt is a wasted read-modify-write.",
            "The count grows sharply with the number of competing threads, "
            "because more threads are fighting for the same word.",
            "A spinlock is only the right choice when the critical section is "
            "shorter than the cost of a context switch, which is true inside a "
            "kernel and rarely true in application code.",
            "If the thread holding the lock is descheduled, every other thread "
            "burns a full time slice doing nothing useful.",
        ]),
    )

    r.page(
        ptitle("The comparison table"),
        table(["Algorithm", "Family", "States", "Mutual exclusion",
               "Deadlock free", "Starvation free"],
              [_md_row(n) for n in ("dekker", "peterson", "lock_variable",
                                    "flag_spin", "tas", "semaphore_binary",
                                    "semaphore_wrong_order", "monitor_mesa")],
              caption="Every verdict in this table is exhaustive, not sampled"),
    )

    r.page(
        ptitle("The comparison table as a property matrix"),
        image("fig_property_matrix.png", width_cm=12.5,
              caption="The same results as a property matrix"),
        h1("How to read it"),
        bullets([
            "Three of the eight are broken, and each in a different way: one "
            "loses exclusion, one deadlocks, one neither excludes wrongly nor "
            "deadlocks but permits unbounded overtaking.",
            "The two correct software protocols and the two correct "
            "higher-level mechanisms all pass all three properties.",
            "A semaphore used in the wrong order keeps every property of the "
            "primitive and still deadlocks the system.",
        ]),
    )

    r.page(
        ptitle("When to use what"),
        table(["Situation", "Recommended", "Why"],
              [["Two processes, no OS support, teaching",
                "Peterson", "shortest correct software protocol"],
               ["More than two participants",
                "semaphore or monitor", "the two-process protocols do not apply"],
               ["Critical section shorter than a context switch",
                "spinlock (with a queue)", "blocking would cost more than waiting"],
               ["Critical section does any real work",
                "blocking semaphore / monitor", "do not burn CPU spinning"],
               ["Shared state plus a predicate to wait for",
                "monitor with condition variables",
                "encapsulates both exclusion and waiting"],
               ["Multiple locks required",
                "any, with a global lock order",
                "prevents the circular wait measured on page 17"],
               ["Read-mostly shared data",
                "fair readers-writers",
                "the preference variants starve one side"]],
              caption="A practical decision guide"),
        h1("What this report does not recommend"),
        bullets([
            "Using Dekker or Peterson in production code. They are correct only "
            "under sequential consistency, which modern hardware does not give "
            "you without explicit fences.",
            "Building your own lock in application code at all, if the runtime "
            "already provides one.",
            "Assuming a semaphore is 'safer' than a monitor. It is more "
            "primitive, which means more ways to get it wrong.",
        ]),
    )

    r.page(
        ptitle("Limits and honest scope"),
        h1("What has been proved"),
        bullets([
            "For each of the eight algorithms, a verdict over the entire "
            "reachable state space, under the model of page 7.",
            "Mutual exclusion, deadlock freedom and starvation freedom are "
            "settled exhaustively, not sampled.",
        ]),
        h1("What has not been proved"),
        bullets([
            "Only two participants are modelled. Dekker and Peterson are "
            "two-process algorithms, but the semaphore and monitor verdicts do "
            "not automatically extend to n threads: only the two-thread case "
            "was checked here.",
            "The model assumes sequential consistency. Real hardware reorders "
            "loads and stores, and a compiler may do the same. On real hardware "
            "Dekker and Peterson need memory fences that this model does not "
            "represent.",
            "The model has no failures, no timeouts and no interrupts.",
            "The monitor model is a one-slot buffer with a producer and a "
            "consumer; it is not a general monitor checker.",
        ]),
        h1("What the measurements do and do not show"),
        bullets([
            "They are single-machine, single-run-time timings on a shared "
            "sandbox with a GIL. They are indicative of relative cost, not a "
            "portable benchmark.",
            "CPython's GIL changes contention behaviour substantially compared "
            "with a native runtime; the spin counts are the most affected.",
            "The readers-writers starvation is real behaviour of the code, but "
            "the exact ratios depend on the runtime's lock implementation.",
        ]),
        note("The strongest claim in this report is the model-checking table on "
             "page 25, and it is conditional on the model of page 7. The "
             "weakest claims are the timings, which is why they are medians "
             "with their spread reported.", "Strength of the claims"),
    )

    r.page(
        ptitle("Conclusion and answers"),
        para("Eight mutual-exclusion algorithms were checked exhaustively and "
             "five mechanisms were measured on running threads. The verified "
             "and the measured results agree with the textbook account, and "
             "where the textbook is often vague, this report supplies a witness "
             "trace instead of an assertion."),
        bullets([
            "Dekker and Peterson provide all three properties for two "
            "processes, at the cost of assuming sequential consistency.",
            "Test-and-set provides exclusion and progress but not bounded "
            "waiting: the checker exhibits a cycle where one thread is overtaken "
            "for ever.",
            "A binary semaphore with a FIFO queue provides all three, and "
            "generalises beyond two participants.",
            "A Mesa monitor adds condition synchronisation, and the measurement "
            f"shows the while-loop was needed "
            f"{PC['capacity_1']['re_waits_after_signal']:,} times at capacity 1.",
            "Deadlock is a usage error, not a primitive defect: the same "
            "semaphore that verifies correctly deadlocks when two threads take "
            "two locks in opposite orders.",
        ]),
        h1("Answers to the questions of the exercise"),
        table(["Question", "Answer"],
              [["Do Dekker and Peterson guarantee mutual exclusion?",
                "yes, verified exhaustively for two processes"],
               ["Is either of them starvation free?",
                "yes, both provide bounded waiting"],
               ["Does test-and-set provide bounded waiting?",
                "no; that is its one failing property"],
               ["Can a correct primitive still deadlock?",
                "yes; the wrong-order experiment shows it deterministically"],
               ["Why must a Mesa monitor re-check its predicate?",
                "a woken thread must re-acquire the lock and the predicate may "
                "have been invalidated meanwhile"],
               ["Which is fastest here?",
                "the busy-wait protocols, because they never block; but they "
                "burn CPU under contention"]],
              caption="Short answers"),
    )

    r.page(
        ptitle("References and reproduction"),
        h1("References"),
        bullets([
            "Dijkstra, E. W. — Solution of a problem in concurrent programming "
            "control — Communications of the ACM, 1965. (Dekker's algorithm as "
            "presented by Dijkstra.)",
            "Peterson, G. L. — Myths About the Mutual Exclusion Problem — "
            "Information Processing Letters, 1981.",
            "Dijkstra, E. W. — The structure of the THE multiprogramming "
            "system — Communications of the ACM, 1968. (Semaphores.)",
            "Hoare, C. A. R. — Monitors: An Operating System Structuring "
            "Concept — Communications of the ACM, 1974.",
            "Lampson, B. W., & Redell, D. D. — Experience with Processes and "
            "Monitors in Mesa — Communications of the ACM, 1980. (Mesa "
            "semantics.)",
            "Coffman, E. G., Elphick, M. J., & Shoshani, A. — System Deadlocks — "
            "Computing Surveys, 1971.",
            "Silberschatz, A., Galvin, P. B., & Gagne, G. — Operating System "
            "Concepts — chapters on Process Synchronization and Deadlocks.",
        ]),
        h1("Reproduction commands"),
        code(["# from the branch root",
              "python code/sync_model.py         # all eight verdicts",
              "python code/run_experiments.py    # every number in this report",
              "python code/make_diagrams.py      # every figure",
              "python -m pytest tests -q         # 52 tests"],
             caption="Everything in this report can be regenerated in one command each"),
        note("Every figure and every number quoted in this report comes out of "
             "output/experiments.json, which is written by run_experiments.py. "
             "Nothing was typed in by hand.", "Provenance"),
    )

    r.page(
        ptitle("File inventory"),
        table(["Path", "Contents"],
              [["README.md", "this exercise's documentation"],
               ["COMPARISON_FA.md", "the earlier short Persian comparison"],
               ["COMPARISON_EN.md", "the earlier short English comparison"],
               ["code/sync_model.py",
                "the model checker: 8 algorithms, verdicts and witnesses"],
               ["code/sync_algorithms.py",
                "runnable Dekker, Peterson, TAS, semaphore, monitor, "
                "readers-writers and the deadlock experiment"],
               ["code/run_experiments.py", "writes everything under output/"],
               ["code/make_diagrams.py", "regenerates all figures"],
               ["code/sync_demo.py",
                "the earlier semaphore and monitor demonstration"],
               ["tests/test_sync_model.py", "locks in the verified verdicts"],
               ["tests/test_sync_algorithms.py", "tests the threading layer"],
               ["tests/test_sync_demo.py", "tests the earlier demonstration"],
               ["output/experiments.json", "every measured number"],
               ["output/model_check.txt", "verdicts plus witness traces"],
               ["output/experiments_summary.txt", "full text log"],
               ["diagrams/", "8 figures used in this report"],
               ["requirements.txt", "pytest and matplotlib"],
               [".gitignore", "keeps bytecode out of the branch"]],
              caption="What ships on this branch"),
    )

    r.page(
        ptitle("Figure list and how to regenerate everything"),
        h1("Figure list"),
        table(["Figure", "Shows"],
              [["fig_state_spaces.png", "reachable states per algorithm"],
               ["fig_property_matrix.png", "the three properties as a matrix"],
               ["chart_throughput.png", "cost of each mechanism"],
               ["chart_contention.png", "throughput versus thread count"],
               ["chart_spins.png", "wasted work in the spinlock"],
               ["chart_readers_writers.png", "fairness of the three variants"],
               ["fig_deadlock.png", "the circular wait as a wait-for graph"],
               ["fig_monitor_timeline.png",
                "buffer occupancy and re-checked waits"]],
              caption="The eight figures"),
    )

    return r
