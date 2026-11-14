# Exercise 6 — Research Paper and Seminar

Bilingual research paper and two ready-to-present seminar decks on multilevel
queue scheduling, the real-time algorithms EDF and RM, and mutual exclusion.
The paper is a synthesis of Exercises 1 to 4: every number in it is read from
those exercises' `output/experiments.json` files at build time, so none of them
is typed by hand.

## Deliverables

| File | What it is | Measured pages |
|---|---|---|
| `PAPER_EN.md` / `docs/PAPER_EN.docx` / `docs/PAPER_EN.pdf` | the paper, English | **33** |
| `PAPER_FA.md` / `docs/PAPER_FA.docx` / `docs/PAPER_FA.pdf` | the paper, Persian | **31** |
| `docs/SEMINAR_EN.pptx` | seminar deck, English | 26 slides |
| `docs/SEMINAR_FA.pptx` | seminar deck, Persian | 26 slides |

Page counts are the PDF page counts reported by the build, not an estimate.
Both decks carry speaker notes on all 26 slides.

- [Seminar slide outline](SEMINAR_SLIDES.md) — the 26 slides, slide by slide
- [References](REFERENCES.md) — seven verified entries, plus textbooks listed
  without unverified metadata

## What the paper claims, and how

Two methods, kept strictly apart and labelled as such throughout:

| Question | Method | Where |
|---|---|---|
| How fast / how fair / how predictable | discrete-event simulation, deterministic given a scenario file | Exercises 1, 2, 3 |
| Is it correct | exhaustive model checking over every reachable interleaving | Exercise 4 |

The headline results:

- **MLQ has no notion of a deadline.** Measured against EDF and RM on four
  workloads, it behaves inconsistently for exactly that reason — it beats RM on
  the aperiodic workload and loses to it under stress.
- **The RM/EDF gap is a cliff, not a slope.** Across 2 329 random task sets
  (seed 20250101), RM schedulability stays at 100 % below 0.70 utilisation and
  falls to 17.8 % in the top band, while EDF stays at 100 % throughout.
- **Analysis and simulation agree in both directions.** Where the exact test
  says feasible, the simulator reports zero misses; where it says infeasible,
  the simulator finds misses. Exercise 3 confirms both against a hand-worked
  three-task solution, down to the identity and the instant of the single RM
  miss.
- **Three of eight mutual-exclusion algorithms fail, each differently**: the
  lock variable loses safety, announce-then-spin loses progress, and
  test-and-set loses fairness. A correct semaphore used in the wrong order
  deadlocks with no property violated at all.

## Repository layout on this branch

```
README.md                 this file
PAPER_EN.md  PAPER_FA.md  the paper, markdown form
REFERENCES.md             verified bibliography
SEMINAR_SLIDES.md         slide-by-slide outline of both decks
code/build_deck.py        builds docs/SEMINAR_EN.pptx and docs/SEMINAR_FA.pptx
diagrams/                 five figures, all regenerable
docs/                     the deliverables: DOCX, PDF, PPTX
output/deck_numbers.json  the figures the slides quote (generated)
tests/test_deck.py        17 tests over the two decks
```

## Running it

From this folder:

```bash
pip install -r requirements.txt

python3 code/build_deck.py     # rebuild both seminar decks
python3 -m pytest tests -q     # 17 tests
```

`code/build_deck.py` reads `output/deck_numbers.json` instead of recomputing
anything, because the other exercises' data files are not on this branch. To
regenerate the figures **and** that file after an experiment changes, run from
the repository root on the working branch:

```bash
python3 tools/make_figures_ex6.py
python3 tools/build_report.py ex6_en exercise-6 PAPER_EN
python3 tools/build_report.py ex6_fa exercise-6 PAPER_FA
```

## Limits, stated plainly

- **Timings are comparative, not absolute.** They come from CPython under a GIL
  on a shared sandbox, and two mechanisms swing by more than a factor of two
  between runs of the same binary. Only medians are reported, always with their
  spread.
- **The proofs cover two participants** under sequential consistency with
  atomic single-word loads and stores. They say nothing about relaxed memory
  models and nothing about more than two threads.
- **The feasibility study is a sample, not a theorem.** One generator, one
  seed, 2 329 sets.
- **Nothing here is a kernel.** The schedulers are models of policies, so
  measured turnaround reflects the policy's decisions, not the cost of the
  mechanism that would implement them.
- The Exercise 5 demonstration clip was delivered privately to the instructor
  and is deliberately not in this repository.

## Academic note

This is a course submission, not peer-reviewed research. The seven entries in
`REFERENCES.md` were checked against publisher records; the four textbooks are
listed without unverified years, editions or page numbers. No figure in the
paper or the decks is invented: if the code does not produce it, the paper does
not state it.
