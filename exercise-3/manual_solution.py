"""Reproduce the hand-worked one-shot EDF and RM example in README.md."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Job:
    name: str
    execution: int
    deadline: int
    period: int

JOBS = [Job("A", 3, 7, 4), Job("B", 2, 4, 6), Job("C", 1, 5, 8)]

def schedule(order):
    now = 0
    rows = []
    for job in order:
        start, finish = now, now + job.execution
        rows.append((job.name, start, finish, job.deadline))
        now = finish
    return rows

def main():
    edf_order = sorted(JOBS, key=lambda j: (j.deadline, j.name))
    rm_order = sorted(JOBS, key=lambda j: (j.period, j.name))
    for label, order in (("EDF", edf_order), ("RM", rm_order)):
        print(label)
        for name, start, finish, deadline in schedule(order):
            print(f"{name}: [{start},{finish}) deadline={deadline} "
                  f"{'ON TIME' if finish <= deadline else 'MISS'}")

if __name__ == "__main__":
    main()
