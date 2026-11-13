# Fixed Multilevel Queue Scheduling: Design, Trade-offs, and Real-Time Alternatives
## Abstract
Multilevel Queue (MLQ) scheduling separates ready processes into fixed classes and applies queue-specific policies. This paper reviews the model, explains its behavior, and contrasts it with EDF and RM. The central finding is that MLQ is a class-based general-purpose scheduling structure, whereas EDF and RM are deadline/period-based real-time policies. Strict inter-queue priority can cause starvation, and a successful finite trace is not a schedulability proof.

## 1. Introduction
CPU scheduling mediates access to a limited processor. Workloads may include interactive, batch, and system tasks with different response and throughput needs. MLQ makes this heterogeneity explicit by separating work into queues. This simplicity comes at the cost of classification decisions and possible unfairness between classes.

## 2. System model
A process has an identifier, arrival time, CPU burst, and fixed queue assignment. The queue order is Q1>Q2>Q3. The examined educational configuration uses Round Robin with quantum two in Q1 and FCFS in Q2 and Q3. The sample assumes one processor, all arrivals at zero, positive known bursts, and zero scheduling overhead.

## 3. Algorithm
At each dispatch boundary, scan the queues in priority order. Select the first non-empty queue. Execute the head of Q1 for at most one quantum, requeueing it if unfinished. Execute a selected Q2/Q3 process to completion under the simplified model. Record the trace and calculate completion, turnaround, waiting and response metrics.

## 4. Analysis
For a fixed number of three queues, selection and deque operations are constant time. Total simulation work is linear in the number of process dispatches. Q1 fairness is bounded in terms of the finite number of peers ahead in its FIFO queue, but lower queues have no such guarantee under strict priority. Aging or reserved bandwidth can mitigate starvation but changes the policy and must be evaluated separately.

## 5. Synchronization
Shared ready queues require mutual exclusion if multiple threads modify them. Binary semaphores and monitors can protect queue invariants. Condition variables must be used with predicate loops. A combined design requires a consistent lock acquisition order. A single-threaded deterministic simulation illustrates synchronization structure but does not establish race freedom under concurrent stress.

## 6. Comparison with EDF
EDF selects the ready job with the earliest absolute deadline. Under the classical preemptive uniprocessor model with independent tasks and implicit deadlines, EDF is optimal and utilization not exceeding one is sufficient and necessary for feasibility. This result does not automatically extend to arbitrary deadlines, blocking, self-suspension, multiprocessors or overhead.

## 7. Comparison with RM
RM assigns static priorities according to task period. The Liu-Layland utilization bound is sufficient for the classic periodic task model; response-time analysis can prove additional task sets schedulable. RM is easier to implement with fixed priorities but lower-priority tasks experience interference from higher-priority tasks.

## 8. Evaluation methodology
A rigorous experiment should use the same task sets, arrival phases, execution costs, deadlines, preemption model and overhead for every policy. It should include feasible and overloaded sets, multiple random seeds, deadline-miss ratio, worst-case and average response, waiting, throughput, utilization and context-switch counts. Publish code, raw traces and test output.

## 9. Limitations
The repository's current MLQ code is an educational model, not a production OS scheduler. The sample workload is small and does not model I/O, multiple CPUs, dynamic queue assignment, or hard real-time admission control. EDF/RM comparison claims require independently implemented and tested baselines.

## 10. Conclusion
MLQ is appropriate when stable service classes and policy separation are important. EDF and RM are more directly suited to periodic/deadline-driven real-time task models. Policy choice must follow workload requirements and formal assumptions, not a universal ranking.

## References
See REFERENCES.md. Confirm publication details and citation style against the original sources before academic submission.
