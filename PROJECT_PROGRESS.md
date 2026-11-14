# PROJECT PROGRESS

**Repository:** `kaspian021/Multilevel-Queue-Scheduling`
**Last updated:** 2026-11-14
**Session branch (where integration work happens):** `arena/fbc5b096-multilevel-queue-scheduling`
**Master root commit:** `ec6fad1`

This file is the single source of truth for resuming work. **Nothing in it is
claimed unless it has been verified against the actual repository state.**
Page counts below are *measured*, not estimated (see "How page counts are
measured").

---

## 0. Professor's requirements, as corrected by the student

| # | Requirement | Status |
|---|---|---|
| 1 | Six exercises, each on its **own dedicated branch** | Branches exist for 1–6 |
| 2 | Each branch has its **own README** describing only that branch's files | Done for 1, 2, 3 |
| 3 | Bilingual (Persian + English) report per exercise | Done for 1, 2, 3 |
| 4 | **Real DOCX + PDF** per report | Done for 1, 2, 3 |
| 5 | **Word file must be 20–40 pages** | **CORRECTED by the student on 2026-11-14.** An earlier note in this file said ">40 pages for all reports combined". That was wrong. The student's correction: **each exercise's Word file must be 20 to 40 pages.** Exercises 1–3 are at 35, 35 and 24 pages respectively. |
| 6 | Content must be **presentation / slide-style** (ارائه‌ای), not dense prose paragraphs | Done — every page is a slide-like unit: a title, short bullets, tables and figures |
| 7 | Runnable + tested Python code | 59 (Ex1), 38 (Ex2), 29 (Ex3) tests passing |
| 8 | Diagrams, flowcharts, Gantt charts | 14 (Ex1), 20 (Ex2), 6 (Ex3) PNGs |
| 9 | Comparison tables | Present in all reports built so far |
| 10 | Exercise 6 needs a **PPTX with speaker notes** | Not started |
| 11 | No fabricated authors / DOIs / page numbers / dates | Respected; unverifiable items are marked as such |
| 12 | No page padding, no repeated text, no fake whitespace | Respected |
| 13 | Leave "class attendance" and "student grade" columns **blank** | Respected — never fill them in |
| 14 | Never merge into `main`/`master` without explicit approval | Respected — nothing has been merged |

### Exercise 5 — video (recorded exactly, do not alter)

* The Exercise-5 video was **sent privately to the professor**.
* Its duration is **exactly 5 seconds**.
* It is **not** in the repository and must **not** be uploaded publicly.
* No replacement video has been made, no dummy file or fake link has been
  created, and no claim has been made that it contained explanations or code.
* Do not create or send a new video without explicit permission.

---

## 1. Branch map

| Exercise | Branch | Purpose |
|---|---|---|
| 1 | `Exercise-1-Algorithm-Introduction` | Introduction to the MLQ algorithm |
| 2 | `Exercise-2-MLQ-EDF-RM-Comparison` | MLQ vs EDF vs RM comparison |
| 3 | `Exercise-3-EDF-RM-Manual-Scheduling` | Hand-worked EDF/RM solution, three tasks |
| 4 | `Exercise-4-Dekker-Peterson-Semaphore-Monitor` | Dekker, Peterson, semaphore, monitor |
| 5 | `Exercise-5` / `Exercise-5-MLQ-Synchronization` / `exercise-5` | Three pre-existing branches, all still present, **untouched** |
| 6 | `Exercise-6-Paper-And-Seminar` | Paper + seminar PPTX |

Branch tip commits as of this update:

* `Exercise-1-Algorithm-Introduction` → `bf5a743`
* `Exercise-2-MLQ-EDF-RM-Comparison` → `4d8145c9`
* `Exercise-3-EDF-RM-Manual-Scheduling` → `ed00ba0b` (content `c3419654`, then a cleanup commit removing `__pycache__` files that a previous session had accidentally committed)
* Exercise 4, 5, 6 branches → untouched this session

---

## 2. Exercise 1 — COMPLETE

**Branch** `Exercise-1-Algorithm-Introduction`, tip `bf5a743`.

| Language | Markdown | DOCX | PDF | Pages |
|---|---|---|---|---:|
| Persian | `exercise-1/REPORT_FA.md` | `docs/REPORT_FA.docx` | `docs/REPORT_FA.pdf` | **35** |
| English | `exercise-1/REPORT_EN.md` | `docs/REPORT_EN.docx` | `docs/REPORT_EN.pdf` | **35** |

* Simulator: `exercise-1/code/mlq.py` (MLQ: FCFS/RR/SJF per queue, fixed-priority
  preemption between queues, optional aging, validation, text + PNG Gantt, metrics).
* Scenarios: `exercise-1/code/scenarios/*.json` (baseline, policy_mix, starvation,
  timeslice, plus three invalid-input scenarios).
* Experiments: `code/run_experiments.py`; diagrams: `code/make_diagrams.py`.
* **59 tests passing** (`exercise-1/tests/`).
* 14 diagram PNGs.

API note (do not break): `mlq.py` keeps **both** `simulate`/`simulate_full` and
`metrics`/`metrics_full`. Rewriting `simulate()` to return a 3-tuple broke the
original tests. The simulator's Gantt output is **compressed intervals**
`(start, end, name)`, not one entry per tick; `tests/test_mlq_extra.py` expands
them locally.

---

## 3. Exercise 2 — COMPLETE

**Branch** `Exercise-2-MLQ-EDF-RM-Comparison`, tip `4d8145c9`.

| Language | Markdown | DOCX | PDF | Pages |
|---|---|---|---|---:|
| Persian | `exercise-2/COMPARISON_FA.md` | `docs/COMPARISON_FA.docx` | `docs/COMPARISON_FA.pdf` | **35** |
| English | `exercise-2/COMPARISON_EN.md` | `docs/COMPARISON_EN.docx` | `docs/COMPARISON_EN.pdf` | **35** |

* `exercise-2/code/rt_sched.py` — MLQ / EDF / RM / DM simulator plus the analytic
  tests (Liu–Layland bound, RM response-time analysis, EDF processor-demand).
* Four scenarios: `A_fair`, `B_stress`, `C_aperiodic`, `D_overload`.
* **38 tests passing**; 20 figure PNGs; `output/experiments.json` holds every number.

### Analytic verdicts (Exercise 2)

| Scenario | U | RM | EDF |
|---|---:|---|---|
| A_fair | 0.8000 | feasible | feasible |
| B_stress | 0.9714 | **not feasible** (`R_B = 8 > D_B = 7`) | feasible |
| C_aperiodic | 0.9000 | **not feasible** | feasible |
| D_overload | 1.2333 | **not feasible** | **not feasible** |

### Measured (EDF / RM / MLQ)

* `A_fair` (H=40): misses 0/0/0; avg response 3.000 / 3.105 / 3.105; jitter
  2.891 / 3.272 / 3.255; ctx 54/57/54; preempt 9/12/9; util 80.00 %.
* `B_stress` (H=35): misses 0/3/3; avg response 3.833 / 4.000 / 4.000; jitter
  1.424 / 2.449 / 2.449; ctx 36/48/48; preempt 3/15/15; util 97.14 %;
  missed jobs `B#0, B#5, B#10`.
* `C_aperiodic` (horizon 30): misses 0/3/0; avg response 10.857 / 13.000 / 10.857;
  jitter 7.221 / 4.320 / 7.493; ctx 6/6/7; preempt 0/0/1; util 90.00 %.
* `D_overload` (horizon 120, offered 123.33 %, achieved 100 %): misses 31/10/10;
  avg response 18.200 / 11.400 / 11.400; max response 30/96/96; jitter
  6.975 / 20.612 / 20.612; ctx 29/35/35. Per-task misses — RM & MLQ: X 0/15,
  Y 0/12, Z 10/10; EDF: X 13/15, Y 10/12, Z 8/10.

### Random feasibility study (seed 20250101, 2329 task sets)

| Utilisation band | n | RM schedulable % | EDF schedulable % |
|---|---:|---:|---:|
| 0.25–0.50 | 443 | 100.0 | 100.0 |
| 0.50–0.70 | 827 | 100.0 | 100.0 |
| 0.70–0.80 | 366 | 99.7 | 100.0 |
| 0.80–0.90 | 344 | 82.3 | 100.0 |
| 0.90–1.00 | 349 | 17.8 | 100.0 |

---

## 4. Exercise 3 — COMPLETE

**Branch** `Exercise-3-EDF-RM-Manual-Scheduling`, tip `ed00ba0b`.

| Language | Markdown | DOCX | PDF | Pages |
|---|---|---|---|---:|
| Persian | `exercise-3/MANUAL_SOLUTION_FA.md` | `docs/MANUAL_SOLUTION_FA.docx` | `docs/MANUAL_SOLUTION_FA.pdf` | **24** |
| English | `exercise-3/MANUAL_SOLUTION_EN.md` | `docs/MANUAL_SOLUTION_EN.docx` | `docs/MANUAL_SOLUTION_EN.pdf` | **24** |

### Task set

T1(C=1, T=4, D=4), T2(C=3, T=8, D=8), T3(C=4, T=12, D=12).
`U = 23/24 ≈ 0.9583`, hyperperiod `H = 24`, demand in `[0,24)` = 23, idle = 1,
11 jobs.

### Verdicts

* Liu–Layland bound for n=3 is `0.77976 < U` → **inconclusive** (only sufficient).
* RM response-time analysis: `R(T1)=1 ≤ 4`, `R(T2)=4 ≤ 8`, `R(T3)=14 > 12`
  → **RM is NOT schedulable**.
* EDF, implicit deadlines: `U ≤ 1` is necessary and sufficient → **EDF is schedulable**.

### Measured timelines (24 ticks, `-` = idle)

```
t :  0  1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16 17 18 19 20 21 22 23
EDF T1 T2 T2 T2 T1 T3 T3 T3 T1 T3 T2 T2 T1 T2 T3 T3 T1 T2 T2 T2 T1 T3 T3  -
RM  T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3 T3 T1 T2 T2 T2 T1 T3 T3  -
```

* EDF: 0 misses. Per task (min/avg/max response) — T1 1/1.000/1, jitter 0;
  T2 4/4.667/6, jitter 0.943; T3 10/10.500/11, jitter 0.500.
* RM: **1 miss** — `T3 job 0, release 0, deadline 12, finish 14`. Per task —
  T1 1/1.000/1; T2 4/4.000/4, jitter 0; T3 11/12.500/14, jitter 1.500.
* Both: utilisation 95.83 %, idle 1, demand 23, 11 jobs.

### Code, tests and figures

* `exercise-3/code/edf_rm.py` — unit-time preemptive simulator:
  `Task`, `Job`, `validate`, `hyperperiod`, `utilization`, `rm_bound`,
  `simulate`, `segments`, `idle_time`, `response_time_analysis`,
  `format_timeline`, `trace`, plus the new `rm_schedulability`,
  `edf_schedulability`, `summarize`, `step_rows`, `format_summary`, `main_cli`.
  CLI: `python3 code/edf_rm.py --tasks "T1:1:4:4,T2:3:8:8,T3:4:12:12" --json F --table F --lang fa|en`
* `code/run_experiments.py` (new) writes every artefact into `output/`.
* `code/make_figures.py` regenerates all six PNGs.
* **29 tests passing** (27 in `tests/test_edf_rm.py`, 2 in
  `tests/test_manual_solution.py`). The hand-worked 24-tick timelines are locked
  as literal strings, so the code cannot drift from the printed hand solution.
* 6 figures: `gantt_edf.png`, `gantt_rm.png`, `chart_response.png`,
  `chart_utilization.png`, `chart_rta.png`, `fig_release_pattern.png`.

### Housekeeping done on this branch

* `output/MANUAL_SOLUTION_FA.pdf` (an 8-page HTML→Chrome artefact from an
  earlier session) was **removed**, because the real report now lives in
  `docs/` under the same name and two files with the same stem in different
  folders was confusing. `code/build_manual_pdf.py` is kept but now writes
  `output/HAND_WORKSHEET_FA.pdf`; it is an optional extra and needs
  `google-chrome` plus the Vazirmatn font, neither of which is installed in this
  sandbox, so it was **not** used to build `docs/*.pdf`.
* `exercise-1/code/__pycache__/` and `exercise-1/tests/__pycache__/`, which a
  previous session had accidentally committed to this branch, were **deleted**
  (commit `ed00ba0b`). The Exercise-3 branch now contains only `exercise-3/`
  plus the repo-level files inherited from master.

---

## 5. Exercises 4, 5 and 6 — NOT STARTED this session

Current content found on the remote (unchanged, from before this session):

* **Exercise 4** (`Exercise-4-Dekker-Peterson-Semaphore-Monitor`):
  `exercise-4/COMPARISON_FA.md`, `COMPARISON_EN.md`, `README.md`,
  `sync_demo.py`, `test_sync_demo.py`. Gaps: no Dekker / Peterson /
  Readers–Writers implementations, no DOCX/PDF, no diagrams, page count far
  below the 20-page floor.
* **Exercise 5**: three branches exist (`Exercise-5`,
  `Exercise-5-MLQ-Synchronization`, `exercise-5`). All left untouched. The only
  Exercise-5 fact on record is the private 5-second video — see section 0.
* **Exercise 6** (`Exercise-6-Paper-And-Seminar`): `PAPER_EN.md`, `PAPER_FA.md`,
  `README.md`, `REFERENCES.md`, `SEMINAR_SLIDES.md`. Gaps: no PPTX, no speaker
  notes, references not verified against real sources.

---

## 6. Tooling (lives on the session branch, not on the exercise branches)

| Path | Purpose |
|---|---|
| `tools/report_kit.py` | `Report` model, page blocks, `exact_heights()`, `build_pdf()`, `render_markdown`, `build_docx`, `pdf_page_count` |
| `tools/build_report.py` | CLI: `python3 tools/build_report.py <module> <exercise> <STEM>`; prints JSON with pages, pdf_pages, overflow, max_page_fill, missing_figures, missing_glyphs; **exits 1** on overflow or a missing figure |
| `tools/check_outputs.py` | Re-measures artefacts: PDF pages are exact, DOCX pages are a measured estimate with `max_page_fill` |
| `tools/push_to_branch.sh` | Publishes one folder onto a long-lived branch **without checking it out** |
| `tools/content/ex{1,2,3}_{fa,en}.py` | Report content modules; each `build()` returns a `Report` |
| `tools/fonts/Vazirmatn-{400,700}.ttf` | Merged Persian TTFs used by ReportLab |

### How page counts are measured

`build_report.py` renders each page with ReportLab and reports `pdf_pages`
(read back out of the PDF — exact) and `pages` (the DOCX count, a *measured
estimate* because Word reflows text). `tools/check_outputs.py` re-measures the
artefacts afterwards. `max_page_fill` is the fraction of the A4 text frame used
by the fullest page; it must stay below ~0.75 so Word's reflow cannot spill a
page. A page count is only reported here after both tools agree.

### Layout constraints (learned the hard way)

* A4, margins 1.9 cm horizontally / 1.7 cm vertically; text frame ≈ 17.2 × 26.3 cm.
* The usable frame height is ≈ 746 pt. **Keep every image ≤ 15.8 cm wide** and
  well under that height — ReportLab cannot split an image across pages and
  fails with `LayoutError: Flowable <Image> too large on page`.
* **Never trust `estimate_height()`/`validate()` for page fitting** — use
  `exact_heights()`.
* Vazirmatn lacks `→ ≤ ≥ Σ √ ▪ ■` and **τ**. Use `SYMBOL_MAP` and the glyph
  guard, which must run **after** XML escaping, or write Latin transliterations
  (`tau_i`) in Persian text.
* Persian text extracted from a PDF by `pypdf` looks reversed/isolated — that is
  an extraction artefact, never judge Persian output that way.
* LibreOffice is unavailable in this sandbox, so PDFs are authored directly with
  ReportLab rather than converted from DOCX.
* `git add -f -- "$DIR"` bypasses `.gitignore` and was what committed the
  `__pycache__` files; `push_to_branch.sh` now uses `git add -A -- "$DIR"`.

---

## 7. What to do next

1. **Exercise 4** — implement Dekker, Peterson, semaphore and monitor
   (including Readers–Writers) in `exercise-4/code/`, with tests, then build the
   bilingual 20–40-page reports with `tools/build_report.py`.
2. **Exercise 6** — verify the references against real sources, then build the
   PPTX with speaker notes.
3. **Exercise 5** — only record the status of the private 5-second video; ask
   before doing anything else with it.
4. Keep this file updated at the end of every piece of work.

---

## 8. Changelog

| Date | Change |
|---|---|
| 2026-11-14 | Exercise 1 completed and pushed (`bf5a743`, 35/35 pages, 59 tests). |
| 2026-11-14 | Exercise 2 completed and pushed (`4d8145c9`, 35/35 pages, 38 tests). |
| 2026-11-14 | Exercise 3 completed and pushed (`c3419654`, 24/24 pages, 29 tests, 6 figures); branch cleaned in `ed00ba0b`. |
| 2026-11-14 | **Correction applied:** the page rule is 20–40 pages **per Word report**, not ">40 pages for all reports combined" as an earlier note here claimed. |
| 2026-11-14 | This file rewritten from scratch to reflect only verified state. |
