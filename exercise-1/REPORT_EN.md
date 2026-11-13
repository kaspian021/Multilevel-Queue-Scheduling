# Multilevel Queue Scheduling (MLQ): Technical Report
## 1. Abstract
Multilevel Queue scheduling partitions the ready workload into distinct queues. Each queue represents a class of processes and has an associated scheduling policy. A scheduler first selects a queue according to inter-queue priority and then selects a process according to the policy inside that queue. This report describes the fixed-queue MLQ variant represented in this repository and separates it from Multilevel Feedback Queue (MLFQ), which dynamically changes process priority or queue membership.

## 2. Problem definition
A CPU scheduler decides which ready process receives the processor next. Workloads differ: interactive jobs benefit from short response times, batch jobs benefit from throughput, and periodic real-time tasks need deadline-aware decisions. A single policy may not satisfy every class. MLQ addresses this by separating classes and applying a policy per queue. It does not automatically make the system real-time: deadlines, admission control, worst-case execution times, and schedulability analysis must be added for that purpose.

## 3. Model and notation
Let P={p1,...,pn}. Each process pi has arrival time ai, CPU burst bi>0, fixed queue qi∈{1,2,3}, and remaining service ri. Queue rank is Q1 highest, Q3 lowest. The repository's synchronization exercise uses quantum q=2 for Q1 and FCFS for Q2 and Q3. All sample jobs arrive at time zero. A dispatch decision selects the highest-priority non-empty queue. Q1 receives at most q units per turn; unfinished work returns to the tail of Q1. Q2 and Q3 run their selected job to completion in the simplified exercise.

## 4. Fixed MLQ versus MLFQ
In MLQ, queue membership is fixed by classification or configuration. In MLFQ, feedback rules may promote or demote a process based on observed behavior, CPU usage, or waiting time. The two algorithms are not synonyms. A static MLQ can starve low-priority queues under sustained high-priority load. MLFQ may mitigate this with aging or periodic boosts, but those mechanisms must be explicitly implemented.

## 5. Scheduling procedure
The scheduler validates process identifiers, queue numbers, and positive bursts. It inserts each process in its assigned FIFO queue. At each dispatch boundary, it scans Q1, Q2, then Q3. It selects the first non-empty queue. If Q1 is selected, it executes the head process for min(remaining, quantum); if Q2 or Q3 is selected, the educational model executes the head process to completion. The scheduler records start and finish times, remaining burst, and completion time. The process is requeued only if its Q1 quantum expires before completion.

## 6. Correctness properties
**Queue selection:** at every dispatch boundary, the selected queue is the highest-ranked non-empty queue, because the selection scan checks queues in strict priority order.
**Within-Q1 fairness:** with a finite quantum and FIFO requeueing, each continuously ready Q1 process receives a turn after at most the other currently queued Q1 processes have received one turn, assuming finite dispatch overhead and no arrivals inserted ahead of it.
**Completion:** if bursts are finite, service is not lost, and the scheduler continues dispatching, every process eventually completes provided it is not permanently prevented from receiving service by higher-priority arrivals.
**Limitation:** the last condition is not guaranteed for Q2 and Q3 under an unbounded stream of higher-priority work.

## 7. Complexity
Scanning three queues is O(1) because the number of queues is fixed. Enqueue and dequeue operations on a deque are O(1). For n processes and total number of Q1 slices s, simulation time is O(n+s), excluding rendering and output. If the number of priority queues is generalized to k and scanned linearly, selection is O(k) per dispatch; a priority bitmap or heap can alter this cost but may complicate dynamic readiness.

## 8. Performance measures
- Completion time: absolute time at which a process finishes.
- Turnaround: completion minus arrival.
- Waiting: turnaround minus CPU service, under the single-burst model.
- Response: first start minus arrival.
- Throughput: completed processes divided by elapsed time.
- CPU utilization: busy time divided by observation interval.
- Starvation: indefinite postponement despite remaining ready.
- Context-switch overhead: time spent changing execution context; omitted from the simple simulator unless explicitly modeled.

## 9. Worked example
Take P1(Q1, burst 5), P2(Q1, burst 3), P3(Q2, burst 4), P4(Q2, burst 2), P5(Q3, burst 3), with Q1 quantum 2 and all arrivals at 0. The trace is:
`P1 0–2; P2 2–4; P1 4–6; P2 6–7; P1 7–8; P3 8–12; P4 12–14; P5 14–17`.
Q1 is exhausted before Q2 starts; Q2 is exhausted before Q3 starts. Completion/turnaround/waiting values are P1=(8,8,3), P2=(7,7,4), P3=(12,12,8), P4=(14,14,12), P5=(17,17,14). These values assume zero arrival times and no overhead.

## 10. Starvation and mitigation
Strict priority can starve lower queues. Aging can gradually raise a process's priority, but that changes fixed MLQ semantics and should be described as an extension. Weighted service, periodic priority boosts, or a bounded share for lower queues can also reduce starvation. Any mitigation changes response-time and predictability properties and must be tested under adversarial arrivals.

## 11. Synchronization considerations
When multiple threads can add, remove, or inspect ready queues, queue state is shared mutable state. A semaphore can provide mutual exclusion. A monitor encapsulates shared state behind synchronized operations and may use condition variables to wait for a predicate. Correct condition-variable usage requires a predicate loop, not a one-time check. A combined semaphore/monitor design must document lock ordering to avoid deadlock. The current teaching simulator is deterministic and single-dispatcher; identical traces across synchronization modes do not constitute a stress test of concurrent correctness.

## 12. Limitations and future work
The current model omits I/O blocking, multiple CPUs, dynamic arrivals in its fixed example, context-switch costs, priority inheritance, and formal worst-case response-time analysis. Future experiments should add arrival streams, overhead, starvation metrics, randomized workloads with fixed seeds, concurrency stress tests, and comparison baselines under identical workloads.

## 13. Conclusion
MLQ is useful when workloads can be classified into stable service classes. Its strengths are policy separation and predictable queue hierarchy. Its main risk is starvation under strict priority. The implementation's assumptions must be stated alongside every result; the algorithm should not be presented as an EDF/RM-equivalent real-time scheduler.
