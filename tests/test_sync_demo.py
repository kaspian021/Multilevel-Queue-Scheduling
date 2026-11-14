import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))
from sync_demo import semaphore_demo, monitor_demo

class SynchronizationDemoTests(unittest.TestCase):
    def test_semaphore_protects_counter(self):
        self.assertEqual(semaphore_demo(workers=4, increments=500), 2000)

    def test_monitor_protects_shared_state(self):
        result = monitor_demo(workers=4, increments=500)
        self.assertEqual(result["counter"], 2000)
        self.assertEqual(result["maximum_active"], 1)

if __name__ == "__main__":
    unittest.main()
