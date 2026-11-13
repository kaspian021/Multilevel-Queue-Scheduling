# Exercise 3 — Manual Scheduling of EDF and RM
**Three jobs, step-by-step paper-style solution.**

## Task set
All jobs are released at t=0. For the EDF example, the jobs have absolute deadlines shown below. For the RM example, periods define fixed priorities.

| Job | Execution C | EDF relative deadline D | RM period T |
|---|---:|---:|---:|
| A | 3 | 7 | 4 |
| B | 2 | 4 | 6 |
| C | 1 | 5 | 8 |

Total execution = 6 time units. No context-switch cost; single preemptive processor. Since all three jobs are released at zero and no new jobs arrive in this one-shot illustration, no preemption is needed after the initial choice. This is a hand-worked priority-order illustration, not a periodic feasibility proof.

## EDF hand calculation
At t=0, deadlines are B=4, C=5, A=7. Choose B (earliest), run 0–2. Remaining ready jobs: C deadline 5, A deadline 7. Run C 2–3. Run A 3–6. All complete before their deadlines.

Gantt:
```text
0       2   3       6
|   B   | C |   A   |
```

| Job | Start | Finish | Completion | Turnaround | Waiting | Deadline | Result |
|---|---:|---:|---:|---:|---:|---:|---|
| A | 3 | 6 | 6 | 6 | 3 | 7 | on time |
| B | 0 | 2 | 2 | 2 | 0 | 4 | on time |
| C | 2 | 3 | 3 | 3 | 2 | 5 | on time |

## RM hand calculation
RM priority is inversely related to period: A(T=4) has highest priority, B(T=6) second, C(T=8) third. Run A 0–3, B 3–5, C 5–6.

Gantt:
```text
0       3     5   6
|   A   |  B  | C |
```

| Job | Priority | Start | Finish | Completion | Turnaround | Waiting |
|---|---:|---:|---:|---:|---:|---:|
| A | 1 | 0 | 3 | 3 | 3 | 0 |
| B | 2 | 3 | 5 | 5 | 5 | 3 |
| C | 3 | 5 | 6 | 6 | 6 | 5 |

## Interpretation
EDF minimizes the current absolute deadline; RM uses a static priority assigned from period. The different orders are expected. These examples use one job per task only. To establish periodic schedulability, release subsequent jobs at multiples of T, define deadlines, and analyze the full hyperperiod or use a valid schedulability test. An actual handwritten-paper photo is not fabricated here; this Markdown contains the transparent calculation and Gantt diagrams and can be printed or exported to PDF.
