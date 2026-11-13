# Exercise 2 — MLQ vs EDF vs RM
This study compares the repository's fixed MLQ configuration with Earliest Deadline First (EDF) and Rate Monotonic (RM). See [English analysis](COMPARISON_EN.md) and [تحلیل فارسی](COMPARISON_FA.md).

## Fair comparison rules
A valid real-time comparison must use the same task set, release times, execution costs, deadlines, processor model, preemption assumptions, and overhead assumptions. MLQ is not inherently a deadline-driven policy. EDF chooses the ready job with the earliest absolute deadline; RM assigns static priority by shorter period. The MLQ implementation in this repository chooses a fixed queue first and has no deadline test.

## Scope
The report distinguishes qualitative policy comparison from a schedulability proof. EDF utilization bound U≤1 applies to independent preemptive periodic tasks on one processor under the classic assumptions and implicit deadlines. RM's Liu-Layland sufficient bound for n tasks is n(2^(1/n)-1), approaching ln 2; it is sufficient, not necessary. For constrained/arbitrary deadlines or blocking, more detailed analysis is required.

## Required experiments
Run all policies on identical generated task sets, include release/deadline traces, count missed deadlines, and report response, waiting, utilization and overhead. Never infer a real-time guarantee from one successful trace.
