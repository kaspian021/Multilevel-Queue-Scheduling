# Exercise 3 — EDF and RM scheduling with three inputs, solved by hand

**Branch:** `Exercise-3-EDF-RM-Manual-Scheduling`
**Scope of this README:** only the files in this `exercise-3/` folder.

---

## 1. Deliverables

| Language | Markdown | Word (DOCX) | PDF | Pages |
|---|---|---|---|---:|
| Persian (فارسی) | [`MANUAL_SOLUTION_FA.md`](MANUAL_SOLUTION_FA.md) | [`docs/MANUAL_SOLUTION_FA.docx`](docs/MANUAL_SOLUTION_FA.docx) | [`docs/MANUAL_SOLUTION_FA.pdf`](docs/MANUAL_SOLUTION_FA.pdf) | **24** |
| English | [`MANUAL_SOLUTION_EN.md`](MANUAL_SOLUTION_EN.md) | [`docs/MANUAL_SOLUTION_EN.docx`](docs/MANUAL_SOLUTION_EN.docx) | [`docs/MANUAL_SOLUTION_EN.pdf`](docs/MANUAL_SOLUTION_EN.pdf) | **24** |

Page counts are measured, not estimated: the PDF count is read out of the PDF file
itself, and the DOCX count is a measured estimate of the Word reflow. Both reports
were rendered by `tools/build_report.py`, which refuses to emit a document when a
page overflows the A4 frame or a figure is missing.

Both reports contain: task-set design, utilisations and hyperperiod arithmetic,
RM priority computation, the EDF selection rule, the Liu–Layland bound,
response-time analysis, 24-tick step tables with the ready set for **both**
algorithms, Gantt charts, deadline checklists, a comparative results table,
utilisation/idle-time arithmetic, verification against the code, scope of the
claim, references, and **three blank worksheets** for rewriting the schedule by
hand.

---

## 2. Task set

Single preemptive CPU, discrete time, all tasks released in phase at `t = 0`.

| Task | C (execution) | T (period) | D (relative deadline) | Releases in [0,24) |
|---|---:|---:|---:|---|
| T1 | 1 | 4 | 4 | 0, 4, 8, 12, 16, 20 |
| T2 | 3 | 8 | 8 | 0, 8, 16 |
| T3 | 4 | 12 | 12 | 0, 12 |

* `U = 1/4 + 3/8 + 4/12 = 23/24 ≈ 0.9583`
* Hyperperiod `H = lcm(4, 8, 12) = 24`
* Total demand in one hyperperiod = `6·1 + 3·3 + 2·4 = 23` units → **1 unit of idle time**
* Jobs in one hyperperiod = 11

### Conventions used by the simulator

* EDF tie rule: on equal absolute deadlines the **smaller task index** runs first.
* A job that misses its deadline is **not aborted**; it keeps running to completion.
* The analysis horizon is exactly one hyperperiod.

---

## 3. Results

### 3.1 Analytic verdicts (valid for all time, not just one hyperperiod)

| Test | Result | Verdict |
|---|---|---|
| Liu–Layland bound for RM, n = 3 (`0.7798`) | `U = 0.9583 > 0.7798` | inconclusive (only a sufficient condition) |
| RM response-time analysis | `R(T1) = 1 ≤ 4`, `R(T2) = 4 ≤ 8`, `R(T3) = 14 > 12` | **RM is NOT schedulable** |
| EDF utilisation test (implicit deadlines) | `U = 0.9583 ≤ 1` | **EDF is schedulable** |

Because `D = T` for every task, `U ≤ 1` is both necessary and sufficient for EDF,
so no processor-demand test is needed here.

### 3.2 Measured over one hyperperiod

| Metric | EDF | RM |
|---|---:|---:|
| Deadline misses | 0 | 1 |
| Job that missed | — | `T3_0` (release 0, deadline 12, finish 14) |
| Busy time | 23 | 23 |
| Idle time | 1 | 1 |
| Utilisation | 95.83 % | 95.83 % |
| Context switches | 12 | 11 |
| Avg response of T1 | 1.000 | 1.000 |
| Avg response of T2 | 4.667 | 4.000 |
| Avg response of T3 | 10.500 | 12.500 |
| Max response | 11 | 14 |

### 3.3 Execution timelines (24 ticks, `-` = idle)

```
t :  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23
EDF T1 T2 T2 T2 T1 T3 T3 T3 T1 T3 T2 T2 T1 T2 T3 T3 T1 T2 T2 T2 T1 T3 T3  -
RM  T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3  -
```

**Why RM misses.** `T3_0` is released at `t = 0`, runs at ticks 5–7, and one unit
remains. At `t = 8` the higher-priority `T2_1` arrives and runs for three ticks, and
at `t = 12` `T1_3` arrives and, having a shorter period, runs immediately. The last
unit of `T3_0` therefore runs at tick 13 and finishes at `t = 14`, two units past
its deadline of 12. EDF instead continues `T3_0` at `t = 12`, because its absolute
deadline (12) is nearer than that of `T1_3` (16).

---

## 4. Files in this branch

```
exercise-3/
├── README.md                        this file
├── requirements.txt                 pytest, matplotlib
├── .gitignore
├── MANUAL_SOLUTION_FA.md            Persian report (Markdown source)
├── MANUAL_SOLUTION_EN.md            English report (Markdown source)
├── docs/
│   ├── MANUAL_SOLUTION_FA.docx      Persian report, 24 pages
│   ├── MANUAL_SOLUTION_FA.pdf       Persian report, 24 pages
│   ├── MANUAL_SOLUTION_EN.docx      English report, 24 pages
│   └── MANUAL_SOLUTION_EN.pdf       English report, 24 pages
├── code/
│   ├── edf_rm.py                    simulator, schedulability tests, CLI
│   ├── run_experiments.py           writes every artefact under output/
│   ├── make_figures.py              regenerates every PNG under diagrams/
│   ├── manual_solution.py           the earlier one-shot illustration
│   └── build_manual_pdf.py          HTML → headless Chrome Persian worksheet
├── diagrams/
│   ├── gantt_edf.png                EDF Gantt over one hyperperiod
│   ├── gantt_rm.png                 RM Gantt over one hyperperiod
│   ├── chart_rta.png                R vs. D for the three tasks
│   ├── chart_response.png           min / avg / max response per task
│   ├── chart_utilization.png        23 busy vs. 1 idle unit
│   └── fig_release_pattern.png      releases and deadlines in [0,24)
├── output/
│   ├── experiments.json             every number, machine-readable
│   ├── experiments_summary.txt      text summary
│   ├── summary_EDF.txt / summary_RM.txt
│   ├── step_table_EDF.txt / step_table_RM.txt
│   └── pytest_result.txt
└── tests/
    ├── test_edf_rm.py               27 tests
    └── test_manual_solution.py      2 tests
```

---

## 5. Running it

```bash
cd exercise-3

python3 code/run_experiments.py          # every number, table and JSON
python3 code/make_figures.py             # regenerates all six PNGs
python3 -m pytest tests -q               # 29 passed

# any other task set from the command line, no code change needed:
python3 code/edf_rm.py --tasks "T1:1:4:4,T2:3:8:8,T3:4:12:12" \
                       --json out.json --table table.txt --lang en
```

`--tasks` takes `name:C:T:D[:phase]` items, so phases and other task sets can be
explored without editing anything.

Test result recorded in `output/pytest_result.txt`: **29 passed** (27 in `test_edf_rm.py`, 2 in `test_manual_solution.py`).
`tests/test_edf_rm.py` locks the hand-worked 24-tick timelines for both algorithms
as literal strings, so the code can never silently drift away from the hand
solution printed in the report.

---

## 6. Reproducing the reports

From the repository root:

```bash
python3 tools/build_report.py ex3_fa exercise-3 MANUAL_SOLUTION_FA
python3 tools/build_report.py ex3_en exercise-3 MANUAL_SOLUTION_EN
python3 tools/check_outputs.py exercise-3        # re-measures page counts
```

The content modules live in `tools/content/ex3_fa.py` and `tools/content/ex3_en.py`
and import their numbers straight from `edf_rm.py`, so the report text, the
step tables and the program can never disagree.

---

## 7. Limits and honest scope

* One synchronous task set is analysed over one hyperperiod. The definitive
  schedulability verdicts come from the **analytic tests**, not from the
  simulation; the simulation only confirms them on this sample.
* This is **not** a general claim that EDF beats RM. It is a claim about this
  task set only, backed by both an analytic test and a simulation.
* The model ignores context-switch cost, cache effects, blocking, resource
  sharing and release jitter.
* `code/build_manual_pdf.py` is an optional extra: it renders a printer-friendly
  Persian worksheet (`output/HAND_WORKSHEET_FA.pdf`) through HTML and headless
  Chrome, and needs `google-chrome` plus the Vazirmatn font installed. It is not
  required for any deliverable and was not used to build `docs/*.pdf`.
* No scan of handwriting is provided; the blank worksheets in the reports are
  typeset tables, not images of paper.
* `code/manual_solution.py` keeps the earlier one-shot illustration for reference.

## 8. References

* Liu, C. L., & Layland, J. W. — *Scheduling Algorithms for Multiprogramming in a
  Hard-Real-Time Environment* — Journal of the ACM, 1973.
* Joseph, M., & Pandya, P. — *Finding Response Times in a Real-Time System* — The
  Computer Journal, 1986.
* Buttazzo, G. C. — *Hard Real-Time Computing Systems: Predictable Scheduling
  Algorithms and Applications*.
* Silberschatz, A., Galvin, P. B., & Gagne, G. — *Operating System Concepts*,
  chapter on Real-Time CPU Scheduling.
