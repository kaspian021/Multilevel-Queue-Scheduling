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

    job_list = list(jobs)
    queues = {1: deque(), 2: deque(), 3: deque()}
    queue_lock = Semaphore(1)
    # A Condition plus its lock acts as a monitor for shared queue state.
    monitor = Condition()
    # In the combined variant, the semaphore gates admissions and the monitor
    # protects the queues. Capacity is sized to avoid blocking this serial demo.
    capacity = Semaphore(max(1, len(job_list))) if mode == "both" else None

    for job in job_list:
        if mode == "semaphore":
            with_semaphore(queue_lock, queues[job.queue], job)
        elif mode == "monitor":
            with monitor:
                queues[job.queue].append(job)
                monitor.notify_all()
        else:
            assert capacity is not None
            capacity.acquire()
            try:
                with monitor:
                    queues[job.queue].append(job)
                    monitor.notify_all()
            finally:
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
            with monitor:
                job = next((queues[q].popleft() for q in (1, 2, 3) if queues[q]), None)

        if job is None:
            break
        timeline.append(Segment(job.pid, job.queue, now, now + job.burst))
        now += job.burst
    return timeline


def with_semaphore(lock: Semaphore, queue: deque, job: Job) -> None:
    lock.acquire()
    try:
        queue.append(job)
    finally:
        lock.release()


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
        print_gantt(scheduler(jobs))


if __name__ == "__main__":
    demo()
