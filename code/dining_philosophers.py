"""Fair dining-philosophers implementation for Exercise 8."""
from collections import deque
from threading import Condition, Lock, Thread
from time import monotonic, sleep


class FairSemaphore:
    """Counting semaphore that grants permits to waiting tickets in FIFO order."""
    def __init__(self, capacity=1, name="semaphore"):
        if not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self.name = name
        self.available = capacity
        self.waiters = deque()
        self.cv = Condition()

    def acquire(self, timeout=None):
        ticket = object()
        deadline = None if timeout is None else monotonic() + timeout
        with self.cv:
            self.waiters.append(ticket)
            try:
                while self.waiters[0] is not ticket or self.available == 0:
                    if deadline is None:
                        self.cv.wait()
                    else:
                        remaining = deadline - monotonic()
                        if remaining <= 0:
                            self.waiters.remove(ticket)
                            self.cv.notify_all()
                            return False
                        self.cv.wait(remaining)
                self.waiters.popleft()
                self.available -= 1
                self.cv.notify_all()
                return True
            except BaseException:
                try:
                    self.waiters.remove(ticket)
                except ValueError:
                    pass
                self.cv.notify_all()
                raise

    def release(self):
        with self.cv:
            if self.available >= self.capacity:
                raise ValueError(f"over-release of {self.name}")
            self.available += 1
            self.cv.notify_all()

    @property
    def waiting_count(self):
        with self.cv:
            return len(self.waiters)


class DiningPhilosophers:
    """N-1 admission + global fork order + FIFO semaphores."""
    def __init__(self, count=5, eat_seconds=0.001, think_seconds=0.0):
        if count < 3:
            raise ValueError("at least three philosophers are required")
        if eat_seconds < 0 or think_seconds < 0:
            raise ValueError("durations cannot be negative")
        self.count = count
        self.room = FairSemaphore(count - 1, "room")
        self.forks = [FairSemaphore(1, f"fork-{i}") for i in range(count)]
        self.eat_seconds = eat_seconds
        self.think_seconds = think_seconds
        self.meals = [0] * count
        self.events = []
        self.event_lock = Lock()
        self.active_eaters = {}

    def record(self, i, action, pair):
        with self.event_lock:
            if action == "eat_start":
                for other, used in self.active_eaters.items():
                    if set(pair) & used:
                        raise AssertionError(f"adjacent P{i} and P{other} eating")
                self.active_eaters[i] = set(pair)
            elif action == "eat_end":
                self.active_eaters.pop(i, None)
            self.events.append((len(self.events) + 1, i, action, pair, monotonic()))

    def one_meal(self, i):
        pair = (i, (i + 1) % self.count)
        first, second = sorted(pair)
        got_room = got_first = got_second = False
        try:
            self.room.acquire()
            got_room = True
            self.record(i, "room_enter", (first, second))
            self.forks[first].acquire()
            got_first = True
            self.record(i, "first_fork", (first, second))
            self.forks[second].acquire()
            got_second = True
            self.record(i, "second_fork", (first, second))
            self.record(i, "eat_start", (first, second))
            if self.eat_seconds:
                sleep(self.eat_seconds)
            self.meals[i] += 1
            self.record(i, "eat_end", (first, second))
        finally:
            if got_second:
                self.forks[second].release()
            if got_first:
                self.forks[first].release()
            if got_room:
                self.room.release()
            self.record(i, "leave", (first, second))

    def run(self, meals_per_philosopher=1, timeout=10.0):
        if meals_per_philosopher < 1:
            raise ValueError("meals_per_philosopher must be positive")
        self.meals = [0] * self.count
        errors = []
        error_lock = Lock()

        def worker(i):
            try:
                for _ in range(meals_per_philosopher):
                    if self.think_seconds:
                        sleep(self.think_seconds)
                    self.one_meal(i)
            except BaseException as exc:
                with error_lock:
                    errors.append(exc)

        threads = [Thread(target=worker, args=(i,), name=f"P{i}", daemon=True)
                   for i in range(self.count)]
        deadline = monotonic() + timeout
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(max(0.0, deadline - monotonic()))
        alive = [t.name for t in threads if t.is_alive()]
        if alive:
            raise TimeoutError(f"threads did not finish: {alive}")
        if errors:
            raise RuntimeError("philosopher worker failed") from errors[0]
        if self.meals != [meals_per_philosopher] * self.count:
            raise AssertionError(f"incomplete meals: {self.meals}")
        return list(self.events)


if __name__ == "__main__":
    import argparse, json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--philosophers", type=int, default=5)
    parser.add_argument("--meals", type=int, default=3)
    parser.add_argument("--eat-ms", type=float, default=1.0)
    args = parser.parse_args()
    sim = DiningPhilosophers(args.philosophers, args.eat_ms / 1000.0)
    trace = sim.run(args.meals)
    print(json.dumps({
        "philosophers": args.philosophers,
        "events": len(trace),
        "meals_completed": sum(sim.meals),
        "per_philosopher": sim.meals,
        "all_completed": sim.meals == [args.meals] * args.philosophers,
    }, indent=2))
    for seq, philosopher, action, pair, _ in trace:
        print(f"{seq:03d} P{philosopher} {action:<12} forks={pair}")
