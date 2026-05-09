"""Unit tests for workbench.physics.dynamics.forces (Phase 2.4b)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.atmosphere import AtmosphereState, isa_density
from workbench.physics.dynamics.forces import (
    G_STANDARD_M_PER_S2,
    ThrustProfile,
    ThrustProfileKind,
    control_force,
    drag_force,
    gravity_force,
    lift_force,
    thrust_force,
)

# ---------------------------------------------------------------------
# Gravity
# ---------------------------------------------------------------------


def test_gravity_returns_minus_mg_along_up() -> None:
    f = gravity_force(mass_kg=1000.0)
    assert f[0] == 0.0
    assert f[1] == 0.0
    assert f[2] == pytest.approx(-1000.0 * G_STANDARD_M_PER_S2, abs=1e-9)


def test_gravity_constant_value() -> None:
    # Lock the ICAO 1976 standard value — same as ISA_G_M_PER_S2 in
    # workbench.physics.atmosphere. Cross-check via local import.
    from workbench.physics.atmosphere import ISA_G_M_PER_S2

    assert G_STANDARD_M_PER_S2 == ISA_G_M_PER_S2 == 9.80665


@pytest.mark.parametrize("bad_mass", [0.0, -1.0])
def test_gravity_rejects_non_positive_mass(bad_mass: float) -> None:
    with pytest.raises(ValueError, match=r"mass_kg"):
        gravity_force(mass_kg=bad_mass)


# ---------------------------------------------------------------------
# Drag
# ---------------------------------------------------------------------


def _atm() -> AtmosphereState:
    return AtmosphereState()


def test_drag_zero_velocity_zero_force() -> None:
    f = drag_force(
        (0.0, 0.0, 0.0), drag_coef=0.3, reference_area_m2=0.1, altitude_m=0.0, atm=_atm()
    )
    assert f == (0.0, 0.0, 0.0)


def test_drag_below_threshold_zero() -> None:
    # speed = 0.005 < 0.01
    f = drag_force(
        (0.003, 0.004, 0.0),
        drag_coef=0.3,
        reference_area_m2=0.1,
        altitude_m=0.0,
        atm=_atm(),
    )
    assert f == (0.0, 0.0, 0.0)


def test_drag_opposes_velocity_direction() -> None:
    # +East velocity → drag in -East direction
    f = drag_force(
        (100.0, 0.0, 0.0),
        drag_coef=0.5,
        reference_area_m2=2.0,
        altitude_m=0.0,
        atm=_atm(),
    )
    assert f[0] < 0.0
    assert f[1] == pytest.approx(0.0, abs=1e-12)
    assert f[2] == pytest.approx(0.0, abs=1e-12)


def test_drag_magnitude_matches_formula() -> None:
    velocity = (100.0, 0.0, 0.0)
    cd = 0.5
    area = 2.0
    altitude = 1000.0
    atm = _atm()
    rho = isa_density(altitude, atm)
    speed = 100.0
    expected_mag = 0.5 * rho * speed * speed * cd * area

    f = drag_force(velocity, drag_coef=cd, reference_area_m2=area, altitude_m=altitude, atm=atm)
    f_mag = math.sqrt(f[0] ** 2 + f[1] ** 2 + f[2] ** 2)
    assert f_mag == pytest.approx(expected_mag, rel=1e-12)


def test_drag_scales_with_v_squared() -> None:
    atm = _atm()
    f100 = drag_force((100.0, 0.0, 0.0), 0.3, 1.0, 0.0, atm)
    f200 = drag_force((200.0, 0.0, 0.0), 0.3, 1.0, 0.0, atm)
    # double speed → 4x drag magnitude
    assert abs(f200[0]) == pytest.approx(4.0 * abs(f100[0]), rel=1e-12)


def test_drag_density_drops_with_altitude() -> None:
    atm = _atm()
    f_sea = drag_force((100.0, 0.0, 0.0), 0.3, 1.0, 0.0, atm)
    f_high = drag_force((100.0, 0.0, 0.0), 0.3, 1.0, 5000.0, atm)
    # rho drops with altitude → drag magnitude shrinks
    assert abs(f_high[0]) < abs(f_sea[0])


def test_drag_3d_direction() -> None:
    # 1-1-1 unit-ish velocity → drag along (-1,-1,-1)/sqrt(3)
    v = (10.0, 10.0, 10.0)
    f = drag_force(v, 0.3, 1.0, 0.0, _atm())
    # all three components should be equal and negative
    assert f[0] == pytest.approx(f[1], rel=1e-12)
    assert f[0] == pytest.approx(f[2], rel=1e-12)
    assert f[0] < 0.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"drag_coef": -0.1, "reference_area_m2": 1.0}, r"drag_coef"),
        ({"drag_coef": 0.3, "reference_area_m2": 0.0}, r"reference_area_m2"),
        ({"drag_coef": 0.3, "reference_area_m2": -1.0}, r"reference_area_m2"),
    ],
)
def test_drag_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        drag_force((10.0, 0.0, 0.0), altitude_m=0.0, atm=_atm(), **kwargs)


# ---------------------------------------------------------------------
# Lift
# ---------------------------------------------------------------------


def test_lift_trim_only_at_reference() -> None:
    # h == h_ref, v_up == 0 → lift = mg only
    mass = 1000.0
    f = lift_force(
        mass_kg=mass,
        altitude_m=1000.0,
        target_altitude_m=1000.0,
        velocity_up_mps=0.0,
        kp_altitude=10.0,
        kd_altitude=5.0,
    )
    assert f[2] == pytest.approx(mass * G_STANDARD_M_PER_S2, abs=1e-9)
    assert f[0] == 0.0
    assert f[1] == 0.0


def test_lift_below_reference_increases_force() -> None:
    # h < h_ref → kp * (h_ref - h) > 0 → extra +Up force
    f = lift_force(
        mass_kg=1000.0,
        altitude_m=900.0,
        target_altitude_m=1000.0,
        velocity_up_mps=0.0,
        kp_altitude=10.0,
        kd_altitude=5.0,
    )
    expected = 1000.0 * G_STANDARD_M_PER_S2 + 10.0 * 100.0
    assert f[2] == pytest.approx(expected, abs=1e-9)


def test_lift_velocity_damps_climb() -> None:
    # h == h_ref but v_up positive → kd damps it (smaller force)
    f = lift_force(
        mass_kg=1000.0,
        altitude_m=1000.0,
        target_altitude_m=1000.0,
        velocity_up_mps=5.0,
        kp_altitude=10.0,
        kd_altitude=20.0,
    )
    expected = 1000.0 * G_STANDARD_M_PER_S2 - 20.0 * 5.0
    assert f[2] == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"mass_kg": 0.0}, r"mass_kg"),
        ({"mass_kg": -1.0}, r"mass_kg"),
        ({"kp_altitude": -1.0}, r"kp_altitude"),
        ({"kd_altitude": -1.0}, r"kd_altitude"),
    ],
)
def test_lift_validation(kwargs: dict, match: str) -> None:
    base = {
        "mass_kg": 1000.0,
        "altitude_m": 1000.0,
        "target_altitude_m": 1000.0,
        "velocity_up_mps": 0.0,
        "kp_altitude": 10.0,
        "kd_altitude": 5.0,
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        lift_force(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# ThrustProfile
# ---------------------------------------------------------------------


def test_thrust_kind_enum_values() -> None:
    assert ThrustProfileKind.CONSTANT.value == "constant"
    assert ThrustProfileKind.CURVE.value == "curve"


def test_thrust_constant_returns_same_value() -> None:
    p = ThrustProfile(kind=ThrustProfileKind.CONSTANT, constant_thrust_n=500.0)
    assert p.thrust_at(0.0) == 500.0
    assert p.thrust_at(100.0) == 500.0
    assert p.thrust_at(-5.0) == 500.0


def test_thrust_curve_interpolates_linearly() -> None:
    p = ThrustProfile(
        kind=ThrustProfileKind.CURVE,
        curve=((0.0, 0.0), (1.0, 1000.0), (2.0, 0.0)),
    )
    # Boundary
    assert p.thrust_at(0.0) == 0.0
    assert p.thrust_at(1.0) == 1000.0
    assert p.thrust_at(2.0) == 0.0
    # Mid-segment (linear)
    assert p.thrust_at(0.5) == pytest.approx(500.0, abs=1e-9)
    assert p.thrust_at(1.5) == pytest.approx(500.0, abs=1e-9)


def test_thrust_curve_clamps_outside_range() -> None:
    p = ThrustProfile(
        kind=ThrustProfileKind.CURVE,
        curve=((0.0, 100.0), (10.0, 200.0)),
    )
    assert p.thrust_at(-5.0) == 100.0  # clamps to first
    assert p.thrust_at(20.0) == 200.0  # clamps to last


def test_thrust_curve_rejects_short_curve() -> None:
    with pytest.raises(ValueError, match=r"at least 2 samples"):
        ThrustProfile(kind=ThrustProfileKind.CURVE, curve=((0.0, 100.0),))


def test_thrust_curve_rejects_non_monotonic_time() -> None:
    with pytest.raises(ValueError, match=r"strictly increasing"):
        ThrustProfile(
            kind=ThrustProfileKind.CURVE,
            curve=((0.0, 100.0), (1.0, 200.0), (1.0, 300.0)),
        )


def test_thrust_curve_rejects_negative_thrust() -> None:
    with pytest.raises(ValueError, match=r"must be >= 0"):
        ThrustProfile(
            kind=ThrustProfileKind.CURVE,
            curve=((0.0, 100.0), (1.0, -200.0)),
        )


def test_thrust_constant_rejects_negative() -> None:
    with pytest.raises(ValueError, match=r"constant_thrust_n"):
        ThrustProfile(kind=ThrustProfileKind.CONSTANT, constant_thrust_n=-1.0)


def test_thrust_force_along_forward_direction() -> None:
    p = ThrustProfile(kind=ThrustProfileKind.CONSTANT, constant_thrust_n=1000.0)
    # +North forward
    f = thrust_force(p, sim_t_s=0.0, forward_direction=(0.0, 1.0, 0.0))
    assert f == (0.0, 1000.0, 0.0)


def test_thrust_force_at_specific_time() -> None:
    p = ThrustProfile(
        kind=ThrustProfileKind.CURVE,
        curve=((0.0, 0.0), (1.0, 2000.0), (2.0, 0.0)),
    )
    # Forward = pure +East, t=0.5 → magnitude = 1000
    f = thrust_force(p, sim_t_s=0.5, forward_direction=(1.0, 0.0, 0.0))
    assert f[0] == pytest.approx(1000.0, abs=1e-9)
    assert f[1] == 0.0
    assert f[2] == 0.0


# ---------------------------------------------------------------------
# Control force
# ---------------------------------------------------------------------


def test_control_at_reference_zero_velocity_zero_force() -> None:
    f = control_force(
        east_m=10.0,
        north_m=20.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        ref_east_m=10.0,
        ref_north_m=20.0,
        kp_position=1.0,
        kd_position=0.5,
        max_accel_n=1000.0,
    )
    assert f == (0.0, 0.0, 0.0)


def test_control_pulls_toward_reference() -> None:
    # pos=(0, 0), ref=(100, 0), v=0 → +East force
    f = control_force(
        east_m=0.0,
        north_m=0.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        ref_east_m=100.0,
        ref_north_m=0.0,
        kp_position=2.0,
        kd_position=0.5,
        max_accel_n=1e6,
    )
    assert f[0] == pytest.approx(200.0, abs=1e-9)
    assert f[1] == pytest.approx(0.0, abs=1e-12)
    assert f[2] == 0.0


def test_control_velocity_damps_force() -> None:
    # At ref but moving +East fast → -East force from kd damping
    f = control_force(
        east_m=100.0,
        north_m=0.0,
        velocity_east_mps=10.0,
        velocity_north_mps=0.0,
        ref_east_m=100.0,
        ref_north_m=0.0,
        kp_position=1.0,
        kd_position=2.0,
        max_accel_n=1e6,
    )
    assert f[0] == pytest.approx(-20.0, abs=1e-9)


def test_control_force_clamped_to_max_accel() -> None:
    # Huge position error but max_accel_n=100
    f = control_force(
        east_m=0.0,
        north_m=0.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        ref_east_m=10000.0,
        ref_north_m=-10000.0,
        kp_position=10.0,
        kd_position=0.0,
        max_accel_n=100.0,
    )
    assert f[0] == 100.0
    assert f[1] == -100.0


def test_control_vertical_always_zero() -> None:
    # control_force never touches vertical channel — lift_force does.
    f = control_force(
        east_m=0.0,
        north_m=0.0,
        velocity_east_mps=0.0,
        velocity_north_mps=0.0,
        ref_east_m=100.0,
        ref_north_m=100.0,
        kp_position=1.0,
        kd_position=0.0,
        max_accel_n=1e6,
    )
    assert f[2] == 0.0


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"kp_position": -1.0}, r"kp_position"),
        ({"kd_position": -1.0}, r"kd_position"),
        ({"max_accel_n": -1.0}, r"max_accel_n"),
    ],
)
def test_control_validation(kwargs: dict, match: str) -> None:
    base = {
        "east_m": 0.0,
        "north_m": 0.0,
        "velocity_east_mps": 0.0,
        "velocity_north_mps": 0.0,
        "ref_east_m": 0.0,
        "ref_north_m": 0.0,
        "kp_position": 1.0,
        "kd_position": 1.0,
        "max_accel_n": 100.0,
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        control_force(**base)  # type: ignore[arg-type]
