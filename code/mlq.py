"""Multilevel Queue (MLQ) scheduling simulator — discrete, integer time.

Exercise 1 deliverable: a *runnable* model of Multilevel Queue Scheduling.

Model
-----
* The ready set is partitioned into queues numbered ``1..N`` where ``1`` is the
  highest priority level.
* **Inter-queue policy** (how the scheduler chooses *which queue* runs):
    - ``fixed``     — strict fixed priority: a ready process in a higher queue
                      always preempts a running process of a lower queue.
    - ``slice``     — time-slice (round-robin) between queues: each queue gets
                      at most ``slice`` consecutive ticks, then service moves to
                      the next non-empty queue (this is the classic
                      "time slice" alternative described in textbooks).
* **Intra-queue policy** (how the scheduler chooses *which process* runs inside
  the selected queue):
    - ``FCFS`` — first come, first served (non-preemptive inside the queue)
    - ``RR``   — round robin with a quantum
    - ``SJF``  — shortest total burst first (non-preemptive inside the queue)
    - ``SRTF`` — shortest remaining time first (preemptive inside the queue)
* Optional **aging** promotes a process one queue up after it has waited
  ``aging`` ticks in the ready state.  This is a starvation-avoidance
  extension and is labelled as such everywhere it appears, because pure MLQ
  has no aging.

All times are integer simulation ticks.  This is a **model**: it simulates a
scheduler, it is not a kernel scheduler and it does not measure real wall-clock
CPU time.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

POLICIES = ("FCFS", "RR", "SJF", "SRTF")
INTER_POLICIES = ("fixed", "slice")


class InputError(ValueError):
    """Raised for invalid user input."""


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------

@dataclass
class Process:
    pid: str
    arrival: int
    burst: int
    queue: int
    priority: int = 0          # tie-break inside a queue (lower = earlier)
    remaining: int = field(init=False)
    first_start: Optional[int] = None
    finish: Optional[int] = None
    wait_since: int = 0        # last tick it entered the ready state
    home_queue: int = field(init=False)

    def __post_init__(self):
        self.remaining = self.burst
        self.home_queue = self.queue


@dataclass
class QueueConfig:
    policy: str = "FCFS"
    quantum: int = 2


@dataclass
class Stats:
    total_time: int = 0
    busy_time: int = 0
    idle_time: int = 0
    context_switches: int = 0      # switches between two different processes
    switches_total: int = 0        # any change of the running entity (incl. idle)
    dispatches: int = 0            # times a process started to run
    preemptions: int = 0           # a running process was removed while unfinished
    promotions: int = 0            # aging promotions


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------

def validate(procs: List[dict], configs: Dict[int, QueueConfig]) -> List[Process]:
    if not isinstance(procs, list) or not procs:
        raise InputError("at least one process is required")
    out, seen = [], set()
    for i, p in enumerate(procs):
        if not isinstance(p, dict):
            raise InputError(f"process #{i + 1}: expected an object, got {type(p).__name__}")
        try:
            pid = str(p["pid"])
            arrival, burst, queue = int(p["arrival"]), int(p["burst"]), int(p["queue"])
            prio = int(p.get("priority", 0))
        except KeyError as e:
            raise InputError(f"process #{i + 1}: missing field {e}")
        except (TypeError, ValueError) as e:
            raise InputError(f"process #{i + 1}: non-integer field ({e})")
        if not pid:
            raise InputError(f"process #{i + 1}: pid must be a non-empty string")
        if pid in seen:
            raise InputError(f"duplicate pid {pid}")
        if arrival < 0:
            raise InputError(f"{pid}: arrival must be >= 0")
        if burst <= 0:
            raise InputError(f"{pid}: burst must be > 0")
        if queue not in configs:
            raise InputError(f"{pid}: queue {queue} not in {sorted(configs)}")
        seen.add(pid)
        out.append(Process(pid, arrival, burst, queue, prio))
    for q, c in configs.items():
        if c.policy not in POLICIES:
            raise InputError(f"queue {q}: unknown policy {c.policy}")
        if c.policy == "RR" and c.quantum <= 0:
            raise InputError(f"queue {q}: quantum must be > 0")
    return out


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

def _pick(q: List[Process], policy: str) -> Process:
    if policy == "SJF":
        return min(q, key=lambda p: (p.burst, p.arrival, p.priority, p.pid))
    if policy == "SRTF":
        return min(q, key=lambda p: (p.remaining, p.arrival, p.priority, p.pid))
    return q[0]                                     # FCFS / RR


def simulate_full(procs: List[dict], configs: Dict[int, QueueConfig], aging: int = 0,
                  inter_policy: str = "fixed", inter_slice: int = 2,
                  max_ticks: int = 100000):
    """Run the simulation.

    Returns ``(process_list, gantt, stats)`` where ``gantt`` is a list of
    ``(start, end, label)`` intervals (``IDLE`` for idle ticks) and ``stats`` is
    a :class:`Stats` record with utilisation / context-switch counters.
    """
    if inter_policy not in INTER_POLICIES:
        raise InputError(f"unknown inter-queue policy {inter_policy!r}")
    if inter_policy == "slice" and inter_slice <= 0:
        raise InputError("slice must be > 0")
    if aging < 0:
        raise InputError("aging must be >= 0")

    plist = validate(procs, configs)
    levels = sorted(configs)
    queues: Dict[int, List[Process]] = {q: [] for q in levels}
    pending = sorted(plist, key=lambda p: (p.arrival, p.pid))

    def admit(t: int):
        """Move every process whose arrival <= t into its ready queue."""
        while pending and pending[0].arrival <= t:
            p = pending.pop(0)
            p.wait_since = t
            queues[p.queue].append(p)

    st = Stats()
    t, current, slice_used = 0, None, 0

    def release(reason: str):
        """Take the running process off the CPU (it is not finished)."""
        nonlocal current, slice_used
        if current is not None and current.remaining > 0:
            st.preemptions += 1
        current, slice_used = None, 0
    queue_budget, last_queue = inter_slice, None
    done = 0
    ticks: List[str] = []

    while done < len(plist):
        if t > max_ticks:
            raise InputError("simulation did not terminate (max_ticks exceeded)")
        admit(t)

        # ---- aging ------------------------------------------------------
        if aging > 0:
            for q in levels[1:]:
                for p in list(queues[q]):
                    if t - p.wait_since >= aging:
                        queues[q].remove(p)
                        p.queue = levels[levels.index(q) - 1]
                        p.wait_since = t
                        queues[p.queue].append(p)
                        st.promotions += 1
                        if current is not None and p.queue < current.queue and inter_policy == "fixed":
                            queues[current.queue].insert(0, current)
                            current.wait_since = t
                            release("aging")

        top = next((q for q in levels if queues[q]), None)

        # ---- inter-queue arbitration ------------------------------------
        if inter_policy == "fixed":
            if current is not None and top is not None and top < current.queue:
                queues[current.queue].insert(0, current)      # preempted: back to front
                current.wait_since = t
                release("higher-queue")
        else:                                                  # slice (round-robin)
            if current is None or current.queue not in queues or queue_budget <= 0:
                if current is not None:
                    queues[current.queue].append(current)
                    current.wait_since = t
                    release("queue-slice")
                queue_budget = inter_slice
            if current is not None and top is not None and current.queue != top and queue_budget <= 0:
                pass

        if current is None and top is not None:
            if inter_policy == "fixed":
                qsel = top
            else:
                nxt = [q for q in levels if queues[q]]
                if last_queue in nxt and nxt.index(last_queue) + 1 < len(nxt):
                    qsel = nxt[nxt.index(last_queue) + 1]
                else:
                    qsel = nxt[0]
                last_queue = qsel
                queue_budget = inter_slice
            cfg = configs[qsel]
            nxt_p = _pick(queues[qsel], cfg.policy)
            queues[qsel].remove(nxt_p)
            current, slice_used = nxt_p, 0
            if current.first_start is None:
                current.first_start = t

        # ---- intra-queue preemption (SRTF) ------------------------------
        if current is not None and configs[current.queue].policy == "SRTF":
            better = _pick(queues[current.queue] + [current], "SRTF") if queues[current.queue] else current
            if better is not current:
                queues[current.queue].remove(better)
                queues[current.queue].append(current)
                current.wait_since = t
                release("srtf")
                current, slice_used = better, 0
                if current.first_start is None:
                    current.first_start = t

        if current is None:
            ticks.append("IDLE")
            t += 1
            continue

        ticks.append(current.pid)
        current.remaining -= 1
        slice_used += 1
        queue_budget -= 1
        t += 1

        if current.remaining == 0:
            current.finish = t
            done += 1
            current, slice_used = None, 0
            queue_budget = 0
        else:
            cfg = configs[current.queue]
            time_slice_over = (cfg.policy == "RR" and slice_used >= cfg.quantum)
            if inter_policy == "slice" and queue_budget <= 0:
                time_slice_over = True
            if time_slice_over:
                # arrivals at time t must enter before the preempted process (convention)
                admit(t)
                current.wait_since = t
                queues[current.queue].append(current)
                release("quantum")

    st.total_time = t
    st.busy_time = sum(1 for n in ticks if n != "IDLE")
    st.idle_time = st.total_time - st.busy_time

    # Derive the switching counters from the tick trace so that they cannot
    # disagree with the Gantt chart that is printed next to them.
    prev = None
    for label in ticks:
        if label != prev:
            if prev is not None:
                st.switches_total += 1
                if prev != "IDLE" and label != "IDLE":
                    st.context_switches += 1
            if label != "IDLE":
                st.dispatches += 1
            prev = label

    gantt: List[Tuple[int, int, str]] = []
    for i, name in enumerate(ticks):
        if gantt and gantt[-1][2] == name:
            gantt[-1] = (gantt[-1][0], i + 1, name)
        else:
            gantt.append((i, i + 1, name))
    return plist, gantt, st


def simulate(procs: List[dict], configs: Dict[int, QueueConfig], aging: int = 0,
             inter_policy: str = "fixed", inter_slice: int = 2, max_ticks: int = 100000):
    """Backwards-compatible wrapper: returns ``(process_list, gantt)``."""
    plist, gantt, _ = simulate_full(procs, configs, aging, inter_policy, inter_slice, max_ticks)
    return plist, gantt


# --------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------

def metrics_full(plist: List[Process], stats: Optional[Stats] = None):
    """Full metrics: ``(rows, summary, per_queue_stats)``."""
    rows = []
    for p in sorted(plist, key=lambda p: p.pid):
        tat = p.finish - p.arrival
        rows.append({"pid": p.pid, "queue": p.home_queue, "final_queue": p.queue,
                     "arrival": p.arrival, "burst": p.burst, "finish": p.finish,
                     "waiting": tat - p.burst, "turnaround": tat,
                     "response": p.first_start - p.arrival})
    n = len(rows)
    avg = {k: sum(r[k] for r in rows) / n for k in ("waiting", "turnaround", "response")}
    summary = dict(avg)
    summary["n"] = n
    if stats is not None:
        summary["total_time"] = stats.total_time
        summary["busy"] = stats.busy_time
        summary["idle"] = stats.idle_time
        summary["utilization"] = stats.busy_time / stats.total_time if stats.total_time else 0.0
        summary["throughput"] = n / stats.total_time if stats.total_time else 0.0
        summary["context_switches"] = stats.context_switches
        summary["switches_total"] = stats.switches_total
        summary["dispatches"] = stats.dispatches
        summary["preemptions"] = stats.preemptions
        summary["promotions"] = stats.promotions
    # per-queue breakdown
    per_queue = {}
    for r in rows:
        per_queue.setdefault(r["queue"], []).append(r)
    qstats = {}
    for q in sorted(per_queue):
        g = per_queue[q]
        qstats[q] = {
            "count": len(g),
            "avg_waiting": sum(r["waiting"] for r in g) / len(g),
            "avg_turnaround": sum(r["turnaround"] for r in g) / len(g),
            "avg_response": sum(r["response"] for r in g) / len(g),
            "max_turnaround": max(r["turnaround"] for r in g),
        }
    return rows, summary, qstats


def metrics(plist: List[Process]):
    """Backwards-compatible wrapper: returns ``(rows, averages)``."""
    rows, summary, _ = metrics_full(plist)
    avg = {k: summary[k] for k in ("waiting", "turnaround", "response")}
    return rows, avg


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def format_gantt(gantt) -> str:
    bar = "|" + "|".join(f" {n} ".center(max(len(n) + 2, 2 * (e - s)))
                         for s, e, n in gantt) + "|"
    return bar + "\n" + "  ".join(f"{s}-{e}:{n}" for s, e, n in gantt)


def format_table(rows, summary, qstats=None) -> str:
    head = (f"{'PID':<6}{'Q':>3}{'Arr':>5}{'Burst':>6}{'Fin':>5}"
            f"{'Wait':>6}{'TAT':>5}{'Resp':>6}")
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(f"{r['pid']:<6}{r['queue']:>3}{r['arrival']:>5}{r['burst']:>6}"
                     f"{r['finish']:>5}{r['waiting']:>6}{r['turnaround']:>5}{r['response']:>6}")
    lines.append("-" * len(head))
    lines.append(f"avg waiting   = {summary['waiting']:.2f}")
    lines.append(f"avg turnaround= {summary['turnaround']:.2f}")
    lines.append(f"avg response  = {summary['response']:.2f}")
    if "utilization" in summary:
        lines.append(f"total time    = {summary['total_time']}   busy = {summary['busy']}"
                     f"   idle = {summary['idle']}")
        lines.append(f"CPU utilization = {summary['utilization'] * 100:.2f}%")
        lines.append(f"throughput    = {summary['throughput']:.4f} proc/tick")
        lines.append(f"context switches (proc->proc) = {summary['context_switches']}"
                     f"   dispatches = {summary['dispatches']}"
                     f"   total switches = {summary['switches_total']}")
        lines.append(f"preemptions = {summary['preemptions']}"
                     f"   aging promotions = {summary['promotions']}")
    if qstats:
        lines.append("")
        lines.append(f"{'Q':>3}{'n':>4}{'avgW':>9}{'avgTAT':>9}{'avgR':>9}{'maxTAT':>9}")
        for q, s in qstats.items():
            lines.append(f"{q:>3}{s['count']:>4}{s['avg_waiting']:>9.2f}"
                         f"{s['avg_turnaround']:>9.2f}{s['avg_response']:>9.2f}"
                         f"{s['max_turnaround']:>9}")
    return "\n".join(lines)


def to_csv(rows) -> str:
    keys = ["pid", "queue", "arrival", "burst", "finish", "waiting", "turnaround", "response"]
    out = [",".join(keys)]
    for r in rows:
        out.append(",".join(str(r[k]) for k in keys))
    return "\n".join(out)


def plot_gantt(gantt, path: str, title: str = "MLQ Gantt chart",
               queue_of: Optional[Dict[str, int]] = None):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = sorted({n for _, _, n in gantt if n != "IDLE"})
    cmap = plt.get_cmap("tab20")
    colors_ = {q: cmap(i % 20) for i, q in enumerate(sorted(set((queue_of or {}).values())))}
    fig, ax = plt.subplots(figsize=(10, 0.9 + 0.42 * len(names)))
    for s, e, n in gantt:
        if n == "IDLE":
            ax.barh(len(names), e - s, left=s, color="#d9d9d9", edgecolor="black", hatch="//")
        else:
            q = (queue_of or {}).get(n, 1)
            ax.barh(names.index(n), e - s, left=s, color=colors_.get(q, "#4c72b0"),
                    edgecolor="black")
    ax.set_yticks(list(range(len(names))) + ([len(names)] if any(n == "IDLE" for _, _, n in gantt) else []))
    ax.set_yticklabels(names + (["IDLE"] if any(n == "IDLE" for _, _, n in gantt) else []))
    ax.set_xlabel("time (ticks)")
    ax.set_title(title)
    ax.grid(axis="x", linestyle=":", alpha=0.6)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Input handling
# --------------------------------------------------------------------------

def load_config(spec: dict):
    if "queues" not in spec:
        raise InputError("scenario must define 'queues'")
    if "processes" not in spec:
        raise InputError("scenario must define 'processes'")
    cfgs = {int(q): QueueConfig(str(v.get("policy", "FCFS")).upper(), int(v.get("quantum", 2)))
            for q, v in spec["queues"].items()}
    return spec["processes"], cfgs, int(spec.get("aging", 0))


def interactive_input() -> dict:
    """Read a scenario from the keyboard (used by ``--interactive``)."""

    def ask_int(prompt, minimum=None):
        while True:
            raw = input(prompt).strip()
            try:
                v = int(raw)
            except ValueError:
                print("  ! please enter an integer")
                continue
            if minimum is not None and v < minimum:
                print(f"  ! value must be >= {minimum}")
                continue
            return v

    nq = ask_int("number of queues: ", 1)
    queues = {}
    for q in range(1, nq + 1):
        pol = ""
        while pol not in POLICIES:
            pol = input(f"  policy for queue {q} {POLICIES}: ").strip().upper()
        quantum = ask_int(f"  quantum for queue {q} (used by RR): ", 1) if pol == "RR" else 2
        queues[str(q)] = {"policy": pol, "quantum": quantum}
    np_ = ask_int("number of processes: ", 1)
    procs = []
    for i in range(np_):
        print(f"process {i + 1}:")
        pid = input("  pid: ").strip() or f"P{i + 1}"
        arrival = ask_int("  arrival: ", 0)
        burst = ask_int("  burst: ", 1)
        q = 0
        while str(q) not in queues:            # keys of `queues` are strings
            q = ask_int(f"  queue (1..{nq}): ")
        procs.append({"pid": pid, "arrival": arrival, "burst": burst, "queue": q})
    aging = ask_int("aging threshold (0 disables): ", 0)
    return {"queues": queues, "processes": procs, "aging": aging}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description="Multilevel Queue (MLQ) scheduling simulator")
    ap.add_argument("input", nargs="?", help="JSON scenario file ('-' for stdin)")
    ap.add_argument("--interactive", action="store_true", help="enter the scenario by hand")
    ap.add_argument("--png", help="write a Gantt chart PNG to this path")
    ap.add_argument("--csv", help="write the per-process table to this CSV path")
    ap.add_argument("--json", dest="json_out", help="write metrics as JSON to this path")
    ap.add_argument("--aging", type=int, default=None, help="override the aging threshold")
    ap.add_argument("--inter-policy", choices=INTER_POLICIES, default=None,
                    help="override the inter-queue policy")
    ap.add_argument("--slice", type=int, default=None,
                    help="override the inter-queue time slice length")
    ap.add_argument("--policy", action="append", default=[],
                    help="override an intra-queue policy, e.g. --policy 2=RR")
    ap.add_argument("--quiet", action="store_true", help="print only the metrics table")
    a = ap.parse_args(argv)

    try:
        if a.interactive:
            spec = interactive_input()
        else:
            if not a.input:
                raise InputError("no input file given (use a path, '-' for stdin, or --interactive)")
            raw = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
            try:
                spec = json.loads(raw)
            except json.JSONDecodeError as e:
                raise InputError(f"invalid JSON: {e}")
        procs, cfgs, aging = load_config(spec)
        for ov in a.policy:
            if "=" not in ov:
                raise InputError(f"--policy expects Q=POLICY, got {ov!r}")
            q, pol = ov.split("=", 1)
            q = int(q)
            if q not in cfgs:
                raise InputError(f"--policy: queue {q} does not exist")
            cfgs[q].policy = pol.strip().upper()
        plist, gantt, st = simulate_full(procs, cfgs, aging,
                                    inter_policy=(a.inter_policy or spec.get("inter_policy", "fixed")),
                                    inter_slice=int(a.slice or spec.get("inter_slice", 2)))
    except (OSError, json.JSONDecodeError, KeyError, InputError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rows, summary, qstats = metrics_full(plist, st)
    if not a.quiet:
        print(format_gantt(gantt))
        print()
    print(format_table(rows, summary, qstats))
    if a.png:
        plot_gantt(gantt, a.png, queue_of={p.pid: p.home_queue for p in plist})
    if a.csv:
        with open(a.csv, "w", encoding="utf-8") as f:
            f.write(to_csv(rows) + "\n")
    if a.json_out:
        with open(a.json_out, "w", encoding="utf-8") as f:
            json.dump({"rows": rows, "summary": summary,
                       "per_queue": {str(k): v for k, v in qstats.items()},
                       "gantt": [list(g) for g in gantt]}, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
