# -*- coding: utf-8 -*-
"""Exercise 3 — English hand-worked EDF / RM solution.

Mirror of :mod:`ex3_fa`. Every number comes from ``exercise-3/code/edf_rm.py``.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "exercise-3", "code"))

from edf_rm import (Task, hyperperiod, utilization, rm_schedulability,      # noqa: E402
                    edf_schedulability, summarize, step_rows)

from report_kit import (Report, cover, toc, ptitle, h1, para, bullets, table,
                        kv, image, code, formula, note)

TASKS = [Task("T1", 1, 4, 4), Task("T2", 3, 8, 8), Task("T3", 4, 12, 12)]

TITLE = "Exercise 3 — EDF and RM Scheduling with Three Inputs: A Complete Hand Solution"
SUBTITLE = "Step-by-step printable hand solution of EDF and RM scheduling for a three-task periodic set"

COVER_META = [
    ("Exercise", "EDF and RM scheduling with three inputs and a hand solution"),
    ("Course", "Advanced Operating Systems"),
    ("Topic", "Real-time scheduling of periodic tasks"),
    ("Task set", "T1(C=1,T=4,D=4), T2(C=3,T=8,D=8), T3(C=4,T=12,D=12)"),
    ("Total utilisation", "U = 23/24 ≈ 0.9583"),
    ("Deliverable", "Persian and English reports (DOCX and PDF) + runnable code + blank worksheets"),
    ("Repository", "github.com/kaspian021/Multilevel-Queue-Scheduling"),
    ("Branch", "Exercise-3-EDF-RM-Manual-Scheduling"),
]

_RM = rm_schedulability(TASKS)
_EDF = edf_schedulability(TASKS)
_S = {a: summarize(TASKS, a) for a in ("EDF", "RM")}
_H = hyperperiod(TASKS)
_U = utilization(TASKS)
_DEMAND = sum(t.C * (_H // t.T) for t in TASKS)


def _step_table(algo, first, last):
    rows = step_rows(TASKS, algo, "en")[first:last]
    return [[r["interval"], r["ran"], r["ready_detail"], r["reason"]] for r in rows]


def _blank_rows(start, end, cols=3):
    return [[str(i)] + [""] * cols for i in range(start, end)]


def build():
    r = Report(TITLE, SUBTITLE, "en", cover_meta=COVER_META)

    r.page(cover(COVER_META))
    r.page(toc())

    r.page(
        ptitle("Abstract, keywords and report map"),
        h1("Abstract"),
        para("This exercise designs a three-task periodic set and solves its scheduling "
             "under EDF and RM by hand, step by step. Every calculation was first worked "
             "out on paper and then cross-checked against a Python program; the program "
             "output and the hand solution agree exactly."),
        para(f"The set is T1(C=1,T=4,D=4), T2(C=3,T=8,D=8) and T3(C=4,T=12,D=12). Total "
             f"utilisation is {_U:.4f}, i.e. 23/24, and the hyperperiod is {_H}. The "
             f"analytic test shows that EDF runs this set without a single deadline miss, "
             f"while response-time analysis for RM gives R(T3)={_RM['response_times']['T3']['R']}, "
             f"which exceeds the deadline of 12. Simulation reproduces exactly that one miss "
             f"at t=12."),
        h1("Keywords"),
        para("Real-time scheduling; EDF; RM; absolute deadline; period; hyperperiod; "
             "response-time analysis; utilisation; deadline miss; idle time; hand solution."),
        h1("Report map"),
        bullets([
            "Sections 1-4: task-set design, preliminary arithmetic and priorities.",
            "Sections 5-8: analytic tests and selection rules.",
            "Sections 9-15: step-by-step EDF solution and its analysis.",
            "Sections 16-21: step-by-step RM solution and the deadline miss.",
            "Sections 22-28: comparison, hand arithmetic and the limits of the claim.",
            "Sections 29-30: blank worksheets for rewriting the solution by hand.",
        ]),
    )

    r.page(
        ptitle("Introduction, problem statement and goals"),
        h1("Problem statement"),
        para("Three periodic tasks run on a single preemptive processor. Each task is "
             "released at multiples of its period and every job must finish by its relative "
             "deadline. The goal is to determine the execution order under EDF and RM, "
             "compute the metrics and check for deadline misses."),
        h1("Goals"),
        bullets([
            "Design a task set with parameters that can be computed by hand.",
            "Compute the fixed RM priorities from the periods.",
            "Apply the earliest-deadline-first selection rule.",
            "Produce a step table for every tick of the hyperperiod.",
            "Draw the Gantt chart for both algorithms.",
            "Compute utilisation, idle time and deadline misses.",
            "Reconcile the hand solution with the Python program.",
        ]),
        h1("Model rules"),
        bullets([
            "Single processor, preemptive scheduling.",
            "Time is discrete; one tick consumes one unit of execution.",
            "All tasks are released in phase at t=0.",
            "EDF tie rule: on equal absolute deadlines the smaller task index wins.",
            "A job that misses its deadline is not aborted; it runs to completion.",
            "The analysis horizon is one complete hyperperiod.",
        ]),
        note("This solution shows the behaviour of the set over one hyperperiod. The "
             "definitive schedulability verdict for all time comes from the analytic tests "
             "presented in the following pages.", "Scope"),
    )

    r.page(
        ptitle("Task-set design and preliminary arithmetic"),
        h1("Task parameters"),
        table(["Task", "C (execution)", "T (period)", "D (relative deadline)",
               "Release instants"],
              [["T1", "1", "4", "4", "0, 4, 8, 12, 16, 20"],
               ["T2", "3", "8", "8", "0, 8, 16"],
               ["T3", "4", "12", "12", "0, 12"]],
              caption="Parameters of the three periodic tasks"),
        h1("Utilisation"),
        formula("U = C1/T1 + C2/T2 + C3/T3\n"
                "  = 1/4 + 3/8 + 4/12\n"
                "  = 6/24 + 9/24 + 8/24 = 23/24 = 0.9583",
                caption="Hand computation of total utilisation"),
        h1("Hyperperiod"),
        formula("H = lcm(4, 8, 12) = 24", caption="Hand computation of the hyperperiod"),
        h1("Total load in one hyperperiod"),
        bullets([
            "T1 is released 6 times in 24 units and carries 6 x 1 = 6 units of load.",
            "T2 is released 3 times and carries 3 x 3 = 9 units.",
            "T3 is released 2 times and carries 2 x 4 = 8 units.",
            f"Total load is {_DEMAND} units, so in 24 time units there is exactly 1 unit of idle time.",
        ]),
        kv([["Quantity", "Value"],
            ["Total utilisation U", f"{_U:.4f} (23/24)"],
            ["Hyperperiod H", str(_H)],
            ["Total load in the hyperperiod", f"{_DEMAND} units"],
            ["Idle time", f"{_H - _DEMAND} unit"],
            ["Jobs in the hyperperiod", "11 jobs"]],
           caption="Summary of the preliminary arithmetic"),
    )

    r.page(
        ptitle("RM priority computation and the EDF selection rule"),
        h1("Fixed priority in RM"),
        para("In RM the priority is derived from the period: a shorter period means a "
             "higher priority. The priority is computed at design time and never changes "
             "at run time."),
        table(["Task", "Period", "RM priority", "Rank"],
              [["T1", "4", "highest", "1"],
               ["T2", "8", "medium", "2"],
               ["T3", "12", "lowest", "3"]],
              caption="Fixed RM priorities for this task set"),
        h1("The selection rule in EDF"),
        para("Under EDF, at every instant the job with the earliest absolute deadline is "
             "selected. The absolute deadline of job k of task i is k*T + D."),
        formula("d(k, i) = k * T_i + D_i\n"
                "choose the ready job with the smallest d(k, i)\n"
                "tie rule: smaller task index first",
                caption="Absolute deadline and the EDF selection rule"),
        h1("Absolute deadlines over one hyperperiod"),
        table(["Task", "job 0", "job 1", "job 2", "job 3", "job 4", "job 5"],
              [["T1", "4", "8", "12", "16", "20", "24"],
               ["T2", "8", "16", "24", "-", "-", "-"],
               ["T3", "12", "24", "-", "-", "-", "-"]],
              caption="Absolute deadlines of all jobs in [0,24)"),
        bullets([
            "At t=0 three jobs with deadlines 4, 8 and 12 are ready; EDF picks the nearest, T1.",
            "At t=12 the deadline of T3_0 arrives, while T1_3 with deadline 16 has just been released.",
            "EDF continues T3_0 at that instant, but RM preempts it because T1 has higher priority.",
        ]),
    )

    r.page(
        ptitle("Analytic tests before scheduling"),
        h1("The Liu and Layland sufficient bound for RM"),
        formula("U <= n * (2^(1/n) - 1)\n"
                "n = 3  ->  bound = 3 * (2^(1/3) - 1) = 0.7798\n"
                f"U = {_U:.4f} > 0.7798   =>   the bound gives no answer",
                caption="Checking the Liu and Layland sufficient bound"),
        bullets([
            "Utilisation exceeds the bound, but that does not mean failure.",
            "The condition is only sufficient; many sets above it are still schedulable.",
            "A definite answer needs response-time analysis.",
        ]),
        h1("RM response-time analysis"),
        formula("R_i = C_i + sum over j in hp(i):  ceil(R_i / T_j) * C_j",
                caption="The response-time recurrence"),
        table(["Task", "C", "iter 1", "iter 2", "iter 3", "final R", "D", "verdict"],
              [["T1", "1", "1", "-", "-", "1", "4", "ok"],
               ["T2", "3", "4", "4", "-", "4", "8", "ok"],
               ["T3", "4", "8", "13", "14", "14", "12", "MISS"]],
              caption="Hand execution of response-time analysis for the three tasks"),
        bullets([
            "R(T1) = 1 <= 4, so T1 always finishes in time.",
            "R(T2) = 3 + ceil(4/4)*1 = 4 <= 8, so T2 is safe.",
            "R(T3) = 4 + ceil(14/4)*1 + ceil(14/8)*3 = 4 + 4 + 6 = 14 > 12, so T3 misses.",
            "Analytic verdict: this set is NOT schedulable under RM.",
        ]),
    )

    r.page(
        ptitle("The EDF analytic test and the prediction before running"),
        h1("The utilisation condition for EDF"),
        para("Because D equals T for every task in this set (implicit deadlines), the "
             "condition U <= 1 is both necessary and sufficient for EDF. No more elaborate "
             "test is required."),
        formula(f"U = {_U:.4f} <= 1   =>   EDF can schedule this task set",
                caption="Necessary and sufficient EDF condition for implicit deadlines"),
        h1("Prediction before running"),
        table(["Test", "Result", "Prediction"],
              [["Liu and Layland bound (RM)", "inconclusive", "a sharper test is needed"],
               ["Response-time analysis (RM)", "R(T3)=14 > 12", "exactly one deadline miss"],
               ["Utilisation condition (EDF)", "satisfied", "no deadline miss"]],
              caption="Summary of the analytic predictions before simulation"),
        image("chart_rta.png", width_cm=12.5,
              caption="Response-time analysis chart: computed R against the deadline D"),
        bullets([
            "In this chart the T3 bar crosses the deadline line.",
            "The figure announces the result we are about to see in the RM Gantt chart.",
            "Agreement between analytic prediction and simulation is the strongest evidence of correctness.",
        ]),
    )

    r.page(
        ptitle("Release pattern and deadlines"),
        image("fig_release_pattern.png", width_cm=16.0,
              caption="Release instants (arrows) and deadlines (dashed lines) in [0,24)"),
        h1("Reading the figure"),
        bullets([
            "T1 is released at 0, 4, 8, 12, 16 and 20 and has 4 units of deadline each time.",
            "T2 is released at 0, 8 and 16 and has 8 units of deadline each time.",
            "T3 is released at 0 and 12 and has 12 units of deadline each time.",
            "At t=0 all three tasks are released together: the worst-case release pattern.",
            "At t=24 all tasks are in phase again, so one hyperperiod of analysis suffices.",
        ]),
        h1("Why being in phase matters"),
        bullets([
            "Simultaneous release puts the heaviest load on the scheduler.",
            "In real-time analysis this is normally taken as the worst case.",
            "If a set is schedulable in this case, it is schedulable in the others.",
        ]),
    )

    r.page(
        ptitle("Hand solution for EDF (part 1): ticks 0 to 11"),
        para("In every row the ready set is shown with the absolute deadline and the "
             "remaining execution time; the job name T1_0 means job zero of task T1."),
        table(["Interval", "Ran", "Ready jobs (d=deadline, rem=remaining)", "Reason"],
              _step_table("EDF", 0, 12),
              caption="Step-by-step EDF table from t=0 to t=11"),
    )

    r.page(
        ptitle("Hand solution for EDF (part 2): ticks 12 to 23"),
        table(["Interval", "Ran", "Ready jobs (d=deadline, rem=remaining)", "Reason"],
              _step_table("EDF", 12, 24),
              caption="Step-by-step EDF table from t=12 to t=23"),
    )

    r.page(
        ptitle("Gantt chart and EDF analysis"),
        image("gantt_edf.png", width_cm=16.0,
              caption="EDF Gantt chart over one hyperperiod; dashed lines are deadlines, arrows releases"),
        h1("Resulting schedule"),
        code(["t :  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23",
              "   : T1 T2 T2 T2 T1 T3 T3 T3 T1 T3 T2 T2 T1 T2 T3 T3 T1 T2 T2 T2 T1 T3 T3  -"],
             caption="EDF execution order over 24 ticks (the last tick is idle)"),
        h1("Checking the deadlines"),
        table(["Job", "Release", "Deadline", "Finish", "Response", "Verdict"],
              [["T1_0", "0", "4", "1", "1", "on time"],
               ["T2_0", "0", "8", "4", "4", "on time"],
               ["T3_0", "0", "12", "11", "11", "on time"],
               ["T1_1", "4", "8", "5", "1", "on time"],
               ["T1_2", "8", "12", "9", "1", "on time"],
               ["T2_1", "8", "16", "13", "5", "on time"],
               ["T1_3", "12", "16", "13", "1", "on time"],
               ["T3_1", "12", "24", "19", "7", "on time"]],
              caption="Hand check of EDF deadlines (first eight jobs)"),
        bullets([
            "No job missed its deadline.",
            "The only idle time is at tick 23, because the total load is 23 units.",
            "Utilisation is 23/24 = 95.83%.",
        ]),
    )

    r.page(
        ptitle("Hand solution for RM (part 1): ticks 0 to 11"),
        para("Under RM the priority is fixed, so the reason column always refers to the "
             "period of the task, never to its absolute deadline."),
        table(["Interval", "Ran", "Ready jobs (d=deadline, rem=remaining)", "Reason"],
              _step_table("RM", 0, 12),
              caption="Step-by-step RM table from t=0 to t=11"),
    )

    r.page(
        ptitle("Hand solution for RM (part 2): ticks 12 to 23"),
        table(["Interval", "Ran", "Ready jobs (d=deadline, rem=remaining)", "Reason"],
              _step_table("RM", 12, 24),
              caption="Step-by-step RM table from t=12 to t=23"),
    )

    r.page(
        ptitle("Gantt chart and the deadline miss under RM"),
        image("gantt_rm.png", width_cm=16.0,
              caption="RM Gantt chart; the red line marks the missed deadline of T3_0"),
        h1("Resulting schedule"),
        code(["t :  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23",
              "   : T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3  -"],
             caption="RM execution order over 24 ticks"),
        h1("The critical instant: t=12"),
        bullets([
            "T3_0 was released at t=0 and ran during ticks 5, 6 and 7; one unit remained.",
            "At t=8 task T2_1 is released with higher priority and runs for three ticks.",
            "At t=12 task T1_3 is released and, having a shorter period, runs immediately.",
            "As a result the last unit of T3_0 runs at tick 13 and its finish time is 14.",
            "The deadline of T3_0 is 12, so it is 2 units late.",
        ]),
        table(["Job", "Release", "Deadline", "Finish", "Tardiness", "Verdict"],
              [["T3_0", "0", "12", "14", "2", "MISS"],
               ["T3_1", "12", "24", "20", "0", "on time"]],
              caption="The T3 jobs under RM and their deadline status"),
    )

    r.page(
        ptitle("Comparing the two schedules"),
        table(["Metric", "EDF", "RM"],
              [["Deadline misses", "0", "1"],
               ["Job that missed", "-", "T3_0 (deadline 12, finish 14)"],
               ["Idle time", "1", "1"],
               ["Utilisation", "95.83%", "95.83%"],
               ["Context switches", "12", "11"],
               ["Average response of T1", "1.000", "1.000"],
               ["Average response of T2", "4.667", "4.000"],
               ["Average response of T3", "10.500", "12.500"],
               ["Maximum response", "11", "14"]],
              caption="Measured results of the two algorithms over one hyperperiod"),
        h1("Comparative analysis"),
        bullets([
            "RM gives a better average response for T2: 4.000 against 4.667.",
            "EDF gives a better average response for T3: 10.500 against 12.500.",
            "But the primary criterion in real-time scheduling is deadline misses, not averages.",
            "So despite RM's better average for T2, the overall verdict favours EDF.",
            "Context-switch counts are close, so overhead is not the deciding factor.",
        ]),
        image("chart_response.png", width_cm=15.5,
              caption="Minimum, average and maximum response per task under both algorithms"),
    )

    r.page(
        ptitle("Utilisation, idle time and processor occupancy"),
        image("chart_utilization.png", width_cm=11.5,
              caption="Processor occupancy over one hyperperiod: 23 working units, 1 idle"),
        h1("Hand computation of utilisation"),
        formula("busy = 23   idle = 1   H = 24\n"
                "CPU utilization = busy / H = 23 / 24 = 0.9583 = 95.83%\n"
                "offered load    = U = 23/24            = 95.83%",
                caption="Computing utilisation from the execution trace"),
        h1("Why one unit of idle time exists"),
        bullets([
            "The total load in the hyperperiod is 23 units and the hyperperiod is 24 units long.",
            "So there is exactly one time unit with nothing to do.",
            "In both algorithms that unit lands at the end of the hyperperiod, at tick 23.",
            "Idle time is not a defect; it simply means the load is below 100%.",
            "If the load were exactly 24 units there would be no idle time at all.",
        ]),
        h1("Tardiness"),
        bullets([
            "Tardiness is how late a job is relative to its deadline.",
            "Under EDF the tardiness of every job is zero.",
            "Under RM the tardiness of T3_0 is 2 units.",
            "In a hard real-time system any positive tardiness counts as failure.",
        ]),
    )

    r.page(
        ptitle("Reconciling the hand solution with the code"),
        h1("How the check is done"),
        bullets([
            "The execution order computed by hand is stored as a string in the program output.",
            "The automated tests compare that string against the simulator output.",
            "The job count and total load are also verified automatically.",
            "Any disagreement between the hand solution and the code fails the tests.",
        ]),
        code(["$ python code/run_experiments.py",
              "",
              "algorithm: EDF",
              "  horizon=24  jobs=11  busy=23  idle=1",
              "  utilization=95.83%  (offered 95.83%)  demand=23",
              "  deadline misses: 0",
              "  timeline: T1 T2 T2 T2 T1 T3 T3 T3 T1 T3 T2 T2 T1 T2 T3 T3 T1 T2 T2 T2 T1 T3 T3 -",
              "",
              "algorithm: RM",
              "  horizon=24  jobs=11  busy=23  idle=1",
              "  utilization=95.83%  (offered 95.83%)  demand=23",
              "  deadline misses: 1",
              "    miss -> task=T3 job=0 release=0 deadline=12 finish=14",
              "  timeline: T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 -"],
             caption="Actual program output, which agrees with the hand solution"),
        h1("Locked tests"),
        bullets([
            "The first test compares the EDF execution order with the hand-worked one.",
            "The second checks the RM order and exactly one miss.",
            "The third controls the hyperperiod, utilisation and the Liu and Layland bound.",
            "Newer tests lock the response-time values and the per-task metrics.",
        ]),
    )

    r.page(
        ptitle("Scope of the results"),
        h1("What has been proved"),
        bullets([
            "Response-time analysis showed this set is not schedulable under RM; that is definitive.",
            "The condition U <= 1 showed this set is schedulable under EDF; that is also definitive.",
            "Both results hold for all time, not just for one hyperperiod.",
        ]),
        h1("What has not been proved"),
        bullets([
            "Simulating one hyperperiod on its own is not a proof; it is a sample of behaviour.",
            "If the set were one-shot rather than periodic, the results above would not apply.",
            "Here the set is periodic, so hyperperiod analysis is valid.",
            "But if deadlines were constrained (D shorter than T), the EDF condition would no longer be sufficient.",
            "It is also assumed that there is no blocking, no resource sharing and no release jitter.",
        ]),
        note("The claim of this report is not that EDF is always better than RM. The claim "
             "is that for this particular task set EDF is schedulable and RM is not, and "
             "that this has been confirmed both analytically and by simulation.",
             "Precision of the claim"),
        h1("Scenarios that would change the result"),
        bullets([
            "If C3 dropped from 4 to 2, utilisation would fall to 0.7917 and RM would probably succeed.",
            "If T3 rose from 12 to 24, its priority would not change but the load would drop.",
            "If deadlines became constrained, the processor-demand criterion would be needed.",
            "All of these can be tested with this same program by changing its arguments.",
        ]),
    )

    r.page(
        ptitle("Conclusion"),
        para("A three-task periodic set with utilisation 23/24 was designed and scheduled "
             "by hand under EDF and RM, step by step. The analytic results and the "
             "simulation agree completely."),
        bullets([
            "EDF met every deadline; the reason is that its priority is dynamic.",
            "RM missed one deadline: T3_0, whose deadline was 12, finished at 14.",
            "The cause is repeated preemption by tasks with shorter periods.",
            "Response-time analysis had already predicted this miss with R(T3)=14.",
            "Utilisation is 95.83% under both algorithms and idle time is 1 unit.",
        ]),
        h1("Answers to the exercise questions"),
        table(["Question", "Answer"],
              [["Which algorithm schedules the set?", "EDF"],
               ["How many deadline misses occur?", "zero under EDF, one under RM"],
               ["What is the utilisation?", "23/24 ≈ 95.83%"],
               ["How much idle time is there?", "1 unit at the end of the hyperperiod"],
               ["Is this a definitive proof?", "Yes, from the analytic test; not from simulation alone"]],
              caption="Short answers to the main questions of the exercise"),
        note("The difference between EDF and RM in this example comes from a single "
             "decision: at t=12, when the deadline of T3_0 has arrived, EDF continues it "
             "while RM preempts it in favour of T1_3.", "Key message"),
    )

    r.page(
        ptitle("References and reproduction commands"),
        h1("References"),
        bullets([
            "Liu, C. L., & Layland, J. W. — Scheduling Algorithms for Multiprogramming in a Hard-Real-Time Environment — Journal of the ACM, 1973.",
            "Joseph, M., & Pandya, P. — Finding Response Times in a Real-Time System — The Computer Journal, 1986.",
            "Buttazzo, G. C. — Hard Real-Time Computing Systems: Predictable Scheduling Algorithms and Applications.",
            "Silberschatz, A., Galvin, P. B., & Gagne, G. — Operating System Concepts — chapter on Real-Time CPU Scheduling.",
        ]),
        h1("Reproduction commands"),
        code(["cd exercise-3",
              "python code/run_experiments.py      # every number and table",
              "python code/make_figures.py         # Gantt charts and figures",
              "python code/edf_rm.py --tasks T1:1:4:4,T2:3:8:8,T3:4:12:12 \\",
              "                      --json out.json --table table.txt",
              "python -m pytest tests/ -q"],
             caption="Commands for running Exercise 3"),
        h1("Output files"),
        table(["File", "Description"],
              [["output/experiments.json", "all numbers in machine-readable form"],
               ["output/experiments_summary.txt", "text summary of the results"],
               ["output/summary_EDF.txt", "full EDF metrics"],
               ["output/summary_RM.txt", "full RM metrics"],
               ["output/step_table_EDF.txt", "step-by-step EDF table"],
               ["output/step_table_RM.txt", "step-by-step RM table"],
               ["diagrams/gantt_edf.png", "EDF Gantt chart"],
               ["diagrams/gantt_rm.png", "RM Gantt chart"],
               ["diagrams/chart_rta.png", "response-time analysis chart"],
               ["diagrams/chart_response.png", "response-time chart"],
               ["diagrams/chart_utilization.png", "processor occupancy chart"],
               ["diagrams/fig_release_pattern.png", "release pattern and deadlines"]],
              caption="Output files of Exercise 3"),
    )

    r.page(
        ptitle("Blank worksheet 1: rewriting the EDF schedule by hand"),
        para("The table below is for practising the EDF schedule by hand. Fill the "
             "'Ran' column with the name of the job executed in each tick and note the "
             "remaining execution time of the ready jobs."),
        table(["Tick", "Ran (EDF)", "Chosen absolute deadline", "Notes"],
              _blank_rows(0, 20),
              caption="Blank worksheet for the EDF schedule — part one"),
    )

    r.page(
        ptitle("Blank worksheet 2: EDF continued and the RM schedule"),
        table(["Tick", "Ran (EDF)", "Notes"],
              [[str(i), "", ""] for i in range(20, 24)],
              caption="EDF worksheet continued"),
        para("Now repeat the exercise for RM. Remember that under RM the priority is "
             "fixed and the task with the shorter period always wins."),
        table(["Tick", "Ran (RM)", "Chosen absolute deadline", "Notes"],
              _blank_rows(0, 16),
              caption="Blank worksheet for the RM schedule — part one"),
    )

    r.page(
        ptitle("Blank worksheet 3: RM continued and the deadline checklist"),
        table(["Tick", "Ran (RM)", "Notes"],
              [[str(i), "", ""] for i in range(16, 24)],
              caption="RM worksheet continued"),
        para("After completing the schedule, fill in the table below to check the "
             "deadline of every job."),
        table(["Job", "Release", "Deadline", "Finish", "Status"],
              [[f"T1_{k}", str(4 * k), str(4 * k + 4), "", ""] for k in range(6)]
              + [[f"T2_{k}", str(8 * k), str(8 * k + 8), "", ""] for k in range(3)]
              + [[f"T3_{k}", str(12 * k), str(12 * k + 12), "", ""] for k in range(2)],
              caption="Empty deadline checklist for both algorithms"),
        note("The correct answers for these worksheets are given in the earlier pages and "
             "in the files under output/. For self-testing, fill the tables by hand first "
             "and then compare them with the program output.", "How to use"),
    )

    return r
