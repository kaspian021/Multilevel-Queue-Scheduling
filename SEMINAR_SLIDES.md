# Seminar decks — slide outline

Two ready-to-present decks are shipped on this branch, built from the outline
below by `code/build_deck.py`:

| File | Language | Slides | Speaker notes |
|---|---|---|---|
| `docs/SEMINAR_EN.pptx` | English | 26 | on every slide |
| `docs/SEMINAR_FA.pptx` | Persian (Vazirmatn, RTL) | 26 | on every slide |

Both decks are 16:9 and carry four figures from `diagrams/`. The two languages
have identical slide **kinds** in identical order, so the English and Persian
presentations stay in step slide by slide.

## The outline

| # | Kind | Slide | What it establishes |
|---|---|---|---|
| 1 | title | Multilevel Queue Scheduling: design, limits, and what it costs | scope and repository |
| 2 | section | 1 — The problem |  |
| 3 | bullets | Multilevel Queue in one slide | fixed queues, per-queue policy, inter-queue arbitration |
| 4 | bullets | Design decisions that actually matter | queue count, per-queue policy, aging |
| 5 | picture | Design decision one: how patient should the scheduler be? | `fig_aging.png` — the aging threshold sweep |
| 6 | section | 2 — Method |  |
| 7 | bullets | Two different kinds of claim | measured vs proved, and why neither substitutes |
| 8 | section | 3 — Results: scheduling |  |
| 9 | table | Measured: MLQ against EDF and RM | four workloads, misses per algorithm |
| 10 | bullets | What overload reveals | the miss count hides who suffers |
| 11 | picture | The same task set, two choices about who suffers | `fig_overload_gantt.png` |
| 12 | bullets | Schedulability: what can be known | Liu–Layland is sufficient only |
| 13 | picture | Where rate monotonic stops working | `fig_utilisation_cliff.png` |
| 14 | section | 4 — Results: mutual exclusion |  |
| 15 | table | Eight algorithms, checked exhaustively | safety / deadlock / starvation per algorithm |
| 16 | picture | Three ways to be wrong | `fig_property_matrix.png` |
| 17 | bullets | Three failures, three lessons | safety vs progress vs fairness |
| 18 | bullets | Deadlock is a usage error | a correct primitive, used wrongly |
| 19 | bullets | Monitors: the abstraction that helps | Mesa semantics and the `while` re-test |
| 20 | bullets | Readers and writers: fairness has a price | read share for three variants |
| 21 | section | 5 — Cost |  |
| 22 | bullets | Under contention, blocking degrades gently | predictability, not raw speed |
| 23 | section | 6 — Conclusions |  |
| 24 | bullets | Limitations, stated plainly | what the results do not cover |
| 25 | bullets | Reproducing everything | one command per artefact |
| 26 | closing | Questions |  |

## About the speaker notes

The notes are a **spoken script**, not a restatement of the bullets. Two tests
enforce that:

- every slide has notes longer than 80 characters;
- the notes are never equal to the slide's own body text.

On the shipped decks the notes run from 124 to 691 characters, averaging around
300, so the deck can be delivered without a separate script.

## Rebuilding the decks

```bash
# figures and output/deck_numbers.json, from the repository root
python3 tools/make_figures_ex6.py

# the two decks, from this folder
python3 code/build_deck.py

# checks
python3 -m pytest tests -q
```

`code/build_deck.py` reads `output/deck_numbers.json` rather than computing
anything, so it runs on this branch where the other exercises' data files are
not present. Regenerate that file with `tools/make_figures_ex6.py` whenever an
experiment changes; a test fails if a published number is no longer quoted
anywhere in the decks.

## Presentation cautions

- Do not present the feasibility study as a theorem. It is a reproducible
  sample of 2 329 task sets from one generator with one seed.
- Do not present the timings as absolute; they are medians from a shared
  sandbox and two of them swing by more than a factor of two between runs.
- Do not say EDF is "worse" under overload because it misses more deadlines.
  It misses different ones, and that is a design choice.
