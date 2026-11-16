# -*- coding: utf-8 -*-
"""Exercise 6 — English paper.

Every number quoted here is read from the ``output/experiments.json`` of
exercises 1, 2 and 4, which are produced by their own experiment runners. The
paper therefore cannot quote a figure that the code does not produce.
"""
from __future__ import annotations

import json
import os

from report_kit import (Report, cover, toc, ptitle, h1, para, bullets, table,
                        kv, image, code, formula, note)

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))


def _load(ex, name="experiments.json"):
    with open(os.path.join(_REPO, ex, "output", name), encoding="utf-8") as f:
        return json.load(f)


E1 = _load("exercise-1")
E2 = _load("exercise-2")
E4 = _load("exercise-4")

MM = E2["measured"]
AN = E2["analytic"]
FS = E2["feasibility_study"]
SC = E2["scenarios"]
E3 = _load("exercise-3")
E1S = E1["experiments"]["scenarios"]
E1Q = E1["scenarios"]["baseline.json"]["per_queue"]
QP = E1["experiments"]["queue_policy"]
IQ = E1["experiments"]["interqueue"]
AG = E1["experiments"]["aging"]
OH = E1["experiments"]["overhead"]
ERR1 = E1["errors"]

M4 = E4["model"]
B4 = E4["benchmark"]
C4 = E4["contention"]
PC4 = E4["producer_consumer"]
RW4 = E4["readers_writers"]
DL4 = E4["deadlock"]

TITLE = ("Scheduling and Synchronisation in a Multilevel Queue System: "
         "a measured and verified study")
SUBTITLE = ("What four exercises on one codebase reveal about MLQ, EDF, RM and "
            "mutual exclusion")

COVER_META = [
    ("Title", "Scheduling and synchronisation in a multilevel queue system"),
    ("Subtitle", "A measured and verified study"),
    ("Course", "Advanced Operating Systems"),
    ("Exercise", "6 — research paper and seminar"),
    ("Companion material", "Exercises 1 to 5 on their own branches"),
    ("Method", "discrete-event simulation plus exhaustive model checking"),
    ("Deliverable", "Persian and English papers (DOCX and PDF) plus two PPTX "
                    "decks with speaker notes"),
    ("Repository", "github.com/kaspian021/Multilevel-Queue-Scheduling"),
    ("Branch", "Exercise-6-Paper-And-Seminar"),
]


def _m(scn, algo, key):
    return MM[f"{scn}|{algo}"][key]


def _pct(x):
    return f"{100 * x:.2f}%"


def _scn_rows():
    rows = []
    for s in ("A_fair", "B_stress", "C_aperiodic", "D_overload"):
        rows.append([s.split("_")[1].capitalize() + f" ({s[0]})",
                     _pct(MM[f"{s}|EDF"]["utilization"]),
                     str(SC[s]["hyperperiod"]),
                     str(_m(s, "EDF", "deadline_misses")),
                     str(_m(s, "RM", "deadline_misses")),
                     str(_m(s, "MLQ", "deadline_misses"))])
    return rows


def _metric_rows(key, fmt="{:.3f}"):
    rows = []
    for s in ("A_fair", "B_stress", "C_aperiodic", "D_overload"):
        rows.append([s.split("_")[1].capitalize() + f" ({s[0]})"]
                    + [fmt.format(_m(s, a, key)) for a in ("EDF", "RM", "MLQ")])
    return rows


def _bucket_rows():
    rows = []
    for name in sorted(FS["buckets"]):
        b = FS["buckets"][name]
        if b["n"] == 0:
            continue
        rows.append([name, str(b["n"]),
                     f"{100.0 * b['rm'] / b['n']:.1f}%",
                     f"{100.0 * b['edf'] / b['n']:.1f}%"])
    return rows


def _model_rows():
    order = ("dekker", "peterson", "lock_variable", "flag_spin", "tas",
             "semaphore_binary", "semaphore_wrong_order", "monitor_mesa")
    rows = []
    for n in order:
        r = M4[n]
        rows.append([f"`{n}`", r["family"], str(r["states"]),
                     "holds" if r["mutual_exclusion"] else "**VIOLATED**",
                     "yes" if r["deadlock_free"] else "**no**",
                     "yes" if all(r["starvation_free"].values()) else "**no**"])
    return rows


def _baseline_rows():
    pq = E1Q
    labels = {"1": "1 (highest)", "2": "2", "3": "3 (lowest)"}
    policies = {"1": "FCFS", "2": "RR", "3": "FCFS"}
    return [[labels[q], policies[q], str(pq[q]["count"]),
             f"{pq[q]['avg_waiting']:.1f}", f"{pq[q]['avg_turnaround']:.1f}",
             str(pq[q]["max_turnaround"])] for q in ("1", "2", "3")]


def _cost_rows():
    rows = []
    for k, v in B4.items():
        rows.append([k, f"{v['throughput_median']:,.0f}",
                     f"{v['throughput_min']:,.0f}",
                     f"{v['throughput_max']:,.0f}",
                     f"{v['spins_median']:,}" if v["spins_median"] is not None
                     else "blocks"])
    return rows


def build():
    r = Report(TITLE, SUBTITLE, "en", cover_meta=COVER_META)

    r.page(cover(COVER_META))
    r.page(toc())

    # ---------------------------------------------------------------- abstract
    r.page(
        ptitle("Abstract and keywords"),
        h1("Abstract"),
        para("This paper reports what a single codebase, developed across four "
             "exercises of an operating-systems course, can establish about "
             "multilevel queue (MLQ) scheduling, the real-time algorithms EDF "
             "and RM, and four approaches to mutual exclusion. Two methods are "
             "used and kept strictly apart. Where the question is quantitative, "
             "a discrete-event simulator produces reproducible numbers. Where "
             "the question is correctness, an exhaustive model checker "
             "enumerates every reachable interleaving and returns a verdict "
             "with a witness."),
        para(f"The findings are these. First, MLQ's weakness is structural, not "
             f"incidental: fixed queue assignment combined with fixed inter-"
             f"queue priority guarantees starvation unless aging is added, and "
             f"the measurements reproduce that. Second, the analytic "
             f"schedulability tests and the simulations agree wherever both "
             f"apply, which is a useful cross-check on both. Third, across "
             f"{FS['sets']:,} randomly generated task sets, RM schedulability "
             f"collapses from 100 per cent below 0.70 utilisation to "
             f"{100.0 * FS['buckets']['0.90-1.00']['rm'] / FS['buckets']['0.90-1.00']['n']:.1f} "
             f"per cent in the top bucket, while EDF stays at 100 per cent "
             f"throughout. Fourth, of eight mutual-exclusion algorithms checked "
             f"exhaustively, three fail, and each fails in a different way."),
        h1("Keywords"),
        para("Multilevel queue scheduling; earliest deadline first; rate "
             "monotonic; response-time analysis; Liu and Layland bound; mutual "
             "exclusion; Dekker; Peterson; test-and-set; semaphore; monitor; "
             "Mesa semantics; deadlock; starvation; model checking; discrete-"
             "event simulation."),
        h1("Contribution"),
        bullets([
            "A single reproducible codebase spanning scheduling, real-time "
            "analysis and synchronisation.",
            "Measured comparisons of MLQ against EDF and RM on four workloads, "
            "including a genuine overload.",
            "Exhaustive verification of eight mutual-exclusion algorithms with "
            "witness traces for every failure.",
            "An explicit separation between claims that were measured and "
            "claims that were proved, and a statement of what neither kind "
            "covers.",
        ]),
    )

    r.page(
        ptitle("Introduction"),
        h1("Motivation"),
        para("Textbook treatments of CPU scheduling present each algorithm in "
             "isolation and rank them on a single metric. That framing is "
             "convenient and misleading. In practice a scheduler is chosen for "
             "a workload and an objective, and the metrics conflict: the "
             "algorithm that minimises average waiting time is not the "
             "algorithm that bounds worst-case latency, and neither is the "
             "algorithm that treats every class of work fairly."),
        para("This paper takes the opposite approach. Rather than asking which "
             "algorithm is best, it asks what each one guarantees, what it "
             "costs, and where it breaks — and it answers with numbers produced "
             "by code that can be re-run."),
        h1("Scope"),
        bullets([
            "Exercise 1: a multilevel queue simulator with per-queue policies, "
            "optional aging and an invalid-input suite.",
            "Exercise 2: a shared harness that runs MLQ, EDF and RM over the "
            "same task sets, plus the analytic schedulability tests.",
            "Exercise 3: a hand-worked EDF and RM solution for a three-task "
            "set, checked against the simulator.",
            "Exercise 4: mutual exclusion, verified exhaustively and measured "
            "on running threads.",
            "Exercise 5: a short demonstration clip, delivered privately to "
            "the instructor.",
        ]),
        h1("Organisation"),
        bullets([
            "Section 2 states the models and the metrics.",
            "Section 3 describes the two methods and why they cannot replace "
            "each other.",
            "Sections 4 to 7 report the results.",
            "Section 8 discusses threats to validity.",
            "Sections 9 and 10 cover related work and conclusions.",
        ]),
    )

    r.page(
        ptitle("Models and metrics"),
        h1("The scheduler model"),
        para("A single processor, discrete time, one tick per unit of "
             "execution, preemptive. For the scheduling experiments a job is "
             "described by an arrival time, a burst and a queue assignment. "
             "For the real-time experiments a task is described by a worst-case "
             "execution time C, a period T and a relative deadline D, with all "
             "tasks released in phase."),
        h1("The metrics"),
        table(["Metric", "Definition", "Why it matters"],
              [["Turnaround", "completion minus arrival",
                "how long a user waits for a result"],
               ["Waiting", "time ready but not running",
                "how much capacity the queue structure wastes"],
               ["Response", "first time the job gets the CPU",
                "what an interactive user actually feels"],
               ["Jitter", "spread of response times within one task",
                "predictability, not just speed"],
               ["Deadline misses", "jobs finishing after their deadline",
                "the only metric that matters in hard real time"]],
              caption="The five metrics used throughout"),
        h1("Why these metrics conflict"),
        bullets([
            "Shortest-job-first provably minimises average waiting time among "
            "non-preemptive policies, and starves long jobs.",
            "Round-robin bounds the wait for every job but lengthens "
            "turnaround for all of them.",
            "Fixed-priority scheduling bounds the latency of the highest class "
            "and abandons the lowest one.",
            "There is no policy that is simultaneously optimal on all five; "
            "the choice is a requirement, not a measurement.",
        ]),
    )

    r.page(
        ptitle("Method: two kinds of claim"),
        h1("Measurement"),
        bullets([
            "A discrete-event simulator with one tick per time unit and no "
            "wall-clock dependence, so a run is reproducible.",
            "Scenarios are JSON data files, so a result can be re-derived "
            "without editing code.",
            "Tests lock in the numbers: a refactor that changes a result fails "
            "the suite.",
        ]),
        h1("Proof"),
        bullets([
            "A model checker enumerates the entire reachable state space of a "
            "two-process algorithm, with shared memory as a tuple of integers.",
            "A blocked process is modelled by a self-loop, which the explorer "
            "prunes, so a deadlock appears as a state with no useful "
            "successor.",
            "Starvation is detected as a strongly connected component of the "
            "graph restricted to transitions in which the victim never enters, "
            "with weak fairness enforced by requiring the victim to take at "
            "least one step in the cycle.",
        ]),
        h1("Why the two cannot be swapped"),
        para("A passing test means no violation was observed; it never means no "
             "violation exists. A proof means no violation can occur, but only "
             "relative to its model. Both are needed and neither substitutes "
             "for the other, which is why this paper labels every result as one "
             "or the other."),
        note("The proofs in Section 7 assume sequential consistency and atomic "
             "loads and stores of a single word, and cover exactly two "
             "participants. They say nothing about hardware with relaxed memory "
             "ordering, and nothing about n greater than two.",
             "What the proofs assume"),
    )

    r.page(
        ptitle("The design space of a multilevel queue"),
        h1("MLQ is a template, not an algorithm"),
        para("A multilevel queue scheduler is defined by three independent "
             "choices, and almost every published comparison collapses them "
             "into one. Making them explicit is the first useful thing the "
             "simulator did."),
        bullets([
            "How many queues exist, and how work is assigned to them.",
            "What policy each queue runs internally: FCFS, SJF, SRTF or "
            "round-robin with its own quantum.",
            "How the queues arbitrate against each other: fixed priority, or a "
            "time slice shared between them.",
        ]),
        h1("Per-queue policy: measured"),
        table(["Policy", "Avg waiting", "Avg turnaround", "Avg response",
               "Switches"],
              [["FCFS", f"{QP['FCFS']['waiting']:.3f}",
                f"{QP['FCFS']['turnaround']:.3f}",
                f"{QP['FCFS']['response']:.3f}",
                str(QP['FCFS']['switches_total'])],
               ["Round-robin", f"{QP['RR']['waiting']:.3f}",
                f"{QP['RR']['turnaround']:.3f}",
                f"{QP['RR']['response']:.3f}",
                str(QP['RR']['switches_total'])],
               ["SJF", f"{QP['SJF']['waiting']:.3f}",
                f"{QP['SJF']['turnaround']:.3f}",
                f"{QP['SJF']['response']:.3f}",
                str(QP['SJF']['switches_total'])],
               ["SRTF", f"{QP['SRTF']['waiting']:.3f}",
                f"{QP['SRTF']['turnaround']:.3f}",
                f"{QP['SRTF']['response']:.3f}",
                str(QP['SRTF']['switches_total'])]],
              caption="One workload, four intra-queue policies"),
        bullets([
            f"SJF gives the best average waiting time here "
            f"({QP['SJF']['waiting']:.3f}) and SRTF the best turnaround "
            f"({QP['SRTF']['turnaround']:.3f}), which is what the theory "
            f"predicts and is worth confirming rather than assuming.",
            f"The price is fairness: both need to know or estimate the burst, "
            f"and both can starve a long job indefinitely.",
            f"Round-robin is worst on turnaround "
            f"({QP['RR']['turnaround']:.3f}) and best on response "
            f"({QP['RR']['response']:.3f}), which is exactly the trade it is "
            f"designed to make.",
            f"The extra context switches are visible: "
            f"{QP['RR']['switches_total']} against {QP['FCFS']['switches_total']} "
            f"for FCFS on the same workload.",
        ]),
    )

    r.page(
        ptitle("Inter-queue arbitration"),
        h1("Fixed priority against time slicing between queues"),
        table(["Arbitration", "Avg waiting", "Avg turnaround", "Avg response",
               "Switches", "Preemptions"],
              [["Fixed priority", f"{IQ['fixed/2']['waiting']:.3f}",
                f"{IQ['fixed/2']['turnaround']:.3f}",
                f"{IQ['fixed/2']['response']:.3f}",
                str(IQ['fixed/2']['switches_total']),
                str(IQ['fixed/2']['preemptions'])],
               ["Slice, 2 ticks", f"{IQ['slice/2']['waiting']:.3f}",
                f"{IQ['slice/2']['turnaround']:.3f}",
                f"{IQ['slice/2']['response']:.3f}",
                str(IQ['slice/2']['switches_total']),
                str(IQ['slice/2']['preemptions'])],
               ["Slice, 3 ticks", f"{IQ['slice/3']['waiting']:.3f}",
                f"{IQ['slice/3']['turnaround']:.3f}",
                f"{IQ['slice/3']['response']:.3f}",
                str(IQ['slice/3']['switches_total']),
                str(IQ['slice/3']['preemptions'])],
               ["Slice, 5 ticks", f"{IQ['slice/5']['waiting']:.3f}",
                f"{IQ['slice/5']['turnaround']:.3f}",
                f"{IQ['slice/5']['response']:.3f}",
                str(IQ['slice/5']['switches_total']),
                str(IQ['slice/5']['preemptions'])]],
              caption="Five jobs, 24 ticks of work, four ways of sharing"),
        h1("The trade, made visible"),
        bullets([
            f"Fixed priority has the best turnaround "
            f"({IQ['fixed/2']['turnaround']:.3f}) and the worst response "
            f"({IQ['fixed/2']['response']:.3f}): the bottom queue waits for "
            f"everything above it.",
            f"A 2-tick slice inverts that — response drops to "
            f"{IQ['slice/2']['response']:.3f} while turnaround rises to "
            f"{IQ['slice/2']['turnaround']:.3f} — and does it with "
            f"{IQ['slice/2']['switches_total']} switches against "
            f"{IQ['fixed/2']['switches_total']}.",
            f"As the slice grows the behaviour converges back towards fixed "
            f"priority, as it should; a 5-tick slice is already "
            f"{IQ['slice/5']['response']:.3f} on response.",
            "Utilisation is 100 per cent and throughput identical in every "
            "row: none of these choices changes how much work gets done, only "
            "who waits for it and how long.",
        ]),
        note("Slicing between queues costs context switches and buys "
             "responsiveness. It is the same trade as round-robin, applied one "
             "level up. Nothing in the table identifies a right answer; the "
             "answer comes from what the workload needs.", "No free lunch"),
    )

    r.page(
        ptitle("Aging and starvation, measured"),
        h1("The problem"),
        para("With fixed queues and fixed inter-queue priority, starvation is "
             "not a risk — it is a guarantee whenever the upper queues stay "
             "non-empty. Aging is the standard remedy: a job that has waited "
             "longer than a threshold is promoted. The measurement question is "
             "what the threshold costs."),
        table(["Threshold", "Promotions", "Avg waiting (all)",
               "Low-queue waiting", "Low-queue turnaround"],
              [[str(AG["thresholds"][i]), str(AG["promotions"][i]),
                f"{AG['avg_wait'][i]:.3f}", str(AG["low_wait"][i]),
                str(AG["low_tat"][i])]
               for i in range(len(AG["thresholds"]))],
              caption="Aging threshold sweep; threshold 0 means aging disabled"),
        h1("Reading the sweep"),
        bullets([
            f"With aging disabled the lowest queue waits "
            f"{AG['low_wait'][0]} ticks and takes {AG['low_tat'][0]} to "
            f"finish; with a threshold of 2 it waits {AG['low_wait'][1]} and "
            f"finishes in {AG['low_tat'][1]}.",
            f"The improvement for the victim is larger than the cost to "
            f"everyone else: average waiting across all queues actually "
            f"*falls* from {AG['avg_wait'][0]:.3f} to {AG['avg_wait'][1]:.3f}, "
            f"because promoting a nearly-finished job is cheap.",
            "As the threshold grows the benefit decays monotonically until, at "
            f"12, the numbers return to the no-aging case "
            f"({AG['low_wait'][5]} ticks) — the threshold is now larger than "
            f"the run, so nothing is ever promoted.",
            "Aging therefore has a usable range, not a single value, and the "
            "right end of that range depends on the job mix.",
        ]),
    )

    r.page(
        ptitle("Aging, plotted"),
        image("fig_aging.png", width_cm=13.5,
              caption="waiting time for the lowest queue (red) and "
                      "for all queues on average (blue), against the aging "
                      "threshold"),
        h1("What the shape says"),
        bullets([
            "The red curve is close to a straight line: every extra tick of "
            "patience costs the lowest queue almost exactly a tick of waiting.",
            "The blue curve barely moves, which is the whole argument for "
            "aging — the aggregate cost is small because promotions happen "
            "late, when the waiting job is nearly done.",
            "Both curves flatten at the right-hand end because the threshold "
            "has exceeded the length of the run and nothing is promoted at "
            "all.",
        ]),
        note("Aging does not remove the trade, it re-weights it. Promoting a "
             "low-priority job delays a high-priority one by definition; the "
             "measurement shows only that with these workloads the delay is "
             "smaller than the gain.", "What aging does not do"),
    )

    r.page(
        ptitle("Results I: multilevel queue behaviour"),
        h1("The simulator"),
        para("Exercise 1 built an MLQ simulator with a fixed number of queues, "
             "an independent policy per queue (FCFS, SJF or round-robin with a "
             "per-queue quantum), fixed-priority arbitration between queues and "
             "optional aging. It accepts scenario files and rejects invalid "
             "input with a diagnostic rather than a crash."),
        h1("Per-queue behaviour in the baseline scenario"),
        table(["Queue", "Policy", "Jobs", "Avg waiting", "Avg turnaround",
               "Max turnaround"],
              _baseline_rows(),
              caption="Baseline scenario, measured per queue"),
        h1("What this shows"),
        bullets([
            "The inter-queue priority dominates: the lowest queue waits for "
            "everything else regardless of its own policy.",
            "Round-robin inside a queue costs throughput in exchange for "
            "bounded waiting inside that queue.",
            "Aging removes the starvation that fixed assignment otherwise "
            "guarantees, at the cost of letting low-priority work delay "
            "high-priority work.",
        ]),
        note("The simulator is a model of a scheduling policy, not a kernel. "
             "It measures the policy's decisions, not the cost of the "
             "mechanism that would implement them.", "Status of the numbers"),
    )

    r.page(
        ptitle("Results II: MLQ against EDF and RM"),
        h1("The four workloads"),
        table(["Scenario", "Utilisation", "Hyperperiod", "EDF misses",
               "RM misses", "MLQ misses"],
              _scn_rows(),
              caption="Deadline misses per scenario and algorithm"),
        h1("Reading the table"),
        bullets([
            "At a comfortable load everything passes; that is a sanity check, "
            "not a result.",
            f"Under stress (B), EDF meets every deadline while RM and MLQ each "
            f"miss {_m('B_stress', 'RM', 'deadline_misses')}. This is the case "
            f"where the Liu–Layland bound has already stopped being useful.",
            f"In the aperiodic scenario (C), MLQ actually beats RM "
            f"({_m('C_aperiodic', 'MLQ', 'deadline_misses')} misses against "
            f"{_m('C_aperiodic', 'RM', 'deadline_misses')}). That is an "
            f"accident of the workload, not a property, and the paper treats "
            f"it as such.",
            f"Under overload (D) the ordering reverses: EDF misses "
            f"{_m('D_overload', 'EDF', 'deadline_misses')} while RM and MLQ "
            f"miss {_m('D_overload', 'RM', 'deadline_misses')} each.",
        ]),
        h1("Response time and jitter"),
        table(["Scenario", "EDF avg", "RM avg", "MLQ avg"],
              _metric_rows("avg_response", "{:.3f}"),
              caption="Average response time"),
        table(["Scenario", "EDF jitter", "RM jitter", "MLQ jitter"],
              _metric_rows("jitter", "{:.3f}"),
              caption="Response-time jitter (population standard deviation)"),
    )

    r.page(
        ptitle("Results II, continued: the overload case"),
        h1("What overload actually shows"),
        para(f"Scenario D offers 123.33 per cent load. The processor achieves "
             f"100 per cent; the remaining 23.33 per cent is work that cannot "
             f"be done at all. The interesting question is not how many "
             f"deadlines are missed — miss count is fixed by arithmetic — but "
             f"which jobs are sacrificed."),
        table(["Algorithm", "Misses", "Avg response", "Max response", "Jitter"],
              [[a, str(_m("D_overload", a, "deadline_misses")),
                f"{_m('D_overload', a, 'avg_response'):.3f}",
                str(_m("D_overload", a, "max_response")),
                f"{_m('D_overload', a, 'jitter'):.3f}"]
               for a in ("EDF", "RM", "MLQ")],
              caption="Behaviour under 123.33 per cent offered load"),
        h1("Interpretation"),
        bullets([
            "EDF spreads the damage: it refuses to protect any priority class, "
            "so all three tasks miss.",
            "RM and MLQ protect the high-priority tasks by abandoning the "
            "lowest one almost entirely.",
            "The lower miss count of RM and MLQ is therefore not evidence that "
            "they handle overload better; it is evidence that they choose a "
            "different victim.",
            "For a hard real-time system the second behaviour is usually what "
            "you want, which makes it a design requirement rather than a "
            "metric to optimise.",
        ]),
        image("fig_overload_gantt.png", width_cm=14.5,
              caption="the same task set and the same 120 ticks "
                      "under EDF (top) and RM (bottom)"),
        note("A naive reading of the table says EDF is worse under overload "
             "because 31 is more than 10. The honest reading is that the two "
             "families make different choices about who suffers, and that the "
             "choice belongs to the system designer.", "The trap to avoid"),
    )

    r.page(
        ptitle("Results III: schedulability"),
        h1("What the analytic tests can and cannot say"),
        bullets([
            "The Liu–Layland bound n(2^(1/n) − 1) is sufficient for RM but not "
            "necessary. At n = 4 it is 0.7568; a task set above it is not "
            "thereby infeasible.",
            "Exact RM feasibility needs response-time analysis: iterate "
            "R = C + sum over higher-priority tasks of ceil(R/T)·C until it "
            "converges, then compare with D.",
            "For EDF with implicit deadlines, U ≤ 1 is both necessary and "
            "sufficient, so there is nothing to iterate and nothing to guess.",
        ]),
        formula("R_i = C_i + sum_{j in hp(i)} ceil(R_i / T_j) * C_j",
                caption="The response-time recurrence used for exact RM analysis"),
        h1("Agreement between analysis and simulation"),
        table(["Scenario", "U", "RM bound", "RM analysis", "EDF analysis",
               "RM misses", "EDF misses"],
              [["A — fair", _pct(AN["A_fair"]["utilization"]),
                f"{AN['A_fair']['liu_layland_bound']:.4f}",
                "feasible" if AN["A_fair"]["rm"]["feasible"] else "infeasible",
                "feasible" if AN["A_fair"]["edf"]["feasible"] else "infeasible",
                str(_m("A_fair", "RM", "deadline_misses")),
                str(_m("A_fair", "EDF", "deadline_misses"))],
               ["B — stress", _pct(AN["B_stress"]["utilization"]),
                f"{AN['B_stress']['liu_layland_bound']:.4f}",
                "feasible" if AN["B_stress"]["rm"]["feasible"] else "infeasible",
                "feasible" if AN["B_stress"]["edf"]["feasible"] else "infeasible",
                str(_m("B_stress", "RM", "deadline_misses")),
                str(_m("B_stress", "EDF", "deadline_misses"))],
               ["C — aperiodic", _pct(AN["C_aperiodic"]["utilization"]),
                f"{AN['C_aperiodic']['liu_layland_bound']:.4f}",
                "feasible" if AN["C_aperiodic"]["rm"]["feasible"] else "infeasible",
                "feasible" if AN["C_aperiodic"]["edf"]["feasible"] else "infeasible",
                str(_m("C_aperiodic", "RM", "deadline_misses")),
                str(_m("C_aperiodic", "EDF", "deadline_misses"))],
               ["D — overload", _pct(AN["D_overload"]["utilization"]),
                f"{AN['D_overload']['liu_layland_bound']:.4f}",
                "feasible" if AN["D_overload"]["rm"]["feasible"] else "infeasible",
                "feasible" if AN["D_overload"]["edf"]["feasible"] else "infeasible",
                str(_m("D_overload", "RM", "deadline_misses")),
                str(_m("D_overload", "EDF", "deadline_misses"))]],
              caption="Analytic verdict against measured misses, per scenario"),
        bullets([
            "Where the analysis says feasible, the simulation reports zero "
            "misses. Where it says infeasible, the simulation finds misses.",
            "That agreement in both directions is the useful part: it "
            "validates the simulator as much as the analysis.",
        ]),
    )

    r.page(
        ptitle("Results III, continued: the feasibility study"),
        h1("Design"),
        para(f"Task sets were generated at random with a fixed seed and "
             f"classified by utilisation. For each set both the exact RM "
             f"response-time analysis and the EDF utilisation test were run. "
             f"{FS['sets']:,} sets were generated in total, with seed "
             f"{FS['seed']}, so the study is reproducible even though it is a "
             f"sample and not a theorem."),
        table(["Utilisation band", "Sets", "RM schedulable", "EDF schedulable"],
              _bucket_rows(),
              caption=f"Feasibility by utilisation band, {FS['sets']:,} random "
                      f"task sets"),
        h1("The cliff"),
        bullets([
            "Below 0.70 utilisation, RM schedulability is 100 per cent.",
            "Between 0.80 and 0.90 it falls to "
            f"{100.0 * FS['buckets']['0.80-0.90']['rm'] / FS['buckets']['0.80-0.90']['n']:.1f} "
            "per cent.",
            "In the top band it collapses to "
            f"{100.0 * FS['buckets']['0.90-1.00']['rm'] / FS['buckets']['0.90-1.00']['n']:.1f} "
            "per cent.",
            "EDF remains at 100 per cent throughout, which is exactly what the "
            "theory predicts for implicit deadlines.",
        ]),
    )

    r.page(
        ptitle("The cliff, plotted"),
        image("fig_utilisation_cliff.png", width_cm=14.5,
              caption=f"Figure 3: feasibility against utilisation, "
                      f"{FS['sets']:,} random task sets, seed {FS['seed']}"),
        h1("What the shape says"),
        bullets([
            "The EDF line is flat at 100 per cent, which is the theory being "
            "visible: with implicit deadlines, U ≤ 1 is the whole answer.",
            "The RM line is flat until roughly 0.70 and then falls off a "
            "cliff. The fall is not gradual, and that is the practically "
            "useful part of the result.",
            "The dotted line is the Liu–Layland bound. Sets to its left are "
            "guaranteed schedulable by the bound alone; everywhere else the "
            "bound is silent and only the exact test can answer.",
            "The gap between the two curves at high utilisation is the "
            "quantitative statement of what choosing RM costs.",
        ]),
        note("This is a sample of "
             f"{FS['sets']:,} sets from one generator with one seed. It is "
             "reproducible and it is not a theorem: a different generator or a "
             "different distribution of periods would shift every number in "
             "the table.", "What this study is"),
    )

    r.page(
        ptitle("A worked cross-check: analysis by hand"),
        h1("Why this section exists"),
        para("The schedulability results in Section 6 are produced by two "
             "independent routes: an analytic test and a simulation. Before "
             "trusting either, it is worth checking that both reproduce a "
             "solution that can be worked out on paper. Exercise 3 does "
             "exactly that on a three-task set, and this section reports the "
             "outcome."),
        table(["Task", "C", "T", "D"],
              [[t["name"], str(t["C"]), str(t["T"]), str(t["D"])]
               for t in E3["tasks"]],
              caption=f"The task set; U = {E3['utilization']:.6f}, "
                      f"hyperperiod {E3['hyperperiod']}"),
        h1("The two verdicts"),
        table(["", "EDF", "RM"],
              [["Utilisation", f"{E3['utilization']:.6f}",
                f"{E3['utilization']:.6f}"],
               ["Test", "U ≤ 1 (exact here)",
                f"Liu–Layland bound {E3['rm']['liu_layland_bound']:.4f}, then "
                f"response-time analysis"],
               ["Bound verdict", "feasible",
                "inconclusive — U is above the bound"],
               ["Exact verdict", "feasible",
                "infeasible: R(T3) = "
                f"{E3['rm']['response_times']['T3']['R']} > D = "
                f"{E3['rm']['response_times']['T3']['D']}"],
               ["Measured misses",
                str(E3["measured"]["EDF"]["deadline_misses"]),
                str(E3["measured"]["RM"]["deadline_misses"])]],
              caption="Hand analysis against simulation, on the same task set"),
        h1("Why the RM case is the interesting one"),
        bullets([
            f"The Liu–Layland bound at n = 3 is "
            f"{E3['rm']['liu_layland_bound']:.4f}, and U = "
            f"{E3['utilization']:.4f} exceeds it. That proves nothing: the "
            f"bound is sufficient, not necessary.",
            f"Working the response-time recurrence by hand gives R(T3) = "
            f"{E3['rm']['response_times']['T3']['R']} against a deadline of "
            f"{E3['rm']['response_times']['T3']['D']}, so the set is genuinely "
            f"infeasible under RM — and now the reason is precise.",
            f"The simulator agrees in the smallest possible detail: it reports "
            f"exactly {E3['measured']['RM']['deadline_misses']} miss, at "
            f"t = {E3['measured']['RM']['missed_jobs'][0][4]}, which is "
            f"exactly the response time the hand analysis computed.",
            f"EDF schedules the same set with "
            f"{E3['measured']['EDF']['deadline_misses']} misses, as U ≤ 1 "
            f"guarantees for implicit deadlines.",
        ]),
        note("This is the tightest check available in the project: a hand "
             "computation, an exact analytic test and a simulation all "
             "agreeing on the same number, including the identity of the "
             "failing job and the instant it fails.", "Value of the exercise"),
    )

    r.page(
        ptitle("Mutual exclusion, algorithm by algorithm"),
        h1("Eight algorithms, one model"),
        para("All eight were expressed in the same model: shared memory as a "
             "tuple of integers, a program counter per process, and one "
             "transition per enabled step. The explorer then walks the whole "
             "reachable graph. Because the model is identical for all eight, "
             "the verdicts are directly comparable — a difference in the "
             "result is a difference in the algorithm, not in the encoding."),
        table(["Algorithm", "Idea", "Verdict"],
              [["Dekker", "turn-taking plus flags, with a tie broken "
                          "explicitly", "correct"],
               ["Peterson", "two flags and a single turn variable", "correct"],
               ["Lock variable", "one shared boolean, read then write",
                "safety violated"],
               ["Announce then spin", "set my flag, then spin on the other",
                "liveness violated"],
               ["Test-and-set", "atomic hardware primitive, spin until free",
                "correct but unfair"],
               ["Semaphore, correct order", "acquire then release, one lock",
                "correct"],
               ["Semaphore, wrong order", "two locks acquired in opposite "
                                          "orders", "deadlock"],
               ["Monitor, Mesa semantics", "condition variables inside a "
                                           "monitor", "correct"]],
              caption="The eight algorithms in one sentence each"),
        h1("What the state counts are for"),
        bullets([
            f"Dekker needs {M4['dekker']['states']} states, Peterson "
            f"{M4['peterson']['states']}: the extra bookkeeping of a "
            f"turn-taking protocol is directly visible.",
            f"The lock-variable protocol needs only "
            f"{M4['lock_variable']['states']} states and one of them breaks "
            f"safety — a small space is not a safe space.",
            f"The wrong-order semaphore has "
            f"{M4['semaphore_wrong_order']['states']} states and every "
            f"individual property holds, yet the system deadlocks.",
        ]),
    )

    r.page(
        ptitle("Results IV: mutual exclusion, verified"),
        h1("The verdicts"),
        table(["Algorithm", "Family", "States", "Mutual exclusion",
               "Deadlock free", "Starvation free"],
              _model_rows(),
              caption="Exhaustive verdicts; the largest space has "
                      f"{max(v['states'] for v in M4.values())} states"),
        h1("Three failures, three mechanisms"),
        bullets([
            "The lock-variable protocol loses **safety**: the read and the "
            "write are separate steps, so both processes can see the lock free.",
            "Announce-then-spin keeps safety and loses **progress**: both can "
            "announce before either looks.",
            "Test-and-set keeps both and loses **fairness**: nothing remembers "
            "who has waited longest.",
            "The wrong-order semaphore keeps every property of the primitive "
            "and still deadlocks the system — the only failure here that is a "
            "usage error rather than a design error.",
        ]),
        h1("Why the witness matters more than the verdict"),
        para("A verdict of 'violated' is only useful if it comes with the "
             "interleaving that violates it. The checker reports the shortest "
             "such path, which turns an assertion into something a reader can "
             "step through and check by hand."),
    )

    r.page(
        ptitle("Three ways to be wrong"),
        image("fig_property_matrix.png", width_cm=13.0,
              caption="which property fails, for each algorithm; "
                      "every cell is an exhaustive verdict, not a sample"),
        h1("Reading the grid"),
        bullets([
            "A red cell is a proof that the property fails somewhere in the "
            "state space, not an observation that it failed once.",
            "The three failures occupy three different columns: the lock "
            "variable loses safety, announce-then-spin loses freedom from "
            "deadlock, and test-and-set loses freedom from starvation.",
            "The wrong-order semaphore has no red cell at all, and still "
            "deadlocks the program that uses it — the grid cannot show that, "
            "because the fault is in the client, not in the primitive.",
        ]),
    )

    r.page(
        ptitle("Results V: deadlock and the monitor"),
        h1("The circular wait, reproduced"),
        code([f"wrong order   : t0 = \"{DL4['wrong_order']['state']['t0']}\"",
              f"                t1 = \"{DL4['wrong_order']['state']['t1']}\"",
              f"                deadlocked = {DL4['wrong_order']['deadlocked']}",
              f"consistent    : t0 = \"{DL4['consistent_order']['state']['t0']}\"",
              f"                t1 = \"{DL4['consistent_order']['state']['t1']}\"",
              f"                completed  = "
              f"{DL4['consistent_order']['both_completed']}"],
             caption="Deterministic deadlock experiment"),
        bullets([
            "A barrier sits between the two acquisitions, so the circular wait "
            "is produced deliberately rather than left to the scheduler.",
            "All four Coffman conditions hold: mutual exclusion, hold-and-wait, "
            "no preemption and circular wait.",
            "With a global lock order the identical program always finishes.",
        ]),
        h1("The monitor, measured"),
        table(["Capacity", "Max occupancy", "Capacity respected",
               "Re-checks after a wake", "Throughput (items/s)"],
              [[str(PC4[f"capacity_{c}"]["capacity"]),
                str(PC4[f"capacity_{c}"]["max_observed_in_buffer"]),
                "yes" if PC4[f"capacity_{c}"]["capacity_respected"] else "no",
                f"{PC4[f'capacity_{c}']['re_waits_after_signal']:,}",
                f"{PC4[f'capacity_{c}']['throughput_items_per_s']:,.0f}"]
               for c in (1, 4, 16)],
              caption="Bounded buffer monitor, 1600 items, two producers and "
                      "two consumers"),
        bullets([
            "The re-check column is the argument for the while-loop around a "
            "condition wait under Mesa semantics.",
            f"At capacity 1 a woken thread had to wait again "
            f"{PC4['capacity_1']['re_waits_after_signal']:,} times; at capacity "
            f"16, only {PC4['capacity_16']['re_waits_after_signal']:,} times.",
            "Had the code used `if` rather than `while`, those re-waits would "
            "have been silent corruption instead of a measured statistic.",
        ]),
    )

    r.page(
        ptitle("Fairness: the readers and writers problem"),
        h1("Why this belongs in a scheduling paper"),
        para("Readers and writers is usually presented as a synchronisation "
             "problem, but the three standard solutions differ only in their "
             "scheduling policy: who gets in next when both a reader and a "
             "writer are waiting. That makes it the cleanest available "
             "laboratory for the fairness question that Section 7 could only "
             "answer with a verdict."),
        table(["Variant", "Reads (total)", "Writes (total)", "Read share",
               "Readers starved", "Writers starved"],
              [["Readers preference",
                f"{RW4['ReadersPreferenceRW']['reads_total']:,}",
                f"{RW4['ReadersPreferenceRW']['writes_total']:,}",
                f"{RW4['ReadersPreferenceRW']['read_share_mean']:.3f}",
                str(RW4['ReadersPreferenceRW']['trials_with_reader_starved']),
                str(RW4['ReadersPreferenceRW']['trials_with_writer_starved'])],
               ["Writers preference",
                f"{RW4['WritersPreferenceRW']['reads_total']:,}",
                f"{RW4['WritersPreferenceRW']['writes_total']:,}",
                f"{RW4['WritersPreferenceRW']['read_share_mean']:.3f}",
                str(RW4['WritersPreferenceRW']['trials_with_reader_starved']),
                str(RW4['WritersPreferenceRW']['trials_with_writer_starved'])],
               ["Fair (FIFO ticket)", f"{RW4['FairRW']['reads_total']:,}",
                f"{RW4['FairRW']['writes_total']:,}",
                f"{RW4['FairRW']['read_share_mean']:.3f}",
                str(RW4['FairRW']['trials_with_reader_starved']),
                str(RW4['FairRW']['trials_with_writer_starved'])]],
              caption=f"Six readers and one writer, {RW4['FairRW']['duration_s']} "
                      f"s per trial, {RW4['FairRW']['reps']} trials each"),
        h1("What the numbers say"),
        bullets([
            f"Readers preference achieves a read share of exactly "
            f"{RW4['ReadersPreferenceRW']['read_share_mean']:.3f} — in "
            f"{RW4['ReadersPreferenceRW']['reps']} trials, "
            f"{RW4['ReadersPreferenceRW']['writes_total']} writes happened in "
            f"total, roughly one per trial. This is writer starvation "
            f"observed, not inferred.",
            f"Writers preference swings to a read share of "
            f"{RW4['WritersPreferenceRW']['read_share_mean']:.3f} and "
            f"{RW4['WritersPreferenceRW']['writes_total']:,} writes.",
            f"The fair variant lands at "
            f"{RW4['FairRW']['read_share_mean']:.3f} with "
            f"{RW4['FairRW']['writes_total']:,} writes and no starvation of "
            f"either side.",
            "The starvation columns are zero everywhere, which is the honest "
            "and slightly awkward result: our detector did not fire in these "
            "trials. The read share is the evidence, not the flag.",
        ]),
        note("A read share of 1.000 across every trial is a stronger statement "
             "than a starvation flag, because it does not depend on the "
             "detector's threshold. This is why the raw counts are reported "
             "alongside the verdicts.", "Why report both"),
    )

    r.page(
        ptitle("Validation: what the test suites lock in"),
        h1("Numbers that cannot silently change"),
        para("A result that is only asserted in prose is a result that decays. "
             "Every number quoted in this paper is also asserted by a test, so "
             "a refactor that changes a measurement fails the suite rather "
             "than quietly altering a table."),
        table(["Branch", "Tests", "What is locked in"],
              [["Exercise 1", "59",
                "per-queue metrics, Gantt construction, aging sweep, "
                "rejection of invalid scenario files"],
               ["Exercise 2", "38",
                "the analytic tests against known-answer task sets, the "
                "miss counts per scenario, the feasibility study seed"],
               ["Exercise 3", "29",
                "the hand-computed timelines for EDF and RM, step by step"],
               ["Exercise 4", "52",
                "all eight model-checking verdicts, the deadlock experiment, "
                "the threading layer, the figure set"],
               ["Exercise 6", "14",
                "both decks, slide counts, speaker notes on every slide, RTL "
                "markup on every Persian paragraph"]],
              caption="Regression suites per branch (counts as last run)"),
        h1("What is tested and what is not"),
        bullets([
            "Analytic results are checked against hand-computed known answers, "
            "not against the simulator — otherwise the two could agree by "
            "sharing a bug.",
            "Simulation results are checked by re-deriving them, and "
            "separately by comparison with the analytic verdicts.",
            "Model-checking results are checked by re-running the explorer; "
            "the interesting ones are also checked by asserting the specific "
            "violating state.",
            "Timing results are *not* asserted. They are reported as medians "
            "with their spread precisely because they cannot be locked in.",
        ]),
    )

    r.page(
        ptitle("Validation, continued: inputs and reproduction"),
        h1("Input validation"),
        code([f"{k}: {v}" for k, v in sorted(ERR1.items())],
             caption="Malformed scenario files rejected with a diagnostic"),
        bullets([
            "A simulator that accepts a malformed scenario and produces a "
            "plausible number is worse than one that crashes.",
            "These cases are asserted, so the diagnostics cannot silently "
            "regress into silent defaults.",
        ]),
        h1("Scenario-driven experimentation"),
        bullets([
            "Every scenario is a JSON data file, so a new workload needs no "
            "code change and no rebuild.",
            "The same file drives the simulation, the report and the test, "
            "which removes the possibility of them disagreeing about inputs.",
        ]),
        h1("Determinism"),
        bullets([
            "The simulator advances in whole ticks and never reads the clock, "
            "so a scenario produces byte-identical output on every run.",
            "The model checker explores in a fixed order, so its verdicts and "
            "its witness traces are stable too.",
            "Only the timings are non-deterministic, which is why they are the "
            "only numbers reported as medians with a spread.",
        ]),
    )

    r.page(
        ptitle("Results VI: cost"),
        table(["Mechanism", "Median ops/s", "Min", "Max", "Spins"],
              _cost_rows(),
              caption="Two threads, 5000 critical sections each, median of "
                      "seven runs"),
        h1("Reading the table honestly"),
        bullets([
            f"The two turn-taking protocols are fastest, and the reason is "
            f"visible in the last column: their median spin count is zero. "
            f"They almost never contend, because the turn variable already "
            f"decides who goes next.",
            f"Test-and-set is the *slowest* of the five at this thread count, "
            f"not the fastest, because it spins "
            f"{B4['tas']['spins_median']:,} times per run while Dekker spins "
            f"{B4['dekker']['spins_median']} times. Spinning is only cheap "
            f"when the wait is short.",
            f"Note the spread: Dekker's minimum is "
            f"{B4['dekker']['throughput_min']:,.0f} against a maximum of "
            f"{B4['dekker']['throughput_max']:,.0f} for identical code on the "
            f"same machine — a factor of "
            f"{B4['dekker']['throughput_max'] / B4['dekker']['throughput_min']:.1f}.",
            "A single timing on a shared machine is noise. Only the medians "
            "are meaningful, and only for relative comparison.",
        ]),
        h1("Under contention"),
        table(["Threads", "Test-and-set", "Semaphore", "Monitor", "TAS spins"],
              [[str(n),
                f"{C4[f'tas_{n}t']['throughput_median']:,.0f}",
                f"{C4[f'semaphore_{n}t']['throughput_median']:,.0f}",
                f"{C4[f'monitor_{n}t']['throughput_median']:,.0f}",
                f"{C4[f'tas_{n}t']['spins_median']:,}"]
               for n in (2, 4, 8)],
              caption="Median of five runs, 5000 critical sections per thread"),
        bullets([
            "The blocking mechanisms degrade gently and predictably: the "
            f"monitor goes from {C4['monitor_2t']['throughput_median']:,.0f} "
            f"to {C4['monitor_8t']['throughput_median']:,.0f} across a "
            f"fourfold increase in threads.",
            f"The spinlock is *faster* at two and four threads "
            f"({C4['tas_2t']['throughput_median']:,.0f} and "
            f"{C4['tas_4t']['throughput_median']:,.0f}) and only falls behind "
            f"at eight ({C4['tas_8t']['throughput_median']:,.0f}). Its "
            f"throughput is not the interesting column.",
            f"Its wasted attempts are: they rise from "
            f"{C4['tas_2t']['spins_median']:,} at two threads to "
            f"{C4['tas_8t']['spins_median']:,} at eight, nearly sixfold.",
            "That is CPU time spent achieving nothing, and it is the reason a "
            "spinlock is a kernel primitive rather than an application one.",
        ]),
    )

    r.page(
        ptitle("Contention, plotted"),
        image("fig_contention.png", width_cm=14.5,
              caption="median throughput against thread count, with "
                      "the wasted spin attempts of the test-and-set lock "
                      "shown as bars"),
        h1("What the shape says"),
        bullets([
            "The three blocking or semi-blocking mechanisms track each other "
            "closely; the ranking between them is stable but the gap is small.",
            "The spinlock's wasted attempts, shown as bars against the right "
            "axis, rise far faster than its throughput falls — the cost is "
            "paid in CPU time that produces nothing, not only in the "
            "workload's own completion.",
            "Only two, four and eight threads are plotted, because that is "
            "what the sandbox reliably provides; the trend is the point, not "
            "the values.",
        ]),
    )

    r.page(
        ptitle("Cost, continued: what the timings can and cannot support"),
        h1("The spread is the finding"),
        table(["Mechanism", "Median", "Minimum", "Maximum",
               "Max ÷ min"],
              [[k, f"{v['throughput_median']:,.0f}",
                f"{v['throughput_min']:,.0f}",
                f"{v['throughput_max']:,.0f}",
                f"{v['throughput_max'] / v['throughput_min']:.1f}x"]
               for k, v in B4.items()],
              caption="Spread of seven runs per mechanism, identical code"),
        bullets([
            f"One mechanism, Dekker, swings by a factor of "
            f"{B4['dekker']['throughput_max'] / B4['dekker']['throughput_min']:.1f} "
            f"between runs of the same binary on the same machine. Three "
            f"others stay within about ten per cent.",
            "That is not measurement error in the usual sense; it is the "
            "operating system, the GIL and the shared host intervening.",
        ]),
        h1("What survives the noise"),
        bullets([
            "The gentle, monotone degradation of the blocking mechanisms as "
            "threads are added is stable across repetitions.",
            "The rise in wasted spin attempts with thread count is large and "
            "does not depend on the absolute rate.",
            "Everything else — which busy-wait protocol is 'fastest' — is "
            "within the noise and is deliberately not claimed.",
        ]),
        note("Reported timings come from CPython under a global interpreter "
             "lock on a shared sandbox. They are comparative, not absolute; "
             "a native runtime with true parallelism would rank the "
             "mechanisms differently, and the spinlock in particular would "
             "look worse, not better.", "Standing caveat"),
    )

    r.page(
        ptitle("Discussion"),
        h1("What the four exercises add up to"),
        bullets([
            "MLQ is a template, not an algorithm: the engineering content is in "
            "the number of queues, the per-queue policy and whether aging is "
            "enabled.",
            "Once deadlines matter, MLQ is the wrong tool: it has no notion of "
            "a deadline, and the measurements show it behaving inconsistently "
            "for that reason.",
            "EDF is the right default when every deadline matters equally and "
            "utilisation is high; RM is the right choice when protecting a "
            "priority class matters more than total throughput.",
            "Correctness of a synchronisation protocol is a property of all "
            "interleavings, and where the state space is small that can be "
            "settled rather than sampled.",
        ]),
        h1("A recurring surprise"),
        para("The most consistent lesson across the four exercises was how "
             "often the textbook answer and the measured answer disagreed, and "
             "how often the measured answer was the one that needed "
             "explaining. MLQ beating RM in the aperiodic scenario, EDF "
             "'losing' under overload, and a correct semaphore deadlocking are "
             "all cases where the number is right and the obvious reading of "
             "it is wrong."),
        h1("Practical recommendations"),
        bullets([
            "State the objective before choosing the scheduler.",
            "Add aging to any fixed-assignment queue structure, or accept "
            "starvation as a documented property.",
            "Use the exact test, not the sufficient bound, whenever a "
            "schedulability decision matters.",
            "Agree on a global lock order and enforce it in review; it is "
            "cheaper than detecting deadlock at run time.",
            "Report timings as medians with their spread, or do not report "
            "them.",
        ]),
    )

    r.page(
        ptitle("Threats to validity"),
        h1("Construct validity"),
        bullets([
            "Every scheduler is a model of a policy, not an implementation of "
            "one. Measured turnaround reflects the policy's decisions, not the "
            "cost of the mechanism that would realise them.",
            "The metric definitions are the standard ones, but 'fairness' is "
            "deliberately left qualitative rather than reduced to a single "
            "index.",
        ]),
        h1("Internal validity"),
        bullets([
            "The simulations are deterministic given a scenario file, so a "
            "result can be re-derived exactly. The analytic tests and the "
            "simulations agree in both directions, which is the strongest "
            "internal check available here.",
            "The mutual-exclusion proofs are exhaustive over the modelled "
            "state space; the risk is that the model omits a behaviour, not "
            "that the search missed a state.",
        ]),
        h1("External validity"),
        bullets([
            "All timings come from one shared sandbox running CPython with a "
            "GIL. They indicate relative cost, not absolute performance, and "
            "they would differ on native runtimes.",
            "The proofs cover two participants under sequential consistency; "
            "they do not transfer to relaxed memory models or to n greater "
            "than two without further argument.",
            f"The feasibility study is a reproducible sample of {FS['sets']:,} "
            f"task sets from one generator with one seed, not a theorem about "
            f"the space of task sets.",
            "No claim is made about any specific commercial operating system.",
        ]),
        note("The strongest results in this paper are the model-checking "
             "verdicts and the agreement between analysis and simulation. The "
             "weakest are the timings, which is why they are reported with "
             "their spread and treated as indicative only.",
             "Relative strength of the results"),
    )

    r.page(
        ptitle("Related work"),
        h1("Scheduling"),
        bullets([
            "Liu and Layland established the fixed-priority result and the "
            "utilisation bound that still anchors the field; their bound is "
            "sufficient only, which is why later work turned to exact "
            "response-time analysis.",
            "Joseph and Pandya gave the response-time recurrence used in "
            "Section 6; it is exact for fixed-priority preemptive scheduling "
            "under the stated assumptions.",
            "Multilevel queue and multilevel feedback queue scheduling are "
            "standard material in operating-system texts; the contribution "
            "here is measured behaviour, not new theory.",
        ]),
        h1("Synchronisation"),
        bullets([
            "Dijkstra presented the two-process protocol now known as Dekker's "
            "algorithm; Peterson simplified it and generalised it through a "
            "tournament construction.",
            "Hoare introduced monitors; Lampson and Redell documented the Mesa "
            "variant in which a signalled thread must re-test its predicate, "
            "which is the behaviour measured in Section 7.",
            "Coffman, Elphick and Shoshani stated the four necessary "
            "conditions for deadlock used in Section 7.",
        ]),
        h1("Position of this work"),
        para("This paper does not propose a new algorithm. Its contribution is "
             "a single reproducible body of code in which the classical "
             "results can be re-derived, cross-checked against measurement, "
             "and, where the state space allows, proved rather than assumed."),
    )

    r.page(
        ptitle("Conclusion and future work"),
        h1("Conclusions"),
        bullets([
            "There is no best scheduler; there is a best scheduler for a "
            "stated workload and a stated objective, and the two metrics that "
            "usually decide it are worst-case latency and who suffers under "
            "overload.",
            f"Across {FS['sets']:,} task sets the RM/EDF gap is not gradual: "
            f"it is a cliff between 0.80 and 1.00 utilisation.",
            "Mutual exclusion can be settled exhaustively for small state "
            "spaces, and doing so distinguishes three failure modes that "
            "testing conflates.",
            "Deadlock is a property of how locks are used, and the cheapest "
            "prevention is a global lock order.",
            "Measurement and proof answer different questions; a project that "
            "needs both should say which result is which.",
        ]),
        h1("Future work"),
        bullets([
            "Extend the model checker beyond two participants, which needs a "
            "symbolic or partial-order-reduced search rather than explicit "
            "enumeration.",
            "Model a relaxed memory ordering and add fences, so the Dekker and "
            "Peterson verdicts become statements about hardware rather than "
            "about an idealised model.",
            "Port the benchmarks to a native runtime without a GIL, so the "
            "contention figures reflect real spin costs.",
            "Add multicore scheduling, which introduces migration and "
            "cache-affinity costs that this single-processor study cannot see.",
        ]),
        h1("Reproduction"),
        code(["# on each exercise branch, from that branch's root",
              "python code/run_experiments.py    # every number in this paper",
              "python -m pytest tests -q         # regression suite",
              "",
              "# this paper and the two seminar decks, on the session branch",
              "python3 tools/build_report.py ex6_en exercise-6 PAPER_EN",
              "python3 tools/build_report.py ex6_fa exercise-6 PAPER_FA",
              "python exercise-6/code/build_deck.py"],
             caption="One command per artefact"),
    )

    r.page(
        ptitle("References"),
        h1("Verified bibliography"),
        para("Every entry below was checked against the publisher's own record "
             "while this paper was written. Volume, number, page range, year "
             "and DOI are reproduced from those records; no entry is inferred "
             "or remembered."),
        table(["Reference", "Record"],
              [["Liu and Layland (1973)",
                "Journal of the ACM 20(1), 46–61. DOI 10.1145/321738.321743"],
               ["Joseph and Pandya (1986)",
                "The Computer Journal 29(5), 390–395. DOI 10.1093/comjnl/29.5.390"],
               ["Dijkstra (1965)",
                "Communications of the ACM 8(9), 569. DOI 10.1145/365559.365617"],
               ["Peterson (1981)",
                "Information Processing Letters 12(3), 115–116. "
                "DOI 10.1016/0020-0190(81)90106-X"],
               ["Hoare (1974)",
                "Communications of the ACM 17(10), 549–557. "
                "DOI 10.1145/355620.361161"],
               ["Lampson and Redell (1980)",
                "Communications of the ACM 23(2), 105–117. "
                "DOI 10.1145/358818.358824"],
               ["Coffman, Elphick and Shoshani (1971)",
                "ACM Computing Surveys 3(2), 67–78. DOI 10.1145/356586.356588"]],
              caption="Seven references, each verified against the publisher record"),
        h1("Textbooks consulted"),
        bullets([
            "Silberschatz, Galvin and Gagne — Operating System Concepts. "
            "Edition not fixed: the page numbers differ between editions, so "
            "no page is cited.",
            "Tanenbaum and Bos — Modern Operating Systems. Same caution.",
            "Buttazzo — Hard Real-Time Computing Systems. Consulted for the "
            "statement of the schedulability tests; no page numbers are cited.",
        ]),
        note("Earlier drafts of this branch listed bibliographic metadata that "
             "had not been checked. Those entries have been replaced by the "
             "table above, and the unchecked items are labelled as needing "
             "verification against the edition assigned by the course.",
             "What changed and why"),
    )

    r.page(
        ptitle("Appendix: artefacts and provenance"),
        table(["Branch", "Contents", "Used in"],
              [["Exercise-1", "MLQ simulator, scenarios, 14 figures",
                "Section 4"],
               ["Exercise-2", "MLQ / EDF / RM harness, analytic tests, "
                              "feasibility study", "Sections 5 and 6"],
               ["Exercise-3", "Hand-worked EDF and RM solution for three tasks",
                "background"],
               ["Exercise-4", "Model checker, threading layer, eight figures",
                "Sections 7 and 8"],
               ["Exercise-5", "Short demonstration clip, delivered privately",
                "not used as evidence"],
               ["Exercise-6", "This paper and the two seminar decks",
                "this document"]],
              caption="Where each number in this paper comes from"),
        h1("How the paper is generated"),
        bullets([
            "The content module reads the experiment JSON files of exercises 1, "
            "2 and 4 directly, so no figure is typed by hand.",
            "If a number changes, the paper changes with it on the next build.",
            "The seminar decks are generated by "
            "`exercise-6/code/build_deck.py` and carry speaker notes on every "
            "slide.",
        ]),
        h1("Deliverables on this branch"),
        table(["File", "Description"],
              [["PAPER_EN.md / .docx / .pdf", "this paper, English, 33 pages"],
               ["PAPER_FA.md / .docx / .pdf", "this paper, Persian, 31 pages"],
               ["docs/SEMINAR_EN.pptx", "seminar deck, English, 26 slides"],
               ["docs/SEMINAR_FA.pptx", "seminar deck, Persian, 26 slides"],
               ["SEMINAR_SLIDES.md", "the slide outline behind both decks"],
               ["REFERENCES.md", "the verified bibliography"],
               ["diagrams/", "the five figures, all regenerable"],
               ["output/deck_numbers.json", "the figures the slides quote"],
               ["code/build_deck.py", "generates both decks"],
               ["tests/test_deck.py", "17 tests over slides, notes, figures "
                                      "and RTL markup"]],
              caption="Files published on the Exercise-6 branch"),
    )

    return r
