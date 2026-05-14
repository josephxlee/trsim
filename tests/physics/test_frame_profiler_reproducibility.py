"""Phase 5 #19 — FrameProfiler reproducibility (plan/04 § 4.3).

Same sequence of (stage_name, elapsed_ns) samples must always produce
the same StageReport (avg / p50 / p95 / p99). A regression where the
profiler internally re-orders samples or rounds differently is caught
here.
"""

from __future__ import annotations

from dataclasses import asdict

import pytest

from workbench.app.timing.frame_profiler import FrameProfiler

# ---------------------------------------------------------------------
# Same-input reproducibility
# ---------------------------------------------------------------------


def test_same_sample_sequence_produces_same_report() -> None:
    rng_samples_ns = [1_000_000, 1_100_000, 1_200_000, 1_300_000, 1_400_000] * 20
    p1 = FrameProfiler(warmup_samples=0)
    p2 = FrameProfiler(warmup_samples=0)
    for s in rng_samples_ns:
        p1.record_sample("detector", s)
        p2.record_sample("detector", s)
    assert p1.report("detector") == p2.report("detector")


def test_report_all_sorted_alphabetically() -> None:
    """``report_all`` ordering must be deterministic — alphabetic."""
    profiler = FrameProfiler(warmup_samples=0)
    # Insert in a non-alphabetic order.
    for stage in ("tracker", "detector", "pairing"):
        for _ in range(10):
            profiler.record_sample(stage, 1_000_000)
    names = [r.stage_name for r in profiler.report_all()]
    assert names == sorted(names) == ["detector", "pairing", "tracker"]


def test_reset_makes_profiler_equivalent_to_fresh_instance() -> None:
    """After reset, recording the same samples gives the same report."""
    fresh = FrameProfiler(warmup_samples=0)
    used = FrameProfiler(warmup_samples=0)
    for _ in range(15):
        used.record_sample("detector", 500_000)
    used.reset()
    for v in (1_000_000, 2_000_000, 3_000_000):
        fresh.record_sample("detector", v)
        used.record_sample("detector", v)
    assert fresh.report("detector") == used.report("detector")


# ---------------------------------------------------------------------
# Percentile math invariants — values within numerical tolerance
# ---------------------------------------------------------------------


def test_constant_workload_reports_constant_metrics() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    for _ in range(50):
        profiler.record_sample("detector", 1_500_000)
    r = profiler.report("detector")
    assert r.avg_ms == pytest.approx(1.5)
    assert r.p50_ms == pytest.approx(1.5)
    assert r.p95_ms == pytest.approx(1.5)
    assert r.p99_ms == pytest.approx(1.5)


def test_linear_workload_monotone_percentiles() -> None:
    """1, 2, 3, ..., 100 ms samples — percentiles must be monotone."""
    profiler = FrameProfiler(warmup_samples=0)
    for i in range(1, 101):
        profiler.record_sample("detector", i * 1_000_000)
    r = profiler.report("detector")
    assert r.p50_ms < r.p95_ms < r.p99_ms


def test_warmup_dropped_samples_match_post_count() -> None:
    profiler = FrameProfiler(warmup_samples=10)
    for v in range(20):
        profiler.record_sample("detector", (v + 1) * 1_000_000)
    r = profiler.report("detector")
    assert r.n_samples == 20
    assert r.n_post_warmup == 10
    # Average of 11..20 ms = 15.5 ms.
    assert r.avg_ms == pytest.approx(15.5)


def test_report_round_trip_via_dataclass_asdict() -> None:
    """JSON round-trip via asdict must preserve every key/value."""
    profiler = FrameProfiler(warmup_samples=0)
    for v in (1_000_000, 2_000_000, 3_000_000, 4_000_000):
        profiler.record_sample("detector", v)
    r = profiler.report("detector")
    d = asdict(r)
    assert d["stage_name"] == "detector"
    assert d["n_samples"] == 4
    assert d["n_post_warmup"] == 4
    assert d["avg_ms"] == pytest.approx(2.5)


def test_report_all_is_idempotent() -> None:
    """Calling report_all twice returns equal results (no internal mutation)."""
    profiler = FrameProfiler(warmup_samples=0)
    for _ in range(20):
        profiler.record_sample("detector", 1_000_000)
        profiler.record_sample("tracker", 2_000_000)
    first = profiler.report_all()
    second = profiler.report_all()
    assert first == second


def test_record_order_independent_for_constant_workload() -> None:
    """For samples with identical values, recording order doesn't change percentiles."""
    samples_a = [1_000_000] * 10 + [2_000_000] * 10
    samples_b = [2_000_000] * 10 + [1_000_000] * 10
    pa = FrameProfiler(warmup_samples=0)
    pb = FrameProfiler(warmup_samples=0)
    for s in samples_a:
        pa.record_sample("detector", s)
    for s in samples_b:
        pb.record_sample("detector", s)
    # Sorted percentile math: same multiset -> same percentiles.
    assert pa.report("detector").p50_ms == pytest.approx(pb.report("detector").p50_ms)
    assert pa.report("detector").p95_ms == pytest.approx(pb.report("detector").p95_ms)
    assert pa.report("detector").avg_ms == pytest.approx(pb.report("detector").avg_ms)


# ---------------------------------------------------------------------
# Multi-stage independence
# ---------------------------------------------------------------------


def test_stages_isolated_from_each_other() -> None:
    profiler = FrameProfiler(warmup_samples=0)
    for _ in range(10):
        profiler.record_sample("detector", 1_000_000)
        profiler.record_sample("tracker", 5_000_000)
    rd = profiler.report("detector")
    rt = profiler.report("tracker")
    assert rd.avg_ms == pytest.approx(1.0)
    assert rt.avg_ms == pytest.approx(5.0)


def test_unknown_stage_raises_keyerror() -> None:
    profiler = FrameProfiler()
    with pytest.raises(KeyError, match=r"no samples recorded"):
        profiler.report("nonexistent")
