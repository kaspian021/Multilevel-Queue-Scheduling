# Exercise 7 — Readers and Writers: semaphore, monitor, Dekker, Peterson

The readers-writers problem asks for a lock that keeps writers exclusive of
everybody while letting any number of readers share the section. Four classic
mechanisms are usually offered as the answer and they are not interchangeable.
This branch builds all four, then asks two separate questions of each:

* **What is proved.** An exhaustive model checker (`code/rw_model.py`) walks
  every reachable interleaving of a two- or three-process protocol and returns
  a verdict on safety, deadlock freedom, starvation freedom, and — the
  property the problem actually exists for — whether two readers can be
  inside at once.
* **What is measured.** A threaded harness (`code/rw_sync.py`) runs every lock
  under load and checks the invariant on *every single entry*, not at the end.

The two answers do not always agree, and the disagreements are the interesting
part. Section 8 of the paper is about exactly that.

## Deliverables

| File | What it is | Pages |
|---|---|---|
| `REPORT_EN.md` / `docs/REPORT_EN.docx` / `docs/REPORT_EN.pdf` | the paper, English | **28** |
| `REPORT_FA.md` / `docs/REPORT_FA.docx` / `docs/REPORT_FA.pdf` | the paper, Persian | **28** |
| `diagrams/` | 9 figures, all regenerable | — |
| `output/experiments.json` | every number in both papers | — |

Page counts are the PDF page counts reported by the build, not an estimate.
No PPTX deck on this branch: the deliverable set is the standard one.

## Running it

```bash
python3 code/rw_model.py                  # the verdicts, with witnesses
python3 code/run_experiments.py           # every measurement -> output/
python3 code/make_diagrams.py             # every figure -> diagrams/
python3 -m pytest tests -q                # 102 tests
```

Building the papers needs the shared tooling at the repository root, from the
repository root:

```bash
python3 tools/build_report.py ex7_en exercise-7 REPORT_EN
python3 tools/build_report.py ex7_fa exercise-7 REPORT_FA
```

## Headline results

* **Every mutual exclusion solution satisfies safety and liveness and still
  fails the one property the problem exists for.** The semaphore mutex, the
  monitor mutex, Dekker and Peterson never let two readers in at once.
* **Readers preference starves the writer.** Six readers and one writer, nine
  half-second trials: the writer's share of the traffic was under one per cent
  in most of them, and the longest unbroken read run was
  **tens of thousands of operations**.
* **Writers preference needs two writers to starve the reader.** With one
  writer the reader door reopens every time and nothing starves; add a second
  and the reader is the one that never gets in. The starvation is a property of
  the *load*, not only of the algorithm.
* **A Mesa monitor does not bound waiting.** Because a notified thread has to
  re-compete for the monitor lock, the checker finds a fair cycle in which
  *every* participant starves. Hand the woken thread a place in the entry queue
  instead — two instructions — and only the writer can starve.
* **Dekker and Peterson can carry the pattern, between two participants.**
  Used as the count lock rather than as the section lock, both let two readers
  inside together. Both are written for exactly two processes, and that is the
  whole of their limitation.
* **The measurements and the proofs disagree about Peterson.** It is provably
  starvation free, and it starved the writer in most trials — because a
  spinning thread burns its whole quantum under the GIL. The spin counts make
  that plain.

## Layout

```
code/rw_model.py          exhaustive model checker, 17 protocols
code/rw_sync.py           threaded locks plus the benchmark harness
code/run_experiments.py   runs every experiment, writes output/experiments.json
code/make_diagrams.py     regenerates all nine figures
tests/test_exercise7.py   102 tests over the model, the locks and the artefacts
diagrams/*.png            the figures
output/experiments.json   the data behind every number
docs/                     the four deliverable files
```

Both papers are generated: every figure in them is read from
`output/experiments.json` at build time, so a paper cannot quote a number the
code does not produce.
