"""Unit tests for app.timing runtime: PerformanceClock + StageTimingProbe +
FrameBoundaryDetector + FrameProfiler (Phase 3.6)."""

from __future__ import annotations

import math
import time

import pytest

from workbench.app.timing.frame_boundary_detector import FrameBoundaryDetector
from workbench.app.timing.frame_profiler import (
    DEFAULT_WARMUP_SAMPLES,
    FrameProfiler,
    StageReport,
)
from workbench.app.timing.performance_clock import PerformanceClock
from workbench.app.timing.stage_timing_probe import StageTimingProbe

# ---------------------------------------------------------------------
# FrameProfiler — sample / report
# ---------------------------------------------------------------------


def test_default_warmup_samples_locked() -> None:
    assert DEFAULT_WARMUP_SAMPLES == 10


def test_profiler_warmup_negative_rejected() -> None:
    with pytest.raises(ValueError, match=r"warmup_samples"):
        FrameProfiler(warmup_samples=-1)


def test_profiler_record_and_stages_listed() -> None:
    p = FrameProfiler(warmup_samples=0)
    p.record_sample("a", 1_000)
    p.record_sample("b", 2_000)
    p.record_sample("a", 3_000)
    assert p.stages() == ("a", "b")


def test_profiler_record_validation() -> None:
    p = FrameProfiler()
    with pytest.raises(ValueError, match=r"stage_name"):
        p.record_sample("", 100)
    with pytest.raises(ValueError, match=r"elapsed_ns"):
        p.record_sample("x", -1)


def test_profiler_report_with_no_warmup() -> None:
    p = FrameProfiler(warmup_samples=0)
    # 1, 2, 3, 4, 5 ms in nanoseconds
    for ms in [1, 2, 3, 4, 5]:
        p.record_sample("x", ms * 1_000_000)
    r = p.report("x")
    assert isinstance(r, StageReport)
    assert r.n_samples == 5
    assert r.n_post_warmup == 5
    assert r.avg_ms == pytest.approx(3.0, abs=1e-6)
    assert r.p50_ms == pytest.approx(3.0, abs=1e-6)
    # NumPy-style linear-interpolation: rank = 0.95 * 4 = 3.8 -> 3.8 ms
    assert r.p95_ms == pytest.approx(4.8, abs=1e-6)
    assert r.p99_ms == pytest.approx(4.96, abs=1e-6)


def test_profiler_warmup_discards_leading_samples() -> None:
    p = FrameProfiler(warmup_samples=2)
    # Two slow warmup samples, three fast post-warmup samples.
    p.record_sample("x", 100_000_000)  # 100 ms warmup
    p.record_sample("x", 100_000_000)  # 100 ms warmup
    p.record_sample("x", 1_000_000)  # 1 ms
    p.record_sample("x", 2_000_000)  # 2 ms
    p.record_sample("x", 3_000_000)  # 3 ms
    r = p.report("x")
    assert r.n_samples == 5
    assert r.n_post_warmup == 3
    assert r.avg_ms == pytest.approx(2.0, abs=1e-6)


def test_profiler_report_below_warmup_returns_nan() -> None:
    p = FrameProfiler(warmup_samples=10)
    p.record_sample("x", 1_000)
    r = p.report("x")
    assert r.n_post_warmup == 0
    assert math.isnan(r.avg_ms)
    assert math.isnan(r.p50_ms)


def test_profiler_report_unknown_stage_raises() -> None:
    p = FrameProfiler()
    with pytest.raises(KeyError, match=r"x"):
        p.report("x")


def test_profiler_report_all_alphabetical() -> None:
    p = FrameProfiler(warmup_samples=0)
    p.record_sample("zeta", 1)
    p.record_sample("alpha", 1)
    p.record_sample("mid", 1)
    names = [r.stage_name for r in p.report_all()]
    assert names == ["alpha", "mid", "zeta"]


def test_profiler_reset_drops_samples() -> None:
    p = FrameProfiler(warmup_samples=0)
    p.record_sample("x", 1)
    p.reset()
    assert p.stages() == ()


# ---------------------------------------------------------------------
# StageTimingProbe — context manager
# ---------------------------------------------------------------------


def test_probe_records_one_sample_on_exit() -> None:
    p = FrameProfiler(warmup_samples=0)
    with StageTimingProbe(p, stage_name="detector"):
        time.sleep(0.001)  # 1 ms
    r = p.report("detector")
    assert r.n_samples == 1
    # Should be at least ~1 ms; allow generous slack for Windows CI.
    assert r.avg_ms >= 0.5


def test_probe_records_even_when_body_raises() -> None:
    p = FrameProfiler(warmup_samples=0)
    with pytest.raises(RuntimeError), StageTimingProbe(p, stage_name="x"):
        raise RuntimeError("boom")
    # The probe still emitted a sample so percentiles see the failure.
    assert p.stages() == ("x",)


# ---------------------------------------------------------------------
# FrameBoundaryDetector
# ---------------------------------------------------------------------


def test_frame_boundary_detector_increments() -> None:
    d = FrameBoundaryDetector()
    assert d.frame_id == 0
    assert d.on_track_output() is True
    assert d.frame_id == 1
    d.on_track_output()
    d.on_track_output()
    assert d.frame_id == 3


def test_frame_boundary_detector_reset() -> None:
    d = FrameBoundaryDetector()
    d.on_track_output()
    d.on_track_output()
    d.reset()
    assert d.frame_id == 0


# ---------------------------------------------------------------------
# PerformanceClock
# ---------------------------------------------------------------------


def test_performance_clock_construction() -> None:
    c = PerformanceClock(target_frame_budget_s=0.05)
    assert c.target_frame_budget_s == 0.05


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_performance_clock_rejects_non_positive_budget(bad: float) -> None:
    with pytest.raises(ValueError, match=r"target_frame_budget_s"):
        PerformanceClock(target_frame_budget_s=bad)


def test_performance_clock_from_target_latency_ms() -> None:
    c = PerformanceClock.from_target_latency_ms(50.0)
    assert c.target_frame_budget_s == pytest.approx(0.05, abs=1e-12)


def test_performance_clock_from_frame_rate_hz() -> None:
    c = PerformanceClock.from_frame_rate_hz(20.0)
    assert c.target_frame_budget_s == pytest.approx(0.05, abs=1e-12)


def test_performance_clock_from_frame_rate_zero_rejected() -> None:
    with pytest.raises(ValueError, match=r"frame_rate_hz"):
        PerformanceClock.from_frame_rate_hz(0.0)


def test_performance_clock_sleep_remaining_returns_zero_when_overrun() -> None:
    c = PerformanceClock(target_frame_budget_s=0.001)
    start = time.perf_counter_ns()
    time.sleep(0.005)  # 5 ms — well past 1 ms budget
    slept = c.sleep_remaining(start)
    assert slept == 0.0


def test_performance_clock_sleep_remaining_sleeps_when_within_budget() -> None:
    c = PerformanceClock(target_frame_budget_s=0.05)
    start = time.perf_counter_ns()
    slept = c.sleep_remaining(start)
    # Slept some non-trivial duration close to 50 ms (allow generous slack).
    assert slept > 0.01
    assert slept < 0.1
