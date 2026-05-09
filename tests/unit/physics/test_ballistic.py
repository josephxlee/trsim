"""Unit tests for workbench.physics.dynamics.ballistic (Phase 2.4e)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.ballistic import BallisticDynamics, make_ballistic_force_fn
from workbench.physics.dynamics.forces import G_STANDARD_M_PER_S2
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import integrate

# ---------------------------------------------------------------------
# BallisticDynamics dataclass
# ---------------------------------------------------------------------


def test_ballistic_defaults() -> None:
    b = BallisticDynamics(mass_kg=40.0)
    assert b.drag_coef == 0.4
    assert b.reference_area_m2 == 0.05
    assert b.initial_velocity_mps == (0.0, 0.0, 0.0)
    assert b.spin_rate_rps == 0.0


def test_ballistic_custom_initial_velocity() -> None:
    b = BallisticDynamics(mass_kg=40.0, initial_velocity_mps=(0.0, 800.0, 0.0))
    assert b.initial_velocity_mps == (0.0, 800.0, 0.0)


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"mass_kg": 0.0}, r"mass_kg"),
        ({"mass_kg": -1.0}, r"mass_kg"),
        ({"drag_coef": -0.1}, r"drag_coef"),
        ({"reference_area_m2": 0.0}, r"reference_area_m2"),
        ({"reference_area_m2": -0.5}, r"reference_area_m2"),
        ({"initial_velocity_mps": (0.0, 0.0)}, r"initial_velocity_mps"),
    ],
)
def test_ballistic_validation(override: dict, match: str) -> None:
    base: dict = {"mass_kg": 40.0}
    base.update(override)
    with pytest.raises(ValueError, match=match):
        BallisticDynamics(**base)


# ---------------------------------------------------------------------
# Force composition (gravity + drag only)
# ---------------------------------------------------------------------


def _state(**overrides: float) -> RigidBodyState:
    base: dict[str, float] = {
        "east_m": 0.0,
        "north_m": 0.0,
        "altitude_m": 0.0,
        "velocity_east_mps": 0.0,
        "velocity_north_mps": 0.0,
        "velocity_up_mps": 0.0,
        "roll_rad": 0.0,
        "pitch_rad": 0.0,
        "yaw_rad": 0.0,
        "sim_t_s": 0.0,
    }
    base.update(overrides)
    return RigidBodyState(**base)  # type: ignore[arg-type]


def test_force_fn_no_thrust_no_lift_no_control() -> None:
    # Stationary at sea level → drag = 0 → only gravity remains.
    b = BallisticDynamics(mass_kg=100.0)
    fn = make_ballistic_force_fn(b, AtmosphereState())
    f = fn(_state())
    assert f[0] == 0.0
    assert f[1] == 0.0
    assert f[2] == pytest.approx(-100.0 * G_STANDARD_M_PER_S2, abs=1e-9)


def test_force_fn_drag_opposes_velocity() -> None:
    b = BallisticDynamics(mass_kg=100.0)
    fn = make_ballistic_force_fn(b, AtmosphereState())
    # Moving fast East → drag pulls West.
    f = fn(_state(velocity_east_mps=500.0))
    assert f[0] < 0.0


# ---------------------------------------------------------------------
# Energy conservation when drag = 0 (vacuum ballistics)
# ---------------------------------------------------------------------


def test_vacuum_ballistic_energy_conserved() -> None:
    # Cd = 0 → only gravity. Vertical-launch projectile reaches a peak
    # then falls; KE + PE must be conserved across integration.
    mass = 10.0
    b = BallisticDynamics(mass_kg=mass, drag_coef=0.0)
    fn = make_ballistic_force_fn(b, AtmosphereState())

    s = _state(velocity_up_mps=100.0)
    e0 = 0.5 * mass * 100.0**2
    s = integrate(s, fn, mass_kg=mass, dt_main_s=2.0, n_substeps=20)
    e1 = 0.5 * mass * s.velocity_up_mps**2 + mass * G_STANDARD_M_PER_S2 * s.altitude_m
    assert e1 == pytest.approx(e0, abs=1e-9)


def test_vacuum_ballistic_45deg_horizontal_range() -> None:
    # Closed-form 45-deg projectile: range = v0^2 * sin(2*45) / g = v0^2 / g
    mass = 10.0
    v0 = 100.0
    angle = math.radians(45.0)
    v_north = v0 * math.cos(angle)
    v_up = v0 * math.sin(angle)
    b = BallisticDynamics(mass_kg=mass, drag_coef=0.0)
    fn = make_ballistic_force_fn(b, AtmosphereState())

    s = _state(velocity_north_mps=v_north, velocity_up_mps=v_up)
    # Time of flight = 2*v0*sin(theta)/g
    t_flight = 2.0 * v_up / G_STANDARD_M_PER_S2
    s = integrate(s, fn, mass_kg=mass, dt_main_s=t_flight, n_substeps=200)
    # Closed-form range
    expected_range = v0 * v0 * math.sin(2.0 * angle) / G_STANDARD_M_PER_S2
    assert s.north_m == pytest.approx(expected_range, abs=1e-6)
    # Should be back at altitude 0.
    assert s.altitude_m == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------
# With drag: trajectory shorter than vacuum
# ---------------------------------------------------------------------


def test_drag_shortens_ballistic_range() -> None:
    mass = 10.0
    v0 = 100.0
    angle = math.radians(45.0)
    v_north = v0 * math.cos(angle)
    v_up = v0 * math.sin(angle)
    fn_drag = make_ballistic_force_fn(
        BallisticDynamics(mass_kg=mass, drag_coef=0.4, reference_area_m2=0.05),
        AtmosphereState(),
    )
    fn_vacuum = make_ballistic_force_fn(
        BallisticDynamics(mass_kg=mass, drag_coef=0.0),
        AtmosphereState(),
    )

    t = 2.0 * v_up / G_STANDARD_M_PER_S2
    s0 = _state(velocity_north_mps=v_north, velocity_up_mps=v_up)
    s_drag = integrate(s0, fn_drag, mass_kg=mass, dt_main_s=t, n_substeps=100)
    s_vacuum = integrate(s0, fn_vacuum, mass_kg=mass, dt_main_s=t, n_substeps=100)
    # Drag must reduce horizontal range.
    assert s_drag.north_m < s_vacuum.north_m
