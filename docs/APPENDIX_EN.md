<!-- page 29 -->

## Appendix 1 — Formal problem statement

A shared resource is read by readers and modified by writers. Multiple readers may occupy the critical section concurrently, but a writer must be alone. The central invariant is that whenever the number of active writers is non-zero, the number of active readers must be zero; no two writers may be active together either. The problem therefore requires both mutual exclusion and permitted reader concurrency.

<!-- page 30 -->

## Appendix 2 — Safety is not enough

A simple exclusive lock can serialize every entry and prevent reader-writer overlap. However, it may also serialize all readers and eliminate the required concurrent-read behavior. An implementation that satisfies only the safety invariant is not necessarily a readers-writers solution. Tests must check both exclusion and the existence of a state in which two readers are inside simultaneously.

<!-- page 31 -->

## Appendix 3 — Properties under evaluation

Four properties should be evaluated separately: safety, progress, starvation freedom, and read concurrency. Safety forbids incompatible states; progress prevents a permanent decision stall; starvation freedom prevents an individual requester from being postponed forever; read concurrency permits simultaneous readers. A protocol may satisfy the first three while failing the fourth. A comparison table is meaningful only when these columns remain independent.

<!-- page 32 -->

## Appendix 4 — Reader preference

Under reader preference, new readers may continue entering while readers are active, leaving a writer waiting behind the stream of reads. The benefit is good responsiveness for read-heavy workloads and use of reader concurrency. The risk is that a writer may never enter if readers keep arriving. Writer latency should therefore be reported alongside reader throughput; an overall mean can hide the problem.

<!-- page 33 -->

## Appendix 5 — Writer preference

Under writer preference, registering a waiting writer can prevent new readers from entering until the writer receives service. This avoids writer starvation but can delay new readers when writers arrive consecutively. The outcome depends on writer count, arrival spacing, and critical-section duration. The label 'writer preference' alone does not guarantee bounded waiting for readers.

<!-- page 34 -->

## Appendix 6 — Fairness and bounded waiting

Fairness is a precise policy property, not merely the visual impression of a balanced chart. Bounded waiting usually places a bound on the number of other entries allowed after a process requests access. Traffic share or mean waiting time can describe observed experience, but does not replace a bounded-waiting guarantee. If an experiment reports only the mean, one process may starve for a long interval without the aggregate exposing it.

<!-- page 35 -->

## Appendix 7 — Model checking interleavings

A model checker represents each state using counters, flags, lock states, and each process's program location, then follows all possible transitions. Keeping a set of visited states avoids endless traversal of cycles. If an invariant fails, the path to the failing state is recorded as a witness. Exhausting every reachable state is complete for that finite model, not for process counts or primitives outside the model.

<!-- page 36 -->

## Appendix 8 — Thread-based experiments

Real threads complement model checking because they introduce runtime contention, waiting queues, and wake-up behavior. For every critical-section entry, active reader and writer counts should be recorded and the invariant checked at that moment. Checking only the final state is insufficient: a transient violation may occur and disappear before the test ends. Results should include operation count, duration, workload composition, and environment.

<!-- page 37 -->

## Appendix 9 — Interpreting the reader-preference experiment

The branch README reports that with six readers and one writer across nine half-second trials, the writer's traffic share was below one percent in most trials, and the longest uninterrupted read run reached tens of thousands of operations. This is an observation tied to a workload and environment. Initial scheduling order can alter traffic share in other runs. Report all repetitions rather than selecting one favorable trace.

<!-- page 38 -->

## Appendix 10 — Interpreting writer preference

The branch's experiment description states that with one writer, the reader gate reopened in the tested workload, while adding a second writer could keep readers waiting behind the writer stream. This shows that starvation depends not only on the algorithm label but also on arrival rates and the number of competitors. State writer count, arrival spacing, operation duration, and wake-up policy when interpreting the result.

<!-- page 39 -->

## Appendix 11 — Mesa monitor semantics

Under Mesa semantics, notify does not transfer lock ownership immediately to the awakened thread. The awakened thread later competes to reacquire the lock, and the condition may become false in the meantime. For this reason, condition waits belong in a while loop. If a writer or reader repeatedly loses the race to newcomers after wake-up, model checking should examine whether a fair starvation cycle exists.

<!-- page 40 -->

## Appendix 12 — Changing the wake-up queue

One way to limit recompetition is to place an awakened thread at a defined position in the entry queue instead of returning it to the general competition. Such a change alters the fairness contract and should be documented as a monitor-policy change. Explicit fair queueing may increase bookkeeping and implementation complexity, so both correctness and overhead should be evaluated.

<!-- page 41 -->

## Appendix 13 — Limits of Dekker and Peterson

Dekker and Peterson are classical software solutions for two participants. Their abstract proofs assume atomic shared-variable operations, and a two-process implementation cannot be generalized to arbitrary thread counts without a different design. Modern architectures also require memory ordering consistent with the language and hardware model. Using these algorithms as a reader-count lock does not remove their participant-count limitation.

<!-- page 42 -->

## Appendix 14 — Why proof and measurement may disagree

An abstract model may assume atomic operations or a particular interleaving structure, while a threaded program runs under a language runtime, operating-system scheduler, and library locks. The branch report discusses a difference between Peterson's model verdict and its threaded benchmark and identifies GIL effects on spinning threads as a possible explanation. Interpret this as a difference between model and execution environment rather than discarding either source without analysis.

<!-- page 43 -->

## Appendix 15 — Choosing a policy

For read-heavy workloads, reader preference may improve throughput, but writer delay and possible starvation must be controlled. For write-sensitive workloads, writer preference can improve writer latency but its effect on readers must be evaluated. Where fairness is required, an explicit FIFO or turn-taking policy should be considered. Choose using tail latency, throughput, participant count, and arrival pattern rather than mechanism name alone.

<!-- page 44 -->

## Appendix 16 — Reproducibility protocol

For each experiment, record code revision, reader and writer counts, duration, request generation rate, critical-section length, operating system, Python version, and runtime configuration. Save the random seed or scheduling seed if one is used. Keep model-checker traces and raw experiment data beside the final figures. These records allow replication and help explain environment-dependent differences.

<!-- page 45 -->

## Appendix 17 — Validity threats and scope

A half-second run may reveal a fast contention pattern but is insufficient to infer rare tail delays. The GIL, core count, background load, and operating-system scheduler can change throughput rankings. Model checking is also limited to the state space and participant count defined by the model. A scientific result should state which claims come from model proof and which come from observing one execution environment.

<!-- page 46 -->

## Appendix 18 — Oral-presentation checklist

In a presentation, state the reader-writer invariant first; show why a simple lock removes concurrent reading; compare reader and writer preference using two traces; and close by distinguishing model checking from threaded experiments. A starvation chart should state competitor count and test duration. Define safety, progress, starvation, and concurrency before showing the verdict table.
