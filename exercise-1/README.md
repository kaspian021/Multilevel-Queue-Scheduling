# Exercise 1 — Multilevel Queue Scheduling (MLQ)
**Bilingual study pack | بسته آموزشی دوزبانه**

This branch documents the repository's actual algorithm, not a generic scheduler. The implementation in the base project assigns each job permanently to Q1, Q2, or Q3, then executes queues in strict priority order. Within the original implementation jobs are run sequentially; the synchronization extension uses Q1 Round Robin (quantum 2), Q2 FCFS, and Q3 FCFS. These are distinct configurations and must not be conflated.

## Deliverables / محتویات
- [English report](REPORT_EN.md)
- [گزارش فارسی](REPORT_FA.md)
- Flowchart and pseudocode below.
- Figures are reproducible using Mermaid; render the diagrams in GitHub or export them for a final PDF.

## Algorithm contract
| Property | Definition |
|---|---|
| Queue model | Fixed Multilevel Queue (MLQ), not MLFQ |
| Queue priority | Q1 > Q2 > Q3 |
| Queue assignment | Static; a process does not migrate |
| Q1 policy in the synchronization exercise | Round Robin, quantum = 2 |
| Q2 / Q3 policy in that exercise | FCFS |
| Preemption | At dispatch boundaries; a higher queue is selected before the next lower-queue dispatch |
| Arrival assumption in sample | All processes arrive at time 0 |
| Workload model | Known positive CPU burst values |
| Guarantee | No hard real-time deadline guarantee |

## Flowchart
```mermaid
flowchart TD
 A([Start]) --> B[Read process ID, queue, burst]
 B --> C{Input valid?}
 C -- No --> X[Report input error] --> Z([End])
 C -- Yes --> D[Insert process in its fixed queue]
 D --> E{Any ready process?}
 E -- No --> H[Finish and calculate metrics] --> Z
 E -- Yes --> F[Choose highest-priority non-empty queue]
 F --> G{Selected queue is Q1?}
 G -- Yes --> I[Run min(remaining, quantum)]
 G -- No --> J[Run selected FCFS process to completion]
 I --> K[Update remaining burst; requeue if unfinished]
 J --> L[Mark process complete]
 K --> E
 L --> E
```

## Pseudocode
```text
MLQ(processes):
    Q1, Q2, Q3 = empty FIFO queues
    for each process p:
        validate p.queue in {1,2,3} and p.burst > 0
        append p to its fixed queue

    time = 0
    while at least one queue is non-empty:
        q = first non-empty queue in [Q1,Q2,Q3]
        p = pop_front(q)
        if q == Q1:
            run_time = min(p.remaining, quantum)
        else:
            run_time = p.remaining
        execute p for run_time
        time += run_time
        if p.remaining > 0:
            append p to the tail of q
        else:
            record completion[p] = time
    calculate waiting and turnaround metrics
```

## Reproducibility
From the repository root:
```bash
python exercise-5/mlq_sync_demo.py --all --gantt exercise-5/gantt.svg
python -m unittest discover -s exercise-5 -p 'test_*.py' -v
```
The command and tests refer to the existing synchronization branch layout; this branch is a documentation branch based on the repository's default branch. For an exact snapshot, merge or cherry-pick the implementation branch first.

## Scope and academic integrity
This is an explanatory report and reproducible diagram source. It is not evidence that an external AI tool (including Claude) was used. No tool-use claim is made. Page count depends on the final PDF layout; this Markdown source should be expanded and typeset before claiming a 40-page submission. The instructor's formatting rules and the exact assigned variant should be checked before final submission.
