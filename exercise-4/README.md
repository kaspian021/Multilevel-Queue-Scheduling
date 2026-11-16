# Exercise 4 — Dekker, Peterson, Semaphore and Monitor

**Branch:** `Exercise-4-Dekker-Peterson-Semaphore-Monitor`

**Branch layout:** every file of this exercise sits at the **root of the branch**
(not inside a nested folder), so GitHub renders this README on the branch home
page. The repository root also carries `PROJECT_PROGRESS.md`,
`EXERCISE_BRANCH_INDEX.md`, `Multilevel_Queue_Scheduling.py` and `assets/`,
which are inherited from `master` and are not part of this exercise.

---

## 1. Deliverables

| Language | Markdown | Word (DOCX) | PDF | Pages |
|---|---|---|---|---:|
| Persian (فارسی) | [`COMPARISON_FA.md`](COMPARISON_FA.md) | [`docs/COMPARISON_FA.docx`](docs/COMPARISON_FA.docx) | [`docs/COMPARISON_FA.pdf`](docs/COMPARISON_FA.pdf) | **37** |
| English | [`COMPARISON_EN.md`](COMPARISON_EN.md) | [`docs/COMPARISON_EN.docx`](docs/COMPARISON_EN.docx) | [`docs/COMPARISON_EN.pdf`](docs/COMPARISON_EN.pdf) | **38** |

Page counts are measured, not estimated: the PDF count is read out of the PDF
itself, and the DOCX count is a measured estimate of the Word reflow. Both
reports were rendered by `tools/build_report.py`, which fails rather than emit a
document when a page overflows the A4 frame or a figure is missing.

---

## 2. The central idea

Running a concurrent program and watching it succeed **proves nothing**. A bug
may need one specific interleaving of a dozen atomic steps, and that
interleaving may not appear in a million test runs. So this exercise does two
separate things and keeps them strictly apart:

* **Correctness** is settled by an **exhaustive model checker**
  (`code/sync_model.py`) that enumerates the entire reachable state space of
  each algorithm. The largest space has 324 states, so every verdict is
  complete rather than sampled.
* **Cost** is measured on real threads (`code/sync_algorithms.py`). Timings on a
  shared machine are noisy — a single run of one workload varied by more than an
  order of magnitude — so every timing is a **median over 5–7 trials** with the
  minimum and maximum reported beside it.

---

## 3. Verified results (exhaustive)

| Algorithm | Family | States | Mutual exclusion | Deadlock free | Starvation free |
|---|---|---:|---|---|---|
| `dekker` | software | 324 | holds | yes | yes |
| `peterson` | software | 199 | holds | yes | yes |
| `lock_variable` | broken | 60 | **VIOLATED** | yes | no |
| `flag_spin` | broken | 55 | holds | **no** | yes |
| `tas` | hardware | 51 | holds | yes | **no** |
| `semaphore_binary` | primitive | 22 | holds | yes | yes |
| `semaphore_wrong_order` | broken | 48 | holds | **no** | yes |
| `monitor_mesa` | monitor | 54 | holds | yes | yes |

Three failures, each of a different kind:

* `lock_variable` (look, then announce) loses **mutual exclusion** — the checker
  prints the shortest interleaving in which both processes walk in.
* `flag_spin` (announce, then look) keeps exclusion but **deadlocks**: both
  processes announce before either looks.
* `tas` (test-and-set) is safe and live but has **no bounded waiting** — the
  checker exhibits a reachable cycle in which one thread spins while the other
  enters repeatedly.
* `semaphore_wrong_order` shows that a *correct* primitive still deadlocks when
  two threads take two locks in opposite orders.

Witness traces for every failure are printed by `python code/sync_model.py` and
stored in `output/model_check.txt`.

---

## 4. Measured results

### 4.1 Throughput, 2 threads x 5000 critical sections (median of 7)

| Mechanism | Median (ops/s) | Min | Max | Spins (median) |
|---|---:|---:|---:|---:|
| dekker | 995,696 | 245,408 | 1,029,634 | 0 |
| peterson | 1,048,660 | 1,018,671 | 1,069,822 | 0 |
| tas | 425,099 | 408,594 | 745,474 | 37,613 |
| semaphore | 501,066 | 477,697 | 527,005 | blocks |
| monitor | 551,455 | 528,263 | 557,830 | blocks |

### 4.2 Contention sweep (median of 5, 5000 sections per thread)

| Threads | Test-and-set | Semaphore | Monitor | TAS spins |
|---:|---:|---:|---:|---:|
| 2 | 554,397 | 524,972 | 540,953 | 24,163 |
| 4 | 624,466 | 492,372 | 532,148 | 24,714 |
| 8 | 476,978 | 494,447 | 510,747 | 141,814 |

### 4.3 Monitor bounded buffer (2 producers, 2 consumers, 1600 items)

| Capacity | Max occupancy | Capacity respected | Re-checks after a wake | Throughput (items/s) |
|---:|---:|---|---:|---:|
| 1 | 1 | yes | 1,383 | 23,343 |
| 4 | 4 | yes | 361 | 51,045 |
| 16 | 16 | yes | 147 | 114,212 |

The re-check column is direct evidence that the `while` loop around
`condition.wait()` is load-bearing: under Mesa semantics a woken thread must
re-test its predicate. Had the code used `if`, those re-waits would have been
silent corruption.

### 4.4 Readers and writers (6 readers, 1 writer, 5 trials of 0.6 s)

| Variant | Reads | Writes | Mean read share |
|---|---:|---:|---:|
| Readers preference | 189,832 | **5** | 1.000 |
| Writers preference | 479,104 | 1,165,632 | 0.292 |
| Fair (FIFO ticket) | 91,051 | 10,136 | 0.898 |

With 6 readers against 1 writer, a fair scheduler should give readers about
6/7 = 0.857 of the completions; the FIFO variant lands at 0.898. The
readers-preference variant gives the writer essentially nothing.

### 4.5 Deadlock, reproduced deterministically

```
wrong order   : t0 = "holds A, blocked on B" | t1 = "holds B, blocked on A"   deadlocked = True
same order    : t0 = "completed"             | t1 = "completed"               completed  = True
```

A barrier sits between the two acquisitions and the second acquisition is
non-blocking, so the circular wait is produced on purpose rather than left to
scheduler luck or to a timeout race.

---

## 5. Files on this branch

```
README.md                     this file
requirements.txt              pytest, matplotlib
.gitignore
COMPARISON_FA.md              Persian report (Markdown source)
COMPARISON_EN.md              English report (Markdown source)
docs/
├── COMPARISON_FA.docx        Persian report, 37 pages
├── COMPARISON_FA.pdf         Persian report, 37 pages
├── COMPARISON_EN.docx        English report, 38 pages
└── COMPARISON_EN.pdf         English report, 38 pages
code/
├── sync_model.py             the model checker: 8 algorithms, verdicts, witnesses
├── sync_algorithms.py        runnable Dekker, Peterson, TAS, semaphore, monitor,
│                             three readers-writers variants, deadlock experiment
├── run_experiments.py        writes everything under output/
├── make_diagrams.py          regenerates every figure
└── sync_demo.py              the earlier semaphore/monitor demonstration
diagrams/
├── fig_state_spaces.png      reachable states and transitions per algorithm
├── fig_property_matrix.png   the three properties as a matrix
├── chart_throughput.png      cost of each mechanism
├── chart_contention.png      throughput versus thread count
├── chart_spins.png           wasted work in the spinlock
├── chart_readers_writers.png fairness of the three variants
├── fig_deadlock.png          the circular wait as a wait-for graph
└── fig_monitor_timeline.png  buffer occupancy and re-checked waits
output/
├── experiments.json          every measured number
├── model_check.txt           verdicts plus witness traces
├── experiments_summary.txt   full text log
├── model_table.md            the verified verdicts as a Markdown table
├── figures.json              list of generated figures
└── pytest_result.txt
tests/
├── test_sync_model.py        26 tests locking in the verified verdicts
├── test_sync_algorithms.py   24 tests for the threading layer
└── test_sync_demo.py         2 tests for the earlier demonstration
```

---

## 6. Running it

```bash
# from the branch root (this folder IS the branch root)
pip install -r requirements.txt

python code/sync_model.py         # all eight verdicts plus witness traces
python code/run_experiments.py    # every number quoted in the report
python code/make_diagrams.py      # regenerates all eight figures
python -m pytest tests -q         # 52 passed
```

Test result recorded in `output/pytest_result.txt`: **52 passed**.
The tests lock in the verified verdicts (state counts, which properties hold,
which do not), so editing a step function in `sync_model.py` and breaking a
property fails the suite.

Reproducing the reports, from the repository root on the session branch:

```bash
python3 tools/build_report.py ex4_fa exercise-4 COMPARISON_FA
python3 tools/build_report.py ex4_en exercise-4 COMPARISON_EN
python3 tools/check_outputs.py exercise-4        # re-measures page counts
```

The content modules live in `tools/content/ex4_fa.py` and
`tools/content/ex4_en.py`; they read every number from
`output/experiments.json`, so the prose and the program cannot disagree.

---

## 7. Limits and honest scope

* **Two participants only.** Dekker and Peterson are two-process algorithms, but
  the semaphore and monitor verdicts were checked only in the two-thread case
  and do not automatically extend to n threads.
* **Sequential consistency is assumed.** Real hardware and real compilers
  reorder loads and stores. On real hardware Dekker and Peterson need memory
  fences that this model does not represent — which is precisely why they are
  studied as historical results rather than recommended for production.
* **The model has no failures, no timeouts and no interrupts**, and the monitor
  model is a one-slot buffer with one producer and one consumer, not a general
  monitor checker.
* **The timings are single-machine**, taken in a shared sandbox under CPython's
  GIL. They indicate relative cost, not a portable benchmark; the spin counts
  are the figures most affected by the GIL.
* **Passing thread tests are not proofs.** The tests in `tests/` are regression
  guards for code that is already verified by the model checker; they are not
  the evidence for the correctness claims.

## 8. References

* Dijkstra, E. W. — *Solution of a problem in concurrent programming control* —
  Communications of the ACM, 1965.
* Peterson, G. L. — *Myths About the Mutual Exclusion Problem* — Information
  Processing Letters, 1981.
* Dijkstra, E. W. — *The structure of the THE multiprogramming system* —
  Communications of the ACM, 1968.
* Hoare, C. A. R. — *Monitors: An Operating System Structuring Concept* —
  Communications of the ACM, 1974.
* Lampson, B. W., & Redell, D. D. — *Experience with Processes and Monitors in
  Mesa* — Communications of the ACM, 1980.
* Coffman, E. G., Elphick, M. J., & Shoshani, A. — *System Deadlocks* —
  Computing Surveys, 1971.
* Silberschatz, A., Galvin, P. B., & Gagne, G. — *Operating System Concepts*,
  chapters on Process Synchronization and Deadlocks.
