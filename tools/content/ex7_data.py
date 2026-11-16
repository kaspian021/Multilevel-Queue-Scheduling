# -*- coding: utf-8 -*-
"""Shared data and table builders for the Exercise-7 reports.

Both the Persian and the English paper import this module, so the two
languages cannot disagree about a number. Everything is read from
``exercise-7/output/experiments.json``.
"""

from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))

with open(os.path.join(_REPO, "exercise-7", "output", "experiments.json"),
          encoding="utf-8") as _f:
    D = json.load(_f)

MODEL = D["e6_model"]
E1 = D["e1_throughput"]
E2 = D["e2_concurrency"]
E3 = D["e3_writer_starvation"]
E4 = D["e4_reader_starvation"]
E5 = D["e5_scaling"]
REPS1 = E1["semaphore_mutex"]["reps"]
REPS3 = E3["semaphore_mutex"]["reps"]

# The order the solutions appear in every table of the paper.
MODEL_ORDER = [
    "semaphore_mutex", "monitor_mesa_mutex", "monitor_fifo_mutex",
    "dekker_mutex", "peterson_mutex",
    "rw_readers_pref", "rw_writers_pref", "rw_writers_pref_2w",
    "rw_fair", "rw_barrier", "rw_monitor_mesa", "rw_monitor_fifo",
    "rw_dekker", "rw_dekker_2readers", "rw_peterson", "rw_peterson_2readers",
    "rw_broken_count",
]

THROUGHPUT_ORDER = [
    "semaphore_mutex", "semaphore_mutex_fast", "monitor_mutex",
    "dekker_mutex", "peterson_mutex",
    "readers_pref", "readers_pref_fast", "writers_pref",
    "fair_fifo", "fair_fifo_fast", "barrier",
    "monitor_mesa", "monitor_fifo", "dekker_rw", "peterson_rw",
]

NAME = {
    "semaphore_mutex": "semaphore mutex",
    "semaphore_mutex_fast": "semaphore mutex, no queue",
    "monitor_mesa_mutex": "Mesa monitor mutex",
    "monitor_fifo_mutex": "monitor mutex, FIFO entry",
    "monitor_mutex": "monitor mutex",
    "dekker_mutex": "Dekker",
    "peterson_mutex": "Peterson",
    "readers_pref": "readers preference",
    "readers_pref_fast": "readers preference, no queue",
    "writers_pref": "writers preference",
    "fair_fifo": "fair FIFO",
    "fair_fifo_fast": "fair FIFO, no queue",
    "barrier": "writer barrier",
    "monitor_mesa": "Mesa monitor",
    "monitor_fifo": "monitor, FIFO entry",
    "dekker_rw": "Dekker as count lock",
    "peterson_rw": "Peterson as count lock",
}

FAMILY = {
    "mutex": "mutual exclusion",
    "dekker": "Dekker",
    "peterson": "Peterson",
    "readers-preference": "readers preference",
    "writers-preference": "writers preference",
    "fair": "fair FIFO",
    "writer-barrier": "writer barrier",
    "monitor": "monitor",
    "broken": "broken on purpose",
}


def yes(v) -> str:
    return "yes" if v else "**no**"


def holds(v) -> str:
    return "holds" if v else "**VIOLATED**"


def starves(r) -> str:
    s = r["starvation_free"]
    roles = r["roles"]
    if all(s.values()):
        return "none"
    bad = [f"P{k}({roles[int(k)]})" for k, v in sorted(s.items()) if not v]
    if len(bad) == len(roles):
        return "**all of them**"
    return "**" + ", ".join(bad) + "**"


def model_rows():
    rows = []
    for n in MODEL_ORDER:
        r = MODEL[n]
        rows.append([
            f"`{n}`",
            "".join(r["roles"]),
            f"{r['states']:,}",
            holds(r["rw_safety"]),
            yes(r["deadlock_free"]),
            starves(r),
            yes(r["concurrent_reads_admitted"]),
        ])
    return rows


def throughput_rows():
    rows = []
    for n in THROUGHPUT_ORDER:
        r = E1[n]
        rows.append([
            NAME[n],
            f"{r['ops_per_s']:,.0f}",
            f"{r.get('ops_per_s_spread', 0):,.0f}",
            f"{r['write_share']:.3f}",
            str(r["max_concurrent_readers"]),
        ])
    return rows


def concurrency_rows():
    keys = sorted(E2, key=lambda k: -E2[k]["max_concurrent_readers"])
    return [[NAME[k], str(E2[k]["max_concurrent_readers"]),
             f"{E2[k]['write_share']:.3f}"] for k in keys]


def starvation_rows():
    keys = sorted(E3, key=lambda k: E3[k]["write_share"])
    rows = []
    for k in keys:
        r = E3[k]
        rows.append([
            NAME[k],
            f"{r['write_share']:.3f}",
            f"{r['writer_starved_trials']}/{r['reps']}",
            f"{r['longest_read_run']:,}",
            f"{r['longest_write_run']:,}",
        ])
    return rows


def reader_starvation_rows():
    keys = sorted(E4, key=lambda k: -E4[k]["write_share"])
    return [[NAME[k], f"{E4[k]['write_share']:.3f}",
             f"{E4[k]['longest_write_run']:,}"] for k in keys]


def scaling_rows():
    ns = [1, 2, 4, 6, 8]
    rows = []
    for name in sorted(E5, key=lambda k: -E5[k]["8"]["ops_per_s"]):
        row = E5[name]
        rows.append([NAME[name]] +
                    [f"{row[str(n)]['ops_per_s']:,.0f}" for n in ns])
    return rows


def queue_cost_rows():
    pairs = [("semaphore_mutex", "semaphore_mutex_fast"),
             ("readers_pref", "readers_pref_fast"),
             ("fair_fifo", "fair_fifo_fast")]
    rows = []
    for fifo, fast in pairs:
        a, b = E1[fifo]["ops_per_s"], E1[fast]["ops_per_s"]
        rows.append([NAME[fifo], f"{a:,.0f}", f"{b:,.0f}", f"{b / a:.1f}x"])
    return rows


def kv_facts():
    return [
        ("Solutions modelled", f"{len(MODEL)}"),
        ("Largest proof", f"{max(r['states'] for r in MODEL.values()):,} states"),
        ("Smallest proof", f"{min(r['states'] for r in MODEL.values()):,} states"),
        ("Locks benchmarked", f"{len(E1)}"),
        ("Throughput runs per lock", str(REPS1)),
        ("Starvation trials per lock", str(REPS3)),
        ("Tests in the suite", "102"),
        ("Python", D["python"]),
    ]


# --------------------------------------------------------------- witnesses
# Pulled out of the model at build time rather than copied in, so a trace in
# the paper is always the trace the checker actually produced.

def _witness(name, kind="rw_safety_witness", limit=10):
    import os
    import sys
    sys.path.insert(0, os.path.join(_REPO, "exercise-7", "code"))
    import rw_model as rm
    sol = rm.SOLUTIONS[name]
    r = rm.explore(sol, max_states=200_000,
                   stop_on_violation=(sol.family == "broken"))
    if kind == "starvation":
        wit = r["starvation_witness"]
        pick = sorted(wit)[0]
        return [s.strip() for s in wit[pick][:limit]]
    return [s.strip() for s in (r[kind] or [])[:limit]]


def broken_witness(limit=9):
    return _witness("rw_broken_count", "rw_safety_witness", limit)


def mesa_starvation_witness(limit=11):
    return _witness("rw_monitor_mesa", "starvation", limit)


def program_listing(name, pid=0):
    """One solution's program, disassembled into readable lines.

    The point of printing the modelled instructions rather than a tidy
    pseudocode version is that this is literally what the checker explores:
    every line is one atomic step, and the interleaving of those steps is what
    the verdicts in this paper are about.
    """
    import os
    import sys
    sys.path.insert(0, os.path.join(_REPO, "exercise-7", "code"))
    import rw_model as rm

    sol = rm.SOLUTIONS[name]
    prog = sol.pid_programs[pid]

    def dis(ins):
        op = ins[0]
        if op in ("P", "V"):
            return f"{op.lower()}({ins[1]})"
        if op == "VSIG":
            return f"signal({ins[1]})"
        if op == "SIGNAL":
            return f"notify({ins[1]})"
        if op == "SIGNAL_ALL":
            return f"notifyAll({ins[1]})"
        if op == "HAND":
            return f"notify+handoff({ins[1]})"
        if op == "HAND_ALL":
            return f"notifyAll+handoff({ins[1]})"
        if op == "WAIT":
            return f"wait({ins[1]}) -> {ins[2]}"
        if op == "WAITQ":
            return f"wait-queued({ins[1]}) -> {ins[2]}"
        if op == "INC":
            return f"{ins[1]} = {ins[1]} + 1"
        if op == "DEC":
            return f"{ins[1]} = {ins[1]} - 1"
        if op == "SET":
            return f"{ins[1]} = {ins[2]}"
        if op == "LOAD":
            return f"r{ins[1]} = {ins[2]}"
        if op == "SUBI":
            return f"r{ins[1]} = r{ins[1]} - {ins[2]}"
        if op == "JZ":
            return f"if r{ins[1]} == 0 goto {ins[2]}"
        if op == "JNZ":
            return f"if r{ins[1]} != 0 goto {ins[2]}"
        if op == "JUMP":
            return f"goto {ins[1]}"
        if op == "SETP":
            return f"{ins[1]}[me] = {ins[2]}"
        if op == "SETO":
            return f"{ins[1]}[other] = {ins[2]}"
        if op == "LOADP":
            return f"r{ins[1]} = {ins[2]}[me]"
        if op == "LOADO":
            return f"r{ins[1]} = {ins[2]}[other]"
        if op == "SETOTHER":
            return f"{ins[1]} = other"
        if op == "SETPID":
            return f"{ins[1]} = me"
        if op == "JEQPID":
            return f"if r{ins[1]} == me goto {ins[2]}"
        if op == "JNEPID":
            return f"if r{ins[1]} != me goto {ins[2]}"
        if op in ("ENTER", "EXIT"):
            return op.lower()
        if op == "REM":
            return "remainder; goto 0"
        return " ".join(str(x) for x in ins)

    return [f"{i:>3}  {dis(ins)}" for i, ins in enumerate(prog)]
