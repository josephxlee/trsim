"""Unit tests for workbench.domain.timing.reference_timing (Phase 2.12)."""

from __future__ import annotations

import pytest

from workbench.domain.timing.reference_timing import (
    FrameTimestamp,
    StageTimingProfile,
    TimingConfig,
)

# --- StageTimingProfile ------------------------------------------------


def test_stage_timing_target_only() -> None:
    p = StageTimingProfile(target_name="detector", target_latency_ms=2.5)
    assert p.target_latency_ms == 2.5
    assert p.scale_factor is None


def test_stage_timing_scale_only() -> None:
    p = StageTimingProfile(target_name="tracker", scale_factor=0.5)
    assert p.scale_factor == 0.5
    assert p.target_latency_ms is None


def test_stage_timing_both_specified_rejected() -> None:
    with pytest.raises(ValueError, match=r"exactly one"):
        StageTimingProfile(target_name="x", target_latency_ms=1.0, scale_factor=2.0)


def test_stage_timing_neither_specified_rejected() -> None:
    with pytest.raises(ValueError, match=r"exactly one"):
        StageTimingProfile(target_name="x")


def test_stage_timing_empty_name_rejected() -> None:
    with pytest.raises(ValueError, match=r"target_name"):
        StageTimingProfile(target_name="", target_latency_ms=1.0)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_stage_timing_negative_target_latency(bad: float) -> None:
    with pytest.raises(ValueError, match=r"target_latency_ms"):
        StageTimingProfile(target_name="x", target_latency_ms=bad)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_stage_timing_negative_scale(bad: float) -> None:
    with pytest.raises(ValueError, match=r"scale_factor"):
        StageTimingProfile(target_name="x", scale_factor=bad)


def test_stage_timing_unknown_unit() -> None:
    with pytest.raises(ValueError, match=r"measurement_unit"):
        StageTimingProfile(
            target_name="x",
            target_latency_ms=1.0,
            measurement_unit="garbage",  # type: ignore[arg-type]
        )


# --- TimingConfig ------------------------------------------------------


def test_timing_config_defaults() -> None:
    c = TimingConfig()
    assert c.mode == "sim_time"
    assert c.frame_unit == "auto"
    assert c.profiles == ()


def test_timing_config_with_profiles() -> None:
    p = StageTimingProfile(target_name="x", target_latency_ms=1.0)
    c = TimingConfig(mode="reference", profiles=(p,))
    assert c.profiles == (p,)


def test_timing_config_unknown_mode() -> None:
    with pytest.raises(ValueError, match=r"mode"):
        TimingConfig(mode="garbage")  # type: ignore[arg-type]


def test_timing_config_unknown_frame_unit() -> None:
    with pytest.raises(ValueError, match=r"frame_unit"):
        TimingConfig(frame_unit="garbage")  # type: ignore[arg-type]


# --- FrameTimestamp ----------------------------------------------------


def test_frame_timestamp_defaults() -> None:
    ts = FrameTimestamp(frame_id=0, sim_t_s=0.0)
    assert ts.wall_t_s == 0.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"frame_id": -1}, r"frame_id"),
        ({"sim_t_s": -0.1}, r"sim_t_s"),
        ({"wall_t_s": -0.1}, r"wall_t_s"),
    ],
)
def test_frame_timestamp_validation(kwargs: dict, match: str) -> None:
    base = {"frame_id": 0, "sim_t_s": 0.0, "wall_t_s": 0.0}
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        FrameTimestamp(**base)
