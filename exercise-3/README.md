# Exercise 3 — EDF and RM scheduling of three tasks, hand solution

**Printable Persian hand solution:** [`output/MANUAL_SOLUTION_FA.pdf`](output/MANUAL_SOLUTION_FA.pdf) (8 pages, A4, Vazirmatn font; includes blank grids for hand re-writing).

## Task set (periodic, single preemptive CPU, phase 0)
| Task | C | T | D |
|---|---:|---:|---:|
| T1 | 1 | 4 | 4 |
| T2 | 3 | 8 | 8 |
| T3 | 4 | 12 | 12 |

U = 23/24 ≈ 0.9583, hyperperiod 24, idle = 1 unit in [0,24).
- **EDF:** no deadline miss (U ≤ 1 is necessary and sufficient for implicit deadlines).
- **RM:** the Liu–Layland bound for n=3 is 0.7798 < U, so that test is inconclusive; exact response-time analysis gives R(T3)=14 > 12, and the simulation shows T3's first job missing its deadline at t=12 (finishes at 14).

Tie rule (EDF): equal absolute deadlines → lower task index first. A missed job keeps running (not aborted).

## Run
```bash
cd exercise-3/code
python3 edf_rm.py            # small demo
python3 make_figures.py      # writes ../diagrams/gantt_edf.png, gantt_rm.png
python3 build_manual_pdf.py  # needs google-chrome and the Vazirmatn font
python3 -m pytest ../tests -q
```
Tests: 16 passed (hand-solved timelines for both algorithms, response-time analysis, validation, trace vs. simulation).

## Limits
One synchronous task set analysed over one hyperperiod. This is not a general claim that EDF beats RM; it ignores context-switch cost and non-periodic effects. The earlier one-shot illustration remains in `code/manual_solution.py` for reference. No scan of handwriting is provided.
