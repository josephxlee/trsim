"""Dynamics forces regression vs golden dataset (Phase 5.5)."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.forces import drag_force, gravity_force

_DATASET = GoldenDataset.load(Path(__file__).parent / "golden" / "dynamics_forces.json")
_RTOL = _DATASET.meta.rtol


@pytest.mark.parametrize("case_id", ["gravity_10kg", "gravity_500kg"])
def test_gravity_force_matches_golden(case_id: str) -> None:
    s = _DATASET.case(case_id)
    f = gravity_force(mass_kg=s.inputs["mass_kg"])
    expected = s.expected["force_n"]
    for got, exp in zip(f, expected, strict=True):
        assert got == pytest.approx(exp, rel=_RTOL, abs=1e-12)


def test_drag_zero_velocity_yields_zero() -> None:
    s = _DATASET.case("drag_zero_velocity_yields_zero")
    f = drag_force(
        velocity_mps=tuple(s.inputs["velocity_enu_mps"]),
        drag_coef=s.inputs["drag_coef"],
        reference_area_m2=s.inputs["reference_area_m2"],
        altitude_m=s.inputs["altitude_m"],
        atm=AtmosphereState(),
    )
    assert f == (0.0, 0.0, 0.0)


def test_drag_100mps_east_matches_golden() -> None:
    s = _DATASET.case("drag_100mps_east_at_sea_level")
    f = drag_force(
        velocity_mps=tuple(s.inputs["velocity_enu_mps"]),
        drag_coef=s.inputs["drag_coef"],
        reference_area_m2=s.inputs["reference_area_m2"],
        altitude_m=s.inputs["altitude_m"],
        atm=AtmosphereState(),
    )
    expected = s.expected["force_n"]
    assert f[0] == pytest.approx(expected[0], rel=_RTOL)
    # North / Up components are zero (or negative zero) for pure-east motion.
    assert abs(f[1]) < 1e-12
    assert abs(f[2]) < 1e-12


def test_gravity_scales_linearly_with_mass() -> None:
    f_small = gravity_force(mass_kg=10.0)
    f_big = gravity_force(mass_kg=100.0)
    assert f_big[2] == pytest.approx(f_small[2] * 10.0, rel=_RTOL)


def test_drag_opposes_velocity_direction() -> None:
    """Drag must always reduce kinetic energy: dot(F_drag, v) <= 0."""
    atm = AtmosphereState()
    for v in [(50.0, 0.0, 0.0), (0.0, 75.0, 0.0), (30.0, -40.0, 10.0)]:
        f = drag_force(
            velocity_mps=v,
            drag_coef=0.4,
            reference_area_m2=0.05,
            altitude_m=0.0,
            atm=atm,
        )
        dot = f[0] * v[0] + f[1] * v[1] + f[2] * v[2]
        assert dot <= 0.0


# ---------- 5.5b — Closed-form scaling invariants ----------


def _drag(
    v: tuple[float, float, float], *, cd: float = 0.4, area: float = 0.05, altitude: float = 0.0
) -> tuple[float, float, float]:
    return drag_force(
        velocity_mps=v,
        drag_coef=cd,
        reference_area_m2=area,
        altitude_m=altitude,
        atm=AtmosphereState(),
    )


def test_drag_force_quadratic_in_speed() -> None:
    """|F_drag| = 1/2 rho Cd A v^2 -> doubling |v| multiplies |F_drag|
    by 4. Locks the quadratic-speed dependence of the drag law.
    """
    base = _drag((50.0, 0.0, 0.0))
    doubled = _drag((100.0, 0.0, 0.0))
    assert doubled[0] == pytest.approx(4.0 * base[0], rel=_RTOL)


def test_drag_force_linear_in_reference_area() -> None:
    """Doubling reference area doubles drag at fixed (v, Cd, rho)."""
    base = _drag((50.0, 0.0, 0.0), area=0.05)
    doubled_a = _drag((50.0, 0.0, 0.0), area=0.10)
    assert doubled_a[0] == pytest.approx(2.0 * base[0], rel=_RTOL)


def test_drag_force_linear_in_drag_coef() -> None:
    """Doubling Cd doubles drag at fixed (v, A, rho)."""
    base = _drag((50.0, 0.0, 0.0), cd=0.4)
    doubled_cd = _drag((50.0, 0.0, 0.0), cd=0.8)
    assert doubled_cd[0] == pytest.approx(2.0 * base[0], rel=_RTOL)


def test_drag_force_decreases_with_altitude() -> None:
    """ISA density falls with altitude inside the troposphere, so drag
    at fixed (v, Cd, A) must strictly decrease across sea level ->
    1 km -> 5 km -> 11 km. Locks the density-dependence direction.
    """
    altitudes = (0.0, 1000.0, 5000.0, 11000.0)
    drags = [abs(_drag((100.0, 0.0, 0.0), altitude=a)[0]) for a in altitudes]
    for hi, lo in pairwise(drags):
        assert hi > lo, f"drag should fall with altitude: {drags}"


def test_gravity_force_has_only_vertical_component() -> None:
    """gravity_force returns ENU (E, N, U) — gravity must contribute
    only to the U (vertical) axis, with E and N exactly zero.
    """
    f = gravity_force(mass_kg=50.0)
    assert f[0] == 0.0
    assert f[1] == 0.0
    assert f[2] < 0.0  # gravity pulls down (negative Up)


def test_drag_force_direction_antiparallel_to_velocity() -> None:
    """At any non-zero velocity, F_drag is antiparallel to v: the
    angle between them is exactly pi. Verify via cross-product
    magnitude / dot sign.
    """
    v = (30.0, -40.0, 10.0)  # |v| = sqrt(900+1600+100) = sqrt(2600)
    f = _drag(v)
    # Cross product magnitude must vanish (parallel vectors).
    cx = v[1] * f[2] - v[2] * f[1]
    cy = v[2] * f[0] - v[0] * f[2]
    cz = v[0] * f[1] - v[1] * f[0]
    assert abs(cx) < 1e-9
    assert abs(cy) < 1e-9
    assert abs(cz) < 1e-9
    # And dot < 0 (antiparallel, not parallel).
    dot = f[0] * v[0] + f[1] * v[1] + f[2] * v[2]
    assert dot < 0.0
