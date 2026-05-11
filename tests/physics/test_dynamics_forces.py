"""Dynamics forces regression vs golden dataset (Phase 5.5)."""

from __future__ import annotations

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
        velocity_mps=tuple(s.inputs["velocity_enu_mps"]),  # type: ignore[arg-type]
        drag_coef=s.inputs["drag_coef"],
        reference_area_m2=s.inputs["reference_area_m2"],
        altitude_m=s.inputs["altitude_m"],
        atm=AtmosphereState(),
    )
    assert f == (0.0, 0.0, 0.0)


def test_drag_100mps_east_matches_golden() -> None:
    s = _DATASET.case("drag_100mps_east_at_sea_level")
    f = drag_force(
        velocity_mps=tuple(s.inputs["velocity_enu_mps"]),  # type: ignore[arg-type]
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
