"""Tests for the Exercise-4 model checker.

These tests lock in the verified verdicts. If someone edits an algorithm in
``sync_model.py`` and breaks a property, these tests fail.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import sync_model as sm  # noqa: E402


@pytest.fixture(scope="module")
def results():
    return sm.check_all()


CORRECT = ("dekker", "peterson", "semaphore_binary", "monitor_mesa")


def test_all_algorithms_registered(results):
    assert set(results) == {"dekker", "peterson", "lock_variable", "flag_spin",
                            "tas", "semaphore_binary",
                            "semaphore_wrong_order", "monitor_mesa"}


@pytest.mark.parametrize("name", CORRECT)
def test_mutual_exclusion_holds(results, name):
    assert results[name]["mutual_exclusion"] is True
    assert results[name]["mutual_exclusion_witness"] is None


def test_lock_variable_violates_mutual_exclusion(results):
    r = results["lock_variable"]
    assert r["mutual_exclusion"] is False
    witness = r["mutual_exclusion_witness"]
    assert witness is not None
    # the witness ends with the second process entering while the first is in
    assert sum(1 for step in witness if "ENTER" in step) == 2


@pytest.mark.parametrize("name", ["dekker", "peterson", "tas",
                                  "semaphore_binary", "monitor_mesa"])
def test_deadlock_free(results, name):
    assert results[name]["deadlock_free"] is True


@pytest.mark.parametrize("name", ["flag_spin", "semaphore_wrong_order"])
def test_known_deadlocks(results, name):
    assert results[name]["deadlock_free"] is False
    assert results[name]["deadlock_witness"] is not None


@pytest.mark.parametrize("name", CORRECT)
def test_starvation_free(results, name):
    assert all(results[name]["starvation_free"].values())


def test_tas_has_no_bounded_waiting(results):
    """TAS guarantees exclusion but a process can be overtaken for ever."""
    r = results["tas"]
    assert r["mutual_exclusion"] is True
    assert r["deadlock_free"] is True
    assert all(v is False for v in r["starvation_free"].values())
    for w in r["starvation_witness"].values():
        assert w is not None


def test_state_spaces_are_small_enough_to_be_exhaustive(results):
    for name, r in results.items():
        assert r["truncated"] is False, f"{name} was truncated, not exhaustive"
        assert r["states"] > 0


@pytest.mark.parametrize("name", CORRECT)
def test_critical_section_is_actually_reached(results, name):
    """An algorithm that simply never enters proves nothing."""
    assert results[name]["enter_actions"] > 0


def test_dekker_and_peterson_state_counts(results):
    """Guard against accidental edits to the step functions."""
    assert results["dekker"]["states"] == 324
    assert results["peterson"]["states"] == 199


def test_queue_helpers():
    assert sm._q_head(sm._Q_EMPTY) is None
    assert sm._q_head(sm._Q_P0) == 0
    assert sm._q_head(sm._Q_P1P0) == 1
    assert sm._q_pop(sm._Q_P0P1) == sm._Q_P1
    assert sm._q_pop(sm._Q_P1P0) == sm._Q_P0
    assert sm._q_push(sm._Q_EMPTY, 1) == sm._Q_P1
    assert sm._q_push(sm._Q_P0, 1) == sm._Q_P0P1
    assert sm._q_push(sm._Q_P1, 0) == sm._Q_P1P0


def test_format_report_mentions_every_algorithm(results):
    text = sm.format_report(results)
    for name in results:
        assert name in text
