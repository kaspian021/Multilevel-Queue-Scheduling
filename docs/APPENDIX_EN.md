<!-- page 39 -->

## Appendix 1 — Three distinct properties

Safety says incompatible processes never occupy the critical section simultaneously. Progress says that when the section is empty and requests exist, selection of the next entrant does not stop forever. Bounded waiting places a bound on how many other entries may occur after a process requests entry. These properties are not interchangeable: a lock may be safe while providing no bounded-waiting guarantee. The comparison must evaluate each separately.

<!-- page 40 -->

## Appendix 2 — Dekker and Peterson assumptions

Classical proofs of Dekker and Peterson assume two participants, atomic reads and writes of shared variables, and an observable ordering of operations. Interest flags and a turn variable prevent simultaneous entry. When implemented in a language or architecture that permits memory reordering, appropriate primitives and ordering are required. Copying a teaching algorithm into modern multithreaded code does not automatically preserve the abstract proof.

<!-- page 41 -->

## Appendix 3 — Binary semaphore

A binary semaphore provides a permit that can be acquired and released. A mutex use must preserve its permit invariant and follow a valid ownership/release discipline. A semaphore alone does not guarantee FIFO waiting; that depends on the implementation contract and wake-up order. Avoid claiming that semaphores are always FIFO unless the exact implementation documents that guarantee.

<!-- page 42 -->

## Appendix 4 — Monitors and Mesa semantics

A monitor encapsulates shared data and the operations permitted on it. Under Mesa semantics, notify generally makes a waiting thread eligible to compete again; the condition must be checked in a loop because state may change before the thread reacquires the lock. The standard pattern is while-not-condition, not if. Wake-up policy and fairness are part of the monitor contract, not cosmetic details.

<!-- page 43 -->

## Appendix 5 — Readers and writers

In the readers-writers problem, multiple readers may enter together, but a writer must be exclusive. Reader preference can starve a writer; writer preference can delay newly arriving readers. A simple mutex may be safe while eliminating concurrent reads. Therefore safety, progress, starvation freedom, and concurrency must be reported separately.

<!-- page 44 -->

## Appendix 6 — Mechanism choice and scope

For two participants under the classical atomic model, Dekker and Peterson are important teaching solutions; application software generally uses library mutexes, semaphores, or monitors. Do not choose a mechanism using throughput alone. Report the explored state-space size, participant count, operating system, memory model, and workload. Exhaustive checking of a bounded model is not a correctness claim for every thread count and architecture.
