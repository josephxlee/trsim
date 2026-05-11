"""Single-scatterer RCS regression vs analytic forms (Phase 5.9)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.reflection.rcs_single import (
    cylinder_rcs_broadside_m2,
    dbsm_to_rcs,
    flat_plate_rcs_max_m2,
    rcs_to_dbsm,
    sphere_rcs_geometric_m2,
    sphere_rcs_rayleigh_m2,
    trihedral_corner_rcs_m2,
)

_RTOL = 1e-12


# ---------- Sphere ----------


def test_sphere_geometric_unit_radius_is_pi() -> None:
    """Geometric-optics sphere: sigma = pi * r^2; r=1 -> pi."""
    assert sphere_rcs_geometric_m2(1.0) == pytest.approx(math.pi, rel=_RTOL)


@pytest.mark.parametrize(("r", "expected"), [(0.5, math.pi * 0.25), (2.0, math.pi * 4.0)])
def test_sphere_geometric_scales_with_r_squared(r: float, expected: float) -> None:
    assert sphere_rcs_geometric_m2(r) == pytest.approx(expected, rel=_RTOL)


def test_sphere_rayleigh_known_small_object() -> None:
    """Rayleigh regime r=1 cm @ lambda=3 cm: sigma ~ 9 pi^5 r^6 / lambda^4 * 4 (Skolnik)."""
    sigma = sphere_rcs_rayleigh_m2(0.01, 0.03)
    assert sigma == pytest.approx(0.0005037361066424387, rel=_RTOL)


# ---------- Flat plate ----------


def test_flat_plate_max_rcs_1m2_xband() -> None:
    """sigma_max = 4 pi A^2 / lambda^2; A=1 m^2, lambda=3 cm."""
    sigma = flat_plate_rcs_max_m2(1.0, 0.03)
    assert sigma == pytest.approx(13962.634015954636, rel=_RTOL)


def test_flat_plate_quadratic_in_area() -> None:
    base = flat_plate_rcs_max_m2(1.0, 0.03)
    doubled = flat_plate_rcs_max_m2(2.0, 0.03)
    assert doubled == pytest.approx(4.0 * base, rel=_RTOL)


# ---------- Cylinder ----------


def test_cylinder_broadside_known_value() -> None:
    sigma = cylinder_rcs_broadside_m2(0.5, 2.0, 0.03)
    assert sigma == pytest.approx(418.8790204786391, rel=_RTOL)


def test_cylinder_quadratic_in_length() -> None:
    base = cylinder_rcs_broadside_m2(0.5, 1.0, 0.03)
    quadrupled = cylinder_rcs_broadside_m2(0.5, 2.0, 0.03)
    assert quadrupled == pytest.approx(4.0 * base, rel=_RTOL)


# ---------- Trihedral ----------


def test_trihedral_corner_known_value() -> None:
    sigma = trihedral_corner_rcs_m2(0.5, 0.03)
    assert sigma == pytest.approx(2617.993877991494, rel=_RTOL)


def test_trihedral_grows_as_side_to_fourth() -> None:
    """Trihedral has sigma ~ 12 pi a^4 / lambda^2; doubling a -> x16."""
    base = trihedral_corner_rcs_m2(0.5, 0.03)
    doubled = trihedral_corner_rcs_m2(1.0, 0.03)
    assert doubled == pytest.approx(16.0 * base, rel=_RTOL)


# ---------- dBsm conversions ----------


def test_rcs_to_dbsm_unit_is_zero() -> None:
    assert rcs_to_dbsm(1.0) == 0.0


def test_rcs_to_dbsm_ten_is_ten() -> None:
    assert rcs_to_dbsm(10.0) == pytest.approx(10.0, rel=_RTOL)


def test_rcs_dbsm_round_trip() -> None:
    for rcs in (0.01, 0.5, 1.0, 7.5, 250.0):
        assert dbsm_to_rcs(rcs_to_dbsm(rcs)) == pytest.approx(rcs, rel=1e-12)


def test_dbsm_zero_is_one_m2() -> None:
    assert dbsm_to_rcs(0.0) == pytest.approx(1.0, rel=_RTOL)
