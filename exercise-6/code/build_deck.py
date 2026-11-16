"""Build the Exercise-6 seminar decks (English and Persian) with speaker notes.

    python code/build_deck.py

Writes ``docs/SEMINAR_EN.pptx`` and ``docs/SEMINAR_FA.pptx``.

Every slide carries real speaker notes: a spoken script, not a restatement of
the bullet points. The notes are what the presenter actually says, including
timing cues, so the deck can be delivered without a separate script.

Persian slides are written as logical Unicode text with ``rtl="1"`` set on each
paragraph and the Vazirmatn font, which lets PowerPoint and LibreOffice do
their own bidi layout. No pre-shaped presentation forms are used, so the text
stays searchable and copyable.
"""
from __future__ import annotations

import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Emu, Inches, Pt

import json                                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOCS = os.path.join(ROOT, "docs")
DIAGRAMS = os.path.join(ROOT, "diagrams")
NUMBERS = os.path.join(ROOT, "output", "deck_numbers.json")
os.makedirs(DOCS, exist_ok=True)


def _load_numbers():
    """The figures the slides quote, published by tools/make_figures_ex6.py.

    The deck has to build on the Exercise-6 branch, where the experiment JSON
    files of the other exercises are not present, so it reads this snapshot
    instead of recomputing anything.
    """
    if not os.path.exists(NUMBERS):
        raise SystemExit(
            f"{NUMBERS} is missing. Run, from the repository root:\n"
            f"    python3 tools/make_figures_ex6.py")
    with open(NUMBERS, encoding="utf-8") as f:
        return json.load(f)


N = _load_numbers()

W, H = Inches(13.333), Inches(7.5)          # 16:9

NAVY = RGBColor(0x1F, 0x36, 0x5D)
ACCENT = RGBColor(0xD9, 0x81, 0x2B)
LIGHT = RGBColor(0xF2, 0xF4, 0xF8)
GREY = RGBColor(0x55, 0x5B, 0x66)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

LATIN_FONT = "Calibri"
PERSIAN_FONT = "Vazirmatn"


# ============================================================== slide content
def _en_slides():
    return [
        dict(kind="title", title="Multilevel Queue Scheduling: design, limits, "
                                 "and what it costs",
             subtitle="A measured and verified study of MLQ, EDF, RM and "
                      "mutual exclusion",
             meta="Advanced Operating Systems — Exercise 6 seminar",
             notes=("Good morning. In the next twenty minutes I will argue one "
                    "thing: that our intuition about which scheduling algorithm "
                    "is 'best' is usually wrong, and that the only way to "
                    "settle it is to measure and, where possible, to prove. "
                    "Everything I show you today comes from code I wrote and "
                    "ran for this course, not from a textbook diagram.")),
        dict(kind="section", title="1 — The problem",
             notes=("Let me start by stating the problem precisely, because most of the confusion around scheduling comes from an imprecise statement of what we are optimising. Before we compare any two algorithms I want us to agree on what 'better' would even mean, and on why no single algorithm can be better at everything at once.")),
        dict(kind="bullets", title="Multilevel Queue in one slide",
             bullets=[
                 "Several ready queues, each with its own priority and its own "
                 "scheduling policy.",
                 "A job is assigned to a queue once, by class: interactive, "
                 "batch, system.",
                 "Scheduling happens between queues first (fixed priority), "
                 "then inside a queue (FCFS, SJF or RR).",
                 "The between-queues rule is what makes it 'multilevel'; it is "
                 "also where starvation comes from.",
             ],
             notes=("Emphasise that MLQ is not one algorithm; it is a template. "
                    "The interesting design decisions are how many queues, what "
                    "policy inside each, and whether a job can ever move "
                    "between queues. Fixed assignment is the classic MLQ; "
                    "movable jobs make it a multilevel feedback queue, which is "
                    "a different animal.")),
        dict(kind="bullets", title="Design decisions that actually matter",
             bullets=[
                 "Number of queues: three is a convention, not a law.",
                 "Policy per queue: RR for interactive, FCFS for batch.",
                 "Time quantum inside an RR queue: too small wastes CPU on "
                 "context switches, too large degenerates into FCFS.",
                 "Aging: promote a job that has waited too long. With aging, "
                 "starvation disappears; without it, it is guaranteed.",
             ],
             notes=("This is the slide where the audience should write "
                    "something down. The quantum choice is the one people get "
                    "wrong: the folklore answer is 'about ten milliseconds', "
                    "but the right answer depends on the cost of a context "
                    "switch on your machine relative to your workload.")),
        dict(kind="picture", title="Design decision one: how patient should "
                              "the scheduler be?",
             image="fig_aging.png",
             caption="Aging threshold sweep. Red: waiting time of the lowest "
                     "queue. Blue: mean waiting over all queues.",
             notes=("This is the first design decision, and it is the one "
                    "people usually skip. The red line is the job in the "
                    "lowest queue; with aging switched off it waits twenty "
                    "ticks. Turn aging on with a threshold of two and it "
                    "waits six. Now look at the blue line, which is the cost "
                    "to everyone else: it barely moves, and in fact it drops "
                    "slightly. That is the argument for aging, and it is a "
                    "measured argument rather than an appeal to fairness. "
                    "At the right-hand end both lines flatten, because the "
                    "threshold has grown past the length of the run and "
                    "nothing is ever promoted. So there is a usable range, "
                    "not a magic value.")),
        dict(kind="section", title="2 — Method",
             notes=("Before I show results, I want to spend two slides on how the results were obtained. This matters more than the numbers themselves, because a number without a method is just an assertion with a decimal point. I will separate the claims I measured from the claims I could actually prove, and I will not blur the two.")),
        dict(kind="bullets", title="Two different kinds of claim",
             bullets=[
                 "Measured claims: 'under this workload and this machine, X was "
                 "faster'. Sampling and timing.",
                 "Proved claims: 'no execution of this algorithm ever breaks "
                 "mutual exclusion'. Exhaustive enumeration.",
                 "A passing test is a measured claim and can never become a "
                 "proof.",
                 "A proof is conditional on its model: here, sequential "
                 "consistency and atomic loads and stores.",
             ],
             notes=("This distinction runs through the whole project. In the "
                    "scheduling part I can only measure. In the mutual "
                    "exclusion part I could actually prove things, because the "
                    "state spaces turned out to be tiny. I will come back to "
                    "that.")),
        dict(kind="section", title="3 — Results: scheduling",
             notes=("Now the results. I will show four scenarios, then the comparison against the real-time algorithms. The four workloads are deliberately chosen to cover a comfortable load, a tight one, a case outside the periodic model, and a genuine overload, because an algorithm that only works at eighty percent utilisation is not finished.")),
        dict(kind="table", title="Measured: MLQ against EDF and RM",
             headers=["Scenario", "EDF misses", "RM misses", "MLQ misses",
                      "Utilisation"],
             rows=[["A — fair", "0", "0", "0", "80.0 %"],
                   ["B — stress", "0", "3", "3", "97.1 %"],
                   ["C — aperiodic", "0", "3", "0", "90.0 %"],
                   ["D — overload", "31", "10", "10", "100 % achieved"]],
             notes=("Look at column two against column three. EDF never misses "
                    "until the system is genuinely overloaded, and even then it "
                    "misses differently. Now look at scenario C: MLQ actually "
                    "beats RM there, even though MLQ has no notion of a "
                    "deadline at all. That is luck, not design — and I say so in "
                    "the paper.")),
        dict(kind="bullets", title="What overload reveals",
             bullets=[
                 "At 123 % offered load, the processor still only achieves "
                 "100 %: the rest is simply work that cannot be done.",
                 "EDF misses 31 jobs; RM and MLQ miss 10 each.",
                 "EDF spreads the pain across all three tasks; RM and MLQ "
                 "sacrifice the lowest-priority task almost completely.",
                 "This is not 'EDF is worse at overload'. It is a different "
                 "choice about who suffers.",
             ],
             notes=("This is the slide I would defend in questions. A naive "
                    "reading says EDF is worse because 31 is more than 10. The "
                    "honest reading is that EDF refuses to protect any "
                    "priority class, while RM and MLQ protect the high-"
                    "priority tasks by abandoning the lowest one entirely. For "
                    "a hard real-time system you usually want the second "
                    "behaviour, and that is a design requirement, not a "
                    "metric.")),
        dict(kind="picture", title="The same task set, two choices about who "
                              "suffers",
             image="fig_overload_gantt.png",
             caption=f"Scenario D, {N['D_load_pct']}% offered load, "
                     f"{N['horizon_D']} ticks. EDF above, RM below. Red ticks "
                     f"are deadlines.",
             notes=("This slide is the one I would want people to remember. "
                    "Same tasks, same 120 ticks, same processor. On the top, "
                    "EDF: it refuses to protect any priority class, so all "
                    "three tasks miss deadlines and the total is thirty-one. "
                    "On the bottom, RM: it protects X and Y and abandons Z, "
                    "and the total is only ten. If you only look at the miss "
                    "count you conclude EDF is three times worse, and that "
                    "conclusion is wrong. What actually differs is the "
                    "choice about who suffers. In a hard real-time system "
                    "you usually want the second behaviour on purpose, "
                    "which makes it a requirement you write down, not a "
                    "number you optimise.")),
        dict(kind="bullets", title="Schedulability: what can be known",
             bullets=[
                 f"For RM, the Liu–Layland bound n(2^(1/n) − 1) is sufficient "
                 f"but not necessary: at n = 3 it is {N['liu_layland_n3']}.",
                 "Above the bound the test says nothing — you must run exact "
                 "response-time analysis instead.",
                 "For EDF with implicit deadlines, U ≤ 1 is both necessary and "
                 "sufficient. No slack, no guessing.",
                 f"A random study over {N['sets']:,} task sets reproduced the "
                 f"familiar cliff: at 90–100 % utilisation only "
                 f"{N['rm_top_pct']} % of sets were RM schedulable against "
                 f"100 % for EDF.",
             ],
             notes=(f"The bound is {N['liu_layland_n3']} at n = 3 and "
                    "approaches ln 2, about 0.693, as n grows. People quote "
                    "the 0.69 figure as if it were the bound; it is the limit "
                    f"of the bound. And the random study is the honest way to "
                    f"say 'in practice': it is a sample of {N['sets']:,} sets "
                    f"with a fixed seed, so it is reproducible but it is "
                    f"still a sample.")),
        dict(kind="picture", title="Where rate monotonic stops working",
             image="fig_utilisation_cliff.png",
             caption=f"{N['sets']:,} random task sets, seed {N['seed']}, "
                     f"classified by utilisation.",
             notes=("This is the headline number of the whole project. "
                    "Orange is rate monotonic, blue is EDF, and the vertical "
                    "axis is the percentage of randomly generated task sets "
                    "that are schedulable. Below about seventy per cent "
                    "utilisation the two are indistinguishable, both at a "
                    "hundred per cent. Then the orange line falls off a "
                    f"cliff: {N['rm_mid_pct']} per cent in the next band, "
                    f"and {N['rm_top_pct']} per cent in the top band. EDF "
                    f"stays flat at a "
                    "hundred, exactly as the theory predicts for implicit "
                    "deadlines. The dotted line is the Liu and Layland bound. "
                    "Everything to its left is guaranteed by the bound "
                    "alone; to its right the bound is silent and only the "
                    "exact response-time test can answer.")),
        dict(kind="section", title="4 — Results: mutual exclusion",
             notes=("Second half. Same project, different question: not 'how fast' but 'is it correct'. Here I could stop measuring and start proving, because the state spaces of these mutual-exclusion algorithms turned out to be small enough to enumerate completely. That changes the kind of claim I am allowed to make.")),
        dict(kind="table", title="Eight algorithms, checked exhaustively",
             headers=["Algorithm", "States", "Mutual exclusion", "Deadlock free",
                      "Starvation free"],
             rows=[["Dekker", "324", "holds", "yes", "yes"],
                   ["Peterson", "199", "holds", "yes", "yes"],
                   ["lock variable", "60", "VIOLATED", "yes", "no"],
                   ["announce-then-spin", "55", "holds", "NO", "yes"],
                   ["test-and-set", "51", "holds", "yes", "NO"],
                   ["binary semaphore", "22", "holds", "yes", "yes"],
                   ["wrong lock order", "48", "holds", "NO", "yes"],
                   ["Mesa monitor", "54", "holds", "yes", "yes"]],
             notes=(f"Eight algorithms, and the biggest state space is "
                    f"{N['model_states_max']} states, which is why all of "
                    f"this can be exhaustive rather than sampled. Read the "
                    f"three failures, because they fail in three "
                    "different ways. Lock variable loses safety. "
                    "Announce-then-spin keeps safety and loses progress. Test-"
                    "and-set keeps both and loses fairness. And the seventh row "
                    "is my favourite: a perfectly correct primitive, used in "
                    "the wrong order, deadlocks the whole system.")),
        dict(kind="picture", title="Three ways to be wrong",
             image="fig_property_matrix.png",
             caption="Every cell is an exhaustive verdict over the whole "
                     "reachable state space, not a sample.",
             notes=("I like this grid because it separates three things that "
                    "testing tends to conflate. The lock-variable protocol "
                    "loses safety: the read and the write are separate "
                    "steps, so both processes can see the lock free. "
                    "Announce-then-spin keeps safety and loses progress: "
                    "both can announce before either looks. Test-and-set "
                    "keeps both and loses fairness: nothing remembers who "
                    "waited longest. Three columns, three distinct failure "
                    "modes. And then look at the last-but-one row: the "
                    "wrong-order semaphore has no red cell at all, because "
                    "every property of the primitive holds, and it still "
                    "deadlocks the program. That failure is in the caller, "
                    "and no amount of verifying the primitive would have "
                    "caught it.")),
        dict(kind="bullets", title="Three failures, three lessons",
             bullets=[
                 "Look-then-announce: the read and the write are separate "
                 "steps, so both processes can see 'free'. Safety lost.",
                 "Announce-then-look: safe, but both can announce before either "
                 "looks. Progress lost.",
                 "Test-and-set: safe and live, but nothing remembers who waited "
                 "longest. Bounded waiting lost.",
                 "Each failure is invisible in a short test run.",
             ],
             notes=("Note the symmetry between rows one and two: swapping the "
                    "order of two adjacent lines converts a safety bug into a "
                    "liveness bug. That is a genuinely surprising result and "
                    "worth pausing on.")),
        dict(kind="bullets", title="Deadlock is a usage error",
             bullets=[
                 "Four conditions are needed: mutual exclusion, hold-and-wait, "
                 "no preemption, circular wait.",
                 "None of them is about the quality of the lock.",
                 "Measured: with opposite orders, thread 0 holds A and blocks "
                 "on B while thread 1 holds B and blocks on A — every time.",
                 "With a global lock order the identical program always "
                 "finishes.",
             ],
             notes=("I made this deterministic on purpose, with a barrier "
                    "between the two acquisitions and a non-blocking second "
                    "acquire, so it cannot be dismissed as scheduler luck. The "
                    "takeaway for anyone writing multi-lock code: agree on an "
                    "order, write it down, and enforce it in review.")),
        dict(kind="bullets", title="Monitors: the abstraction that helps",
             bullets=[
                 "A monitor bundles state with the operations on it and "
                 "guarantees one thread inside at a time.",
                 "Condition variables let a thread wait for a predicate and "
                 "release the lock while waiting.",
                 "Under Mesa semantics a woken thread must re-check: measured "
                 "at capacity 1, it had to wait again 1,383 times.",
                 "That number is the argument for the while-loop, and it is not "
                 "stylistic.",
             ],
             notes=("If anyone asks why we do not just use `if`, the answer is "
                    "on this slide: 1,383 times in one run, the predicate was "
                    "false again by the time the woken thread got the lock "
                    "back. Replace `while` with `if` and those become silent "
                    "corruptions.")),
        dict(kind="bullets", title="Readers and writers: fairness has a price",
             bullets=[
                 "Readers preference: 189,832 reads against 5 writes. The "
                 "writer is overtaken essentially every time.",
                 "Writers preference: the mirror image — 1,165,632 writes "
                 "against 479,104 reads.",
                 "Fair FIFO: a read share of 0.898, close to the arrival ratio "
                 "of six readers to one writer, which is what fairness means.",
                 "You cannot have maximum concurrency and no starvation "
                 "simultaneously.",
             ],
             notes=("Frame this as a trade-off, not a bug. Readers preference "
                    "is the right answer when writes are rare and latency "
                    "matters. Fair FIFO is the right answer when a stale write "
                    "is dangerous. The point is to choose deliberately.")),
        dict(kind="section", title="5 — Cost",
             notes=("Finally, what all of this costs. These are medians over repeated runs, because a single timing on a shared machine is worthless. When I first measured this, the same workload varied by more than a factor of ten between runs, so reporting one number would have been reporting noise.")),
        dict(kind="bullets", title="Under contention, blocking degrades "
                              "gently",
             bullets=[
                 "Blocking mechanisms degrade gently: a blocked thread frees "
                 "the CPU.",
                 "With two or four threads the spinlock is actually faster — "
                 "554k and 624k ops/s against 525k and 532k. It only falls "
                 "behind at eight threads: 477k against 494k and 511k.",
                 "A spinlock is right only when the critical section is shorter "
                 "than a context switch — true in a kernel, rarely in "
                 "application code.",
                 "If the lock holder is descheduled, every spinner wastes a "
                 "whole time slice.",
             ],
             notes=("Be careful here, because the obvious claim is wrong. "
                    "At two and four threads the spinlock wins outright; the "
                    "reason is that with a short critical section, spinning "
                    "is cheaper than a kernel wait and wake. What changes at "
                    "eight threads is not really the throughput, which only "
                    "drops by about a quarter. It is the spin count: nearly "
                    "six times the two-thread figure. That is CPU time bought "
                    "by nobody, and on a machine where the lock holder can be "
                    "descheduled it is a whole time slice wasted by every "
                    "spinner. So the honest summary is not 'blocking is "
                    "faster', it is 'blocking is predictable'.")),
        dict(kind="section", title="6 — Conclusions",
             notes=("Two minutes of conclusions, then questions. I will give you five take-aways, state the limitations of the work as plainly as I can, and then stop talking.")),
        dict(kind="bullets", title="Limitations, stated plainly",
             bullets=[
                 "Single machine, shared sandbox, CPython with a GIL: the "
                 "timings indicate relative cost, not absolute performance.",
                 "The mutual-exclusion proofs cover two participants and "
                 "assume sequential consistency.",
                 "The schedulability study is a reproducible sample of 2,329 "
                 "task sets, not a theorem.",
                 "No claim here is about a specific commercial operating "
                 "system.",
             ],
             notes=("Do not skip this slide in the delivery. Stating "
                    "limitations is what separates an engineering result from "
                    "a marketing claim, and it is the first thing a good "
                    "examiner will look for.")),
        dict(kind="bullets", title="Reproducing everything",
             bullets=[
                 "Each exercise lives on its own branch, with its own README "
                 "at the branch root.",
                 "One command per artefact: the simulator, the experiment "
                 "runner, the figure generator, the test suite.",
                 "Reports are generated from content modules that read their "
                 "numbers from the experiment output, so prose and code cannot "
                 "drift apart.",
                 "Bibliography entries were checked against publisher records; "
                 "see REFERENCES.md.",
             ],
             notes=("Point people at the repository. Everything in this deck "
                    "is regenerable, including the deck itself, which is built "
                    "by code/build_deck.py.")),
        dict(kind="closing", title="Questions",
             subtitle="github.com/kaspian021/Multilevel-Queue-Scheduling",
             notes=("Thank you. I am happy to take questions on any of the "
                   "six exercises, and I can re-run any experiment live if "
                   "that is useful.")),
    ]


def _fa_slides():
    return [
        dict(kind="title", title="زمان‌بندی چندسطحی: طراحی، محدودیت‌ها و هزینهٔ آن",
             subtitle="مطالعه‌ای اندازه‌گیری‌شده و اثبات‌شده از MLQ، EDF، RM و انحصار متقابل",
             meta="سیستم‌عامل پیشرفته — سمینار تمرین ششم",
             notes=("با سلام. در بیست دقیقهٔ پیشِ رو یک ادعا را مطرح می‌کنم: اینکه "
                    "شهود ما دربارهٔ اینکه کدام الگوریتم زمان‌بندی «بهتر» است معمولاً "
                    "غلط است، و تنها راه حل کردن آن اندازه‌گیری و هرجا ممکن باشد "
                    "اثبات است. هرچه امروز نشان می‌دهم از کدی می‌آید که برای این "
                    "درس نوشته و اجرا کرده‌ام، نه از نمودار یک کتاب درسی.")),
        dict(kind="section", title="۱ — مسئله",
             notes=("اجازه بدهید با بیان دقیق مسئله شروع کنم، چون بیشترِ سردرگمی پیرامون زمان‌بندی از بیانِ نادقیقِ این است که چه چیزی را بهینه می‌کنیم. پیش از آنکه دو الگوریتم را با هم مقایسه کنیم، می‌خواهم بر سرِ معنای «بهتر» توافق کنیم و بر سرِ اینکه چرا هیچ الگوریتمی نمی‌تواند در همه چیز هم‌زمان بهتر باشد.")),
        dict(kind="bullets", title="صف چندسطحی در یک اسلاید",
             bullets=[
                 "چند صف آماده، هر یک با اولویت و سیاست زمان‌بندی خود.",
                 "یک کار یک‌بار به یک صف نسبت داده می‌شود، بر پایهٔ طبقه: "
                 "تعاملی، دسته‌ای، سیستمی.",
                 "نخست میان صف‌ها زمان‌بندی می‌شود (اولویت ثابت)، سپس درون یک صف "
                 "(FCFS، SJF یا RR).",
                 "قاعدهِ میان‌صفی است که آن را «چندسطحی» می‌کند؛ و همان‌جاست که "
                 "گرسنگی از آن بیرون می‌آید.",
             ],
             notes=("تأکید کنید که MLQ یک الگوریتم نیست؛ یک قالب است. تصمیم‌های "
                    "جالبِ طراحی عبارت‌اند از: چند صف، چه سیاستی درون هر کدام، و "
                    "اینکه آیا یک کار می‌تواند میان صف‌ها جابه‌جا شود. نسبت‌دهی "
                    "ثابت همان MLQ کلاسیک است؛ کارهای قابل‌جابه‌جا آن را به صفِ "
                    "چندسطحیِ بازخوردی تبدیل می‌کند که موجود دیگری است.")),
        dict(kind="bullets", title="تصمیم‌های طراحی که واقعاً مهم‌اند",
             bullets=[
                 "تعداد صف‌ها: سه تا یک قرارداد است، نه قانون.",
                 "سیاست هر صف: RR برای تعاملی، FCFS برای دسته‌ای.",
                 "برش زمانی درون یک صف RR: اگر خیلی کوچک باشد پردازنده صرف "
                 "تعویض زمینه می‌شود، اگر خیلی بزرگ باشد به FCFS تنزل می‌یابد.",
                 "سالخوردگی: ارتقای کاری که زیاد منتظر مانده. با آن گرسنگی از "
                 "بین می‌رود؛ بدون آن تضمین می‌شود.",
             ],
             notes=("این اسلایدی است که مخاطب باید چیزی یادداشت کند. انتخابِ برش "
                    "زمانی همان چیزی است که افراد در آن اشتباه می‌کنند: پاسخِ "
                    "عامیانه «حدود ده میلی‌ثانیه» است، اما پاسخِ درست به هزینهٔ "
                    "تعویض زمینه روی ماشین شما نسبت به بار کاری‌تان بستگی دارد.")),
        dict(kind="picture",
             title="نخستین تصمیم طراحی: زمان‌بند چقدر باید شکیبا باشد؟",
             image="fig_aging.png",
             caption="پویش آستانهٔ پیرسازی. قرمز: زمان انتظارِ پایین‌ترین صف. "
                     "آبی: میانگین انتظارِ همهٔ صف‌ها.",
             notes=("این نخستین تصمیم طراحی است و همان است که معمولاً از کنار "
                    "آن می‌گذرند. خطِ قرمز کاری است در پایین‌ترین صف؛ با "
                    "پیرسازیِ خاموش، بیست تیک منتظر می‌ماند. پیرسازی را با "
                    "آستانهٔ دو روشن کنید، شش تیک منتظر می‌ماند. حالا به خطِ "
                    "آبی نگاه کنید که هزینهٔ بقیه است: به‌سختی جابه‌جا می‌شود "
                    "و در واقع اندکی پایین می‌آید. این برهانِ لهِ پیرسازی "
                    "است، و برهانی اندازه‌گیری‌شده است نه توسلی به انصاف. در "
                    "انتهای سمت راست هر دو خط صاف می‌شوند، زیرا آستانه از "
                    "طول اجرا بزرگ‌تر شده و اصلاً ارتقایی رخ نمی‌دهد. پس یک "
                    "بازهٔ قابل استفاده داریم و نه یک مقدارِ جادویی.")),
        dict(kind="section", title="۲ — روش",
             notes=("پیش از نمایش نتایج، دو اسلاید صرفِ نحوهٔ به دست آمدنِ آن‌ها می‌کنم. این مهم‌تر از خودِ عددها است، چون یک عدد بدون روش فقط یک ادعاست که اعشار دارد. ادعاهایی را که اندازه گرفته‌ام از ادعاهایی که توانسته‌ام واقعاً اثبات کنم جدا می‌کنم و این دو را با هم نمی‌آمیزم.")),
        dict(kind="bullets", title="دو گونهٔ متفاوتِ ادعا",
             bullets=[
                 "ادعای اندازه‌گیری‌شده: «تحت این بار کاری و روی این ماشین، X "
                 "سریع‌تر بود». نمونه‌برداری و زمان‌سنجی.",
                 "ادعای اثبات‌شده: «هیچ اجرایی از این الگوریتم انحصار متقابل را "
                 "نمی‌شکند». شمارش کامل.",
                 "یک تست موفق یک ادعای اندازه‌گیری‌شده است و هرگز به اثبات تبدیل "
                 "نمی‌شود.",
                 "یک اثبات مشروط به مدل خود است: در اینجا سازگاری ترتیبی و "
                 "خواندن/نوشتنِ اتمی.",
             ],
             notes=("این تمایز در سراسر پروژه جاری است. در بخش زمان‌بندی تنها "
                    "می‌توانم اندازه بگیرم. در بخش انحصار متقابل توانستم واقعاً "
                    "اثبات کنم، چون فضاهای حالت کوچک از کار درآمدند. به این "
                    "برمی‌گردم.")),
        dict(kind="section", title="۳ — نتایج: زمان‌بندی",
             notes=("اکنون نتایج. چهار سناریو نشان می‌دهم، سپس مقایسه با الگوریتم‌های بلادرنگ. این چهار بار کاری عمداً انتخاب شده‌اند تا یک بارِ راحت، یک بارِ تنگ، یک مورد بیرون از مدل دوره‌ای و یک اضافه‌بارِ واقعی را پوشش دهند، چون الگوریتمی که تنها در بهره‌وریِ هشتاد درصد کار کند کارش تمام نشده است.")),
        dict(kind="table", title="اندازه‌گیری: MLQ در برابر EDF و RM",
             headers=["سناریو", "نقضِ EDF", "نقضِ RM", "نقضِ MLQ", "بهره‌وری"],
             rows=[["الف — منصفانه", "۰", "۰", "۰", "۸۰٫۰٪"],
                   ["ب — فشار", "۰", "۳", "۳", "۹۷٫۱٪"],
                   ["ج — نادوره‌ای", "۰", "۳", "۰", "۹۰٫۰٪"],
                   ["د — اضافه‌بار", "۳۱", "۱۰", "۱۰", "۱۰۰٪ِ محقق‌شده"]],
             notes=("ستونِ دو را در برابر ستونِ سه ببینید. EDF هیچ مهلتی را از دست "
                    "نمی‌دهد تا زمانی که سیستم واقعاً اضافه‌بار شود، و حتی آن‌گاه به "
                    "شیوهٔ دیگری نقض می‌کند. حالا سناریوی ج را ببینید: MLQ در آنجا "
                    "عملاً از RM بهتر است، با آنکه MLQ اصلاً مفهوم مهلت ندارد. این "
                    "شانس است، نه طراحی — و در مقاله همین را گفته‌ام.")),
        dict(kind="bullets", title="اضافه‌بار چه چیزی را آشکار می‌کند",
             bullets=[
                 "با بارِ پیشنهادیِ ۱۲۳٪، پردازنده باز هم تنها ۱۰۰٪ محقق می‌کند: "
                    "بقیه کاری است که اصلاً انجام‌شدنی نیست.",
                 "EDF سی و یک کار را از دست می‌دهد؛ RM و MLQ هر کدام ده تا.",
                 "EDF درد را میان هر سه وظیفه پخش می‌کند؛ RM و MLQ وظیفهٔ "
                 "کم‌اولویت را تقریباً کاملاً قربانی می‌کنند.",
                 "این یعنی «EDF در اضافه‌بار بدتر است» نیست؛ انتخابِ متفاوتی است "
                 "دربارهٔ اینکه چه کسی رنج ببرد.",
             ],
             notes=("این اسلایدی است که در بخش پرسش از آن دفاع می‌کنم. یک خوانشِ "
                    "ساده‌لوحانه می‌گوید EDF بدتر است چون ۳۱ از ۱۰ بیشتر است. خوانشِ "
                    "صادقانه این است که EDF حاضر نیست از هیچ طبقهٔ اولویتی محافظت "
                    "کند، در حالی که RM و MLQ با رها کردنِ کاملِ کم‌اولویت‌ترین کار، "
                    "از کارهای پُراولویت محافظت می‌کنند. برای یک سیستم بلادرنگِ سخت "
                    "معمولاً رفتارِ دوم را می‌خواهید، و این یک نیازِ طراحی است نه یک "
                    "شاخص.")),
        dict(kind="picture",
             title="یک مجموعهٔ وظیفه، دو انتخاب دربارهٔ اینکه چه کسی آسیب "
                   "ببیند",
             image="fig_overload_gantt.png",
             caption=f"سناریوی D، بار عرضه‌شدهٔ {N['D_load_pct']} درصد، "
                     f"{N['horizon_D']} تیک. EDF در بالا، RM در پایین. "
                     f"نشانه‌های قرمز مهلت‌ها هستند.",
             notes=("این اسلایدی است که دوست دارم به خاطر بماند. وظایف یکسان، "
                    "۱۲۰ تیکِ یکسان، پردازندهٔ یکسان. در بالا EDF: از هیچ "
                    "طبقهٔ اولویتی محافظت نمی‌کند، پس هر سه وظیفه مهلت را از "
                    "دست می‌دهند و مجموع سی و یک است. در پایین RM: از X و Y "
                    "محافظت می‌کند و Z را رها می‌سازد، و مجموع تنها ده است. "
                    "اگر فقط به شمارِ تخطی نگاه کنید نتیجه می‌گیرید که EDF "
                    "سه برابر بدتر است، و این نتیجه غلط است. آنچه واقعاً "
                    "تفاوت دارد، انتخاب دربارهٔ این است که چه کسی آسیب "
                    "ببیند. در یک سیستم بی‌درنگِ سخت معمولاً رفتار دوم را به "
                    "عمد می‌خواهید، که آن را به نیازمندی‌ای تبدیل می‌کند که "
                    "می‌نویسید و نه عددی که بهینه می‌کنید.")),
        dict(kind="bullets", title="زمان‌بندی‌پذیری: چه چیزی را می‌توان دانست",
             bullets=[
                 "برای RM، کرانِ لیو و لی‌لند یعنی n(2^(1/n) − 1) کافی است اما "
                 "لازم نیست: در n = 3 برابر ۰٫۷۷۹۸ است.",
                 "بالاتر از این کران، آزمون هیچ نمی‌گوید — باید تحلیلِ دقیقِ زمان "
                 "پاسخ را اجرا کرد.",
                 "برای EDF با مهلت‌های ضمنی، U ≤ ۱ هم لازم است و هم کافی. نه "
                 "حاشیه‌ای، نه حدسی.",
                 "یک مطالعهٔ تصادفی روی ۲۳۲۹ مجموعهٔ وظیفه، پرتگاهِ آشنا را بازتولید "
                 "کرد: در بهره‌وریِ ۹۰ تا ۱۰۰ درصد تنها ۱۷٫۸٪ مجموعه‌ها تحت RM "
                 "زمان‌بندی‌پذیر بودند در برابر ۱۰۰٪ برای EDF.",
             ],
             notes=("کران در n = 3 برابر ۰٫۷۷۹۸ است و با بزرگ شدنِ n به ln 2 یعنی "
                    "حدود ۰٫۶۹۳ میل می‌کند. افراد عددِ ۰٫۶۹ را طوری نقل می‌کنند که "
                    "گویی خودِ کران است؛ در حالی که آن حدِ کران است. و مطالعهٔ "
                    "تصادفی راهِ صادقانهٔ گفتنِ «در عمل» است: نمونه‌ای از ۲۳۲۹ "
                    "مجموعه با یک دانهٔ ثابت، پس تکرارپذیر است اما باز هم نمونه "
                    "است.")),
        dict(kind="picture", title="جایی که نرخ یکنواخت از کار می‌افتد",
             image="fig_utilisation_cliff.png",
             caption=f"{N['sets']:,} مجموعهٔ وظیفهٔ تصادفی با دانهٔ "
                     f"{N['seed']}، دسته‌بندی‌شده بر حسب بهره‌وری.",
             notes=("این عددِ شاخصِ کلِ پروژه است. نارنجی نرخ یکنواخت است، "
                    "آبی EDF، و محورِ عمودی درصدِ مجموعه‌های تصادفی‌ای است که "
                    "شدنی‌اند. زیرِ حدود هفتاد درصد بهره‌وری این دو از هم "
                    "بازشناخته نمی‌شوند، هر دو روی صد درصد. سپس خطِ نارنجی "
                    "از یک پرتگاه فرو می‌افتد: هشتاد و دو درصد در بازهٔ بعد، "
                    "و هجده درصد در بالاترین بازه. EDF روی صد صاف می‌ماند، "
                    "دقیقاً آن گونه که نظریه برای مهلت‌های ضمنی پیش‌بینی "
                    "می‌کند. خط‌چین کرانِ لیو و لیلند است. هر چه سمت چپِ آن "
                    "است با خودِ کران تضمین می‌شود؛ سمت راستِ آن کران خاموش "
                    "است و تنها آزمون دقیقِ زمان پاسخ می‌تواند پاسخ دهد.")),
        dict(kind="section", title="۴ — نتایج: انحصار متقابل",
             notes=("نیمهٔ دوم. همان پروژه، پرسشی دیگر: نه «چه‌قدر سریع» بلکه «آیا درست است». در اینجا توانستم اندازه‌گیری را رها کنم و به اثبات بپردازم، چون فضاهای حالتِ این الگوریتم‌های انحصار متقابل آن‌قدر کوچک از کار درآمد که بتوان همهٔ آن‌ها را شمرد. این گونهٔ ادعایی را که مجازم بکنم تغییر می‌دهد.")),
        dict(kind="table", title="هشت الگوریتم، بررسی‌شده به‌طور کامل",
             headers=["الگوریتم", "تعداد حالت", "انحصار متقابل", "آزادی از بن‌بست",
                      "آزادی از گرسنگی"],
             rows=[["دکر", "۳۲۴", "برقرار", "بله", "بله"],
                   ["پترسون", "۱۹۹", "برقرار", "بله", "بله"],
                   ["متغیر قفل", "۶۰", "نقض‌شده", "بله", "خیر"],
                   ["اعلام-و-سپس-چرخیدن", "۵۵", "برقرار", "خیر", "بله"],
                   ["Test-and-Set", "۵۱", "برقرار", "بله", "خیر"],
                   ["سمافور دودویی", "۲۲", "برقرار", "بله", "بله"],
                   ["ترتیبِ اشتباهِ قفل", "۴۸", "برقرار", "خیر", "بله"],
                   ["مانیتور Mesa", "۵۴", "برقرار", "بله", "بله"]],
             notes=("سه شکست را بخوانید، چون هر یک به شیوه‌ای متفاوت شکست می‌خورند. "
                    "متغیر قفل ایمنی را از دست می‌دهد. اعلام-و-سپس-چرخیدن ایمنی را "
                    "نگه می‌دارد و پیشرفت را از دست می‌دهد. Test-and-Set هر دو را "
                    "نگه می‌دارد و انصاف را از دست می‌دهد. و سطرِ هفتم موردِ علاقهٔ "
                    "من است: یک پریمتیوِ کاملاً درست، که با ترتیبِ اشتباه به کار "
                    "رود، کل سیستم را بن‌بست می‌دهد.")),
        dict(kind="picture", title="سه راه برای غلط بودن",
             image="fig_property_matrix.png",
             caption="هر خانه یک حکمِ کامل روی کلِ فضای حالتِ قابل دسترسی "
                     "است و نه یک نمونه.",
             notes=("این جدول را دوست دارم چون سه چیز را از هم جدا می‌کند که "
                    "آزمون‌کردن معمولاً در هم می‌آمیزد. پروتکلِ متغیر قفل "
                    "ایمنی را از دست می‌دهد: خواندن و نوشتن دو گام جداگانه‌اند، "
                    "پس هر دو فرایند می‌توانند قفل را آزاد ببینند. "
                    "اعلام-سپس-چرخش ایمنی را نگه می‌دارد و پیشرفت را از دست "
                    "می‌دهد: هر دو می‌توانند پیش از آن که دیگری نگاه کند "
                    "اعلام کنند. Test-and-Set هر دو را نگه می‌دارد و انصاف "
                    "را از دست می‌دهد: هیچ چیز به خاطر نمی‌سپارد چه کسی "
                    "طولانی‌تر منتظر مانده است. سه ستون، سه شیوهٔ شکستِ "
                    "متمایز. و سپس به یکی‌مانده‌به‌آخرین ردیف نگاه کنید: "
                    "سمافور با ترتیب غلط اصلاً خانهٔ قرمز ندارد، چون هر "
                    "ویژگیِ پریمتیو برقرار است، و باز هم برنامه دچار بن‌بست "
                    "می‌شود. آن خطا در استفاده‌کننده است، و هیچ مقدار "
                    "بررسیِ پریمتیو آن را نمی‌گرفت.")),
        dict(kind="bullets", title="سه شکست، سه درس",
             bullets=[
                 "نگاه-و-سپس-اعلام: خواندن و نوشتن دو گام جداگانه‌اند، بنابراین هر "
                 "دو می‌توانند «آزاد» ببینند. ایمنی از دست رفت.",
                 "اعلام-و-سپس-نگاه: ایمن است، اما هر دو می‌توانند پیش از آنکه هر یک "
                 "نگاه کند اعلام کنند. پیشرفت از دست رفت.",
                 "Test-and-Set: ایمن و زنده، اما هیچ چیز به خاطر نمی‌سپارد چه کسی "
                 "طولانی‌تر مانده. انتظارِ محدود از دست رفت.",
                 "هیچ‌یک از این شکست‌ها در یک اجرای کوتاهِ تست دیده نمی‌شود.",
             ],
             notes=("به تقارنِ میان سطرِ یک و دو توجه کنید: جابه‌جا کردنِ ترتیبِ دو "
                    "خطِ مجاور یک خطای ایمنی را به یک خطای زنده‌مانی تبدیل می‌کند. "
                    "این نتیجه‌ای واقعاً شگفت‌انگیز است و ارزشِ مکث دارد.")),
        dict(kind="bullets", title="بن‌بست خطای استفاده است",
             bullets=[
                 "چهار شرط لازم است: انحصار متقابل، نگه‌داشتن و انتظار، غیرقابل‌سلب "
                 "بودن، انتظار دوره‌ای.",
                 "هیچ‌یک از آن‌ها دربارهٔ کیفیتِ قفل نیست.",
                 "اندازه‌گیری: با ترتیبِ معکوس، نخِ ۰ قفلِ A را دارد و روی B مسدود "
                 "می‌شود در حالی که نخِ ۱ قفلِ B را دارد و روی A مسدود است — هر بار.",
                 "با یک ترتیبِ سراسری، همان برنامه همیشه کامل می‌شود.",
             ],
             notes=("این را عمداً قطعی ساختم، با یک مانع میان دو گرفتن و یک گرفتنِ "
                    "دومِ غیرمسدودکننده، تا نتوان آن را به شانسِ زمان‌بند نسبت داد. "
                    "نتیجه برای هر کسی که کدِ چندقفله می‌نویسد: بر یک ترتیب توافق "
                    "کنید، آن را بنویسید، و در بازنگری کد اِعمالش کنید.")),
        dict(kind="bullets", title="مانیتورها: انتزاعی که کمک می‌کند",
             bullets=[
                 "مانیتور وضعیت را همراه عملیاتش در یک بسته می‌گذارد و تضمین می‌کند "
                 "در هر لحظه یک نخ درون باشد.",
                 "متغیرهای شرطی به نخ اجازه می‌دهند منتظر یک گزاره بماند و در این "
                 "مدت قفل را آزاد کند.",
                 "تحت معنای Mesa نخِ بیدارشده باید دوباره بررسی کند: در ظرفیت ۱، "
                 "۱۳۸۳ بار ناچار شد دوباره منتظر بماند.",
                 "این عدد همان استدلالِ لهِ حلقهٔ while است و سبکی نیست.",
             ],
             notes=("اگر کسی پرسید چرا از `if` استفاده نمی‌کنیم، پاسخ روی همین "
                    "اسلاید است: ۱۳۸۳ بار در یک اجرا، گزاره تا زمانی که نخِ "
                    "بیدارشده دوباره قفل را گرفت باز هم نادرست بود. اگر `while` را "
                    "با `if` عوض کنید، این‌ها به خرابیِ بی‌صدا تبدیل می‌شوند.")),
        dict(kind="bullets", title="خوانندگان و نویسندگان: انصاف بهایی دارد",
             bullets=[
                 "اولویت خوانندگان: ۱۸۹٬۸۳۲ خواندن در برابر ۵ نوشتن. نویسنده عملاً "
                 "هر بار پشت سر گذاشته می‌شود.",
                 "اولویت نویسندگان: تصویرِ آینه‌ای — ۱٬۱۶۵٬۶۳۲ نوشتن در برابر "
                 "۴۷۹٬۱۰۴ خواندن.",
                 "FIFO منصفانه: سهمِ خواندنِ ۰٫۸۹۸، نزدیک به نسبتِ ورودِ شش خواننده "
                 "به یک نویسنده، که همان معنای انصاف است.",
                 "نمی‌توان هم‌زمان بیشینهٔ هم‌روندی و نبودِ گرسنگی داشت.",
             ],
             notes=("این را به عنوان یک بده‌بستان نشان دهید، نه یک خطا. اولویتِ "
                    "خوانندگان پاسخِ درست است وقتی نوشتن نادر است و تأخیر مهم است. "
                    "FIFO منصفانه پاسخِ درست است وقتی یک نوشتنِ کهنه خطرناک است. "
                    "نکته این است که آگاهانه انتخاب کنید.")),
        dict(kind="section", title="۵ — هزینه",
             notes=("در پایان، هزینهٔ همهٔ این‌ها. این‌ها میانهٔ اجراهای تکراری‌اند، چون یک زمان‌سنجیِ واحد روی یک ماشینِ اشتراکی بی‌ارزش است. وقتی نخستین بار این را اندازه گرفتم، همان بار کاری میان اجراها بیش از ده برابر تفاوت داشت، بنابراین گزارشِ یک عدد گزارشِ نویز بود.")),
        dict(kind="bullets", title="در شرایط رقابت، مسدود کردن نرم‌تر افت "
                              "می‌کند",
             bullets=[
                 "مکانیزم‌های مسدودکننده به‌نرمی افت می‌کنند: نخِ مسدود پردازنده را "
                 "آزاد می‌گذارد.",
                 "با دو یا چهار نخ، قفلِ چرخشی جلوتر است: ۵۵۴ هزار عمل بر "
                 "ثانیه در دو نخ در برابر ۵۲۵ هزارِ سمافور و ۵۴۱ هزارِ "
                 "مانیتور، و ۶۲۴ هزار در چهار نخ در برابر ۴۹۲ و ۵۳۲ هزار. در "
                 "هشت نخ به ۴۷۷ هزار می‌افتد، پشتِ هر دو.",
                 "قفلِ چرخشی تنها زمانی درست است که بخش بحرانی از تعویض زمینه "
                 "کوتاه‌تر باشد — در هسته درست است، در کدِ کاربردی به‌ندرت.",
                 "اگر دارندهِ قفل از زمان‌بندی خارج شود، هر چرخنده یک برشِ زمانیِ "
                 "کامل را هدر می‌دهد.",
             ],
             notes=("اینجا باید احتیاط کرد، زیرا ادعای بدیهی غلط است. در دو و "
                    "چهار نخ قفلِ چرخشی یک‌سره می‌برد؛ دلیلش این است که با یک "
                    "بخش بحرانیِ کوتاه، چرخیدن از یک انتظار و بیدار کردنِ هسته "
                    "ارزان‌تر است. آنچه در هشت نخ تغییر می‌کند در واقع توان "
                    "عملیاتی نیست، که تنها حدود یک‌چهارم می‌افتد؛ بلکه شمارشِ "
                    "چرخش است: نزدیک به شش برابرِ حالتِ دو نخ. این زمانِ "
                    "پردازنده‌ای است که هیچ‌کس آن را نخریده است، و در ماشینی "
                    "که دارندهِ قفل بتواند از زمان‌بندی خارج شود، یک برشِ "
                    "زمانیِ کامل است که هر چرخنده هدر می‌دهد. پس خلاصهٔ درست "
                    "این نیست که «مسدود کردن سریع‌تر است»، بلکه این است که "
                    "«مسدود کردن پیش‌بینی‌پذیرتر است».")),
        dict(kind="section", title="۶ — نتیجه‌گیری",
             notes=("دو دقیقه نتیجه‌گیری، سپس پرسش‌ها. پنج نکتهٔ قابل‌برداشت می‌گویم، محدودیت‌های کار را تا جایی که می‌توانم به‌صراحت بیان می‌کنم، و سپس صحبت را تمام می‌کنم.")),
        dict(kind="bullets", title="محدودیت‌ها، به‌صراحت",
             bullets=[
                 "یک ماشین، محیطِ اشتراکی، CPython با GIL: زمان‌سنجی‌ها هزینهٔ نسبی "
                 "را نشان می‌دهند نه کاراییِ مطلق.",
                 "اثبات‌های انحصار متقابل دو شرکت‌کننده را پوشش می‌دهند و سازگاری "
                 "ترتیبی را فرض می‌کنند.",
                 "مطالعهٔ زمان‌بندی‌پذیری نمونه‌ای تکرارپذیر از ۲۳۲۹ مجموعهٔ وظیفه "
                 "است، نه یک قضیه.",
                 "هیچ ادعایی در اینجا دربارهٔ یک سیستم‌عاملِ تجاریِ خاص نیست.",
             ],
             notes=("این اسلاید را در ارائه رد نکنید. بیانِ محدودیت‌ها همان چیزی "
                    "است که یک نتیجهٔ مهندسی را از یک ادعای تبلیغاتی جدا می‌کند، و "
                    "نخستین چیزی است که یک ممتحنِ خوب به دنبالش می‌گردد.")),
        dict(kind="bullets", title="بازتولید همه چیز",
             bullets=[
                 "هر تمرین روی شاخهٔ خودش است، با README خودش در ریشهٔ شاخه.",
                 "یک دستور به‌ازای هر محصول: شبیه‌ساز، اجراکنندهٔ آزمایش، تولیدکنندهٔ "
                 "شکل، مجموعهٔ تست.",
                 "گزارش‌ها از ماژول‌های محتوایی تولید می‌شوند که عددهایشان را از "
                 "خروجیِ آزمایش می‌خوانند، بنابراین نثر و کد نمی‌توانند از هم جدا "
                 "شوند.",
                 "مدخل‌های کتاب‌نامه در برابر سوابقِ ناشر بررسی شده‌اند؛ REFERENCES.md "
                 "را ببینید.",
             ],
             notes=("مخاطب را به مخزن ارجاع دهید. هرچه در این ارائه هست بازتولید "
                    "شدنی است، از جمله خودِ این ارائه که توسط code/build_deck.py "
                    "ساخته می‌شود.")),
        dict(kind="closing", title="پرسش‌ها",
             subtitle="github.com/kaspian021/Multilevel-Queue-Scheduling",
             notes=("سپاسگزارم. خوشحال می‌شوم به پرسش‌هایی دربارهٔ هر یک از شش تمرین "
                   "پاسخ دهم، و اگر مفید باشد می‌توانم هر آزمایشی را زنده دوباره "
                   "اجرا کنم.")),
    ]


# ================================================================== rendering
def _blank(prs):
    return prs.slide_layouts[6]


def _set_notes(slide, text):
    notes = slide.notes_slide
    tf = notes.notes_text_frame
    tf.text = text
    for p in tf.paragraphs:
        p.font.size = Pt(12)
    return notes


def _rtl(tf):
    """Mark every paragraph right-to-left so PowerPoint applies bidi layout."""
    for p in tf.paragraphs:
        pPr = p._p.get_or_add_pPr()
        pPr.set("rtl", "1")


def _title_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.9), Inches(2.3), Inches(11.5),
                                   Inches(2.2))
    tf = box.text_frame
    tf.word_wrap = True
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(40)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    box2 = slide.shapes.add_textbox(Inches(0.9), Inches(4.6), Inches(11.5),
                                    Inches(1.2))
    tf2 = box2.text_frame
    tf2.word_wrap = True
    tf2.text = s["subtitle"]
    for p in tf2.paragraphs:
        p.font.size = Pt(20)
        p.font.color.rgb = ACCENT
        p.font.name = font
    box3 = slide.shapes.add_textbox(Inches(0.9), Inches(6.3), Inches(11.5),
                                    Inches(0.6))
    tf3 = box3.text_frame
    tf3.text = s["meta"]
    for p in tf3.paragraphs:
        p.font.size = Pt(13)
        p.font.color.rgb = GREY
        p.font.name = font
    if font == PERSIAN_FONT:
        _rtl(tf)
        _rtl(tf2)
        _rtl(tf3)
    _set_notes(slide, s["notes"])
    return slide


def _section_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.9), Inches(3.0), Inches(11.5),
                                   Inches(1.4))
    tf = box.text_frame
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    if font == PERSIAN_FONT:
        _rtl(tf)
    _set_notes(slide, s["notes"])
    return slide


def _bullets_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7),
                                   Inches(1.0))
    tf = box.text_frame
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    body = slide.shapes.add_textbox(Inches(0.9), Inches(1.75), Inches(11.5),
                                    Inches(5.2))
    tf2 = body.text_frame
    tf2.word_wrap = True
    first = True
    for b in s["bullets"]:
        p = tf2.paragraphs[0] if first else tf2.add_paragraph()
        first = False
        p.text = "•  " + b
        p.font.size = Pt(19)
        p.font.color.rgb = RGBColor(0x22, 0x24, 0x28)
        p.font.name = font
        p.space_after = Pt(14)
    if font == PERSIAN_FONT:
        _rtl(tf)
        _rtl(tf2)
    _set_notes(slide, s["notes"])
    return slide


def _table_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.8), Inches(0.55), Inches(11.7),
                                   Inches(1.0))
    tf = box.text_frame
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(28)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    rows, cols = len(s["rows"]) + 1, len(s["headers"])
    top = Inches(1.8)
    height = min(Inches(4.9), Inches(0.55) * rows)
    shape = slide.shapes.add_table(rows, cols, Inches(0.9), top,
                                   Inches(11.5), height)
    tbl = shape.table
    for c, h in enumerate(s["headers"]):
        cell = tbl.cell(0, c)
        cell.text = h
        for p in cell.text_frame.paragraphs:
            p.font.bold = True
            p.font.size = Pt(15)
            p.font.color.rgb = WHITE
            p.font.name = font
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
    for r, row in enumerate(s["rows"], start=1):
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = val
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(14)
                p.font.color.rgb = RGBColor(0x22, 0x24, 0x28)
                p.font.name = font
            if r % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = LIGHT
    if font == PERSIAN_FONT:
        _rtl(tf)
        for row in tbl.rows:
            for cell in row.cells:
                _rtl(cell.text_frame)
    _set_notes(slide, s["notes"])
    return slide


def _picture_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.8), Inches(0.45), Inches(11.7),
                                   Inches(0.9))
    tf = box.text_frame
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(26)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    path = os.path.join(DIAGRAMS, s["image"])
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"figure {s['image']} is missing; run "
            f"python3 tools/make_figures_ex6.py from the repository root")
    img_w, img_h = _fit_image(path, Inches(11.2), Inches(5.0))
    left = Inches(0.9) + (Inches(11.2) - img_w) / 2
    slide.shapes.add_picture(path, left, Inches(1.45), img_w, img_h)
    cap = slide.shapes.add_textbox(Inches(0.9), Inches(1.55) + img_h,
                                   Inches(11.2), Inches(0.9))
    tfc = cap.text_frame
    tfc.word_wrap = True
    tfc.text = s["caption"]
    for p in tfc.paragraphs:
        p.font.size = Pt(13)
        p.font.color.rgb = GREY
        p.font.name = font
    if font == PERSIAN_FONT:
        _rtl(tf)
        _rtl(tfc)
    _set_notes(slide, s["notes"])
    return slide


def _fit_image(path, max_w, max_h):
    """Largest size for `path` that fits inside max_w x max_h, 1:1 aspect."""
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    scale = min(int(max_w) / w, int(max_h) / h)
    return Emu(int(w * scale)), Emu(int(h * scale))


def _closing_slide(prs, s, font):
    slide = prs.slides.add_slide(_blank(prs))
    box = slide.shapes.add_textbox(Inches(0.9), Inches(2.8), Inches(11.5),
                                   Inches(1.4))
    tf = box.text_frame
    tf.text = s["title"]
    for p in tf.paragraphs:
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = NAVY
        p.font.name = font
    box2 = slide.shapes.add_textbox(Inches(0.9), Inches(4.5), Inches(11.5),
                                    Inches(0.8))
    tf2 = box2.text_frame
    tf2.text = s["subtitle"]
    for p in tf2.paragraphs:
        p.font.size = Pt(17)
        p.font.color.rgb = ACCENT
        p.font.name = font
    if font == PERSIAN_FONT:
        _rtl(tf)
        _rtl(tf2)
    _set_notes(slide, s["notes"])
    return slide


def build(slides, path, font):
    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    for s in slides:
        kind = s["kind"]
        if kind == "title":
            _title_slide(prs, s, font)
        elif kind == "section":
            _section_slide(prs, s, font)
        elif kind == "bullets":
            _bullets_slide(prs, s, font)
        elif kind == "table":
            _table_slide(prs, s, font)
        elif kind == "picture":
            _picture_slide(prs, s, font)
        elif kind == "closing":
            _closing_slide(prs, s, font)
        else:
            raise ValueError(f"unknown slide kind {kind}")
    prs.save(path)
    return path


def main():
    out = []
    out.append(build(_en_slides(), os.path.join(DOCS, "SEMINAR_EN.pptx"),
                     LATIN_FONT))
    out.append(build(_fa_slides(), os.path.join(DOCS, "SEMINAR_FA.pptx"),
                     PERSIAN_FONT))
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
