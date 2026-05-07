"""Unit tests for :mod:`workbench.domain.types`."""

from __future__ import annotations

import pytest

from workbench.domain.types import (
    CommandSource,
    PositionENU,
    PositionerCommand,
    RunState,
    RunTerminationReason,
    SimulationState,
    SpeedMultiplier,
    Time,
    VelocityENU,
)


def test_position_enu_creation(sample_position: PositionENU) -> None:
    """PositionENU stores (x, y, z) coordinates as floats."""
    assert sample_position.x == 100.0
    assert sample_position.y == 200.0
    assert sample_position.z == 10.0


def test_position_enu_immutable() -> None:
    """PositionENU is frozen — cannot mutate after creation."""
    p = PositionENU(x=0.0, y=0.0, z=0.0)
    with pytest.raises((AttributeError, TypeError)):
        p.x = 100.0  # type: ignore[misc]


def test_velocity_enu_speed() -> None:
    """VelocityENU.speed is the L2 norm of (vx, vy, vz)."""
    v = VelocityENU(vx=3.0, vy=4.0, vz=0.0)
    assert v.speed == pytest.approx(5.0)


def test_velocity_enu_speed_zero() -> None:
    """Zero velocity has zero speed."""
    v = VelocityENU(vx=0.0, vy=0.0, vz=0.0)
    assert v.speed == 0.0


def test_time_advance() -> None:
    """Time.advance returns a new Time with seconds + dt (immutable)."""
    t = Time(seconds=10.0)
    t2 = t.advance(0.5)
    assert t.seconds == 10.0  # original unchanged
    assert t2.seconds == pytest.approx(10.5)


# ---------------------------------------------------------------------------
# CommandSource enum
# ---------------------------------------------------------------------------


def test_command_source_members() -> None:
    """Three members exactly per plan/03 § 3.5.1c."""
    assert {m.name for m in CommandSource} == {"TRACKER", "MANUAL_USER", "INITIAL_SCAN"}


def test_command_source_values() -> None:
    """String values are stable lowercase identifiers."""
    assert CommandSource.TRACKER.value == "tracker"
    assert CommandSource.MANUAL_USER.value == "manual_user"
    assert CommandSource.INITIAL_SCAN.value == "initial_scan"


# ---------------------------------------------------------------------------
# PositionerCommand
# ---------------------------------------------------------------------------


def test_positioner_command_initial_scan() -> None:
    """INITIAL_SCAN does not require lineage IDs."""
    cmd = PositionerCommand(
        az_rad=0.0,
        el_rad=0.0,
        source=CommandSource.INITIAL_SCAN,
        timestamp_s=0.0,
    )
    assert cmd.source is CommandSource.INITIAL_SCAN
    assert cmd.source_track_id is None
    assert cmd.source_frame_id is None


def test_positioner_command_manual_user() -> None:
    """MANUAL_USER does not require lineage IDs."""
    cmd = PositionerCommand(
        az_rad=1.5,
        el_rad=0.1,
        source=CommandSource.MANUAL_USER,
        timestamp_s=12.5,
    )
    assert cmd.source is CommandSource.MANUAL_USER


def test_positioner_command_tracker_with_lineage() -> None:
    """TRACKER source with both lineage IDs is valid."""
    cmd = PositionerCommand(
        az_rad=0.5,
        el_rad=0.2,
        source=CommandSource.TRACKER,
        timestamp_s=3.5,
        source_track_id=42,
        source_frame_id=137,
    )
    assert cmd.source_track_id == 42
    assert cmd.source_frame_id == 137


def test_positioner_command_tracker_missing_track_id_raises() -> None:
    """TRACKER source without source_track_id raises ValueError."""
    with pytest.raises(ValueError, match="GT Lineage"):
        PositionerCommand(
            az_rad=0.0,
            el_rad=0.0,
            source=CommandSource.TRACKER,
            timestamp_s=0.0,
            source_track_id=None,
            source_frame_id=1,
        )


def test_positioner_command_tracker_missing_frame_id_raises() -> None:
    """TRACKER source without source_frame_id raises ValueError."""
    with pytest.raises(ValueError, match="GT Lineage"):
        PositionerCommand(
            az_rad=0.0,
            el_rad=0.0,
            source=CommandSource.TRACKER,
            timestamp_s=0.0,
            source_track_id=1,
            source_frame_id=None,
        )


def test_positioner_command_immutable() -> None:
    """frozen=True forbids mutation."""
    cmd = PositionerCommand(
        az_rad=0.0,
        el_rad=0.0,
        source=CommandSource.MANUAL_USER,
        timestamp_s=0.0,
    )
    with pytest.raises((AttributeError, TypeError)):
        cmd.az_rad = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RunState / RunTerminationReason
# ---------------------------------------------------------------------------


def test_run_state_members() -> None:
    """Four members per v0.14."""
    assert {m.name for m in RunState} == {"IDLE", "RUNNING", "PAUSED", "ENDED"}


def test_run_state_values() -> None:
    """String values are stable lowercase identifiers."""
    assert RunState.IDLE.value == "idle"
    assert RunState.RUNNING.value == "running"
    assert RunState.PAUSED.value == "paused"
    assert RunState.ENDED.value == "ended"


def test_run_termination_reason_members() -> None:
    """Four reasons per v0.14."""
    assert {m.name for m in RunTerminationReason} == {
        "COMPLETED",
        "USER_STOPPED",
        "SIM_STOPPED",
        "ERROR",
    }


# ---------------------------------------------------------------------------
# SimulationState / SpeedMultiplier
# ---------------------------------------------------------------------------


def test_simulation_state_members() -> None:
    """Three members per v0.15."""
    assert {m.name for m in SimulationState} == {"STOPPED", "RUNNING", "PAUSED"}


def test_simulation_state_distinct_from_run_state() -> None:
    """SimulationState and RunState are distinct enums (not interchangeable)."""
    # Even if they share a member name, the enums are separate types.
    assert SimulationState.RUNNING is not RunState.RUNNING


def test_speed_multiplier_int_values() -> None:
    """Powers-of-two from 1 to 8."""
    assert SpeedMultiplier.X1 == 1
    assert SpeedMultiplier.X2 == 2
    assert SpeedMultiplier.X4 == 4
    assert SpeedMultiplier.X8 == 8


def test_speed_multiplier_arithmetic() -> None:
    """IntEnum supports int arithmetic."""
    assert SpeedMultiplier.X4 * 2 == 8
    assert int(SpeedMultiplier.X8) == 8
