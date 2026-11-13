# Comparative Study: MLQ, EDF, and RM
## Abstract
This report compares fixed Multilevel Queue scheduling with two canonical real-time policies: Earliest Deadline First (EDF) and Rate Monotonic (RM). The policies solve related but different problems. MLQ classifies work into fixed service classes; EDF prioritizes the job with the nearest absolute deadline; RM assigns fixed priority according to task period. A fair evaluation must use the same workload and explicitly state the assumptions.

## 1. Policy definitions
**MLQ:** the ready set is partitioned into fixed queues. Inter-queue priority chooses the highest non-empty queue. The repository's exercise uses Q1 Round Robin with quantum 2, Q2 FCFS and Q3 FCFS. Queue membership does not change. No deadline is used in selection.
**EDF:** at each dispatch point, select the ready job with minimum absolute deadline. Priorities are dynamic because deadlines advance from release to release.
**RM:** assign each periodic task a static priority; shorter period means higher priority. For tasks with distinct periods, the priority order is fixed.

## 2. Assumptions behind real-time theory
Classic uniprocessor results assume independent periodic or sporadic tasks, known execution costs, preemptive scheduling, negligible overhead, and a defined deadline model. EDF's U≤1 optimality statement is for preemptive independent tasks with implicit deadlines (D=T) on one processor. RM's utilization bound U≤n(2^(1/n)-1) is a sufficient schedulability test for the classic task model, not a necessary condition. A task set above the bound may still be schedulable; exact response-time analysis can be needed. These statements must not be applied blindly to arbitrary deadlines, self-suspension, blocking, multiprocessors, or substantial context-switch costs.

## 3. Starvation
Strict-priority MLQ can starve Q2/Q3 if higher-priority work is continuously available. Q1's RR policy gives bounded turns among its own continuously ready processes but does not protect lower queues. EDF does not have the same fixed queue starvation mechanism, but overload can cause missed deadlines and jobs with later deadlines may be postponed repeatedly. RM can delay low-priority tasks behind higher-priority periodic tasks; response-time analysis determines whether deadlines are met. None of these policies should be described as starvation-free without a precise workload and definition.

## 4. Fairness and predictability
MLQ offers class isolation and simple policy selection, but strict priority is unfair across queues. RR within Q1 improves fairness only within that queue. EDF is deadline-oriented and can be optimal under its classical assumptions, but dynamic priority changes complicate analysis and overload behavior. RM is static and easier to reason about; its fixed priority order may leave processor capacity unused under a sufficient-bound test even when a task set is actually schedulable.

## 5. Response time and waiting
For MLQ, response depends strongly on queue assignment and the work in all higher-priority queues. For RM, worst-case response-time recurrence for task i in the simple preemptive independent model is R_i = C_i + Σ_{j∈hp(i)} ceil(R_i/T_j) C_j; iterate to a fixed point and compare with D_i. Blocking and overhead add terms. EDF analysis differs and depends on deadline assumptions; utilization alone is not a complete response-time report for arbitrary task models.

## 6. Deadline misses
MLQ does not inspect deadlines and therefore cannot promise deadline satisfaction. EDF's earliest-deadline rule is optimal for the classic preemptive uniprocessor implicit-deadline model; under overload, missed deadlines remain possible. RM uses fixed priorities and can be tested with sufficient utilization bounds or response-time analysis. Deadline-miss ratio must be measured on the same finite trace, but a zero-miss experiment is not a proof.

## 7. Utilization and throughput
Utilization is U=Σ(C_i/T_i) for periodic tasks. EDF can feasibly schedule U≤1 in the classic model. RM's sufficient bound is lower for n>1, although exact tests may accept more. MLQ has no universal utilization bound because the policy and queue assignment do not encode periodic deadlines. Throughput depends on overhead, bursts, and workload mix; it is not interchangeable with schedulability.

## 8. Worked three-task illustration
Consider three one-shot jobs released at time 0 with execution times and relative deadlines: A(C=3,D=7), B(C=2,D=4), C(C=1,D=5). EDF orders by deadline: B [0,2), C [2,3), A [3,6); all finish before deadlines. For an RM illustration, assign periods T_A=4, T_B=6, T_C=8, with execution costs as above. RM priority is A>B>C, so A [0,3), B [3,5), C [5,6). This small illustration shows different priority rules; it is not a periodic schedulability proof because only one job of each task is shown.

## 9. Comparative matrix
| Criterion | Fixed MLQ | EDF | RM |
|---|---|---|---|
| Priority | Queue hierarchy | Dynamic absolute deadline | Static period |
| Deadline awareness | No, unless extended | Direct | Indirect via period |
| Starvation risk | Lower queues under strict priority | Overload-dependent postponement | Low-priority interference |
| Within-class policy | Configurable | Earliest deadline | Fixed task priority |
| Analysis | Queue/arrival-specific | Strong classic optimality result | Static-priority response-time tests |
| Adaptivity | Fixed class membership | Changes each job | Fixed per task |
| Overload | High queues dominate | Misses depend on overload policy | Low-priority tasks suffer first |
| Implementation | Simple | Needs deadline tracking | Needs static priority table |

## 10. Experimental protocol
Use identical task sets and simulator semantics. Record task parameters (C,T,D, phase), release and absolute-deadline times, preemption points, context-switch overhead, completion times, and misses. Repeat with fixed random seeds. Include both feasible and overloaded sets. Report mean and maximum response, waiting, utilization, throughput, and deadline-miss ratio. Keep the source code, raw CSV, plots, and test command with the report.

## 11. Limitations
The existing MLQ code is a didactic fixed-queue scheduler and is not an EDF or RM implementation. The worked example is a hand trace, not benchmark evidence. A complete experimental comparison still requires separate EDF/RM simulators and validated tests under the same event model. This report does not claim those tests have already been run.

## 12. Conclusion
Choose MLQ when service classes and queue policy are the primary design concern. Choose EDF when deadlines are explicit and the classic assumptions or a suitable extension apply. Choose RM when static priorities and analyzable periodic workloads are desired. A responsible comparison states task model, assumptions, and limitations rather than declaring one policy universally best.
