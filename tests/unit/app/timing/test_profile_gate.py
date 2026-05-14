"""``gated_stage_probe`` runtime mode-gate tests (Phase 3 Q4)."""

from __future__ import annotations

import time

import pytest

from workbench.app.timing.frame_profiler import FrameProfiler
from workbench.app.timing.profile_gate import gated_stage_probe
from workbench.app.timing.stage_timing_probe import StageTimingProbe
from workbench.domain.timing import ProfileMode


def test_off_returns_null_context_no_sample_recorded() -> None:
    """ProfileMode.OFF must never call profiler.record_sample.

    The gate returns ``nullcontext()`` so the body still runs; only
    the probe instrumentation is skipped.
    """
    profiler = FrameProfiler()
    with gated_stage_probe(ProfileMode.OFF, profiler, "detector"):
        sum(range(20))
    assert profiler.stages() == ()


def test_explicit_returns_real_probe_records_one_sample() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    with gated_stage_probe(ProfileMode.EXPLICIT, profiler, "detector"):
        sum(range(20))
    report = profiler.report("detector")
    assert report.n_samples == 1


def test_live_returns_real_probe_records_one_sample() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    with gated_stage_probe(ProfileMode.LIVE, profiler, "tracker"):
        sum(range(20))
    report = profiler.report("tracker")
    assert report.n_samples == 1


def test_explicit_probe_type_is_stage_timing_probe() -> None:
    """Sanity: explicit / live both return the real probe class."""
    profiler = FrameProfiler()
    probe = gated_stage_probe(ProfileMode.EXPLICIT, profiler, "x")
    assert isinstance(probe, StageTimingProbe)


def test_off_skips_recording_even_on_exception() -> None:
    """The OFF path uses nullcontext so an exception inside the body
    propagates normally and still records nothing."""
    profiler = FrameProfiler()
    with (
        pytest.raises(RuntimeError, match="boom"),
        gated_stage_probe(ProfileMode.OFF, profiler, "detector"),
    ):
        msg = "boom"
        raise RuntimeError(msg)
    assert profiler.stages() == ()


def test_live_records_sample_even_on_exception() -> None:
    """The real probe captures the worst-case sample even when the
    body raised — invariant inherited from StageTimingProbe."""
    profiler = FrameProfiler(warmup_samples=0)
    with (
        pytest.raises(RuntimeError, match="boom"),
        gated_stage_probe(ProfileMode.LIVE, profiler, "detector"),
    ):
        msg = "boom"
        raise RuntimeError(msg)
    assert profiler.report("detector").n_samples == 1


def test_off_consecutive_frames_remain_empty() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    for _ in range(5):
        with gated_stage_probe(ProfileMode.OFF, profiler, "detector"):
            time.sleep(0.0)
    assert profiler.stages() == ()


def test_live_consecutive_frames_accumulate() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    for _ in range(5):
        with gated_stage_probe(ProfileMode.LIVE, profiler, "detector"):
            pass
    assert profiler.report("detector").n_samples == 5
