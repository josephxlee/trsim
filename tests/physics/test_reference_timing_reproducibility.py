"""Phase 5 #18 — Reference Timing reproducibility (plan/04 § 4.3).

The Reference Timing data model (plan/03 § 3.2.1n) is a pure value
record: same inputs must yield bit-identical dataclasses. Phase 5 #18
exists so a regression that, say, silently mutates a `TimingConfig`
or rounds a `FrameTimestamp` is caught immediately.
"""

from __future__ import annotations

import pytest

from workbench.domain.timing.reference_timing import (
    FrameTimestamp,
    StageTimingProfile,
    TimingConfig,
)

# ---------------------------------------------------------------------
# StageTimingProfile — frozen dataclass invariants
# ---------------------------------------------------------------------


def test_stage_profile_with_latency_round_trip() -> None:
    a = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    b = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    assert a == b
    assert hash(a) == hash(b)


def test_stage_profile_with_scale_round_trip() -> None:
    a = StageTimingProfile(target_name="tracker", scale_factor=0.5)
    b = StageTimingProfile(target_name="tracker", scale_factor=0.5)
    assert a == b


def test_stage_profile_distinguishes_by_target_name() -> None:
    a = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    b = StageTimingProfile(target_name="tracker", target_latency_ms=2.5)
    assert a != b


def test_stage_profile_distinguishes_by_measurement_unit() -> None:
    a = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    b = StageTimingProfile(
        target_name="detector", target_latency_ms=2.5, measurement_unit="pipeline"
    )
    assert a != b


def test_stage_profile_is_frozen() -> None:
    p = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    with pytest.raises(AttributeError):
        p.target_latency_ms = 5.0  # type: ignore[misc]


# ---------------------------------------------------------------------
# TimingConfig — same inputs → same output, mode ordering
# ---------------------------------------------------------------------


def test_timing_config_default_is_sim_time_mode() -> None:
    a = TimingConfig()
    b = TimingConfig()
    assert a == b
    assert a.mode == "sim_time"
    assert a.frame_unit == "auto"
    assert a.profiles == ()


def test_timing_config_with_profiles_preserves_order() -> None:
    profiles = (
        StageTimingProfile(target_name="detector", target_latency_ms=2.5),
        StageTimingProfile(target_name="tracker", target_latency_ms=5.0),
        StageTimingProfile(target_name="pairing", scale_factor=1.0),
    )
    a = TimingConfig(mode="reference", profiles=profiles)
    b = TimingConfig(mode="reference", profiles=profiles)
    assert a == b
    # Tuple semantics — ordering is part of identity.
    assert a.profiles[0].target_name == "detector"
    assert a.profiles[-1].target_name == "pairing"


def test_timing_config_distinct_when_profile_order_swapped() -> None:
    p1 = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    p2 = StageTimingProfile(target_name="tracker", target_latency_ms=5.0)
    a = TimingConfig(mode="reference", profiles=(p1, p2))
    b = TimingConfig(mode="reference", profiles=(p2, p1))
    assert a != b


# ---------------------------------------------------------------------
# FrameTimestamp — bit-identical for identical inputs
# ---------------------------------------------------------------------


def test_frame_timestamp_round_trip_zero() -> None:
    a = FrameTimestamp(frame_id=0, sim_t_s=0.0)
    b = FrameTimestamp(frame_id=0, sim_t_s=0.0)
    assert a == b
    assert hash(a) == hash(b)


def test_frame_timestamp_sequence_reproducible() -> None:
    """Replay the same frame_id+sim_t_s sequence twice — values match."""
    inputs = [(i, i * 0.020) for i in range(20)]
    seq_a = tuple(FrameTimestamp(frame_id=i, sim_t_s=t) for i, t in inputs)
    seq_b = tuple(FrameTimestamp(frame_id=i, sim_t_s=t) for i, t in inputs)
    assert seq_a == seq_b


def test_frame_timestamp_distinct_when_frame_id_differs() -> None:
    a = FrameTimestamp(frame_id=1, sim_t_s=0.020)
    b = FrameTimestamp(frame_id=2, sim_t_s=0.020)
    assert a != b


def test_frame_timestamp_is_frozen() -> None:
    fs = FrameTimestamp(frame_id=0, sim_t_s=0.0)
    with pytest.raises(AttributeError):
        fs.frame_id = 1  # type: ignore[misc]
