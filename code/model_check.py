"""Exhaustive finite-state comparison of two dining-philosopher protocols."""
from collections import deque
from dataclasses import dataclass


@dataclass
class Result:
    algorithm: str
    states: int
    transitions: int
    deadlocks: list


def explore_naive(n=5):
    """Each philosopher takes left, then waits for right while holding left."""
    start = (0,) * n
    queue, seen = deque([start]), {start}
    edges = 0
    deadlocks = []
    while queue:
        state = queue.popleft()
        if state == (3,) * n:
            continue
        owners = [None] * n
        for p, stage in enumerate(state):
            if stage in (1, 2):
                owners[p] = p
            if stage == 2:
                owners[(p + 1) % n] = p
        successors = []
        for p, stage in enumerate(state):
            nxt = list(state)
            if stage == 0 and owners[p] is None:
                nxt[p] = 1
                successors.append(tuple(nxt))
            elif stage == 1 and owners[(p + 1) % n] is None:
                nxt[p] = 2
                successors.append(tuple(nxt))
            elif stage == 2:
                nxt[p] = 3
                successors.append(tuple(nxt))
        edges += len(successors)
        if not successors:
            deadlocks.append(state)
        for nxt in successors:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return Result("naive_left_then_right", len(seen), edges, deadlocks)


def explore_ordered(n=5):
    """At most N-1 enter; each obtains lower-numbered fork before higher."""
    start = (0,) * n
    queue, seen = deque([start]), {start}
    edges = 0
    deadlocks = []
    while queue:
        state = queue.popleft()
        if state == (4,) * n:
            continue
        room_users = sum(s in (1, 2, 3) for s in state)
        owners = [None] * n
        for p, stage in enumerate(state):
            if stage in (2, 3):
                first, second = sorted((p, (p + 1) % n))
                owners[first] = p
                if stage == 3:
                    owners[second] = p
        successors = []
        for p, stage in enumerate(state):
            nxt = list(state)
            if stage == 0 and room_users < n - 1:
                nxt[p] = 1
                successors.append(tuple(nxt))
            elif stage == 1:
                first, _ = sorted((p, (p + 1) % n))
                if owners[first] is None:
                    nxt[p] = 2
                    successors.append(tuple(nxt))
            elif stage == 2:
                _, second = sorted((p, (p + 1) % n))
                if owners[second] is None:
                    nxt[p] = 3
                    successors.append(tuple(nxt))
            elif stage == 3:
                nxt[p] = 4
                successors.append(tuple(nxt))
        edges += len(successors)
        if not successors:
            deadlocks.append(state)
        for nxt in successors:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return Result("n_minus_1_plus_global_order", len(seen), edges, deadlocks)


if __name__ == "__main__":
    import json
    for result in (explore_naive(), explore_ordered()):
        print(json.dumps({
            "algorithm": result.algorithm,
            "states": result.states,
            "transitions": result.transitions,
            "deadlock_state_count": len(result.deadlocks),
            "first_deadlock": result.deadlocks[0] if result.deadlocks else None,
        }, indent=2))
