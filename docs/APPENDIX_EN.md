<!-- page 36 -->

## Appendix 1 — Aligning the comparison model

A fair comparison runs each algorithm on the same task set with the same time unit, execution costs, and release rules. MLQ primarily sees class and queue; EDF uses absolute deadlines; RM derives fixed priority from task periods. If the MLQ input has no deadlines, deadline-miss rate is not directly comparable. Any deadline mapping and priority semantics must be stated explicitly.

<!-- page 37 -->

## Appendix 2 — Processor utilization

For periodic tasks with worst-case execution C and period T, total utilization is U=Σ(C_i/T_i). It describes the average computational demand but does not capture every detail of phase, relative deadlines, jitter, or overhead. In the classical preemptive uniprocessor model with D=T, U≤1 is necessary and sufficient for EDF schedulability. Outside those assumptions, a more specific test is required.

<!-- page 38 -->

## Appendix 3 — Liu–Layland bound

For n independent periodic tasks with deadlines equal to periods, the classical sufficient RM utilization bound is n(2^(1/n)−1). For three tasks it is approximately 0.780. If U exceeds the bound, the sufficient test is inconclusive; this alone does not prove RM infeasibility. A fixed-priority response-time analysis is needed for a more decisive test.

<!-- page 39 -->

## Appendix 4 — RM response-time analysis

For a fixed-priority task i, worst-case response time is obtained by iterating R_i=C_i+Σ ceil(R_i/T_j)C_j over higher-priority tasks. Start from C_i and repeat until reaching a fixed point or exceeding the deadline. A fixed point above D_i means the task is not guaranteed to meet its deadline under this model. Recording each iteration makes the calculation auditable.

<!-- page 40 -->

## Appendix 5 — EDF demand-bound test

For EDF, the demand-bound condition checks that the execution required by jobs whose releases and deadlines fall in an interval does not exceed the interval length. With periodic tasks and D=T, demand at interval t is computed from the number of jobs whose deadlines occur by t. The test applies only to its stated model and interval assumptions; do not extend the D=T result to arbitrary deadlines.

<!-- page 41 -->

## Appendix 6 — MLQ and deadlines

Classical MLQ does not itself provide deadline guarantees; it is mainly intended to separate workload classes and apply queue priorities. A deadline comparison requires MLQ inputs to include release, execution, and deadline values, followed by deadline-miss measurement on the same workload trace. Even then, the result describes only the MLQ policy configured in this experiment, not a general real-time guarantee.

<!-- page 42 -->

## Appendix 7 — Results and validity threats

Low-load and stressed scenarios should be reported separately because an overall mean can hide deadline misses. The number of random task sets, seed, C/T distributions, tie-breaking rules, and preemption model must be recorded. A 100% success rate in a finite experiment is not a mathematical proof for every task set. Conversely, an analytical test is valid only under its assumptions and does not automatically include real overhead.
