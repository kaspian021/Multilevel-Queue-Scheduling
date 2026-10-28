#!/usr/bin/env python3
"""Exercise 5: Multilevel Queue scheduling with Semaphore, Monitor, and both.

This is a deterministic educational simulation, not an OS/kernel scheduler.
Lower queue numbers mean higher priority. Jobs are non-preemptive and are
selected in strict queue order (FCFS within each queue).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Condition, Semaphore
from typing import Iterable


@dataclass(frozen=True)
class Job:
    pid: str
    queue: int
    burst: int

    def __post_init__(self) -> None:
        if self.queue not in (1, 2, 3):
            raise ValueError("queue must be 1, 2, or 3")
        if self.burst <= 0:
            raise ValueError("burst must be positive")


@dataclass(frozen=True)
class Segment:
    pid: str
    queue: int
    start: int
    finish: int


def _schedule(jobs: Iterable[Job], mode: str) -> list[Segment]:
    """Schedule jobs using the synchronization mechanism requested by mode."""
    if mode not in {"semaphore", "monitor", "both"}:
        raise ValueError("mode must be semaphore, monitor, or both")

    queues = {1: deque(), 2: deque(), 3: deque()}
    # Semaphore protects queue insertion/removal in semaphore modes.
    queue_lock = Semaphore(1)
    # Condition is the monitor: it protects queue state and signals availability.
    monitor = Condition()
    # In 'both', admission is bounded separately while the monitor protects state.
    capacity = Semaphore(max(1, len(list(jobs)))) if mode == "both" else None
    job_list = list(jobs)

    # The queue state is initialized before the scheduling loop; all jobs are ready.
    for job in job_list:
        if mode == "semaphore":
            queue_lock.acquire()
            try:
                queues[job.queue].append(job)
            finally:
                queue_lock.release()
        elif mode == "monitor":
            with monitor:
                queues[job.queue].append(job)
                monitor.notify_all()
        else:
            assert capacity is not None
            capacity.acquire()
            with monitor:
                queues[job.queue].append(job)
                monitor.notify_all()
            capacity.release()

    timeline: list[Segment] = []
    now = 0
    while True:
        if mode == "semaphore":
            queue_lock.acquire()
            try:
                job = next((queues[q].popleft() for q in (1, 2, 3) if queues[q]), None)
            finally:
                queue_lock.release()
        else:
            # Monitor mode uses Condition's lock for the entire queue selection.
            with monitor:
                job = next((queues[q].popleft() for q in (1, 2, 3) if queues[q]), None)

        if job is None:
            break
        timeline.append(Segment(job.pid, job.queue, now, now + job.burst))
        now += job.burst
    return timeline


def schedule_with_semaphore(jobs: Iterable[Job]) -> list[Segment]:
    return _schedule(jobs, "semaphore")


def schedule_with_monitor(jobs: Iterable[Job]) -> list[Segment]:
    return _schedule(jobs, "monitor")


def schedule_with_semaphore_and_monitor(jobs: Iterable[Job]) -> list[Segment]:
    return _schedule(jobs, "both")


def print_gantt(timeline: list[Segment]) -> None:
    if not timeline:
        print("(no jobs)")
        return
    print("Gantt: " + " | ".join(f"{s.pid} [{s.start}-{s.finish}]" for s in timeline))
    print("Time : " + "    ".join(str(s.start) for s in timeline) + f"    {timeline[-1].finish}")


def demo() -> None:
    jobs = [Job("P1", 2, 3), Job("P2", 1, 2), Job("P3", 3, 1), Job("P4", 1, 1)]
    variants = [
        ("Semaphore", schedule_with_semaphore),
        ("Monitor", schedule_with_monitor),
        ("Semaphore + Monitor", schedule_with_semaphore_and_monitor),
    ]
    for title, scheduler in variants:
        print(f"\n=== MLQ with {title} ===")
        timeline = scheduler(jobs)
        print_gantt(timeline)


if __name__ == "__main__":
    demo()
