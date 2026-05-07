"""Validation tests for :mod:`workbench.physics.reflection.rcs_single`.

The file is named ``test_radar_equation.py`` to align with the plan/04
§ 4.3 Phase 5 verification matrix entry "radar_equation". Phase 1.5
provides the analytic RCS primitives that the radar equation needs.

Coverage:

- Sphere: geometric optics (a >> lambda) and Rayleigh (a << lambda).
- Flat plate: normal-incidence peak.
- Cylinder: broadside peak.
- Trihedral / dihedral corner reflectors.
- dBsm <-> linear conversions and round-trips.

Reference values are produced by the same closed-form expressions in
``docs/matlab_validation/test_rcs.m`` (Octave / MATLAB, no Toolbox).
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.reflection.rcs_single import (
    PI,
    cylinder_rcs_broadside_m2,
    dbsm_to_rcs,
    dihedral_corner_rcs_m2,
    flat_plate_rcs_max_m2,
    rcs_to_dbsm,
    sphere_rcs_geometric_m2,
    sphere_rcs_rayleigh_m2,
    trihedral_corner_rcs_m2,
)

# 9.4 GHz X-band: lambda = c / f = 299_792_458 / 9.4e9 ~= 0.03189 m
LAMBDA_X_BAND_M = 299_792_458.0 / 9.4e9


# ---------------------------------------------------------------------------
# Sphere — geometric optics
# ---------------------------------------------------------------------------


def test_sphere_unit_radius_geometric() -> None:
    """1 m sphere -> sigma = pi m^2 ~= 3.1416 m^2."""
    assert sphere_rcs_geometric_m2(1.0) == pytest.approx(PI, abs=1e-12)
    assert sphere_rcs_geometric_m2(1.0) == pytest.approx(3.14159265, abs=1e-6)


def test_sphere_half_radius_geometric() -> None:
    """0.5 m sphere -> sigma = pi/4 m^2 ~= 0.785 m^2."""
    assert sphere_rcs_geometric_m2(0.5) == pytest.approx(PI / 4.0, abs=1e-12)


def test_sphere_zero_radius() -> None:
    """Zero-radius sphere has zero RCS."""
    assert sphere_rcs_geometric_m2(0.0) == 0.0


def test_sphere_geometric_quadratic_in_radius() -> None:
    """sigma proportional to a^2 (doubling radius -> 4x RCS)."""
    a = sphere_rcs_geometric_m2(1.0)
    b = sphere_rcs_geometric_m2(2.0)
    assert b == pytest.approx(4.0 * a, abs=1e-12)


def test_sphere_geometric_no_wavelength_dependence() -> None:
    """Geometric-optics formula has no lambda — answer is the same at any frequency."""
    assert sphere_rcs_geometric_m2(1.0) == sphere_rcs_geometric_m2(1.0)


# ---------------------------------------------------------------------------
# Sphere — Rayleigh regime
# ---------------------------------------------------------------------------


def test_sphere_rayleigh_a_over_lambda_scaling() -> None:
    """Doubling a (with same lambda) gives 64x sigma (a^6)."""
    s1 = sphere_rcs_rayleigh_m2(0.001, 1.0)
    s2 = sphere_rcs_rayleigh_m2(0.002, 1.0)
    assert s2 == pytest.approx(64.0 * s1, abs=1e-15)


def test_sphere_rayleigh_lambda_scaling() -> None:
    """Doubling lambda (with same a) cuts sigma by 16x (1/lambda^4)."""
    s1 = sphere_rcs_rayleigh_m2(0.001, 1.0)
    s2 = sphere_rcs_rayleigh_m2(0.001, 2.0)
    assert s2 == pytest.approx(s1 / 16.0, abs=1e-15)


def test_sphere_rayleigh_known_value() -> None:
    """a=1mm, lambda=1m -> sigma = (4*pi^5/3) * 1e-18 ~= 4.077e-16 m^2."""
    sigma = sphere_rcs_rayleigh_m2(radius_m=1e-3, wavelength_m=1.0)
    expected = (4.0 * PI**5 / 3.0) * 1e-18
    assert sigma == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------------
# Flat plate
# ---------------------------------------------------------------------------


def test_flat_plate_unit_area_xband() -> None:
    """1 m^2 plate at 9.4 GHz: sigma = 4*pi/lambda^2 ~= 12354.47 m^2 (~40.92 dBsm)."""
    sigma = flat_plate_rcs_max_m2(area_m2=1.0, wavelength_m=LAMBDA_X_BAND_M)
    expected = 4.0 * PI / (LAMBDA_X_BAND_M * LAMBDA_X_BAND_M)
    assert sigma == pytest.approx(expected, abs=1e-9)
    assert sigma == pytest.approx(12354.4713, abs=1e-3)


def test_flat_plate_quartic_in_area() -> None:
    """sigma proportional to A^2 (doubling area -> 4x RCS)."""
    s1 = flat_plate_rcs_max_m2(1.0, 0.03)
    s2 = flat_plate_rcs_max_m2(2.0, 0.03)
    assert s2 == pytest.approx(4.0 * s1, abs=1e-9)


# ---------------------------------------------------------------------------
# Cylinder
# ---------------------------------------------------------------------------


def test_cylinder_broadside_xband() -> None:
    """0.1 m radius x 1 m length cylinder at 9.4 GHz: sigma ~= 19.7009 m^2."""
    sigma = cylinder_rcs_broadside_m2(
        radius_m=0.1,
        length_m=1.0,
        wavelength_m=LAMBDA_X_BAND_M,
    )
    expected = 2.0 * PI * 0.1 * 1.0 / LAMBDA_X_BAND_M
    assert sigma == pytest.approx(expected, abs=1e-12)
    assert sigma == pytest.approx(19.7009, abs=1e-3)


def test_cylinder_length_quadratic() -> None:
    """sigma proportional to L^2 (doubling length -> 4x RCS)."""
    s1 = cylinder_rcs_broadside_m2(0.1, 1.0, 0.03)
    s2 = cylinder_rcs_broadside_m2(0.1, 2.0, 0.03)
    assert s2 == pytest.approx(4.0 * s1, abs=1e-12)


# ---------------------------------------------------------------------------
# Corner reflectors
# ---------------------------------------------------------------------------


def test_trihedral_xband() -> None:
    """0.5 m trihedral at 9.4 GHz: sigma ~= 2316.4634 m^2 (~33.65 dBsm)."""
    sigma = trihedral_corner_rcs_m2(side_length_m=0.5, wavelength_m=LAMBDA_X_BAND_M)
    expected = 12.0 * PI * (0.5**4) / (LAMBDA_X_BAND_M * LAMBDA_X_BAND_M)
    assert sigma == pytest.approx(expected, abs=1e-9)
    assert sigma == pytest.approx(2316.4634, abs=1e-3)


def test_trihedral_quartic_in_side_length() -> None:
    """sigma proportional to L^4."""
    s1 = trihedral_corner_rcs_m2(0.25, 0.03)
    s2 = trihedral_corner_rcs_m2(0.5, 0.03)
    assert s2 == pytest.approx(16.0 * s1, abs=1e-9)


def test_dihedral_xband() -> None:
    """1 m x 0.5 m dihedral at 9.4 GHz: sigma ~= 6177.2357 m^2 (~37.91 dBsm)."""
    sigma = dihedral_corner_rcs_m2(width_m=1.0, height_m=0.5, wavelength_m=LAMBDA_X_BAND_M)
    expected = 8.0 * PI * 0.25 / (LAMBDA_X_BAND_M * LAMBDA_X_BAND_M)
    assert sigma == pytest.approx(expected, abs=1e-9)
    assert sigma == pytest.approx(6177.2357, abs=1e-3)


# ---------------------------------------------------------------------------
# dBsm conversions
# ---------------------------------------------------------------------------


def test_dbsm_unit_reference() -> None:
    """1 m^2 = 0 dBsm by definition."""
    assert rcs_to_dbsm(1.0) == pytest.approx(0.0, abs=1e-12)
    assert dbsm_to_rcs(0.0) == pytest.approx(1.0, abs=1e-12)


def test_dbsm_decade_steps() -> None:
    """100 m^2 = 20 dBsm; 0.01 m^2 = -20 dBsm."""
    assert rcs_to_dbsm(100.0) == pytest.approx(20.0, abs=1e-12)
    assert rcs_to_dbsm(0.01) == pytest.approx(-20.0, abs=1e-12)
    assert dbsm_to_rcs(20.0) == pytest.approx(100.0, abs=1e-9)
    assert dbsm_to_rcs(-20.0) == pytest.approx(0.01, abs=1e-12)


@pytest.mark.parametrize("rcs_m2", [1e-6, 1e-3, 0.5, 1.0, 3.14, 100.0, 1e6])
def test_dbsm_round_trip(rcs_m2: float) -> None:
    """sigma_m2 -> dBsm -> sigma_m2 round-trip is identity."""
    assert dbsm_to_rcs(rcs_to_dbsm(rcs_m2)) == pytest.approx(rcs_m2, rel=1e-12)


def test_unit_sphere_dbsm() -> None:
    """1 m sphere has sigma = pi m^2 = 4.971 dBsm."""
    sigma = sphere_rcs_geometric_m2(1.0)
    db = rcs_to_dbsm(sigma)
    assert db == pytest.approx(10.0 * math.log10(PI), abs=1e-12)
    assert db == pytest.approx(4.9714987, abs=1e-6)
