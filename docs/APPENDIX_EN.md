<!-- page 34 -->

## Appendix 1 — Research question and scope

The paper does not ask which algorithm is universally best. It asks what guarantee each mechanism provides, what it costs, and where it is limited. The codebase brings together several problem families: workload classification with MLQ, periodic real-time tasks with EDF and RM, mutual exclusion, and readers-writers synchronization. These problems do not share one objective or one model, so their results should not be collapsed into a single numerical ranking.

<!-- page 35 -->

## Appendix 2 — Claim-to-evidence map

Every quantitative claim should point to program output and experiment settings; every correctness claim should point to a defined model and reproducible checker; every bibliographic claim should point to verifiable source metadata. A claim-to-evidence map prevents conclusions from exceeding their support. A response-time chart is evidence about one workload, not proof about every system. Exhaustive checking of a bounded state space covers only that model and participant count.

<!-- page 36 -->

## Appendix 3 — Measurement versus proof

Measurement provides an observed sample of program behavior and depends on the execution environment, workload, and configuration. A proof or model check evaluates a property in a defined abstract model and does not necessarily reveal real system cost. The methods complement one another: measurement exposes practical costs and effects; model checking can reveal execution orders not seen in a small set of trials. The type of evidence should remain explicit beside each claim.

<!-- page 37 -->

## Appendix 4 — Scheduling experiment design

Scheduling policies should be compared on aligned inputs wherever possible. For MLQ, queue assignments and process classes are part of the workload definition; for real-time tasks, C, T, D, and release times are essential. Waiting, turnaround, response, and context-switch counts answer different questions. Deadline misses and response-time analysis have distinct importance for real-time workloads. Stating the workload and parameters lets readers identify exactly which problem a result describes.

<!-- page 38 -->

## Appendix 5 — Interpreting the random schedulability study

The paper's random study includes 2,329 task sets and groups outcomes by utilization range. The reported highest-utilization bin shows a clear difference between RM and EDF, but observed percentages depend on the task-set generator, parameter distributions, seed, and model rules. They should not be interpreted as universal probabilities of RM failure. The 100% EDF result applies to the generated task sets and tested assumptions only.

<!-- page 39 -->

## Appendix 6 — High-demand task case

Under high periodic demand, the difference between fixed and dynamic priority becomes more consequential. RM prioritizes shorter periods and keeps those priorities fixed; EDF evaluates the nearest absolute deadline at each decision. RM response-time analysis and the EDF processor-demand test are independent analytical routes. Agreement between analysis and simulation on covered cases is a useful cross-check, but it does not replace validation of the input assumptions.

<!-- page 40 -->

## Appendix 7 — Reading the utilization cliff

Read the schedulability cliff chart together with its x-axis bins and the number of samples in each bin. A percentage without its denominator can mislead, especially when bin sizes differ. EDF and RM should be compared on the same task sets. If any generated task sets do not satisfy an analytical test's assumptions, label them separately rather than mixing them into the valid sample.

<!-- page 41 -->

## Appendix 8 — Synchronization evidence

In the synchronization sections, model checking enumerates reachable interleavings and searches for witnesses to violated properties. Thread-based tests observe a mechanism in a particular runtime environment. If model checking confirms safety while a threaded experiment behaves poorly, investigate differences in assumptions, memory ordering, thread scheduling, and runtime effects. The results are not necessarily contradictory; the methods may describe different system layers.

<!-- page 42 -->

## Appendix 9 — Evidence in the readers-writers problem

The requirement is not merely to keep writers exclusive; it also includes allowing multiple readers to enter concurrently. A simple exclusive lock may preserve safety while failing the read-concurrency requirement. Safety, progress, starvation freedom, and preference policy must be examined separately. Outcomes under reader-heavy or writer-heavy traffic depend on arrival patterns and cannot be generalized without describing the workload.

<!-- page 43 -->

## Appendix 10 — Limitations and threats to validity

A discrete-time model, zero context-switch cost, a uniprocessor assumption, a bounded participant count, or simplified memory ordering limits the scope of conclusions. In threaded tests, the operating system, runtime, core count, background load, and GIL may change results. In random studies, the generator and seed affect the sample. A scientific report should state these limits beside the results rather than hiding them in a final sentence.

<!-- page 44 -->

## Appendix 11 — Bibliographic source control

The branch reference list deliberately separates entries with checked bibliographic metadata from textbooks used as background whose edition or page metadata has not been fixed. This distinction matters for academic credibility. Title, year, volume, issue, pages, and DOI should appear in a final citation only when verified. When the exact edition of a textbook is unavailable, omit the year or page rather than guessing.

<!-- page 45 -->

## Appendix 12 — Seminar presentation framework

For the seminar, introduce the problem and research question with a small example; show why evaluation metrics conflict; distinguish measurement from model checking; and close with the main findings and their limits. Each figure should carry one clear message. Before showing it, explain the axes, units, sample count, and evidence type. Slides should support rather than replace spoken explanation; one claim and one visual per slide is usually easier to follow.
