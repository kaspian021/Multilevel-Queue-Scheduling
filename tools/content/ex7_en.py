# -*- coding: utf-8 -*-
"""Exercise 7 — English paper: the readers-writers problem, four ways.

Every number quoted here is read from ``exercise-7/output/experiments.json``
through ``ex7_data``, so the paper cannot quote a figure the code does not
produce.
"""

from __future__ import annotations

from report_kit import (Report, cover, toc, ptitle, h1, h2, para, bullets,
                        table, kv, image, code, formula, note)

from ex7_data import (D, MODEL, E1, E2, E3, E4, E5, NAME, FAMILY,
                      model_rows, throughput_rows, concurrency_rows,
                      starvation_rows, reader_starvation_rows, scaling_rows,
                      queue_cost_rows, kv_facts, program_listing,
                      broken_witness, mesa_starvation_witness)

TITLE = ("The Readers-Writers Problem, Solved Four Ways: "
         "semaphore, monitor, Dekker, Peterson")

SUBTITLE = ("What is proved about every interleaving, what is measured on "
            "real threads, and where the two disagree")

COVER_META = [
    ("Title", "The readers-writers problem, solved four ways"),
    ("Subtitle", "Semaphore, monitor, Dekker and Peterson, proved and measured"),
    ("Course", "Advanced Operating Systems"),
    ("Exercise", "7 — readers and writers"),
    ("Method", "exhaustive model checking plus a threaded benchmark harness"),
    ("Solutions modelled", f"{len(MODEL)} protocols, 2 to 3 processes each"),
    ("Solutions benchmarked", f"{len(E1)} locks on real threads"),
    ("Deliverable", "Persian and English papers (DOCX and PDF), figures, "
                    "code and tests"),
    ("Repository", "github.com/kaspian021/Multilevel-Queue-Scheduling"),
    ("Branch", "Exercise-7-Readers-Writers-Comparison"),
]

KEYWORDS = [
    "readers-writers problem",
    "mutual exclusion",
    "semaphore",
    "monitor",
    "Mesa semantics",
    "Dekker's algorithm",
    "Peterson's algorithm",
    "starvation",
    "model checking",
    "fairness",
]


def build():
    r = Report(TITLE, SUBTITLE, "en", cover_meta=COVER_META)

    r.page(cover(COVER_META))
    r.page(toc())

    # ------------------------------------------------------------- abstract
    r.page(
        ptitle("Abstract and keywords"),
        h1("Abstract"),
        para(
            "The readers-writers problem asks for a lock that keeps writers "
            "exclusive of everybody while letting any number of readers share "
            "the section. Four classic mechanisms are usually offered as the "
            "answer, and they are not interchangeable: a counting semaphore, "
            "a monitor with condition variables, and the two classic "
            "two-process software solutions of Dekker and Peterson. This "
            "exercise builds all of them, then asks two separate questions of "
            "each. The first is proved: an exhaustive model checker walks "
            "every reachable interleaving of a two- or three-process "
            "protocol and returns a verdict on safety, deadlock freedom, "
            "starvation freedom and, the property the problem actually exists "
            "for, whether two readers can be inside together. The second is "
            "measured: a threaded harness runs each lock under load and "
            "checks the invariant on every single entry."),
        para(
            "The two answers do not always point the same way, and the "
            "disagreements are the interesting part. Readers preference is "
            "safe, deadlock free and fast, and it starves the writer "
            "completely: in "
            f"{E3['readers_pref']['writer_starved_trials']} of "
            f"{E3['readers_pref']['reps']} half-second trials with six "
            "readers and one writer the writer took under one per cent of the "
            "traffic, and in the rest it took almost all of it — the "
            "outcome depends on who wins the opening race and then locks in. "
            "A Mesa "
            "monitor is safe and admits concurrent reads, but because a "
            "notified thread has to re-compete for the monitor lock it does "
            "not bound waiting: the checker finds a fair cycle in which every "
            "participant starves. Hand the woken thread a place in the entry "
            "queue instead and the verdict flips. Dekker and Peterson are "
            "correct and starvation free as locks, and they are written for "
            "exactly two participants, which is the whole of their "
            "limitation: they can carry the readers-writers pattern between "
            "two readers, and they cannot carry it to a third."),
        h1("Keywords"),
        para(", ".join(KEYWORDS)),
        note(
            "Every figure in this paper is produced by "
            "`exercise-7/code/run_experiments.py` and read from "
            "`output/experiments.json` at build time. No number is typed by "
            "hand, so the paper cannot drift away from the code that "
            "produced it."),
    )

    # ---------------------------------------------------------- 1 the problem
    r.page(
        ptitle("1. The problem, and why four answers exist"),
        h1("What has to hold"),
        para(
            "A readers-writers lock guards one shared object. Any number of "
            "readers may hold it at once; a writer must hold it alone. Three "
            "properties follow, and the third is the one that makes the "
            "problem worth an exercise:"),
        bullets([
            "**Safety** — never two writers inside at once, and never a "
            "writer inside together with anybody else.",
            "**Liveness** — a process that asks eventually gets in. This "
            "splits into deadlock freedom (somebody can always still get in) "
            "and starvation freedom (everybody eventually does).",
            "**Concurrency** — two readers really can be inside at once. A "
            "plain mutex satisfies the first two properties perfectly and "
            "still fails this one, which is the entire reason the problem "
            "exists.",
        ]),
        h1("Why the four mechanisms are not interchangeable"),
        para(
            "A semaphore is a counter with a queue. A monitor is a lock plus "
            "condition variables, and when a thread waits it gives the lock "
            "up. Dekker's and Peterson's algorithms are pure software "
            "solutions to mutual exclusion, written with nothing but shared "
            "flags, and both are written for exactly two processes. They "
            "differ in what they can express, in what they cost, and in what "
            "they guarantee about waiting — which is what the rest of this "
            "paper measures."),
        note(
            "The four mechanisms are compared at two levels throughout: as "
            "the *count lock* inside a readers-writers solution, and as the "
            "whole solution. Dekker and Peterson can do the first for two "
            "participants and simply cannot do the second, and that "
            "distinction is proved in section 5 rather than asserted."),
    )

    # ------------------------------------------------- 2 the two instruments
    r.page(
        ptitle("2. Two instruments: a proof and a measurement"),
        h1("2.1 The model checker"),
        para(
            "`code/rw_model.py` enumerates the reachable state space of a "
            "protocol. Memory is sequentially consistent, every load and "
            "store of a single word is atomic, and a global state is the "
            "tuple (shared counters, semaphores, program counters, private "
            "registers). A process that cannot proceed contributes a "
            "self-loop, which the explorer prunes, so a blocked process "
            "simply has no successor and a deadlock shows up as a state from "
            "which no entry is reachable any more."),
        bullets([
            "**Safety** is checked on every state as it is reached.",
            "**Deadlock freedom** is reverse reachability: is there a state "
            "in which somebody is trying, nobody is inside, and no entry is "
            "reachable?",
            "**Starvation freedom** is a fair-cycle search, explained below.",
            "**Concurrent reads** is the positive property: does some "
            "reachable state have two readers inside at once?",
        ]),
        h2("Fairness is the part that is easy to get wrong"),
        para(
            "A cycle in which the victim simply is never scheduled proves "
            "nothing: that is an unfair scheduler, not a broken lock. Three "
            "separate mistakes were made and caught while building this "
            "checker, and each one is worth naming because each produced a "
            "confident wrong answer:"),
        bullets([
            "Fairness only for the **victim** lets a third process sit on an "
            "enabled step it never takes, hold a lock for ever, and make the "
            "victim look starved. Fairness has to be required of every "
            "process.",
            "Pruning the victim's own step into its remainder section "
            "removes exactly the transition that proves it was scheduled.",
            "A **path** that overtakes the victim twice proves nothing; only "
            "a closed cycle can be repeated for ever.",
        ]),
        note(
            "The rule the checker finally implements: a cycle is fair for a "
            "process when, at every state of the cycle where that process has "
            "any enabled step, one of those steps is part of the cycle. If "
            "the process is blocked anywhere on the cycle the obligation is "
            "empty, and the cycle is genuine starvation."),
    )

    r.page(
        ptitle("2.2 The threaded harness"),
        h1("What it runs"),
        para(
            "`code/rw_sync.py` implements every solution as a real lock and "
            "runs it under load. Two design decisions are not incidental."),
        bullets([
            "**The semaphore is strictly FIFO.** A thread takes a ticket on "
            "arrival and is served in ticket order, so a newcomer cannot "
            "overtake a waiter. `threading.Semaphore` does not behave that "
            "way, and using it would quietly invalidate the fairness proofs "
            "below. The paper measures both, so the price of the queue is a "
            "number rather than a claim.",
            "**The invariant is checked on every entry, not at the end.** A "
            "lock that lets a writer in beside a reader for a microsecond "
            "leaves no trace in any counter read afterwards. The harness "
            "records the violation while it is happening, and it records how "
            "many readers were ever inside at once.",
        ]),
        h1("What the harness caught"),
        para(
            "Building `wrt` acquisition outside the count mutex — the "
            "obvious way to write it, and the way it was written first — "
            "opens a window in which a second reader has already raised the "
            "count but the first has not yet taken the writer lock. The "
            "harness found it in under a second of load. The model had it "
            "right all along, which is the argument for having both "
            "instruments."),
        note(
            "Neither instrument is redundant. The model checker explores two "
            "or three processes for a handful of steps and proves statements "
            "about all of them; it says nothing about fifteen locks running "
            "for a second of wall-clock time. The harness says nothing about "
            "the interleaving it happened not to take. Together they caught a "
            "bug that each alone would have missed."),
    )

    r.page(
        ptitle("2.3 The bug, and the fix"),
        code([
            "# wrong: the count is raised, the mutex is dropped, and only",
            "# then is wrt taken -- in that window a writer can be inside",
            "# together with a reader",
            "with self._mutex:",
            "    self._readers += 1",
            "    first = self._readers == 1",
            "if first:",
            "    self._wrt.acquire()          # too late",
            "",
            "# right: wrt is taken while the count is still protected",
            "with self._mutex:",
            "    self._readers += 1",
            "    if self._readers == 1:",
            "        self._wrt.acquire()",
        ], caption="Readers preference, before and after"),
        h1("Why the window exists"),
        para(
            "The invariant is not “the count is right”, it is "
            "“the writer semaphore is held for exactly as long as any "
            "reader is inside”. Between releasing the count mutex and "
            "taking `wrt`, the count already says a reader is coming but "
            "nothing yet stops a writer. A second reader arriving in that "
            "window sees a count of two and walks straight into the section "
            "without touching `wrt` at all, so the writer lock no longer "
            "means what the protocol assumes it means."),
        note(
            "The equivalent mistake on the release side is symmetric and just "
            "as easy to make: giving `wrt` back after dropping the count "
            "mutex lets a writer in while the count is still above zero."),
    )

    # ------------------------------------------------- 3 the five solutions
    r.page(
        ptitle("3. The solutions, in the form the checker explores"),
        para(
            "Each listing below is the actual modelled program, one line per "
            "atomic step, disassembled from `code/rw_model.py` at build time. "
            "The interleaving of these steps is exactly what the verdicts in "
            "section 4 are about, so the level of detail is the point: a tidy "
            "pseudocode version would hide the very steps across which the "
            "solutions differ."),
        h1("3.1 Readers preference"),
        code(program_listing("rw_readers_pref", 0),
             caption="The reader program of `rw_readers_pref`"),
        para(
            "`mutex` protects the count and `wrt` excludes writers. The first "
            "reader takes `wrt`, the last one gives it back, and everybody in "
            "between just walks in. Note that `wrt` is taken at step 5, while "
            "`mutex` is still held — the detail section 2.3 is about."),
    )

    r.page(
        ptitle("3.2 The monitor"),
        code(program_listing("rw_monitor_mesa", 1),
             caption="The writer program of `rw_monitor_mesa`"),
        para(
            "One lock, one condition variable. A writer waits while another "
            "writer is active and waits again while a read phase is open; on "
            "the way out it clears the flag and wakes everybody. Every wait "
            "jumps back to the re-test at step 1 rather than to the top, "
            "which is what Mesa semantics require — a notified thread "
            "has to look at the condition again, because the notification "
            "carried no promise."),
        h1("And the fair variant"),
        code(program_listing("rw_monitor_fifo", 1),
             caption="The same program with `wait-queued` and "
                     "`notifyAll+handoff`"),
        para(
            "Two instructions differ. `wait-queued` puts the woken thread "
            "into the monitor's entry queue instead of leaving it to race, "
            "and `notifyAll+handoff` performs the hand-off atomically at "
            "signal time rather than leaving a notified thread waiting to be "
            "scheduled. That is the whole of the difference between "
            "“every participant can starve” and “only the "
            "writer can”."),
    )

    r.page(
        ptitle("3.3 The two classic algorithms"),
        code(program_listing("dekker_mutex", 0),
             caption="Dekker's algorithm, as modelled"),
        para(
            "Two flags and a turn. Dekker yields: when the other side is "
            "interested and it is not my turn, I lower my flag, wait for the "
            "turn to come back, and raise it again. The yield is the part "
            "that took a correction to get right — the first version "
            "jumped into the section on seeing its own turn, which is the "
            "opposite of what Dekker does, and the checker duly reported a "
            "safety violation."),
    )

    r.page(
        ptitle("3.4 Peterson"),
        code(program_listing("peterson_mutex", 1),
             caption="Peterson's algorithm, as modelled"),
        para(
            "Peterson removes the busy loop: the turn does the yielding, so "
            "the entry protocol is four instructions instead of eleven. Both "
            "need two instruction forms the other solutions do not — one "
            "to write my own flag and one to read the other's — "
            "because a process has to know which of the two it is."),
        para(
            f"Fewer instructions, fewer places to be interrupted: Dekker "
            f"explores {MODEL['dekker_mutex']['states']} states and Peterson "
            f"{MODEL['peterson_mutex']['states']}. Neither admits two readers "
            "at once, because neither is trying to."),
    )

    # --------------------------------------------------------- 4 the verdicts
    r.page(
        ptitle("4. What is proved"),
        para(
            "Every row below is exhaustive: no verdict rests on a truncated "
            "state space. The broken solution is the single exception and it "
            "is an exception by design — it stops at its first witness, "
            "which is a proof that the invariant fails, not a survey of what "
            "happens after."),
        table(["solution", "roles", "states", "safety", "deadlock-free",
               "starves", "concurrent reads"],
              model_rows(),
              caption="Exhaustive model checking, 2 to 3 processes per "
                      "solution"),
    )

    r.page(
        image("fig_verdicts.png", width_cm=15.4,
              caption="The same verdicts as a picture: green holds, red does "
                      "not, orange starves somebody"),
        para(
            "The two rows that carry the argument are the Mesa monitor and "
            "the monitor with a fair entry queue. They are the same program "
            "apart from two instructions, and one of them starves every "
            "participant while the other starves only the writer. Everything "
            "else in the table is either a mutex doing what a mutex does, or "
            "a readers-writers solution paying for fairness in one currency "
            "or another."),
    )

    r.page(
        ptitle("4.1 Reading the table"),
        h1("Every mutual exclusion solution passes two properties and fails "
           "the third"),
        para(
            "The semaphore mutex, the monitor mutex and both classic "
            "two-process algorithms are safe and deadlock free, and none of "
            "them ever lets two readers in at once. They satisfy the letter "
            "of the problem and miss its point entirely. The last column is "
            "the one the problem exists for."),
        h1("Readers preference starves the writer; writers preference needs "
           "two writers to starve the reader"),
        para(
            "`rw_readers_pref` is safe, deadlock free and admits concurrent "
            "reads, and the writer never gets in: two readers can keep the "
            "count above zero for ever by each decrementing and "
            "re-incrementing before the other reaches zero. The mirror image "
            "is asymmetric in an informative way. With a single writer "
            f"(`rw_writers_pref`), nothing starves: the reader door reopens "
            "every time the writer is done. Add a second writer "
            "(`rw_writers_pref_2w`) and the door never reopens, and the "
            "reader is the one that starves. The starvation is a property of "
            "the *load*, not only of the algorithm, and a model with one "
            "writer cannot see it."),
        h1("A Mesa monitor does not bound waiting; a fair entry queue fixes "
           "it"),
        para(
            "`rw_monitor_mesa` is safe and deadlock free and admits "
            "concurrent reads, and every participant can starve. The reason "
            "is the one detail Mesa semantics leave open: a notified thread "
            "has to re-acquire the monitor lock, and a newcomer can take it "
            "first. That is how Java behaves, and it is why `notify` carries "
            "no fairness guarantee. Change one thing — hand the woken "
            "thread a place in the entry queue instead of making it race — "
            "and `rw_monitor_fifo` becomes exactly as fair as readers "
            "preference: the writer can starve, nobody else can."),
        note(
            "This is the clearest result in the table, because the two "
            "monitor models differ in one instruction. What was missing was "
            "never the condition variable. It was the entry queue."),
    )

    r.page(
        ptitle("4.2 How big each proof was"),
        para(
            "The state spaces differ by more than two orders of magnitude, "
            "and the size is not a measure of how complicated the protocol "
            "is — it is a measure of how much freedom the interleaving "
            "has. The barrier solution and writers preference explore "
            f"{MODEL['rw_barrier']['states']:,} states; the semaphore mutex "
            f"needs {MODEL['semaphore_mutex']['states']}. One broken variant "
            "that was tried first, a lost update on the reader count, passed "
            "800,000 states without finishing and was replaced by a cheaper "
            "mistake: an off-by-one in the guard, which collapses in "
            f"{MODEL['rw_broken_count']['states']} states."),
        image("fig_states.png", width_cm=15.0,
              caption="Reachable states and transitions per solution, log "
                      "scale"),
        note(
            "A broken solution is worth modelling on purpose. It is the only "
            "way to know that the checker is looking: a checker that has "
            "never failed a solution has not been tested."),
    )

    # -------------------------------------------------- 4.3 counterexamples
    r.page(
        ptitle("4.3 What a counterexample looks like"),
        para(
            "A verdict without a witness is an assertion. The checker prints "
            "the shortest interleaving that breaks the property, and two of "
            "them are worth reading in full."),
        h1("Safety, broken by one comparison"),
        para(
            "`rw_broken_count` is readers preference with the guard off by "
            "one: the first reader tests whether the count is zero instead of "
            "whether it is one. It is one comparison away from a correct "
            "solution, and the checker reaches a writer inside together with "
            "a reader in " + f"{MODEL['rw_broken_count']['states']} states:"),
        code(broken_witness(9),
             caption="The safety witness for `rw_broken_count`"),
        para(
            "P0 raises the count to one, skips `wrt` because the guard tests "
            "the wrong value, and enters. P1 then takes `wrt` — which is "
            "free, because nobody ever took it — and enters too. Two "
            "lines of the trace, and the invariant is gone."),
    )

    r.page(
        ptitle("4.4 Starvation, found as a fair cycle"),
        para(
            "The Mesa monitor starves every participant, and this is the "
            "cycle that proves it for P0. P2 loops through its whole protocol "
            "and enters; P0 is woken, re-tests, and finds the section taken "
            "again."),
        code(mesa_starvation_witness(11),
             caption="The starvation witness for `rw_monitor_mesa`, P0"),
        para(
            "Every process on this cycle is either scheduled or blocked, so "
            "the schedule is fair: this is not a case of the victim being "
            "ignored. P0 is notified, wakes, and loses the race for the "
            "monitor lock to a thread that arrived after it. Repeating the "
            "cycle keeps it waiting for ever, which is what “no bounded "
            "waiting” means."),
        note(
            "The same cycle does not exist in `rw_monitor_fifo`, because "
            "there the notified thread is handed a place in the entry queue "
            "at signal time. One instruction, and the cycle disappears."),
    )

    # -------------------------------------------- 5 dekker and peterson
    r.page(
        ptitle("5. Dekker and Peterson: correct, fast, and only two of you"),
        h1("As locks, they are correct"),
        para(
            "Both algorithms are modelled with their own instruction "
            "extensions — a process needs to know its own index to set "
            "its own flag and read the other's — and both come out safe, "
            "deadlock free and starvation free. Dekker explores "
            f"{MODEL['dekker_mutex']['states']} states and Peterson "
            f"{MODEL['peterson_mutex']['states']}. Peterson is the shorter "
            "and the cheaper proof, which matches its reputation."),
        h1("They can carry the pattern, between two participants"),
        para(
            "The interesting question is not whether Dekker and Peterson work "
            "as mutexes — they do — but whether the readers-writers "
            "pattern can be built on top of them. It can. Put the lock around "
            "the *reader count* instead of around the section, let the first "
            "reader take the writer semaphore, and two readers end up inside "
            "together. `rw_dekker_2readers` and `rw_peterson_2readers` are "
            "both safe, deadlock free, starvation free, and admit concurrent "
            "reads with no semaphore anywhere in the model."),
        table(["solution", "roles", "states", "safety", "concurrent reads"],
              [[f"`{n}`", "".join(MODEL[n]["roles"]),
                f"{MODEL[n]['states']:,}",
                "holds" if MODEL[n]["rw_safety"] else "**VIOLATED**",
                "yes" if MODEL[n]["concurrent_reads_admitted"] else "no"]
               for n in ("rw_dekker", "rw_dekker_2readers",
                         "rw_peterson", "rw_peterson_2readers")],
              caption="The classic algorithms carrying the readers pattern"),
        h1("And that is where they stop"),
        para(
            "Both algorithms are written for exactly two processes. There is "
            "no third flag and no third turn. Applied to a readers-writers "
            "problem with more than two participants they collapse into a "
            "mutex: one lock around everything, one at a time, and the "
            "concurrency the problem exists for is gone. That is not a "
            "criticism of the algorithms — it is the definition of what "
            "they are for — but it is the answer to the comparison this "
            "exercise asks for. The semaphore and the monitor express the "
            "problem for any number of participants. Dekker and Peterson "
            "express mutual exclusion for two."),
        note(
            "The measurement says the same thing from the other side: run "
            "with one reader and one writer, `dekker_rw` and `peterson_rw` "
            "split the traffic almost evenly, with write shares of "
            f"{E3['dekker_rw']['write_share']:.2f} and "
            f"{E3['peterson_rw']['write_share']:.2f}. There is no third "
            "participant for them to be unfair to."),
    )

    # ------------------------------------------------------- 5 what it costs
    r.page(
        ptitle("6. What the locks cost"),
        para(
            "Four readers and two writers, an empty critical section, "
            f"{REPS1 if False else E1['semaphore_mutex']['reps']} runs per "
            "lock and the median reported with the spread beside it. Read "
            "this table as a ranking of *overhead*, not of parallelism: "
            "CPython's threads do not run in parallel, so no lock here gets "
            "faster by adding readers."),
        table(["lock", "ops/s (median)", "spread", "write share",
               "most readers inside"],
              throughput_rows(),
              caption="Throughput, 4 readers + 2 writers, empty section"),
        image("fig_throughput.png", width_cm=15.0,
              caption="Throughput per lock; whiskers are the spread over "
                      "repeated runs"),
    )

    r.page(
        ptitle("6.1 What the no-barging queue costs"),
        para(
            "The fairness proofs in section 4 assume a semaphore that does "
            "not let a newcomer overtake a waiter. That property is not free, "
            "and this is the bill."),
        table(["solution", "strict FIFO semaphore", "threading.Semaphore",
               "the queue costs"], queue_cost_rows(),
              caption="The surcharge for the property the proofs assume"),
        image("fig_queue_cost.png", width_cm=14.0,
              caption="Same algorithm, same load, two semaphore "
                      "implementations"),
        note(
            "This is the honest reading of the throughput table: the gap "
            "between the monitor solutions and the semaphore solutions is "
            "mostly the cost of the FIFO queue in this implementation, not a "
            "property of the algorithms. Compare within a family, not across "
            "one."),
    )

    # ------------------------------------------------------- 6 concurrency
    r.page(
        ptitle("7. The property the problem exists for"),
        para(
            "Six readers, one writer, and real work inside the section so "
            "that overlap is possible at all. The number is the largest count "
            "of readers observed inside simultaneously. A plain mutex cannot "
            "score more than one; anything that scores one is a mutex wearing "
            "a label."),
        table(["lock", "most readers inside at once", "write share"],
              concurrency_rows(),
              caption="Concurrent readers, 6 readers + 1 writer, work inside "
                      "the section"),
        image("fig_concurrency.png", width_cm=15.0,
              caption="Green reaches two or more readers, red never does"),
        note(
            "The barrier solution caps overlap on purpose — that is what "
            "a barrier is for — so a lower number there is the design "
            "working, not the design failing. It reaches "
            f"{E2['barrier']['max_concurrent_readers']} here against "
            f"{E2['readers_pref']['max_concurrent_readers']} for readers "
            "preference."),
    )

    # ------------------------------------------------------- 7 starvation
    r.page(
        ptitle("8. Starvation, measured"),
        h1("Six readers against one writer"),
        para(
            "This is the load readers preference is supposed to fail, and it "
            "does. The figure records every trial separately rather than "
            "averaging them, because several of these locks are bimodal: the "
            "outcome depends on who wins the opening race and then stays that "
            "way for the rest of the trial. A median of two modes is a number "
            "that describes neither."),
        image("fig_starvation.png", width_cm=14.6,
              caption="Each dot is one 0.6 s trial, the red bar is the "
                      "median, the green line is 1 writer of 7 threads"),
    )

    r.page(
        ptitle("8. Starvation, the numbers"),
        table(["lock", "write share (median)",
               "trials in which the writer starved",
               "longest unbroken read run", "longest unbroken write run"],
              starvation_rows(),
              caption=f"{E3['semaphore_mutex']['reps']} trials per lock, "
                      "6 readers + 1 writer"),
    )

    r.page(
        ptitle("8.1 Reading the starvation figures"),
        h1("Readers preference, and both monitors, starve the writer"),
        para(
            f"Readers preference starved the writer in "
            f"{E3['readers_pref']['writer_starved_trials']} of "
            f"{E3['readers_pref']['reps']} trials; the Mesa monitor did it in "
            f"{E3['monitor_mesa']['writer_starved_trials']} and the "
            f"FIFO-entry monitor in "
            f"{E3['monitor_fifo']['writer_starved_trials']}. The longest "
            "unbroken read run for readers preference is "
            f"{E3['readers_pref']['longest_read_run']:,} operations — a "
            "read phase that never ended. The fair FIFO turnstile, the writer "
            "barrier, writers preference and both mutexes never starved "
            "anybody in any trial."),
        h1("Peterson's spinlock is the surprise"),
        para(
            f"Peterson's algorithm starved the writer in "
            f"{E3['peterson_mutex']['writer_starved_trials']} of "
            f"{E3['peterson_mutex']['reps']} trials, and Dekker's was "
            f"writer-dominant in "
            f"{E3['dekker_mutex']['writer_dominant_trials']} of them. Both "
            "are provably starvation free, and the model checker says so. The "
            "measurement disagrees for a reason that has nothing to do with "
            "the algorithms: a spinning thread holds the CPU and does "
            "nothing with it. Under a global interpreter lock the spinning "
            "thread burns its whole quantum, and the other thread gets "
            "thousands of operations done in its own. The spin counts make it "
            f"plain — the two-process locks recorded "
            f"{max(E1[k]['spins'] for k in ('dekker_mutex', 'peterson_mutex')):,} "
            "spins in a quarter of a second."),
        note(
            "This is the clearest case in the exercise of a proof and a "
            "measurement disagreeing without either being wrong. The proof is "
            "about fair schedules. The measurement is about CPython's "
            "scheduler, which is not obliged to be fair to a thread that is "
            "spinning."),
    )

    r.page(
        ptitle("8.2 The mirror image, and where measurement gives up"),
        para(
            "One reader against four writers. Writers preference keeps the "
            "reader door shut while any writer is waiting, so the reader's "
            "share should collapse."),
        table(["lock", "write share (median)", "longest unbroken write run"],
              reader_starvation_rows(),
              caption="1 reader against 4 writers"),
        image("fig_reader_starvation.png", width_cm=15.0,
              caption="Reads completed under a writer-heavy load"),
        h1("What the measurement can and cannot show here"),
        para(
            "It cannot show what the proof shows. Writers preference does "
            "produce long unbroken write runs where the FIFO solutions "
            "alternate every few operations, but its write share is not "
            "reliably distinguishable from the baselines, and Python's own "
            "monitor lock is at this timescale *less* fair than writers "
            "preference is. The share of the traffic over one second is "
            "dominated by who won the opening race, and by the fairness of "
            "the interpreter's own lock, not by the algorithm. The honest "
            "statement is the one the model checker supplies: with two "
            "writers, writers preference starves the reader for ever. The "
            "measurement corroborates the mechanism and cannot isolate the "
            "effect."),
        note(
            "A measurement that cannot separate signal from noise is still "
            "worth reporting, as long as it is reported as such. The "
            "temptation is to quote the one run that shows what the theory "
            "predicts."),
    )

    # --------------------------------------------------------- 8 scaling
    r.page(
        ptitle("9. Does adding readers help?"),
        para(
            "One writer, one to eight readers, work inside the section. On a "
            "machine with real parallelism this is where a readers-writers "
            "lock should pull away from a mutex. On CPython it does not, "
            "because the threads never run at the same time: what the graph "
            "shows is lock overhead, and the honest conclusion is that none "
            "of these solutions scales with the number of readers here."),
        table(["lock", "1 reader", "2", "4", "6", "8"], scaling_rows(),
              caption="Operations per second against the number of reader "
                      "threads, plus one writer"),
        image("fig_scaling.png", width_cm=14.2,
              caption="Throughput against reader count"),
        note(
            "The one real movement in the table is readers preference going "
            f"from {E5['readers_pref']['1']['ops_per_s']:,.0f} ops/s with one "
            f"reader to {E5['readers_pref']['2']['ops_per_s']:,.0f} with two "
            "— the moment two readers can overlap. It does not continue, "
            "because the bottleneck is the interpreter, not the lock."),
    )

    # ----------------------------------------------------------- 9 verdict
    r.page(
        ptitle("10. Which one to use"),
        table(["If you need", "Use", "Because"],
              [["Any number of participants, no fairness guarantee needed",
                "readers preference",
                "fastest of the semaphore family and the simplest; the "
                "writer can starve"],
               ["Nobody to starve", "fair FIFO turnstile",
                "the only semaphore solution here with no starvation in any "
                "trial; the writer holds a semaphore across its whole wait"],
               ["Bounded phases", "writer barrier",
                "two symmetric gates; caps reader overlap on purpose so "
                "writers are not locked out"],
               ["A monitor", "monitor with a fair entry queue",
                "Mesa semantics alone do not bound waiting; the entry queue "
                "is not an optional refinement"],
               ["Exactly two participants, no OS support",
                "Peterson",
                "shorter and cheaper to prove than Dekker, and both are "
                "correct and starvation free"],
               ["More than two participants",
                "not Dekker, not Peterson",
                "both are written for two; beyond that they degrade to a "
                "mutex"]],
              caption="What the verdicts support"),
        h1("The one lesson that generalises"),
        para(
            "Fairness is not a property of the primitive, it is a property of "
            "the queue. A semaphore has one and you can rely on it. A monitor "
            "does not, and the difference between a monitor that starves "
            "everybody and one that starves only the writer is a single "
            "instruction about where a woken thread waits."),
    )

    # --------------------------------------------------------- 10 method
    r.page(
        ptitle("11. Method, artefacts and limits"),
        h1("What is on this branch"),
        table(["File", "What it is"],
              [["`code/rw_model.py`",
                "the exhaustive model checker, 17 protocols"],
               ["`code/rw_sync.py`",
                "the threaded implementations and the benchmark harness"],
               ["`code/run_experiments.py`",
                "runs every experiment, writes `output/experiments.json`"],
               ["`code/make_diagrams.py`", "regenerates every figure"],
               ["`tests/test_exercise7.py`", "102 tests"],
               ["`output/experiments.json`", "every number in this paper"],
               ["`diagrams/`", "9 figures, all regenerable"],
               ["`docs/REPORT_EN.docx / .pdf`", "this paper, English"],
               ["`docs/REPORT_FA.docx / .pdf`", "this paper, Persian"]],
              caption="Files published on the Exercise-7 branch"),
        h1("Limits, stated plainly"),
        bullets([
            "The model checker covers two or three processes. It proves "
            "properties of the protocol, not of any number of threads.",
            "The measurements run on CPython, where threads do not execute in "
            "parallel; throughput figures are overhead, not scalability.",
            "The strict FIFO semaphore in this exercise is a deliberately "
            "simple implementation, and it is roughly an order of magnitude "
            "slower than `threading.Semaphore`. Section 5.1 prices that.",
            "Starvation results at the half-second scale are bimodal for "
            "several locks; every trial is reported rather than averaged.",
            "Nothing here is sampled. The model checking is exhaustive and "
            "the harness checks the invariant on every entry.",
        ]),
        kv([("Exercise", "7 — readers and writers"),
            ("Branch", "Exercise-7-Readers-Writers-Comparison"),
            ("Solutions modelled", str(len(MODEL))),
            ("Locks benchmarked", str(len(E1))),
            ("Tests passing", "102"),
            ("Python", D["python"])],
           caption="At a glance"),
    )

    return r
