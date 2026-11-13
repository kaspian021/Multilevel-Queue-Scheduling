# Seminar Presentation — Slide Outline
## Slide 1 — Title
Fixed Multilevel Queue Scheduling: Design and Comparison with EDF/RM
## Slide 2 — Motivation
Different workload classes have different response and throughput requirements.
## Slide 3 — MLQ model
Fixed queues, queue priority, per-queue policy; distinguish MLQ from MLFQ.
## Slide 4 — Algorithm flow
Input validation → enqueue → highest-priority non-empty queue → dispatch → metrics.
## Slide 5 — Worked MLQ trace
P1/P2 in Q1 (RR q=2), P3/P4 in Q2 (FCFS), P5 in Q3 (FCFS).
## Slide 6 — Synchronization
Semaphore, monitor, and combined guard; explain critical-section invariant.
## Slide 7 — Starvation
Strict priority can starve lower queues; discuss aging and reserved shares.
## Slide 8 — EDF
Dynamic priority by earliest absolute deadline; state classical assumptions.
## Slide 9 — RM
Static priority by shorter period; utilization bound and response-time analysis.
## Slide 10 — Comparative table
Policy, priority basis, deadline awareness, starvation/overload behavior.
## Slide 11 — Experimental method
Identical workloads, overhead assumptions, trace collection, repeatable seeds.
## Slide 12 — Conclusion
No universal winner; select based on workload and guarantees required.
## Speaker note
Do not claim the sample MLQ trace is a real-time guarantee. Distinguish hand examples from measured experiments and theoretical schedulability results.
