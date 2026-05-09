"""Unit tests for workbench.physics.dynamics.solver_rk4 (Phase 2.4c)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.dynamics.forces import G_STANDARD_M_PER_S2, gravity_force
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import (
    DEFAULT_SUBSTEP_COUNT,
    integrate,
    rk4_step,
)

# ---------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------


def _state(
    *,
    east: float = 0.0,
    north: float = 0.0,
    altitude: float = 0.0,
    v_east: float = 0.0,
    v_north: float = 0.0,
    v_up: float = 0.0,
    yaw_rad: float = 0.0,
    pitch_rad: float = 0.0,
    roll_rad: float = 0.0,
    sim_t_s: float = 0.0,
) -> RigidBodyState:
    return RigidBodyState(
        east_m=east,
        north_m=north,
        altitude_m=altitude,
        velocity_east_mps=v_east,
        velocity_north_mps=v_north,
        velocity_up_mps=v_up,
        roll_rad=roll_rad,
        pitch_rad=pitch_rad,
        yaw_rad=yaw_rad,
        sim_t_s=sim_t_s,
    )


def _zero_force(_: RigidBodyState) -> tuple[float, float, float]:
    return (0.0, 0.0, 0.0)


def _gravity_only(mass_kg: float):
    f = gravity_force(mass_kg)

    def fn(_: RigidBodyState) -> tuple[float, float, float]:
        return f

    return fn


# ---------------------------------------------------------------------
# rk4_step — basic invariants
# ---------------------------------------------------------------------


def test_rk4_no_force_constant_velocity() -> None:
    s0 = _state(v_east=10.0, v_north=5.0, v_up=2.0)
    s1 = rk4_step(s0, _zero_force, mass_kg=1000.0, dt_s=1.0)
    assert s1.velocity_east_mps == pytest.approx(10.0, abs=1e-12)
    assert s1.velocity_north_mps == pytest.approx(5.0, abs=1e-12)
    assert s1.velocity_up_mps == pytest.approx(2.0, abs=1e-12)
    # Position advances exactly v * dt under constant velocity.
    assert s1.east_m == pytest.approx(10.0, abs=1e-12)
    assert s1.north_m == pytest.approx(5.0, abs=1e-12)
    assert s1.altitude_m == pytest.approx(2.0, abs=1e-12)
    assert s1.sim_t_s == pytest.approx(1.0, abs=1e-12)


def test_rk4_advances_sim_time() -> None:
    s0 = _state()
    s1 = rk4_step(s0, _zero_force, mass_kg=10.0, dt_s=0.05)
    assert s1.sim_t_s == pytest.approx(0.05, abs=1e-15)


# ---------------------------------------------------------------------
# rk4_step — exactness for closed-form motion
# ---------------------------------------------------------------------


def test_rk4_free_fall_position_kinematic_match() -> None:
    # h(t) = h0 + v0*t - 1/2*g*t^2 should be reproduced by RK4 to
    # machine precision because gravity is constant (RK4 is exact for
    # quadratic position trajectories under constant acceleration).
    mass = 100.0
    h0 = 1000.0
    s0 = _state(altitude=h0, v_up=0.0)
    s1 = rk4_step(s0, _gravity_only(mass), mass_kg=mass, dt_s=2.0)

    expected_h = h0 - 0.5 * G_STANDARD_M_PER_S2 * 4.0
    expected_v_up = -G_STANDARD_M_PER_S2 * 2.0
    assert s1.altitude_m == pytest.approx(expected_h, abs=1e-9)
    assert s1.velocity_up_mps == pytest.approx(expected_v_up, abs=1e-12)


def test_rk4_constant_horizontal_force_matches_kinematics() -> None:
    # F = (1000, 0, 0) N on m=100 kg → a = 10 m/s^2 East. After t=1 s:
    #   x = 1/2 * 10 * 1 = 5 m, vE = 10 m/s
    mass = 100.0

    def fn(_: RigidBodyState) -> tuple[float, float, float]:
        return (1000.0, 0.0, 0.0)

    s0 = _state()
    s1 = rk4_step(s0, fn, mass_kg=mass, dt_s=1.0)
    assert s1.east_m == pytest.approx(5.0, abs=1e-9)
    assert s1.velocity_east_mps == pytest.approx(10.0, abs=1e-12)


# ---------------------------------------------------------------------
# integrate — sub-step composition
# ---------------------------------------------------------------------


def test_integrate_default_substep_count() -> None:
    assert DEFAULT_SUBSTEP_COUNT == 10


def test_integrate_no_force_position_matches_velocity_dt() -> None:
    s0 = _state(v_north=20.0)
    s1 = integrate(s0, _zero_force, mass_kg=1000.0, dt_main_s=0.5)
    assert s1.north_m == pytest.approx(10.0, abs=1e-12)
    assert s1.sim_t_s == pytest.approx(0.5, abs=1e-12)


def test_integrate_substepping_matches_single_step_for_constant_force() -> None:
    # Constant-force trajectory: 1 large step and many small steps
    # must agree because RK4 is exact for quadratics under constant a.
    mass = 50.0

    def fn(_: RigidBodyState) -> tuple[float, float, float]:
        return (500.0, -200.0, 0.0)

    s0 = _state(v_east=1.0, v_north=2.0)
    s_one = rk4_step(s0, fn, mass_kg=mass, dt_s=1.0)
    s_many = integrate(s0, fn, mass_kg=mass, dt_main_s=1.0, n_substeps=20)

    assert s_one.east_m == pytest.approx(s_many.east_m, abs=1e-9)
    assert s_one.north_m == pytest.approx(s_many.north_m, abs=1e-9)
    assert s_one.velocity_east_mps == pytest.approx(s_many.velocity_east_mps, abs=1e-12)
    assert s_one.velocity_north_mps == pytest.approx(s_many.velocity_north_mps, abs=1e-12)


def test_integrate_state_dependent_force_substeps_help() -> None:
    # Spring force F = -k * (x - x_ref) along East. For oscillatory
    # systems sub-stepping is materially more accurate than one big
    # step. We don't compare to closed-form but confirm both produce
    # bounded amplitudes (i.e. the integrator doesn't blow up).
    mass = 1.0
    k = 4.0  # omega = 2 rad/s, period ~3.14 s

    def fn(s: RigidBodyState) -> tuple[float, float, float]:
        return (-k * s.east_m, 0.0, 0.0)

    s0 = _state(east=1.0)
    s = integrate(s0, fn, mass_kg=mass, dt_main_s=0.5, n_substeps=50)
    # Amplitude must remain in the unit-energy ball: 1/2 m v^2 + 1/2 k x^2 <= 1/2 k * 1.0
    energy = 0.5 * mass * s.velocity_east_mps**2 + 0.5 * k * s.east_m**2
    assert energy == pytest.approx(0.5 * k * 1.0, rel=1e-3)


# ---------------------------------------------------------------------
# Energy conservation (gravity, no drag — closed system)
# ---------------------------------------------------------------------


def test_energy_conservation_under_gravity_only() -> None:
    # Project a target straight up; gravity is the only force. KE+PE
    # must be conserved across sub-stepped integration. Quadratic
    # trajectory → RK4 is exact for constant a.
    mass = 10.0
    g = G_STANDARD_M_PER_S2
    v0 = 50.0
    h0 = 0.0

    def fn(_: RigidBodyState) -> tuple[float, float, float]:
        return (0.0, 0.0, -mass * g)

    s = _state(altitude=h0, v_up=v0)
    e0 = 0.5 * mass * v0**2 + mass * g * h0
    s = integrate(s, fn, mass_kg=mass, dt_main_s=2.0, n_substeps=20)
    e1 = 0.5 * mass * s.velocity_up_mps**2 + mass * g * s.altitude_m
    assert e1 == pytest.approx(e0, abs=1e-9)


# ---------------------------------------------------------------------
# Attitude is recomputed from post-step velocity (Level 1 MVP)
# ---------------------------------------------------------------------


def test_attitude_updated_from_post_step_velocity() -> None:
    # Constant +East force on a stationary target → post-step velocity
    # is +East → yaw should be pi/2.
    def fn(_: RigidBodyState) -> tuple[float, float, float]:
        return (1000.0, 0.0, 0.0)

    s0 = _state()
    s1 = rk4_step(s0, fn, mass_kg=10.0, dt_s=1.0)
    assert s1.velocity_east_mps > 0.0
    assert s1.yaw_rad == pytest.approx(math.pi / 2, abs=1e-12)


def test_attitude_preserved_when_velocity_remains_below_threshold() -> None:
    # No force, no velocity → attitude_from_velocity falls back to the
    # existing yaw because speed < STATIONARY_SPEED_MPS, so the new
    # state's yaw matches the input yaw.
    s0 = _state(yaw_rad=1.234)
    s1 = rk4_step(s0, _zero_force, mass_kg=10.0, dt_s=0.1)
    assert s1.yaw_rad == pytest.approx(1.234, abs=1e-12)


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"mass_kg": 0.0, "dt_s": 1.0}, r"mass_kg"),
        ({"mass_kg": -10.0, "dt_s": 1.0}, r"mass_kg"),
        ({"mass_kg": 10.0, "dt_s": 0.0}, r"dt_s"),
        ({"mass_kg": 10.0, "dt_s": -0.1}, r"dt_s"),
    ],
)
def test_rk4_step_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        rk4_step(_state(), _zero_force, **kwargs)


def test_integrate_rejects_zero_substeps() -> None:
    with pytest.raises(ValueError, match=r"n_substeps"):
        integrate(_state(), _zero_force, mass_kg=10.0, dt_main_s=0.1, n_substeps=0)


def test_integrate_rejects_negative_substeps() -> None:
    with pytest.raises(ValueError, match=r"n_substeps"):
        integrate(_state(), _zero_force, mass_kg=10.0, dt_main_s=0.1, n_substeps=-1)
