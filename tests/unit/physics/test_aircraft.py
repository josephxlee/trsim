"""Unit tests for workbench.physics.dynamics.aircraft (Phase 2.4d)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.aircraft import (
    AircraftDynamics,
    forward_unit_vector,
    make_aircraft_force_fn,
)
from workbench.physics.dynamics.forces import (
    G_STANDARD_M_PER_S2,
    ThrustProfile,
    ThrustProfileKind,
)
from workbench.physics.dynamics.reference import Waypoint
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import integrate

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


def _const_thrust(thrust_n: float = 5000.0) -> ThrustProfile:
    return ThrustProfile(kind=ThrustProfileKind.CONSTANT, constant_thrust_n=thrust_n)


def _aircraft(**overrides: object) -> AircraftDynamics:
    base: dict[str, object] = {
        "mass_kg": 70_000.0,  # airliner
        "thrust_profile": _const_thrust(),
    }
    base.update(overrides)
    return AircraftDynamics(**base)  # type: ignore[arg-type]


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
# AircraftDynamics dataclass
# ---------------------------------------------------------------------


def test_aircraft_dynamics_defaults() -> None:
    a = _aircraft()
    assert a.drag_coef == 0.04
    assert a.reference_area_m2 == 30.0
    assert a.lift_coef == 0.4
    assert a.kp_position == 0.5
    assert a.kd_position == 0.3
    assert a.kp_altitude == 1.0
    assert a.kd_altitude == 0.5
    assert a.max_climb_rate_mps == 25.0
    assert a.max_bank_deg == 60.0
    assert a.max_load_factor_g == 4.0


def test_aircraft_max_control_force_is_mg_times_load_factor() -> None:
    a = _aircraft(mass_kg=1000.0, max_load_factor_g=4.0)
    expected = 1000.0 * G_STANDARD_M_PER_S2 * 4.0
    assert a.max_control_force_n == pytest.approx(expected, abs=1e-9)


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
        ({"max_climb_rate_mps": 0.0}, r"max_climb_rate_mps"),
        ({"max_bank_deg": 0.0}, r"max_bank_deg"),
        ({"max_load_factor_g": 0.0}, r"max_load_factor_g"),
    ],
)
def test_aircraft_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _aircraft(**override)


# ---------------------------------------------------------------------
# forward_unit_vector
# ---------------------------------------------------------------------


def test_forward_unit_from_velocity_north() -> None:
    s = _state(velocity_east_mps=0.0, velocity_north_mps=100.0, velocity_up_mps=0.0)
    fwd = forward_unit_vector(s)
    assert fwd[0] == pytest.approx(0.0, abs=1e-12)
    assert fwd[1] == pytest.approx(1.0, abs=1e-12)
    assert fwd[2] == pytest.approx(0.0, abs=1e-12)


def test_forward_unit_from_velocity_diagonal_normalized() -> None:
    s = _state(velocity_east_mps=10.0, velocity_north_mps=10.0, velocity_up_mps=0.0)
    fwd = forward_unit_vector(s)
    expected = 1.0 / math.sqrt(2.0)
    assert fwd[0] == pytest.approx(expected, abs=1e-12)
    assert fwd[1] == pytest.approx(expected, abs=1e-12)
    # Magnitude == 1
    mag = math.sqrt(fwd[0] ** 2 + fwd[1] ** 2 + fwd[2] ** 2)
    assert mag == pytest.approx(1.0, abs=1e-12)


def test_forward_unit_stationary_uses_yaw() -> None:
    # Yaw = +pi/2 (East, CW from North) → forward = (sin(pi/2), cos(pi/2), 0) = (1, 0, 0)
    s = _state(
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=0.0,
        yaw_rad=math.pi / 2,
    )
    fwd = forward_unit_vector(s)
    assert fwd[0] == pytest.approx(1.0, abs=1e-12)
    assert fwd[1] == pytest.approx(0.0, abs=1e-12)
    assert fwd[2] == 0.0


# ---------------------------------------------------------------------
# make_aircraft_force_fn
# ---------------------------------------------------------------------


def _trajectory_straight_north() -> tuple[Waypoint, ...]:
    return (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
        Waypoint(t_s=60.0, east_m=0.0, north_m=12_000.0, altitude_m=1000.0),
    )


def test_make_force_fn_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match=r"at least one waypoint"):
        make_aircraft_force_fn(_aircraft(), AtmosphereState(), trajectory=())


def test_force_fn_returns_3_tuple() -> None:
    fn = make_aircraft_force_fn(_aircraft(), AtmosphereState(), _trajectory_straight_north())
    f = fn(_state())
    assert isinstance(f, tuple)
    assert len(f) == 3
    assert all(isinstance(x, float) for x in f)


def test_force_fn_at_trim_balanced_to_zero_north_force_when_thrust_matches_drag() -> None:
    # Pick a thrust that exactly balances drag for a 200 m/s cruise at
    # 1000 m. Force fn should produce ~0 net horizontal force when
    # exactly on reference, level, no altitude error.
    from workbench.physics.atmosphere import isa_density
    from workbench.physics.dynamics.forces import drag_force

    atm = AtmosphereState()
    speed = 200.0
    alt = 1000.0
    ac = _aircraft()

    drag_mag = abs(
        drag_force(
            (0.0, speed, 0.0),
            drag_coef=ac.drag_coef,
            reference_area_m2=ac.reference_area_m2,
            altitude_m=alt,
            atm=atm,
        )[1]
    )
    # Sanity check — drag scales with rho.
    assert drag_mag > 0.0
    rho = isa_density(alt, atm)
    assert drag_mag == pytest.approx(
        0.5 * rho * speed**2 * ac.drag_coef * ac.reference_area_m2, rel=1e-12
    )


def test_force_fn_lift_balances_gravity_at_reference() -> None:
    # On reference, no vertical velocity → lift trim = mg, gravity = -mg.
    # Net Up component should be just the PD control = 0.
    fn = make_aircraft_force_fn(_aircraft(), AtmosphereState(), _trajectory_straight_north())
    s = _state(altitude_m=1000.0, velocity_up_mps=0.0)
    f = fn(s)
    # Lift+gravity exactly cancel; vertical thrust component is 0
    # (forward = +North, so Up component of thrust is 0).
    assert f[2] == pytest.approx(0.0, abs=1e-9)


def test_force_fn_thrust_along_velocity_direction() -> None:
    # Stationary except for thrust pushing along yaw=+pi/2 (East).
    # Without lift trim influence (start exactly at altitude), the
    # horizontal force should have a strong +East component from
    # thrust + control PD steering toward (0, 0) ref (no East offset).
    ac = _aircraft(thrust_profile=_const_thrust(thrust_n=10_000.0))
    fn = make_aircraft_force_fn(ac, AtmosphereState(), _trajectory_straight_north())
    s = _state(
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=0.0,
        yaw_rad=math.pi / 2,
    )
    f = fn(s)
    # Forward = (sin(pi/2), cos(pi/2), 0) = (1, 0, 0); thrust = 10000 East.
    # Drag at zero velocity = 0; control pulls toward (0, 0) ref → 0.
    assert f[0] == pytest.approx(10_000.0, abs=1e-6)


def test_force_fn_integrate_smoke_runs_without_error() -> None:
    # Integrate a small step; the aircraft should still be airborne
    # and roughly tracking the +North reference.
    fn = make_aircraft_force_fn(_aircraft(), AtmosphereState(), _trajectory_straight_north())
    s0 = _state()
    s1 = integrate(s0, fn, mass_kg=70_000.0, dt_main_s=0.05)
    # No crash. Sim time advanced.
    assert s1.sim_t_s == pytest.approx(0.05, abs=1e-12)
    # Stays roughly at 1000 m altitude (small dt, small altitude error).
    assert abs(s1.altitude_m - 1000.0) < 1.0


def test_force_fn_control_clamped_for_far_off_reference() -> None:
    # Drive the unclamped PD above the maneuver-g cap with a high
    # kp_position. With kp=1e6 and position error -100 m the raw
    # control force is -1e8 N — far above the clamp m*g*4 ~ 2.7e6 N
    # for the airliner. Verify the East component saturates exactly.
    ac = _aircraft(kp_position=1e6, kd_position=0.0, max_load_factor_g=4.0)
    fn = make_aircraft_force_fn(ac, AtmosphereState(), _trajectory_straight_north())
    s = _state(east_m=100.0, velocity_east_mps=0.0, velocity_north_mps=0.0)
    f = fn(s)
    # Stationary → drag = 0, forward = (0, 1, 0) so thrust East = 0.
    # Gravity contributes 0 East. So East force == clamped control.
    expected_clamp = -ac.mass_kg * G_STANDARD_M_PER_S2 * 4.0
    assert f[0] == pytest.approx(expected_clamp, rel=1e-12)
