"""Unit tests for app.timing.frame_profiler + stage_timing_probe (Phase 5.13)."""

from __future__ import annotations

import math
import time

import pytest

from workbench.app.timing.frame_profiler import (
    DEFAULT_WARMUP_SAMPLES,
    FrameProfiler,
    StageReport,
)
from workbench.app.timing.stage_timing_probe import StageTimingProbe

# ---------- FrameProfiler ----------


def test_default_warmup_matches_plan_recommendation() -> None:
    fp = FrameProfiler()
    assert fp.warmup_samples == DEFAULT_WARMUP_SAMPLES == 10


def test_negative_warmup_rejected() -> None:
    with pytest.raises(ValueError, match=r"warmup_samples"):
        FrameProfiler(warmup_samples=-1)


def test_record_sample_rejects_empty_stage_name() -> None:
    fp = FrameProfiler()
    with pytest.raises(ValueError, match=r"stage_name"):
        fp.record_sample("", 100)


def test_record_sample_rejects_negative_elapsed() -> None:
    fp = FrameProfiler()
    with pytest.raises(ValueError, match=r"elapsed_ns"):
        fp.record_sample("detector", -1)


def test_stages_returns_alphabetical_tuple() -> None:
    fp = FrameProfiler()
    fp.record_sample("tracker", 100)
    fp.record_sample("detector", 200)
    fp.record_sample("pairing", 150)
    assert fp.stages() == ("detector", "pairing", "tracker")


def test_report_missing_stage_raises_keyerror() -> None:
    fp = FrameProfiler()
    with pytest.raises(KeyError, match=r"detector"):
        fp.report("detector")


def test_report_below_warmup_returns_nan_percentiles() -> None:
    fp = FrameProfiler(warmup_samples=5)
    for _ in range(3):
        fp.record_sample("detector", 1_000_000)  # 1 ms
    rep = fp.report("detector")
    assert rep.n_samples == 3
    assert rep.n_post_warmup == 0
    assert math.isnan(rep.avg_ms)
    assert math.isnan(rep.p50_ms)


def test_report_post_warmup_percentiles_on_uniform_distribution() -> None:
    """100 samples of 2 ms each -> avg/p50/p95/p99 all = 2 ms exactly."""
    fp = FrameProfiler(warmup_samples=10)
    for _ in range(110):  # 10 warmup + 100 post
        fp.record_sample("detector", 2_000_000)  # 2 ms in ns
    rep = fp.report("detector")
    assert rep.n_samples == 110
    assert rep.n_post_warmup == 100
    assert rep.avg_ms == pytest.approx(2.0, rel=1e-12)
    assert rep.p50_ms == pytest.approx(2.0, rel=1e-12)
    assert rep.p95_ms == pytest.approx(2.0, rel=1e-12)
    assert rep.p99_ms == pytest.approx(2.0, rel=1e-12)


def test_report_all_returns_one_report_per_stage() -> None:
    fp = FrameProfiler(warmup_samples=0)
    fp.record_sample("a", 1_000_000)
    fp.record_sample("b", 2_000_000)
    reports = fp.report_all()
    assert len(reports) == 2
    assert all(isinstance(r, StageReport) for r in reports)
    assert {r.stage_name for r in reports} == {"a", "b"}


def test_reset_clears_all_samples() -> None:
    fp = FrameProfiler()
    fp.record_sample("detector", 1_000_000)
    fp.reset()
    assert fp.stages() == ()


# ---------- StageTimingProbe ----------


def test_stage_timing_probe_records_one_sample_on_exit() -> None:
    fp = FrameProfiler(warmup_samples=0)
    with StageTimingProbe(profiler=fp, stage_name="detector"):
        time.sleep(0.001)
    rep = fp.report("detector")
    assert rep.n_samples == 1
    # 1 ms sleep should yield ~1 ms; let it bracket loosely.
    assert 0.0005 <= rep.avg_ms * 1e-3 <= 0.05


def test_stage_probe_records_sample_even_if_body_raises() -> None:
    """Plan/18: even worst-case (exception) durations should hit the profiler."""
    fp = FrameProfiler(warmup_samples=0)
    with pytest.raises(RuntimeError, match=r"boom"):  # noqa: SIM117
        with StageTimingProbe(profiler=fp, stage_name="tracker"):
            msg = "boom"
            raise RuntimeError(msg)
    assert "tracker" in fp.stages()
    assert fp.report("tracker").n_samples == 1
