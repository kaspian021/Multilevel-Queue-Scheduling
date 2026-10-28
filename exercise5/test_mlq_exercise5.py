import unittest
from mlq_exercise5 import (
    Job,
    schedule_with_semaphore,
    schedule_with_monitor,
    schedule_with_semaphore_and_monitor,
)


class MLQExercise5Tests(unittest.TestCase):
    def setUp(self):
        self.jobs = [
            Job("P1", 2, 3),
            Job("P2", 1, 2),
            Job("P3", 3, 1),
            Job("P4", 1, 1),
        ]

    def test_priority_then_fcfs(self):
        expected = [
            ("P2", 0, 2),
            ("P4", 2, 3),
            ("P1", 3, 6),
            ("P3", 6, 7),
        ]
        for scheduler in (
            schedule_with_semaphore,
            schedule_with_monitor,
            schedule_with_semaphore_and_monitor,
        ):
            with self.subTest(scheduler=scheduler.__name__):
                actual = [(s.pid, s.start, s.finish) for s in scheduler(self.jobs)]
                self.assertEqual(actual, expected)

    def test_empty_input(self):
        for scheduler in (
            schedule_with_semaphore,
            schedule_with_monitor,
            schedule_with_semaphore_and_monitor,
        ):
            self.assertEqual(scheduler([]), [])

    def test_invalid_queue_or_burst(self):
        with self.assertRaises(ValueError):
            Job("BAD", 4, 1)
        with self.assertRaises(ValueError):
            Job("BAD", 1, 0)


if __name__ == "__main__":
    unittest.main()
