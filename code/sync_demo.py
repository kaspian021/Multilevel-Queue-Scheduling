"""Runnable Python demonstrations for semaphore and monitor-style locking.
Dekker and Peterson are provided as pseudocode in the report, not emulated with
unsafe ordinary Python variables.
"""
from threading import Condition, Semaphore, Thread

def semaphore_demo(workers=4, increments=2000):
    sem = Semaphore(1)
    counter = [0]
    def worker():
        for _ in range(increments):
            with sem:
                counter[0] += 1
    threads = [Thread(target=worker) for _ in range(workers)]
    for t in threads: t.start()
    for t in threads: t.join()
    return counter[0]

def monitor_demo(workers=4, increments=2000):
    condition = Condition()
    state = {"counter": 0, "active": 0, "maximum_active": 0}
    def worker():
        for _ in range(increments):
            with condition:
                state["active"] += 1
                state["maximum_active"] = max(state["maximum_active"], state["active"])
                state["counter"] += 1
                state["active"] -= 1
                condition.notify_all()
    threads = [Thread(target=worker) for _ in range(workers)]
    for t in threads: t.start()
    for t in threads: t.join()
    return state

if __name__ == "__main__":
    print("Semaphore counter:", semaphore_demo())
    print("Monitor state:", monitor_demo())
