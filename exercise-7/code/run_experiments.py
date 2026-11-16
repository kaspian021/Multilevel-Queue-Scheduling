"""Run every Exercise-7 experiment and write all artefacts to output/.

Usage (from the exercise folder)::

    python3 code/run_experiments.py

Everything is repeated and the median is reported. A single run of any of
these benchmarks on a shared machine varied by more than a factor of two, so
no number in the report comes from one run, and the spread is recorded next to
each median rather than being quietly dropped.
"""

from __future__ import annotations

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import rw_model as rm          # noqa: E402
import rw_sync as rs           # noqa: E402

OUT = os.path.join(ROOT, "output")

# The two-process algorithms can only be run with two threads; the harness
# caps them and says so, so they are simply excluded from the sweeps whose
# whole point is more participants.
THREAD_CAP = {n for n, f in rs.LOCKS.items() if getattr(f(), "max_threads", None) == 2}


def median(runs: list, key: str):
    vals = [r[key] for r in runs if isinstance(r.get(key), (int, float))]
    if not vals:
        return None
    return round(statistics.median(vals), 4)


def spread(runs: list, key: str):
    vals = [r[key] for r in runs if isinstance(r.get(key), (int, float))]
    if len(vals) < 2:
        return None
    return round(max(vals) - min(vals), 4)


# Counted over trials rather than averaged: several of these locks are
# bimodal. Readers preference either establishes a read phase that never ends,
# in which case the writer gets in once, or loses the opening race, in which
# case the writer takes most of the traffic. A median of those two is a number
# that describes neither of them.
MAX_OVER = ("reads", "writes", "ops", "spins", "traced_ops",
            "max_concurrent_readers", "longest_read_run", "longest_write_run")
TRIAL_KEYS = ("reads", "writes", "ops", "write_share", "longest_read_run",
              "longest_write_run", "max_concurrent_readers", "traced_ops")


def repeated(fn, reps: int = 5, trials: bool = False) -> dict:
    """Run `fn` `reps` times and reduce the results to medians and spreads."""
    runs = [fn() for _ in range(reps)]
    keys = [k for k in runs[0] if isinstance(runs[0][k], (int, float, bool))]
    out = {}
    for k in keys:
        if isinstance(runs[0][k], bool):
            out[k] = all(r[k] for r in runs)
        elif k in MAX_OVER:
            out[k] = max(r[k] for r in runs)
        else:
            out[k] = median(runs, k)
            sp = spread(runs, k)
            if sp is not None:
                out[k + "_spread"] = sp
    for k in ("lock", "readers", "writers", "thread_limited"):
        if k in runs[0]:
            out[k] = runs[0][k]
    out["reps"] = reps
    if trials:
        out["trials"] = [{k: r[k] for k in TRIAL_KEYS if k in r} for r in runs]
        shares = sorted(r.get("write_share", 0.0) for r in runs)
        out["write_share_sorted"] = shares
        out["writer_starved_trials"] = sum(1 for v in shares if v < 0.01)
        out["writer_dominant_trials"] = sum(1 for v in shares if v > 0.5)
    out["violations"] = [v for r in runs for v in r.get("violations", [])][:10]
    return out


# ------------------------------------------------------------------ E1 cost
def e1_throughput(reps: int = 5, seconds: float = 0.5) -> dict:
    """Four readers and two writers, nothing to do inside the section: how
    many operations per second does each lock cost?"""
    out = {}
    for name, make in rs.LOCKS.items():
        out[name] = repeated(
            lambda m=make: rs.benchmark(m, n_readers=4, n_writers=2,
                                        seconds=seconds), reps)
        print(f"  e1 {name:22s} {out[name]['ops_per_s']:>10.0f} ops/s",
              flush=True)
    return out


# ------------------------------------------------------------- E2 concurrency
def e2_concurrency(reps: int = 5, seconds: float = 0.5, work: int = 3000) -> dict:
    """Six readers, one writer, and real work inside the section: how many
    readers are ever inside at once? This is the property the whole problem
    exists for, and a plain mutex cannot score more than one."""
    out = {}
    for name, make in rs.LOCKS.items():
        if name in THREAD_CAP:
            continue
        out[name] = repeated(
            lambda m=make: rs.benchmark(m, n_readers=6, n_writers=1,
                                        seconds=seconds, work=work), reps)
        print(f"  e2 {name:22s} maxR={out[name]['max_concurrent_readers']}",
              flush=True)
    return out


# -------------------------------------------------------------- E3 starvation
def e3_writer_starvation(reps: int = 5, seconds: float = 0.6) -> dict:
    """Six readers against one writer with nothing to do inside the section:
    the load readers preference is supposed to fail. The telling figure is the
    longest unbroken run of reads -- a lock that never lets the writer in
    produces one run as long as the entire trial."""
    out = {}
    for name, make in rs.LOCKS.items():
        out[name] = repeated(
            lambda m=make: rs.starvation_probe(m, n_readers=6, n_writers=1,
                                               seconds=seconds), reps,
            trials=True)
        row = out[name]
        print(f"  e3 {name:22s} ws={row['write_share']:.3f} "
              f"starved={row['writer_starved_trials']}/{reps} "
              f"dominant={row['writer_dominant_trials']}/{reps}", flush=True)
    return out


def e4_reader_starvation(reps: int = 5, seconds: float = 0.6) -> dict:
    """The mirror image: one reader against three writers. Writers preference
    keeps the reader door shut while any writer is waiting, and with three of
    them it never reopens."""
    out = {}
    for name, make in rs.LOCKS.items():
        if name in THREAD_CAP:
            continue
        out[name] = repeated(
            lambda m=make: rs.starvation_probe(m, n_readers=1, n_writers=3,
                                               seconds=seconds), reps,
            trials=True)
        row = out[name]
        starved = sum(1 for t in row["trials"]
                      if t.get("write_share", 0) > 0.99)
        row["reader_starved_trials"] = starved
        print(f"  e4 {name:22s} ws={row['write_share']:.3f} "
              f"reader_starved={starved}/{reps}", flush=True)
    return out


# ------------------------------------------------------------- E5 scaling
SCALING = ["semaphore_mutex", "readers_pref", "writers_pref", "fair_fifo",
           "barrier", "monitor_mesa", "monitor_fifo"]


def e5_scaling(reps: int = 3, seconds: float = 0.4) -> dict:
    """More readers, one writer, real work in the section: which solutions
    actually gain from having more readers?"""
    out = {}
    for name in SCALING:
        row = {}
        for n in (1, 2, 4, 6, 8):
            row[str(n)] = repeated(
                lambda m=rs.LOCKS[name], k=n: rs.benchmark(
                    m, n_readers=k, n_writers=1, seconds=seconds, work=1500),
                reps)
        out[name] = row
        print(f"  e5 {name:22s} " +
              " ".join(f"{n}R={row[str(n)]['ops_per_s']:.0f}"
                       for n in (1, 2, 4, 6, 8)), flush=True)
    return out


# ---------------------------------------------------------- E6 model checking
def e6_model(reps: int = 1) -> dict:
    results = {}
    for name, sol in rm.SOLUTIONS.items():
        results[name] = rm.explore(sol, max_states=600_000,
                                   stop_on_violation=(sol.family == "broken"))
    return results


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    print("Exercise 7: readers and writers", flush=True)

    print("E1 throughput, 4 readers + 2 writers", flush=True)
    e1 = e1_throughput()
    print("E2 concurrent readers, 6 readers + 1 writer, work in section",
          flush=True)
    e2 = e2_concurrency()
    print("E3 writer starvation, 6 readers + 1 writer", flush=True)
    e3 = e3_writer_starvation(reps=9)
    print("E4 reader starvation, 1 reader + 3 writers", flush=True)
    e4 = e4_reader_starvation(reps=9)
    print("E5 scaling in the number of readers", flush=True)
    e5 = e5_scaling()
    print("E6 exhaustive model checking", flush=True)
    e6 = e6_model()

    payload = {
        "exercise": 7,
        "title": "Readers and writers: semaphore, monitor, Dekker, Peterson",
        "python": sys.version.split()[0],
        "e1_throughput": e1,
        "e2_concurrency": e2,
        "e3_writer_starvation": e3,
        "e4_reader_starvation": e4,
        "e5_scaling": e5,
        "e6_model": e6,
    }
    path = os.path.join(OUT, "experiments.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
    print(f"wrote {path}", flush=True)

    bad = [n for n, r in e1.items() if not r.get("safe")]
    bad += [n for n, r in e2.items() if not r.get("safe")]
    bad += [n for n, r in e3.items() if not r.get("safe")]
    bad += [n for n, r in e4.items() if not r.get("safe")]
    if bad:
        print("INVARIANT VIOLATED:", sorted(set(bad)), flush=True)
        return 1
    print("all locks safe under load", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
