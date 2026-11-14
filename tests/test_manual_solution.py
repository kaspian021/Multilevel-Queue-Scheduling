import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
import unittest
from manual_solution import JOBS, schedule

class ManualSchedulingTests(unittest.TestCase):
    def test_edf_order(self):
        order = sorted(JOBS, key=lambda j: (j.deadline, j.name))
        self.assertEqual([j.name for j in order], ["B", "C", "A"])
        self.assertEqual([(x[1], x[2]) for x in schedule(order)], [(0,2),(2,3),(3,6)])

    def test_rm_order(self):
        order = sorted(JOBS, key=lambda j: (j.period, j.name))
        self.assertEqual([j.name for j in order], ["A", "B", "C"])
        self.assertEqual([(x[1], x[2]) for x in schedule(order)], [(0,3),(3,5),(5,6)])

if __name__ == "__main__":
    unittest.main()
