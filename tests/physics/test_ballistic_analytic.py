"""Ballistic analytic vs RK4 regression (Phase 5.8).

Plan/14 § 14.5.3: a ballistic projectile with drag_coef=0 falls under
gravity alone, so ``z(t) = z0 + v_up0 * t - 0.5 * g * t^2``. RK4
on a constant acceleration field is *exact* up to floating-point
round-off, so the comparison can run at rtol=1e-12.
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.ballistic import (
    BallisticDynamics,
    make_ballistic_force_fn,
)
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import integrate

_G = 9.80665


def _initial_state(z0: float = 1000.0, v_up0: float = 0.0) -> RigidBodyState:
    return RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=z0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=v_up0,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )


def _vacuum_dynamics() -> BallisticDynamics:
    # drag_coef = 0 -> drag_force always returns (0,0,0) regardless of atm.
    return BallisticDynamics(mass_kg=10.0, drag_coef=0.0, reference_area_m2=0.05)


def _step_for(dt: float, n_substeps: int = 100) -> RigidBodyState:
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    force_fn = make_ballistic_force_fn(dyn, atm)
    return integrate(
        _initial_state(),
        force_fn,
        mass_kg=dyn.mass_kg,
        dt_main_s=dt,
        n_substeps=n_substeps,
    )


def test_vacuum_freefall_position_matches_analytic_at_1s() -> None:
    end = _step_for(1.0)
    expected_z = 1000.0 - 0.5 * _G * 1.0 * 1.0
    assert end.altitude_m == pytest.approx(expected_z, rel=1e-12)


def test_vacuum_freefall_velocity_matches_analytic_at_1s() -> None:
    end = _step_for(1.0)
    assert end.velocity_up_mps == pytest.approx(-_G * 1.0, rel=1e-12)


def test_vacuum_freefall_position_matches_analytic_at_2s() -> None:
    end = _step_for(2.0)
    expected_z = 1000.0 - 0.5 * _G * 4.0
    assert end.altitude_m == pytest.approx(expected_z, rel=1e-12)


def test_horizontal_components_stay_zero_in_pure_vertical_fall() -> None:
    end = _step_for(1.5)
    assert end.east_m == 0.0
    assert end.north_m == 0.0
    assert end.velocity_east_mps == 0.0
    assert end.velocity_north_mps == 0.0


def test_sim_time_increments_by_dt_main() -> None:
    end = _step_for(0.5)
    assert end.sim_t_s == pytest.approx(0.5, rel=1e-12)


def test_upward_throw_then_fall_returns_to_initial_height() -> None:
    """Apex at v_up0/g; round trip 2*v_up0/g restores z0."""
    v_up0 = 50.0
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    force_fn = make_ballistic_force_fn(dyn, atm)
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=1000.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=v_up0,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    round_trip_s = 2.0 * v_up0 / _G
    end = integrate(state, force_fn, mass_kg=dyn.mass_kg, dt_main_s=round_trip_s, n_substeps=200)
    assert end.altitude_m == pytest.approx(1000.0, abs=1e-9)
    assert end.velocity_up_mps == pytest.approx(-v_up0, abs=1e-9)


def test_apex_velocity_is_zero_at_half_round_trip() -> None:
    v_up0 = 30.0
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    force_fn = make_ballistic_force_fn(dyn, atm)
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=0.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=v_up0,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    apex_t = v_up0 / _G
    end = integrate(state, force_fn, mass_kg=dyn.mass_kg, dt_main_s=apex_t, n_substeps=200)
    assert end.velocity_up_mps == pytest.approx(0.0, abs=1e-9)
    # Apex height: v_up0^2 / (2g)
    assert end.altitude_m == pytest.approx(v_up0 * v_up0 / (2.0 * _G), abs=1e-9)


def test_drag_zero_means_atmosphere_choice_is_irrelevant() -> None:
    """Same vacuum result whether ISA standard or thin-air atmosphere."""
    dyn = _vacuum_dynamics()
    atm_a = AtmosphereState()  # sea level
    atm_b = AtmosphereState(sea_level_pressure_hpa=500.0)  # half pressure
    f_a = make_ballistic_force_fn(dyn, atm_a)
    f_b = make_ballistic_force_fn(dyn, atm_b)
    end_a = integrate(_initial_state(), f_a, dyn.mass_kg, 1.0, n_substeps=50)
    end_b = integrate(_initial_state(), f_b, dyn.mass_kg, 1.0, n_substeps=50)
    assert end_a.altitude_m == pytest.approx(end_b.altitude_m, rel=1e-12)


def test_with_drag_falls_slower_than_vacuum_when_speed_significant() -> None:
    """Drag must increase travel time / reduce |descent| at high speed."""
    atm = AtmosphereState()
    vacuum = BallisticDynamics(mass_kg=10.0, drag_coef=0.0, reference_area_m2=0.05)
    drag = BallisticDynamics(mass_kg=10.0, drag_coef=1.0, reference_area_m2=0.5)
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=1000.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=-100.0,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    end_vac = integrate(
        state, make_ballistic_force_fn(vacuum, atm), vacuum.mass_kg, 1.0, n_substeps=200
    )
    end_drag = integrate(
        state, make_ballistic_force_fn(drag, atm), drag.mass_kg, 1.0, n_substeps=200
    )
    # Vacuum descended more than the drag case.
    assert end_vac.altitude_m < end_drag.altitude_m


def test_ballistic_dynamics_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match=r"mass_kg"):
        BallisticDynamics(mass_kg=0.0)
    with pytest.raises(ValueError, match=r"drag_coef"):
        BallisticDynamics(mass_kg=1.0, drag_coef=-0.1)
    with pytest.raises(ValueError, match=r"reference_area_m2"):
        BallisticDynamics(mass_kg=1.0, reference_area_m2=0.0)


def test_initial_velocity_field_must_be_three_tuple() -> None:
    with pytest.raises(ValueError, match=r"initial_velocity_mps"):
        BallisticDynamics(mass_kg=1.0, initial_velocity_mps=(1.0, 2.0))  # type: ignore[arg-type]


# ---------- 5.8b — drag / mass / v0 / theta scaling invariants ----------


def _oblique_throw_range(v0: float, theta_rad: float) -> float:
    """Run a vacuum oblique throw at (v0, theta) and return horizontal range."""
    vx = v0 * math.cos(theta_rad)
    vz = v0 * math.sin(theta_rad)
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    f = make_ballistic_force_fn(dyn, atm)
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=0.0,
        velocity_east_mps=vx,
        velocity_north_mps=0.0,
        velocity_up_mps=vz,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    flight_time = 2.0 * vz / _G
    end = integrate(state, f, dyn.mass_kg, flight_time, n_substeps=400)
    return float(end.east_m)


def test_drag_coef_monotonic_in_descent_reduction() -> None:
    """Larger Cd -> smaller |descent| after a fixed time at fixed v0.
    Three Cd values (0.0 / 0.5 / 1.0) must order monotonically.
    """
    atm = AtmosphereState()
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=1000.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        velocity_up_mps=-100.0,  # already falling fast
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    altitudes: list[float] = []
    for cd in (0.0, 0.5, 1.0):
        dyn = BallisticDynamics(mass_kg=10.0, drag_coef=cd, reference_area_m2=0.5)
        end = integrate(state, make_ballistic_force_fn(dyn, atm), dyn.mass_kg, 1.0, n_substeps=200)
        altitudes.append(float(end.altitude_m))
    # Larger Cd = higher remaining altitude (less descent).
    assert altitudes[0] < altitudes[1] < altitudes[2], altitudes


def test_30_and_60_deg_oblique_throws_share_range_sin_2theta_symmetry() -> None:
    """In vacuum: range = v0^2 sin(2*theta) / g. sin(2*30°) = sin(2*60°)
    = sqrt(3)/2, so the two throws land at the exact same distance.
    Pins the sin(2*theta) symmetry of the closed-form range.
    """
    v0 = 50.0
    range_30 = _oblique_throw_range(v0, math.radians(30.0))
    range_60 = _oblique_throw_range(v0, math.radians(60.0))
    assert range_30 == pytest.approx(range_60, rel=1e-9)


def test_oblique_throw_range_quadratic_in_initial_speed() -> None:
    """Doubling v0 at fixed theta multiplies the range by 4 (v0^2 scaling)."""
    theta = math.radians(45.0)
    r_small = _oblique_throw_range(25.0, theta)
    r_large = _oblique_throw_range(50.0, theta)
    assert r_large == pytest.approx(4.0 * r_small, rel=1e-9)


def test_vacuum_freefall_independent_of_mass() -> None:
    """Mass drops out of the equation of motion in vacuum
    (m*a = m*g -> a = g). 1 kg and 100 kg fall identically.
    """
    atm = AtmosphereState()
    dt = 1.0
    dyn_light = BallisticDynamics(mass_kg=1.0, drag_coef=0.0, reference_area_m2=0.05)
    dyn_heavy = BallisticDynamics(mass_kg=100.0, drag_coef=0.0, reference_area_m2=0.05)
    end_light = integrate(
        _initial_state(), make_ballistic_force_fn(dyn_light, atm), dyn_light.mass_kg, dt
    )
    end_heavy = integrate(
        _initial_state(), make_ballistic_force_fn(dyn_heavy, atm), dyn_heavy.mass_kg, dt
    )
    assert end_light.altitude_m == pytest.approx(end_heavy.altitude_m, rel=1e-12)


def test_apex_height_quadratic_in_initial_velocity() -> None:
    """Vacuum apex height = v0^2 / (2g) -> doubling v0 quadruples apex."""
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    f = make_ballistic_force_fn(dyn, atm)

    def _apex(v_up0: float) -> float:
        state = RigidBodyState(
            east_m=0.0,
            north_m=0.0,
            altitude_m=0.0,
            velocity_east_mps=0.0,
            velocity_north_mps=0.0,
            velocity_up_mps=v_up0,
            roll_rad=0.0,
            pitch_rad=0.0,
            yaw_rad=0.0,
        )
        end = integrate(state, f, dyn.mass_kg, v_up0 / _G, n_substeps=200)
        return float(end.altitude_m)

    apex_small = _apex(30.0)
    apex_large = _apex(60.0)
    assert apex_large == pytest.approx(4.0 * apex_small, rel=1e-9)


def test_analytic_form_is_pythagorean_at_oblique_throw() -> None:
    """Throw at 45 deg: horizontal range = v0^2 sin(2*theta)/g."""
    v0 = 50.0
    theta = math.radians(45.0)
    vx = v0 * math.cos(theta)
    vz = v0 * math.sin(theta)
    dyn = _vacuum_dynamics()
    atm = AtmosphereState()
    f = make_ballistic_force_fn(dyn, atm)
    state = RigidBodyState(
        east_m=0.0,
        north_m=0.0,
        altitude_m=0.0,
        velocity_east_mps=vx,
        velocity_north_mps=0.0,
        velocity_up_mps=vz,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=0.0,
    )
    flight_time = 2.0 * vz / _G
    end = integrate(state, f, dyn.mass_kg, flight_time, n_substeps=400)
    # Analytic range: v0^2 * sin(2*theta) / g.
    expected_range = v0 * v0 * math.sin(2.0 * theta) / _G
    assert end.east_m == pytest.approx(expected_range, abs=1e-8)
    assert end.altitude_m == pytest.approx(0.0, abs=1e-8)
