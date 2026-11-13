# Exercise 4 — Dekker, Peterson, Semaphore, and Monitor
A comparative study of four mutual-exclusion approaches. The algorithms are not interchangeable: Dekker and Peterson are software protocols for two participants under a sequentially consistent shared-memory model; semaphores are synchronization primitives; monitors are higher-level abstractions that encapsulate shared state and condition synchronization.

- [English report](COMPARISON_EN.md)
- [گزارش فارسی](COMPARISON_FA.md)
- [Runnable Python demonstrations](sync_demo.py)
- [Unit tests](test_sync_demo.py)

Run:
```bash
python exercise-4/sync_demo.py
python -m unittest discover -s exercise-4 -p 'test_*.py' -v
```
The Python lock/semaphore demonstrations use the runtime's synchronization primitives. They do not claim to implement Dekker or Peterson using low-level atomic memory operations. The code includes reference pseudocode for those classic algorithms and tests the higher-level semaphore/monitor demonstrations.
