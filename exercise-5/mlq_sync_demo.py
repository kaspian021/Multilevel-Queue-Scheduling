#!/usr/bin/env python3
"""Exercise 5: Multilevel Queue (MLQ) scheduling with synchronization variants.

Queue policy (fixed MLQ, not MLFQ):
  Q1: highest priority, Round Robin (quantum=2)
  Q2: medium priority, FCFS
  Q3: lowest priority, FCFS
A higher-priority non-empty queue preempts lower-priority work at dispatch boundaries.
This is a deterministic scheduler simulation; synchronization protects shared ready-queue
state and demonstrates semaphore, monitor, and combined designs.
"""
from __future__ import annotations

import argparse
import unittest
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from threading import Condition, Lock, Semaphore
from typing import Deque, Iterable


@dataclass
class Process:
    pid: str
    queue: int
    burst: int
    remaining: int = 0

    def __post_init__(self) -> None:
        if self.queue not in (1, 2, 3):
            raise ValueError("queue must be 1, 2, or 3")
        if self.burst <= 0:
            raise ValueError("burst must be positive")
        self.remaining = self.burst


@dataclass(frozen=True)
class Slice:
    pid: str
    queue: int
    start: int
    end: int


class SemaphoreGuard:
    """Binary semaphore used as a mutex."""
    def __init__(self) -> None:
        self._sem = Semaphore(1)

    def __enter__(self):
        self._sem.acquire()
        return self

    def __exit__(self, *_):
        self._sem.release()


class MonitorGuard:
    """Monitor-style mutual exclusion using a condition and its underlying lock."""
    def __init__(self) -> None:
        self._condition = Condition(Lock())

    def __enter__(self):
        self._condition.acquire()
        return self

    def __exit__(self, *_):
        self._condition.notify_all()
        self._condition.release()


class CombinedGuard:
    """Monitor condition lock plus a semaphore gate for shared-state access."""
    def __init__(self) -> None:
        self._sem = Semaphore(1)
        self._condition = Condition(Lock())

    def __enter__(self):
        self._sem.acquire()
        self._condition.acquire()
        return self

    def __exit__(self, *_):
        self._condition.notify_all()
        self._condition.release()
        self._sem.release()


GUARDS = {
    "semaphore": SemaphoreGuard,
    "monitor": MonitorGuard,
    "both": CombinedGuard,
}


class MLQScheduler:
    def __init__(self, processes: Iterable[Process], mode: str, quantum: int = 2):
        if mode not in GUARDS:
            raise ValueError(f"unknown mode: {mode}")
        if quantum <= 0:
            raise ValueError("quantum must be positive")
        self.queues: dict[int, Deque[Process]] = {1: deque(), 2: deque(), 3: deque()}
        self.guard = GUARDS[mode]()
        self.quantum = quantum
        self.timeline: list[Slice] = []
        self.waiting: dict[str, int] = {}
        self.completion: dict[str, int] = {}
        self.processes: dict[str, Process] = {}
        for p in processes:
            if p.pid in self.processes:
                raise ValueError(f"duplicate process id: {p.pid}")
            self.processes[p.pid] = p
            self.queues[p.queue].append(p)
            self.waiting[p.pid] = 0

    def run(self) -> list[Slice]:
        now = 0
        last_finish: dict[str, int] = {}
        while any(self.queues[q] for q in (1, 2, 3)):
            with self.guard:
                qid = next((q for q in (1, 2, 3) if self.queues[q]), None)
                if qid is None:
                    break
                proc = self.queues[qid].popleft()
                duration = min(proc.remaining, self.quantum) if qid == 1 else proc.remaining
                # Waiting time is the time a ready process spends behind earlier work.
                for other_q in self.queues.values():
                    for other in other_q:
                        self.waiting[other.pid] += duration
                start = now
                now += duration
                proc.remaining -= duration
                self.timeline.append(Slice(proc.pid, qid, start, now))
                if proc.remaining:
                    self.queues[qid].append(proc)
                else:
                    self.completion[proc.pid] = now
        return self.timeline

    def metrics(self) -> dict[str, dict[str, int]]:
        result = {}
        for pid, p in self.processes.items():
            finish = self.completion[pid]
            result[pid] = {
                "queue": p.queue,
                "burst": p.burst,
                "completion": finish,
                "turnaround": finish,
                "waiting": finish - p.burst,
            }
        return result


def example_processes() -> list[Process]:
    # Queue assignments are fixed at creation, as required by MLQ.
    return [
        Process("P1", 1, 5),
        Process("P2", 1, 3),
        Process("P3", 2, 4),
        Process("P4", 2, 2),
        Process("P5", 3, 3),
    ]


def render_gantt(timeline: list[Slice], output: Path) -> None:
    """Write a standalone SVG Gantt chart from the actual simulated trace."""
    output.parent.mkdir(parents=True, exist_ok=True)
    scale, left, top, height = 55, 55, 50, 44
    width = left * 2 + max((s.end for s in timeline), default=1) * scale
    colors = {1: "#8ecae6", 2: "#ffd166", 3: "#b7e4c7"}
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="180" viewBox="0 0 {width} 180">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="20" y="25" font-size="18" font-family="sans-serif" font-weight="bold">MLQ Gantt Chart (simulated trace)</text>',
    ]
    for s in timeline:
        x = left + s.start * scale
        w = (s.end - s.start) * scale
        parts.append(f'<rect x="{x}" y="{top}" width="{w}" height="{height}" fill="{colors[s.queue]}" stroke="#263238"/>')
        parts.append(f'<text x="{x + w/2}" y="{top + 27}" text-anchor="middle" font-size="14" font-family="sans-serif">{s.pid}</text>')
        parts.append(f'<text x="{x}" y="{top + height + 20}" text-anchor="middle" font-size="11" font-family="sans-serif">{s.start}</text>')
    end = max((s.end for s in timeline), default=0)
    parts.append(f'<text x="{left + end * scale}" y="{top + height + 20}" text-anchor="middle" font-size="11" font-family="sans-serif">{end}</text>')
    parts.append('<text x="20" y="155" font-size="12" font-family="sans-serif">Q1 = blue (RR, q=2) | Q2 = yellow (FCFS) | Q3 = green (FCFS)</text>')
    parts.append('</svg>')
    output.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=GUARDS, default="semaphore", help="synchronization implementation")
    parser.add_argument("--gantt", default="", help="optional path to write a Gantt chart SVG")
    parser.add_argument("--all", action="store_true", help="run all three synchronization modes")
    args = parser.parse_args()
    modes = tuple(GUARDS) if args.all else (args.mode,)
    for mode in modes:
        scheduler = MLQScheduler(example_processes(), mode)
        timeline = scheduler.run()
        print(f"Mode: {mode}")
        print("Gantt: " + " | ".join(f"{s.start}-{s.end}:{s.pid}(Q{s.queue})" for s in timeline))
        print("PID  Queue  Burst  Completion  Waiting  Turnaround")
        metrics = scheduler.metrics()
        for pid, m in metrics.items():
            print(f"{pid:<4} {m['queue']:<6} {m['burst']:<6} {m['completion']:<11} {m['waiting']:<8} {m['turnaround']}")
        if args.gantt:
            path = Path(args.gantt)
            if args.all:
                path = path.with_name(f"{path.stem}-{mode}{path.suffix or '.svg'}")
            render_gantt(timeline, path)
            print(f"Gantt SVG written to: {path}")


class SchedulerTests(unittest.TestCase):
    def test_all_modes_have_same_deterministic_trace(self):
        traces = []
        for mode in GUARDS:
            scheduler = MLQScheduler(example_processes(), mode)
            traces.append([(s.pid, s.queue, s.start, s.end) for s in scheduler.run()])
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])

    def test_queue_one_uses_round_robin_quantum(self):
        scheduler = MLQScheduler(example_processes(), "semaphore", quantum=2)
        timeline = scheduler.run()
        q1 = [s for s in timeline if s.queue == 1]
        self.assertTrue(all(s.end - s.start <= 2 for s in q1))
        self.assertEqual(sum(s.end - s.start for s in q1), 8)

    def test_high_priority_queue_runs_before_lower_queues(self):
        scheduler = MLQScheduler(example_processes(), "monitor")
        timeline = scheduler.run()
        first_lower = next(i for i, s in enumerate(timeline) if s.queue > 1)
        self.assertTrue(all(s.queue == 1 for s in timeline[:first_lower]))
        self.assertEqual(timeline[first_lower].queue, 2)

    def test_every_process_completes(self):
        scheduler = MLQScheduler(example_processes(), "both")
        scheduler.run()
        self.assertEqual(set(scheduler.completion), {"P1", "P2", "P3", "P4", "P5"})
        self.assertTrue(all(p.remaining == 0 for p in scheduler.processes.values()))

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            Process("bad", 4, 2)
        with self.assertRaises(ValueError):
            Process("bad", 1, 0)


if __name__ == "__main__":
    main()
