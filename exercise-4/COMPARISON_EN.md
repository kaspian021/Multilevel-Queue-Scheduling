# Dekker vs Peterson vs Semaphore vs Monitor
## 1. Mutual exclusion problem
A critical section accesses shared state that must not be concurrently modified by conflicting participants. A correct solution is commonly evaluated by: mutual exclusion (never two participants inside simultaneously), progress (if the critical section is free and contenders exist, selection cannot be postponed forever by non-contenders), and bounded waiting (a contender has a finite bound on overtaking). These properties rely on an execution and memory model.

## 2. Dekker's algorithm
Dekker's two-process algorithm uses intent flags and a shared turn variable. Each process announces interest. If both want to enter, the turn variable breaks the tie; one process temporarily withdraws intent and waits for its turn. On exit it assigns turn to the other process and clears its flag. Under the classic atomic read/write and sequential-consistency assumptions, it provides mutual exclusion, progress, and bounded waiting for two processes. It is complex and unsuitable as a modern general-purpose lock without careful memory-order guarantees.

Pseudocode sketch:
```text
flag[i] = true
while flag[j]:
    if turn == j:
        flag[i] = false
        while turn == j: wait
        flag[i] = true
critical_section()
turn = j
flag[i] = false
```

## 3. Peterson's algorithm
Peterson uses two intent flags and a turn variable. Process i sets flag[i]=true, gives priority to j by setting turn=j, and waits while flag[j] and turn==j. It is simpler than Dekker and provides the same classic properties for two processes under sequential consistency. Modern CPUs and compilers may reorder memory operations; a literal implementation with ordinary non-atomic variables in a modern language is not automatically correct. Use atomics with appropriate memory ordering or a proven library primitive.

## 4. Semaphore
A semaphore maintains a counter and supports atomic wait/acquire and signal/release operations. A binary semaphore can protect a critical section; a counting semaphore can represent a finite resource pool or available work count. Correctness depends on atomic primitive implementation and disciplined acquire/release pairing. Incorrect ordering can cause deadlock; unfair semaphore implementations may not guarantee bounded waiting. A semaphore is more general than the two-process algorithms.

## 5. Monitor
A monitor encapsulates shared data and operations so that only one thread executes monitor code at a time. Condition variables allow threads to sleep until a predicate becomes true. A thread must generally wait in a loop that rechecks the predicate after wakeup. Monitors reduce accidental exposure of locks but still require correct invariants and lock discipline. Hoare-style and Mesa-style monitor semantics differ in how condition signaling transfers control.

## 6. Comparison
| Criterion | Dekker | Peterson | Semaphore | Monitor |
|---|---|---|---|---|
| Abstraction | Software protocol | Software protocol | Primitive | High-level construct |
| Participants | Exactly 2 in classic form | Exactly 2 in classic form | General | General |
| Mutual exclusion | Yes, classic model | Yes, classic model | If used correctly | If monitor semantics enforce it |
| Progress | Yes, classic model | Yes, classic model | Depends on use/fairness | Depends on conditions/signaling |
| Bounded waiting | Yes, classic model | Yes, classic model | Not universal | Not universal |
| Busy waiting | Yes | Yes | Usually blocking implementation | Usually blocking |
| Ease of use | Low | Moderate | Moderate | High-level |
| Typical risk | Memory-model assumptions | Memory-model assumptions | Permit leaks/order errors | Wrong predicates/signaling |

## 7. Deadlock and starvation
Mutual exclusion alone does not prevent deadlock. Deadlock can arise from circular waiting across multiple locks, failing to release a semaphore, or waiting on a condition whose predicate can never become true. Starvation is possible when scheduling or lock acquisition is unfair. Bounded waiting is a property of a particular algorithm under stated assumptions, not a universal promise of every semaphore or monitor library.

## 8. Performance
Busy-wait algorithms consume CPU while spinning and can be acceptable only for very short waits in constrained contexts. Blocking locks incur context-switch and wakeup costs but avoid wasting CPU for long waits. Modern mutexes often use adaptive spinning and blocking. Performance must be measured under realistic contention; theoretical instruction counts are not a substitute for benchmarks.

## 9. Correctness and modern memory models
Classic textbook proofs assume atomic reads/writes and a sequentially consistent view of shared memory. Compilers and CPUs can reorder operations unless synchronization or atomic memory ordering prevents it. In C/C++, use atomic variables and appropriate memory orders; in Python, use threading.Lock, Semaphore, or Condition rather than attempting textbook spin algorithms with ordinary variables. The GIL is not a correctness substitute for a multi-step critical-section invariant.

## 10. Recommendation
Use a well-tested mutex/semaphore/monitor abstraction in production. Study Dekker and Peterson to understand the logic of mutual exclusion and the role of intent and tie-breaking. Never deploy textbook pseudocode as production code without matching the language memory model and formal proof.
