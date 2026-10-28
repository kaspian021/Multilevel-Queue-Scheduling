import tempfile
import unittest
from pathlib import Path

from mlq_sync_demo import GUARDS, MLQScheduler, Process, example_processes, render_gantt


class MLQSyncTests(unittest.TestCase):
    def test_all_modes_produce_the_same_trace(self):
        traces = []
        for mode in GUARDS:
            scheduler = MLQScheduler(example_processes(), mode)
            traces.append([(s.pid, s.queue, s.start, s.end) for s in scheduler.run()])
        self.assertEqual(traces[0], traces[1])
        self.assertEqual(traces[1], traces[2])

    def test_expected_gantt_trace(self):
        scheduler = MLQScheduler(example_processes(), "semaphore", quantum=2)
        trace = [(s.pid, s.start, s.end) for s in scheduler.run()]
        self.assertEqual(trace, [
            ("P1", 0, 2), ("P2", 2, 4), ("P1", 4, 6),
            ("P2", 6, 7), ("P1", 7, 8), ("P3", 8, 12),
            ("P4", 12, 14), ("P5", 14, 17),
        ])

    def test_q1_round_robin_respects_quantum(self):
        scheduler = MLQScheduler(example_processes(), "monitor", quantum=2)
        q1 = [s for s in scheduler.run() if s.queue == 1]
        self.assertTrue(all(0 < s.end - s.start <= 2 for s in q1))
        self.assertEqual(sum(s.end - s.start for s in q1), 8)

    def test_strict_queue_priority_and_fcfs(self):
        scheduler = MLQScheduler(example_processes(), "both")
        trace = scheduler.run()
        queue_ids = [s.queue for s in trace]
        first_q2, first_q3 = queue_ids.index(2), queue_ids.index(3)
        self.assertTrue(all(q == 1 for q in queue_ids[:first_q2]))
        self.assertTrue(all(q == 2 for q in queue_ids[first_q2:first_q3]))
        self.assertTrue(all(q == 3 for q in queue_ids[first_q3:]))
        self.assertEqual([s.pid for s in trace[first_q2:first_q3]], ["P3", "P4"])

    def test_completion_and_metrics(self):
        scheduler = MLQScheduler(example_processes(), "semaphore")
        scheduler.run()
        metrics = scheduler.metrics()
        self.assertEqual(set(scheduler.completion), {"P1", "P2", "P3", "P4", "P5"})
        self.assertTrue(all(p.remaining == 0 for p in scheduler.processes.values()))
        self.assertEqual(metrics["P1"]["completion"], 8)
        self.assertEqual(metrics["P1"]["waiting"], 3)
        self.assertEqual(metrics["P1"]["turnaround"], 8)
        for row in metrics.values():
            self.assertEqual(row["waiting"] + row["burst"], row["turnaround"])

    def test_empty_workload(self):
        scheduler = MLQScheduler([], "monitor")
        self.assertEqual(scheduler.run(), [])
        self.assertEqual(scheduler.metrics(), {})

    def test_invalid_inputs_and_duplicate_ids(self):
        with self.assertRaises(ValueError):
            MLQScheduler([], "invalid-mode")
        with self.assertRaises(ValueError):
            MLQScheduler([], "semaphore", quantum=0)
        with self.assertRaises(ValueError):
            Process("bad", 4, 1)
        with self.assertRaises(ValueError):
            Process("bad", 1, 0)
        with self.assertRaises(ValueError):
            MLQScheduler([Process("P", 1, 1), Process("P", 2, 2)], "both")

    def test_gantt_svg_generation(self):
        scheduler = MLQScheduler(example_processes(), "both")
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "gantt.svg"
            render_gantt(scheduler.run(), output)
            self.assertTrue(output.is_file())
            svg = output.read_text(encoding="utf-8")
            self.assertIn("<svg", svg)
            self.assertIn("P1", svg)
            self.assertIn("Q3", svg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
