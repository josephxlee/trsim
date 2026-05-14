"""Phase 5 #18 + #19 — Reference Timing / Frame Profiler reproducibility.

plan/04 § 4.3 Phase 5 lists reproducibility as the verification target:
identical inputs across runs must produce bit-identical outputs from
:class:`PerformanceClock` and :class:`FrameProfiler`. Both modules are
designed to be pure (no internal randomness), so the proof is a
golden-replay style test: feed the same sequence to two instances and
assert their public state / report tuples are equal.
"""

from __future__ import annotations

import math

import pytest

from workbench.app.timing.frame_profiler import FrameProfiler
from workbench.app.timing.performance_clock import PerformanceClock

# ---------------------------------------------------------------------------
# PerformanceClock — pure factory state determinism
# ---------------------------------------------------------------------------


def test_performance_clock_factories_produce_identical_state() -> None:
    """Two clocks built from the same args share bit-identical state."""
    a = PerformanceClock(target_frame_budget_s=0.020)
    b = PerformanceClock(target_frame_budget_s=0.020)
    assert a.target_frame_budget_s == b.target_frame_budget_s
    assert a.target_frame_budget_s == 0.020


def test_performance_clock_from_target_latency_ms_round_trip() -> None:
    clock_a = PerformanceClock.from_target_latency_ms(40.0)
    clock_b = PerformanceClock.from_target_latency_ms(40.0)
    assert clock_a.target_frame_budget_s == clock_b.target_frame_budget_s
    # 40 ms -> 0.040 s exactly.
    assert clock_a.target_frame_budget_s == pytest.approx(0.040, abs=1e-15)


def test_performance_clock_from_frame_rate_hz_round_trip() -> None:
    clock_a = PerformanceClock.from_frame_rate_hz(25.0)
    clock_b = PerformanceClock.from_frame_rate_hz(25.0)
    assert clock_a.target_frame_budget_s == clock_b.target_frame_budget_s
    # 25 Hz -> 0.040 s exactly.
    assert clock_a.target_frame_budget_s == pytest.approx(0.040, abs=1e-15)


def test_performance_clock_factories_agree_at_40ms() -> None:
    """from_target_latency_ms(40) and from_frame_rate_hz(25) cross-validate."""
    ms = PerformanceClock.from_target_latency_ms(40.0)
    hz = PerformanceClock.from_frame_rate_hz(25.0)
    assert ms.target_frame_budget_s == pytest.approx(hz.target_frame_budget_s, abs=1e-15)


# ---------------------------------------------------------------------------
# FrameProfiler — same sample sequence → bit-identical StageReport
# ---------------------------------------------------------------------------


def _replay_samples(profiler: FrameProfiler, samples: dict[str, list[int]]) -> None:
    for stage, sequence in samples.items():
        for s in sequence:
            profiler.record_sample(stage, s)


def test_frame_profiler_same_sequence_yields_identical_report() -> None:
    """Two profilers fed the same (stage, elapsed_ns) sequence must
    produce identical StageReport tuples (avg / p50 / p95 / p99 bit-
    for-bit equal)."""
    samples = {
        "predict": [10_000, 12_000, 11_500, 9_500, 14_000] * 6,  # 30 samples
        "update": [22_000, 21_000, 23_500, 22_750, 21_250] * 6,
    }
    a = FrameProfiler(warmup_samples=10)
    b = FrameProfiler(warmup_samples=10)
    _replay_samples(a, samples)
    _replay_samples(b, samples)
    assert a.report_all() == b.report_all()


def test_frame_profiler_independent_of_call_order_across_stages() -> None:
    """Recording samples interleaved vs grouped yields the same report —
    only the per-stage order matters (which is preserved either way)."""
    interleaved = FrameProfiler(warmup_samples=2)
    grouped = FrameProfiler(warmup_samples=2)
    seq_predict = [10_000, 11_000, 12_000, 13_000, 14_000, 15_000]
    seq_update = [20_000, 21_000, 22_000, 23_000, 24_000, 25_000]
    for p, u in zip(seq_predict, seq_update, strict=True):
        interleaved.record_sample("predict", p)
        interleaved.record_sample("update", u)
    for p in seq_predict:
        grouped.record_sample("predict", p)
    for u in seq_update:
        grouped.record_sample("update", u)
    assert interleaved.report_all() == grouped.report_all()


def test_frame_profiler_reset_re_replay_produces_identical_report() -> None:
    """``reset()`` returns the profiler to a state where re-replaying
    the same samples yields the same report — proves no hidden state
    accumulates across the reset boundary."""
    samples = [1_000, 2_000, 3_000, 4_000, 5_000, 6_000, 7_000, 8_000, 9_000, 10_000]
    profiler = FrameProfiler(warmup_samples=3)
    for s in samples:
        profiler.record_sample("predict", s)
    first = profiler.report("predict")
    profiler.reset()
    for s in samples:
        profiler.record_sample("predict", s)
    second = profiler.report("predict")
    assert first == second


def test_frame_profiler_warmup_independence_invariant() -> None:
    """Reproducibility doesn't depend on the warmup setting — same
    warmup, same samples, same report. (Different warmup values give
    different reports; we don't compare across warmups here.)"""
    seq = list(range(1_000, 31_000, 1_000))  # 30 samples
    a = FrameProfiler(warmup_samples=5)
    b = FrameProfiler(warmup_samples=5)
    for s in seq:
        a.record_sample("predict", s)
        b.record_sample("predict", s)
    assert a.report("predict") == b.report("predict")


def test_frame_profiler_percentile_arithmetic_is_deterministic() -> None:
    """Hand-computed percentiles on a controlled sample set match the
    reported ones bit-for-bit. Guards against any floating drift in
    the percentile implementation."""
    profiler = FrameProfiler(warmup_samples=0)
    samples = [1_000_000, 2_000_000, 3_000_000, 4_000_000, 5_000_000]
    for s in samples:
        profiler.record_sample("x", s)
    report = profiler.report("x")
    # mean = 3.0 ms (exact).
    assert report.avg_ms == pytest.approx(3.0, abs=1e-12)
    assert report.p50_ms == pytest.approx(3.0, abs=1e-12)
    assert math.isfinite(report.p95_ms)
    assert math.isfinite(report.p99_ms)
    # p95 interpolates between index 3 (4.0) and 4 (5.0) at rank 3.8 ->
    # 4.0 * 0.2 + 5.0 * 0.8 = 4.8.
    assert report.p95_ms == pytest.approx(4.8, abs=1e-12)
    # p99 at rank 3.96 -> 4.0 * 0.04 + 5.0 * 0.96 = 4.96.
    assert report.p99_ms == pytest.approx(4.96, abs=1e-12)
