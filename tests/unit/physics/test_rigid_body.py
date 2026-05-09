"""Unit tests for workbench.physics.dynamics.rigid_body (Phase 2.4a)."""

from __future__ import annotations

import dataclasses
import math

import pytest

from workbench.physics.dynamics.rigid_body import (
    STATIONARY_SPEED_MPS,
    RigidBodyState,
    attitude_from_velocity,
)

# ---------------------------------------------------------------------
# Construction & defaults
# ---------------------------------------------------------------------


def _make_state(**overrides: float | tuple[float, float, float]) -> RigidBodyState:
    """Helper that builds a state with all-zero defaults plus overrides."""
    base: dict[str, float | tuple[float, float, float]] = {
        "east_m": 0.0,
        "north_m": 0.0,
        "altitude_m": 0.0,
        "velocity_east_mps": 0.0,
        "velocity_north_mps": 0.0,
        "velocity_up_mps": 0.0,
        "roll_rad": 0.0,
        "pitch_rad": 0.0,
        "yaw_rad": 0.0,
    }
    base.update(overrides)
    return RigidBodyState(**base)  # type: ignore[arg-type]


def test_state_construction_defaults() -> None:
    s = _make_state()
    assert s.angular_velocity_body_rad_s == (0.0, 0.0, 0.0)
    assert s.sim_t_s == 0.0


def test_state_construction_explicit() -> None:
    s = RigidBodyState(
        east_m=10.0,
        north_m=20.0,
        altitude_m=1000.0,
        velocity_east_mps=100.0,
        velocity_north_mps=50.0,
        velocity_up_mps=5.0,
        roll_rad=0.1,
        pitch_rad=0.05,
        yaw_rad=1.2,
        angular_velocity_body_rad_s=(0.01, -0.02, 0.03),
        sim_t_s=12.5,
    )
    assert s.east_m == 10.0
    assert s.angular_velocity_body_rad_s == (0.01, -0.02, 0.03)
    assert s.sim_t_s == 12.5


def test_state_is_frozen() -> None:
    s = _make_state()
    with pytest.raises(dataclasses.FrozenInstanceError):
        s.east_m = 1.0  # type: ignore[misc]


def test_state_uses_slots() -> None:
    s = _make_state()
    assert hasattr(type(s), "__slots__")
    # slots dataclasses have no __dict__ — that's the load-bearing
    # invariant (reduces per-instance memory for the millions of states
    # an RK4 sub-stepped sim produces).
    assert not hasattr(s, "__dict__")


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_state_rejects_short_angular_velocity() -> None:
    with pytest.raises(ValueError, match=r"angular_velocity_body_rad_s"):
        _make_state(angular_velocity_body_rad_s=(0.0, 0.0))  # type: ignore[arg-type]


def test_state_rejects_long_angular_velocity() -> None:
    with pytest.raises(ValueError, match=r"angular_velocity_body_rad_s"):
        _make_state(angular_velocity_body_rad_s=(0.0, 0.0, 0.0, 0.0))  # type: ignore[arg-type]


def test_state_rejects_negative_sim_t_s() -> None:
    with pytest.raises(ValueError, match=r"sim_t_s"):
        _make_state(sim_t_s=-0.001)


def test_state_accepts_zero_sim_t_s() -> None:
    s = _make_state(sim_t_s=0.0)
    assert s.sim_t_s == 0.0


# ---------------------------------------------------------------------
# Convenience properties
# ---------------------------------------------------------------------


def test_speed_mps_zero_velocity() -> None:
    assert _make_state().speed_mps == 0.0


def test_speed_mps_known_value() -> None:
    s = _make_state(
        velocity_east_mps=3.0,
        velocity_north_mps=4.0,
        velocity_up_mps=12.0,
    )
    # 3-4-5 right triangle in horizontal, then 5-12-13 with vertical
    assert s.speed_mps == pytest.approx(13.0, abs=1e-12)


def test_horizontal_speed_mps_ignores_vertical() -> None:
    s = _make_state(
        velocity_east_mps=3.0,
        velocity_north_mps=4.0,
        velocity_up_mps=99.0,
    )
    assert s.horizontal_speed_mps == pytest.approx(5.0, abs=1e-12)


def test_position_enu_tuple() -> None:
    s = _make_state(east_m=1.0, north_m=2.0, altitude_m=3.0)
    assert s.position_enu_m == (1.0, 2.0, 3.0)


def test_velocity_enu_tuple() -> None:
    s = _make_state(
        velocity_east_mps=1.0,
        velocity_north_mps=2.0,
        velocity_up_mps=3.0,
    )
    assert s.velocity_enu_mps == (1.0, 2.0, 3.0)


# ---------------------------------------------------------------------
# attitude_from_velocity
# ---------------------------------------------------------------------


def test_attitude_at_rest_preserves_existing_attitude() -> None:
    s = _make_state(roll_rad=0.1, pitch_rad=0.2, yaw_rad=1.5)
    roll, pitch, yaw = attitude_from_velocity(s)
    assert roll == pytest.approx(0.1, abs=1e-12)
    assert pitch == pytest.approx(0.2, abs=1e-12)
    assert yaw == pytest.approx(1.5, abs=1e-12)


def test_attitude_below_threshold_preserves_attitude() -> None:
    # Speed 0.005 m/s < STATIONARY_SPEED_MPS (0.01)
    s = _make_state(
        velocity_east_mps=0.003,
        velocity_north_mps=0.004,
        velocity_up_mps=0.0,
        yaw_rad=2.0,
    )
    assert s.speed_mps < STATIONARY_SPEED_MPS
    _, _, yaw = attitude_from_velocity(s)
    assert yaw == pytest.approx(2.0, abs=1e-12)


def test_attitude_north_velocity_yaw_zero() -> None:
    # Pure +North velocity → heading (CW from N) = 0
    s = _make_state(velocity_north_mps=100.0)
    roll, pitch, yaw = attitude_from_velocity(s)
    assert roll == 0.0
    assert pitch == pytest.approx(0.0, abs=1e-12)
    assert yaw == pytest.approx(0.0, abs=1e-12)


def test_attitude_east_velocity_yaw_pi_over_2() -> None:
    # Pure +East velocity → heading (CW from N) = +pi/2
    s = _make_state(velocity_east_mps=100.0)
    _, _, yaw = attitude_from_velocity(s)
    assert yaw == pytest.approx(math.pi / 2.0, abs=1e-12)


def test_attitude_south_velocity_yaw_pi() -> None:
    # Pure -North velocity → heading = +-pi (atan2 returns +pi for (0, -y))
    s = _make_state(velocity_north_mps=-100.0)
    _, _, yaw = attitude_from_velocity(s)
    assert abs(yaw) == pytest.approx(math.pi, abs=1e-12)


def test_attitude_north_east_45deg() -> None:
    # Equal +East and +North → heading = pi/4 (NE, CW from N)
    s = _make_state(velocity_east_mps=50.0, velocity_north_mps=50.0)
    _, _, yaw = attitude_from_velocity(s)
    assert yaw == pytest.approx(math.pi / 4.0, abs=1e-12)


def test_attitude_climbing_30deg_pitch() -> None:
    # Horizontal speed 100 m/s, vertical 100*tan(30) → pitch = 30 deg
    horizontal = 100.0
    vertical = horizontal * math.tan(math.radians(30.0))
    s = _make_state(velocity_north_mps=horizontal, velocity_up_mps=vertical)
    _, pitch, yaw = attitude_from_velocity(s)
    assert pitch == pytest.approx(math.radians(30.0), abs=1e-12)
    assert yaw == pytest.approx(0.0, abs=1e-12)


def test_attitude_pure_vertical_pitch_pi_over_2() -> None:
    # Pure +Up velocity → pitch = +pi/2 (asin(1)). Yaw is undefined but
    # the formula gives atan2(0, 0) = 0 — we just check pitch.
    s = _make_state(velocity_up_mps=100.0)
    _, pitch, _ = attitude_from_velocity(s)
    assert pitch == pytest.approx(math.pi / 2.0, abs=1e-12)


def test_attitude_diving_negative_pitch() -> None:
    s = _make_state(velocity_north_mps=100.0, velocity_up_mps=-50.0)
    _, pitch, _ = attitude_from_velocity(s)
    expected = math.asin(-50.0 / math.sqrt(100.0 * 100.0 + 50.0 * 50.0))
    assert pitch == pytest.approx(expected, abs=1e-12)
    assert pitch < 0.0


def test_attitude_roll_always_zero_at_level_1() -> None:
    s = _make_state(velocity_east_mps=10.0, velocity_north_mps=10.0, roll_rad=0.5)
    roll, _, _ = attitude_from_velocity(s)
    assert roll == 0.0


# ---------------------------------------------------------------------
# Module constant
# ---------------------------------------------------------------------


def test_stationary_threshold_value() -> None:
    # plan/14 § 14.3.2 hard-codes 0.01 m/s; lock the value so future
    # refactors must also update plan/14.
    assert STATIONARY_SPEED_MPS == 0.01
