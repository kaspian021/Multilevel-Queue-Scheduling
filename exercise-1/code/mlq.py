"""Multilevel Queue (MLQ) scheduling simulator (discrete, unit-time).

Queues are numbered 1..N (1 = highest priority).  Between queues the policy is
fixed-priority preemptive: a ready process in a higher queue always preempts a
running process of a lower queue.  Inside each queue the policy is configurable:
  FCFS - first come first served (non-preemptive inside the queue)
  RR   - round robin with a time slice (quantum)
  SJF  - shortest (total) burst first, non-preemptive inside the queue
Optional aging promotes a process one queue up after waiting `aging` ticks in a
ready state; this is a starvation-prevention extension (not pure MLQ).

All times are integers (simulation ticks).  This is a model, not a kernel.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

POLICIES = ("FCFS", "RR", "SJF")


class InputError(ValueError):
    """Raised for invalid user input."""


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

    def __post_init__(self):
        self.remaining = self.burst


@dataclass
class QueueConfig:
    policy: str = "FCFS"
    quantum: int = 2


def validate(procs: List[dict], configs: Dict[int, QueueConfig]) -> List[Process]:
    if not isinstance(procs, list) or not procs:
        raise InputError("at least one process is required")
    out, seen = [], set()
    for i, p in enumerate(procs):
        try:
            pid = str(p["pid"])
            arrival, burst, queue = int(p["arrival"]), int(p["burst"]), int(p["queue"])
            prio = int(p.get("priority", 0))
        except (KeyError, TypeError, ValueError) as e:
            raise InputError(f"process #{i + 1}: missing/non-integer field ({e})")
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


def simulate(procs: List[dict], configs: Dict[int, QueueConfig], aging: int = 0):
    """Return (processes, gantt) where gantt is a list of (start, end, pid|'IDLE')."""
    plist = validate(procs, configs)
    levels = sorted(configs)
    queues: Dict[int, List[Process]] = {q: [] for q in levels}
    pending = sorted(plist, key=lambda p: (p.arrival, p.pid))
    t, current, slice_used, done = 0, None, 0, 0
    ticks: List[str] = []
    while done < len(plist):
        while pending and pending[0].arrival <= t:
            p = pending.pop(0)
            p.wait_since = t
            queues[p.queue].append(p)
        if aging > 0:  # promote long-waiting ready processes
            for q in levels[1:]:
                for p in list(queues[q]):
                    if t - p.wait_since >= aging:
                        queues[q].remove(p)
                        p.queue = levels[levels.index(q) - 1]
                        p.wait_since = t
                        queues[p.queue].append(p)
        top = next((q for q in levels if queues[q]), None)
        if current is not None and top is not None and levels.index(top) < levels.index(current.queue):
            queues[current.queue].insert(0, current)      # preempted: back to front
            current.wait_since = t
            current, slice_used = None, 0
        if current is None and top is not None:
            cfg = configs[top]
            q = queues[top]
            if cfg.policy == "SJF":
                nxt = min(q, key=lambda p: (p.burst, p.arrival, p.priority, p.pid))
            elif cfg.policy == "FCFS":
                nxt = q[0]
            else:
                nxt = q[0]
            q.remove(nxt)
            current, slice_used = nxt, 0
            if current.first_start is None:
                current.first_start = t
        if current is None:
            ticks.append("IDLE")
            t += 1
            continue
        ticks.append(current.pid)
        current.remaining -= 1
        slice_used += 1
        t += 1
        if current.remaining == 0:
            current.finish = t
            done += 1
            current, slice_used = None, 0
        elif configs[current.queue].policy == "RR" and slice_used >= configs[current.queue].quantum:
            # arrivals at time t must enter before the preempted process (convention)
            while pending and pending[0].arrival <= t:
                p = pending.pop(0)
                p.wait_since = t
                queues[p.queue].append(p)
            current.wait_since = t
            queues[current.queue].append(current)
            current, slice_used = None, 0
    gantt = []
    for i, name in enumerate(ticks):
        if gantt and gantt[-1][2] == name:
            gantt[-1] = (gantt[-1][0], i + 1, name)
        else:
            gantt.append((i, i + 1, name))
    return plist, gantt


def metrics(plist: List[Process]):
    rows = []
    for p in sorted(plist, key=lambda p: p.pid):
        tat = p.finish - p.arrival
        rows.append({"pid": p.pid, "queue": p.queue, "arrival": p.arrival, "burst": p.burst,
                     "finish": p.finish, "waiting": tat - p.burst, "turnaround": tat,
                     "response": p.first_start - p.arrival})
    n = len(rows)
    avg = {k: sum(r[k] for r in rows) / n for k in ("waiting", "turnaround", "response")}
    return rows, avg


def format_table(rows, avg) -> str:
    head = f"{'PID':<6}{'Q':>3}{'Arr':>5}{'Burst':>6}{'Fin':>5}{'Wait':>6}{'TAT':>5}{'Resp':>6}"
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(f"{r['pid']:<6}{r['queue']:>3}{r['arrival']:>5}{r['burst']:>6}{r['finish']:>5}"
                     f"{r['waiting']:>6}{r['turnaround']:>5}{r['response']:>6}")
    lines.append(f"avg waiting={avg['waiting']:.2f}  turnaround={avg['turnaround']:.2f}  response={avg['response']:.2f}")
    return "\n".join(lines)


def format_gantt(gantt) -> str:
    bar = "|" + "|".join(f" {n} ".center(max(len(n) + 2, 2 * (e - s))) for s, e, n in gantt) + "|"
    return bar + "\n" + "  ".join(f"{s}-{e}:{n}" for s, e, n in gantt)


def plot_gantt(gantt, path: str):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = sorted({n for _, _, n in gantt if n != "IDLE"})
    fig, ax = plt.subplots(figsize=(10, 1.2 + 0.5 * len(names)))
    for s, e, n in gantt:
        if n != "IDLE":
            ax.barh(names.index(n), e - s, left=s, edgecolor="black")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("time (ticks)")
    ax.set_title("MLQ Gantt chart")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def load_config(spec: dict):
    cfgs = {int(q): QueueConfig(v.get("policy", "FCFS").upper(), int(v.get("quantum", 2)))
            for q, v in spec["queues"].items()}
    return spec["processes"], cfgs, int(spec.get("aging", 0))


def main(argv=None):
    ap = argparse.ArgumentParser(description="MLQ scheduling simulator")
    ap.add_argument("input", help="JSON scenario file")
    ap.add_argument("--png", help="write Gantt chart PNG to this path")
    a = ap.parse_args(argv)
    try:
        with open(a.input, encoding="utf-8") as f:
            procs, cfgs, aging = load_config(json.load(f))
        plist, gantt = simulate(procs, cfgs, aging)
    except (OSError, json.JSONDecodeError, KeyError, InputError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    rows, avg = metrics(plist)
    print(format_gantt(gantt))
    print()
    print(format_table(rows, avg))
    if a.png:
        plot_gantt(gantt, a.png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
