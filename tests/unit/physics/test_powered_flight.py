"""Unit tests for workbench.physics.dynamics.powered_flight (Phase 2.4e)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.forces import (
    G_STANDARD_M_PER_S2,
    ThrustProfile,
    ThrustProfileKind,
)
from workbench.physics.dynamics.powered_flight import (
    PoweredFlightDynamics,
    make_powered_flight_force_fn,
)
from workbench.physics.dynamics.reference import Waypoint
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import integrate

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _const_thrust(thrust_n: float) -> ThrustProfile:
    return ThrustProfile(kind=ThrustProfileKind.CONSTANT, constant_thrust_n=thrust_n)


def _missile(**overrides: object) -> PoweredFlightDynamics:
    base: dict[str, object] = {
        "mass_kg": 1000.0,
        "thrust_profile": _const_thrust(20_000.0),
    }
    base.update(overrides)
    return PoweredFlightDynamics(**base)  # type: ignore[arg-type]


def _trajectory() -> tuple[Waypoint, ...]:
    return (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
        Waypoint(t_s=30.0, east_m=0.0, north_m=15_000.0, altitude_m=1000.0),
    )


def _state(**overrides: float) -> RigidBodyState:
    base: dict[str, float] = {
        "east_m": 0.0,
        "north_m": 0.0,
        "altitude_m": 1000.0,
        "velocity_east_mps": 0.0,
        "velocity_north_mps": 200.0,
        "velocity_up_mps": 0.0,
        "roll_rad": 0.0,
        "pitch_rad": 0.0,
        "yaw_rad": 0.0,
        "sim_t_s": 0.0,
    }
    base.update(overrides)
    return RigidBodyState(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# PoweredFlightDynamics dataclass
# ---------------------------------------------------------------------


def test_powered_flight_defaults() -> None:
    p = _missile()
    assert p.drag_coef == 0.3
    assert p.reference_area_m2 == 0.1
    assert p.lift_coef == 0.0
    assert p.kp_position == 5.0
    assert p.kd_position == 2.0
    assert p.kp_altitude == 5.0
    assert p.kd_altitude == 2.0
    assert p.max_load_factor_g == 20.0
    assert p.use_trajectory_as_reference is True


def test_max_control_force_uses_high_load_factor() -> None:
    p = _missile(mass_kg=500.0, max_load_factor_g=20.0)
    expected = 500.0 * G_STANDARD_M_PER_S2 * 20.0
    assert p.max_control_force_n == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"mass_kg": 0.0}, r"mass_kg"),
        ({"mass_kg": -1.0}, r"mass_kg"),
        ({"drag_coef": -0.1}, r"drag_coef"),
        ({"reference_area_m2": 0.0}, r"reference_area_m2"),
        ({"lift_coef": -0.1}, r"lift_coef"),
        ({"kp_position": -1.0}, r"kp_position"),
        ({"kd_position": -1.0}, r"kd_position"),
        ({"kp_altitude": -1.0}, r"kp_altitude"),
        ({"kd_altitude": -1.0}, r"kd_altitude"),
        ({"max_load_factor_g": 0.0}, r"max_load_factor_g"),
    ],
)
def test_powered_flight_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _missile(**override)


# ---------------------------------------------------------------------
# make_powered_flight_force_fn
# ---------------------------------------------------------------------


def test_force_fn_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match=r"at least one waypoint"):
        make_powered_flight_force_fn(_missile(), AtmosphereState(), trajectory=())


def test_force_fn_returns_3_tuple() -> None:
    fn = make_powered_flight_force_fn(_missile(), AtmosphereState(), _trajectory())
    f = fn(_state())
    assert isinstance(f, tuple)
    assert len(f) == 3


def test_force_fn_thrust_along_velocity() -> None:
    # Stationary, yaw = pi/2 (East). Thrust 20kN should produce
    # +East force from the thrust component (forward = (1, 0, 0)).
    fn = make_powered_flight_force_fn(_missile(), AtmosphereState(), _trajectory())
    s = _state(
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=0.0,
        yaw_rad=math.pi / 2,
    )
    # From a (0,0,1000) start the trajectory ref at t=0 is (0,0,1000) too,
    # so position error is zero — control PD East = 0. Thrust dominates.
    f = fn(s)
    assert f[0] == pytest.approx(20_000.0, abs=1e-6)


def test_force_fn_no_control_when_disabled() -> None:
    # use_trajectory_as_reference=False → control_force is zero even
    # when the target is far off the reference.
    p = _missile(use_trajectory_as_reference=False)
    fn = make_powered_flight_force_fn(p, AtmosphereState(), _trajectory())
    s_far = _state(east_m=10_000.0, velocity_east_mps=0.0, velocity_north_mps=0.0)
    s_near = _state(east_m=0.0, velocity_east_mps=0.0, velocity_north_mps=0.0)
    # East force should be the same in both cases (no control_force
    # contribution) — only thrust + gravity + drag, all of which are
    # identical because position doesn't enter them.
    f_far = fn(s_far)
    f_near = fn(s_near)
    assert f_far[0] == pytest.approx(f_near[0], abs=1e-9)


def test_force_fn_with_control_pulls_far_target_back() -> None:
    # use_trajectory_as_reference=True with a large East offset →
    # control force pulls West (negative East).
    p = _missile(
        kp_position=1e5,
        kd_position=0.0,
        max_load_factor_g=50.0,
        use_trajectory_as_reference=True,
    )
    fn = make_powered_flight_force_fn(p, AtmosphereState(), _trajectory())
    s = _state(east_m=1000.0, velocity_east_mps=0.0, velocity_north_mps=0.0)
    f = fn(s)
    # Stationary → thrust is along yaw=0 (North) → east contribution = 0.
    # Drag = 0 (speed below threshold). Gravity has no east component.
    # So east force == clamped control force.
    expected = -p.mass_kg * G_STANDARD_M_PER_S2 * 50.0  # negative East
    assert f[0] == pytest.approx(expected, abs=1e-6)


def test_force_fn_integrate_smoke() -> None:
    fn = make_powered_flight_force_fn(_missile(), AtmosphereState(), _trajectory())
    s0 = _state()
    s1 = integrate(s0, fn, mass_kg=1000.0, dt_main_s=0.05)
    assert s1.sim_t_s == pytest.approx(0.05, abs=1e-12)
    # At launch, lift trim balances gravity and altitude error is
    # zero, so the missile stays close to 1000 m.
    assert abs(s1.altitude_m - 1000.0) < 1.0
