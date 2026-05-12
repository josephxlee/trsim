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


# ---------- 5.13b — distribution variants + warmup boundary + reset ----------


def test_post_warmup_starts_exactly_after_warmup_count() -> None:
    """N warmup samples + 1 post sample -> n_post_warmup == 1 and the
    percentile statistics are derived from that single post-warmup
    sample only. Pins the warmup-boundary off-by-one behaviour.
    """
    fp = FrameProfiler(warmup_samples=10)
    for _ in range(10):
        fp.record_sample("detector", 1_000_000)  # 10 warmup samples at 1 ms
    fp.record_sample("detector", 5_000_000)  # 1 post-warmup sample at 5 ms
    rep = fp.report("detector")
    assert rep.n_samples == 11
    assert rep.n_post_warmup == 1
    # Single post-warmup sample -> every percentile equals it.
    assert rep.avg_ms == pytest.approx(5.0, rel=1e-12)
    assert rep.p50_ms == pytest.approx(5.0, rel=1e-12)
    assert rep.p95_ms == pytest.approx(5.0, rel=1e-12)
    assert rep.p99_ms == pytest.approx(5.0, rel=1e-12)


def test_exactly_warmup_count_leaves_post_warmup_empty() -> None:
    """Recording exactly ``warmup_samples`` samples leaves
    ``n_post_warmup == 0`` -> percentiles must remain NaN even though
    n_samples > 0. Off-by-one in the other direction.
    """
    fp = FrameProfiler(warmup_samples=10)
    for _ in range(10):
        fp.record_sample("detector", 1_000_000)
    rep = fp.report("detector")
    assert rep.n_samples == 10
    assert rep.n_post_warmup == 0
    assert math.isnan(rep.avg_ms)
    assert math.isnan(rep.p50_ms)
    assert math.isnan(rep.p95_ms)
    assert math.isnan(rep.p99_ms)


def test_bimodal_distribution_tail_percentile_picks_up_outlier() -> None:
    """95 fast samples (1 ms) + 5 slow outliers (100 ms): p50 must hug
    the fast mode (~1 ms) while p99 reflects the outlier tail. With
    numpy's default linear-interpolation percentile, a single outlier
    in 100 samples does not yet show up in p99 (sorted index 99 still
    lands inside the fast cluster); five outliers push the top 5% into
    the slow cluster and pin p99 at 100 ms.
    """
    fp = FrameProfiler(warmup_samples=0)
    for _ in range(95):
        fp.record_sample("detector", 1_000_000)  # 1 ms
    for _ in range(5):
        fp.record_sample("detector", 100_000_000)  # 100 ms outlier
    rep = fp.report("detector")
    assert rep.n_samples == 100
    assert rep.p50_ms == pytest.approx(1.0, rel=1e-12)
    assert rep.p99_ms == pytest.approx(100.0, rel=1e-12)
    # Average is pulled by the outlier: (95*1 + 5*100) / 100 = 5.95 ms.
    assert rep.avg_ms == pytest.approx((95.0 * 1.0 + 5.0 * 100.0) / 100.0, rel=1e-12)


def test_ramp_distribution_percentile_monotonicity() -> None:
    """Ramp 1, 2, ..., 100 ms -> percentiles must increase monotonically
    and bracket the analytic positions: p50 ~ 50.5, p95 ~ 95-96,
    p99 ~ 99 (linear-interp positions on a 100-sample CDF).
    """
    fp = FrameProfiler(warmup_samples=0)
    for ms in range(1, 101):
        fp.record_sample("detector", ms * 1_000_000)
    rep = fp.report("detector")
    assert rep.n_samples == 100
    assert rep.p50_ms < rep.p95_ms < rep.p99_ms
    assert 49.0 <= rep.p50_ms <= 52.0
    assert 94.0 <= rep.p95_ms <= 97.0
    assert 98.0 <= rep.p99_ms <= 100.0
    # Average of 1..100 = 50.5 exactly.
    assert rep.avg_ms == pytest.approx(50.5, rel=1e-12)


def test_reset_is_idempotent_and_accepts_new_samples() -> None:
    """Two consecutive reset() calls are safe, and the profiler is
    ready to receive new samples afterwards.
    """
    fp = FrameProfiler(warmup_samples=0)
    fp.record_sample("detector", 1_000_000)
    fp.reset()
    fp.reset()  # second reset must not raise
    assert fp.stages() == ()
    fp.record_sample("tracker", 2_000_000)
    assert fp.stages() == ("tracker",)
    assert fp.report("tracker").avg_ms == pytest.approx(2.0, rel=1e-12)


def test_report_all_is_alphabetical() -> None:
    """``report_all()`` ordering must match the alphabetical contract
    already enforced by ``stages()`` — downstream UIs rely on a stable
    iteration order.
    """
    fp = FrameProfiler(warmup_samples=0)
    fp.record_sample("tracker", 1_000_000)
    fp.record_sample("detector", 2_000_000)
    fp.record_sample("pairing", 3_000_000)
    names = tuple(r.stage_name for r in fp.report_all())
    assert names == ("detector", "pairing", "tracker")
