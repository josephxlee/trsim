"""Unit tests for app.timing.performance_clock (Phase 5.11)."""

from __future__ import annotations

import time

import pytest

from workbench.app.timing.performance_clock import PerformanceClock


def test_constructor_rejects_non_positive_budget() -> None:
    with pytest.raises(ValueError, match=r"target_frame_budget_s"):
        PerformanceClock(target_frame_budget_s=0.0)
    with pytest.raises(ValueError, match=r"target_frame_budget_s"):
        PerformanceClock(target_frame_budget_s=-0.01)


def test_from_target_latency_ms_factory() -> None:
    clock = PerformanceClock.from_target_latency_ms(50.0)
    assert clock.target_frame_budget_s == pytest.approx(0.05, rel=1e-12)


def test_from_frame_rate_hz_factory() -> None:
    clock = PerformanceClock.from_frame_rate_hz(20.0)
    assert clock.target_frame_budget_s == pytest.approx(0.05, rel=1e-12)


@pytest.mark.parametrize("bad_rate", [0.0, -1.0, -100.0])
def test_from_frame_rate_hz_rejects_non_positive(bad_rate: float) -> None:
    with pytest.raises(ValueError, match=r"frame_rate_hz"):
        PerformanceClock.from_frame_rate_hz(bad_rate)


def test_sleep_remaining_returns_zero_when_budget_exhausted() -> None:
    """If the frame body already overran the budget, no sleep occurs."""
    clock = PerformanceClock(target_frame_budget_s=0.001)
    # Build a frame_start_ns from long ago so elapsed > budget guaranteed.
    long_ago_ns = time.perf_counter_ns() - int(0.01 * 1e9)
    slept = clock.sleep_remaining(long_ago_ns)
    assert slept == 0.0


def test_sleep_remaining_pads_short_frames_to_budget() -> None:
    """A frame that finished in negligible time should sleep ~budget."""
    clock = PerformanceClock(target_frame_budget_s=0.020)
    frame_start = time.perf_counter_ns()
    slept = clock.sleep_remaining(frame_start)
    # Sleep duration should be within reasonable tolerance of the budget.
    # OS sleep precision varies; allow generous bracket.
    assert 0.005 <= slept <= 0.05


def test_factories_round_trip_with_constructor() -> None:
    """from_target_latency_ms(t).budget == t/1000 == from_frame_rate(1000/t)."""
    a = PerformanceClock.from_target_latency_ms(40.0)
    b = PerformanceClock.from_frame_rate_hz(25.0)
    assert a.target_frame_budget_s == pytest.approx(b.target_frame_budget_s, rel=1e-12)


# ---------- 5.11b — factory cross-check + sleep bracket invariants ----------


@pytest.mark.parametrize("latency_ms", [10.0, 25.0, 50.0, 100.0, 250.0])
def test_factory_cross_check_across_latency_sweep(latency_ms: float) -> None:
    """``from_target_latency_ms(t) == from_frame_rate_hz(1000/t)`` for
    every plausible latency. Pins the duality across 5 sample points.
    """
    by_latency = PerformanceClock.from_target_latency_ms(latency_ms)
    by_rate = PerformanceClock.from_frame_rate_hz(1000.0 / latency_ms)
    assert by_latency.target_frame_budget_s == pytest.approx(
        by_rate.target_frame_budget_s, rel=1e-12
    )


@pytest.mark.parametrize("bad_ms", [0.0, -1.0, -100.0])
def test_from_target_latency_ms_rejects_non_positive(bad_ms: float) -> None:
    """Mirror of the from_frame_rate_hz rejection — the latency factory
    must reject the same set of non-positive inputs.
    """
    with pytest.raises(ValueError):
        PerformanceClock.from_target_latency_ms(bad_ms)


def test_sleep_remaining_never_exceeds_budget() -> None:
    """The slept duration is bounded above by the configured budget —
    a frame body that took 0 ms still cannot oversleep.
    """
    budget = 0.030  # 30 ms
    clock = PerformanceClock(target_frame_budget_s=budget)
    frame_start = time.perf_counter_ns()
    slept = clock.sleep_remaining(frame_start)
    assert 0.0 <= slept <= budget + 1e-6


def test_frame_rate_inverse_relationship_to_latency() -> None:
    """Doubling the latency halves the equivalent frame rate. Verify
    via budget consistency at two latency points.
    """
    low_lat = PerformanceClock.from_target_latency_ms(20.0)
    high_lat = PerformanceClock.from_target_latency_ms(40.0)
    # 40 ms = 2x of 20 ms -> budget doubles.
    assert high_lat.target_frame_budget_s == pytest.approx(
        2.0 * low_lat.target_frame_budget_s, rel=1e-12
    )
