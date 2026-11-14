# PROJECT_PROGRESS

Last updated: 2026-11-14 (Exercise-3 branch copy). Honest status — nothing here is claimed unless verified.

## Access
- Push works now (verified with git ls-remote).
- Page rule confirmed by student: >40 pages applies to ALL reports combined; some may be shorter.
- Persian font Vazirmatn installed locally; PDFs built via headless Chrome (XeLaTeX lacks `bidi`).

## Existing state found (remote)
| Ex | Branch | Found | Gap vs. instructor table |
|---|---|---|---|
| 1 | Exercise-1-Algorithm-Introduction | short FA/EN markdown (~7–10 KB), no code | no runnable simulator, no DOCX/PDF, far below 40 pages |
| 2 | Exercise-2-MLQ-EDF-RM-Comparison | short FA/EN markdown | no numeric experiment, no charts, no DOCX/PDF, <40 pages |
| 3 | Exercise-3-EDF-RM-Manual-Scheduling | small script + test | no manual-solution PDF, no Gantt charts |
| 4 | Exercise-4-Dekker-Peterson-Semaphore-Monitor | short FA/EN, semaphore/monitor demo | no Dekker/Peterson/Readers-Writers code, no DOCX/PDF |
| 5 | (no clip in repo) | — | private 5-second video sent to instructor; adequacy = needs instructor review |
| 6 | Exercise-6-Paper-And-Seminar | paper drafts, slide outline | no PPTX, no speaker notes/speech, references unverified |
Extra branches present: Exercise-5, Exercise-5-MLQ-Synchronization, exercise-5 (not in the expected list; left untouched).

## Done in this session
- Exercise 1: `exercise-1/code/mlq.py` (MLQ simulator: FCFS/RR/SJF per queue, fixed-priority preemption between queues, optional aging, validation, Gantt text/PNG, metrics), scenario JSON, `tests/test_mlq.py`.
  - Real run: **15 tests passed, 0 failed** (`exercise-1/output/pytest_result.txt`); baseline Gantt/metrics hand-verified (`output/baseline_result.txt`, `output/gantt_baseline.png`).

## Not done (remaining)
- Ex1: expanded FA/EN reports, DOCX/PDF, flowchart, README run commands.
- Ex2–Ex4, Ex6: everything listed under "Gap" above.
- Ex5: video — only record status (private, 5 s). No new video made.
- Page counts: **not measured; no report currently reaches 40 pages.** Ambiguity: "more than 40 pages" per report vs. total is unconfirmed — ask instructor.

## Next step
Grant push access, then continue with Exercise 1 reports (FA/EN) using results in `exercise-1/output/`.

## Update: Exercise 3 (this branch)
- Done: `exercise-3/code/edf_rm.py`, `make_figures.py`, `build_manual_pdf.py`; Gantt PNGs (EDF, RM); `output/MANUAL_SOLUTION_FA.pdf` (**8 pages**, fonts embedded, visually checked pages 2-4); README.
- Tests: **16 passed, 0 failed** (`exercise-3/output/pytest_result.txt`). EDF: 0 misses; RM: 1 miss (T3 job 0, finish 14 > 12), idle 1/24.
- Not done for Ex3: English hand-solution, DOCX version, Markdown copies (MANUAL_SOLUTION_FA/EN.md).
- Exercise-1 code lives on branch Exercise-1-Algorithm-Introduction (pushed, commit 1bf4ec4).
- Next: Exercise 4 (Dekker/Peterson/Readers-Writers code + tests), then 2, 1 reports, 6.
