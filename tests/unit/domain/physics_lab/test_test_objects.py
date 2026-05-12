"""Test Objects 9 + analytic RCS tests (PL-C, plan/19 § 19.7)."""

from __future__ import annotations

import math

import pytest

from workbench.domain.physics_lab import (
    TEST_OBJECT_KINDS,
    Cone,
    Cube,
    Cylinder,
    Plane,
    Plate,
    Point,
    Sphere,
    Trihedral,
    Wall,
    default_library,
)
from workbench.physics.reflection.rcs_single import (
    cylinder_rcs_broadside_m2,
    flat_plate_rcs_max_m2,
    sphere_rcs_geometric_m2,
    sphere_rcs_rayleigh_m2,
    trihedral_corner_rcs_m2,
)

_X_BAND_LAMBDA_M = 299_792_458.0 / 9.4e9  # ~ 0.03189 m


# ---------------------------------------------------------------------
# Catalogue
# ---------------------------------------------------------------------


def test_test_object_kinds_lists_nine() -> None:
    """The 9 standard kinds from plan/19 § 19.7.1."""
    assert len(TEST_OBJECT_KINDS) == 9
    assert set(TEST_OBJECT_KINDS) == {
        "sphere",
        "cube",
        "plate",
        "cylinder",
        "cone",
        "trihedral",
        "wall",
        "plane",
        "point",
    }


def test_default_library_returns_one_per_kind() -> None:
    library = default_library()
    assert len(library) == 9
    visuals = {obj.visual for obj in library}
    assert visuals == set(TEST_OBJECT_KINDS)


# ---------------------------------------------------------------------
# Sphere
# ---------------------------------------------------------------------


def test_sphere_geometric_regime_matches_pi_r_squared() -> None:
    """Large sphere (a >> lambda) -> geometric optics formula."""
    s = Sphere(name="big_sphere", radius_m=1.0)
    sigma = s.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(sphere_rcs_geometric_m2(1.0))
    assert sigma == pytest.approx(math.pi)


def test_sphere_rayleigh_regime_falls_back_to_rayleigh_formula() -> None:
    """Small sphere (a << lambda) -> Rayleigh formula."""
    s = Sphere(name="tiny_sphere", radius_m=1e-3)
    sigma = s.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = sphere_rcs_rayleigh_m2(1e-3, _X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-9)


def test_sphere_rejects_non_positive_radius() -> None:
    with pytest.raises(ValueError, match=r"radius_m must be > 0"):
        Sphere(name="bad", radius_m=0.0)


def test_sphere_rejects_negative_drag_coefficient() -> None:
    with pytest.raises(ValueError, match=r"drag_coefficient"):
        Sphere(name="bad", radius_m=1.0, drag_coefficient=-1.0)


def test_sphere_rejects_non_positive_wavelength() -> None:
    s = Sphere(name="x", radius_m=1.0)
    with pytest.raises(ValueError, match=r"wavelength_m"):
        s.analytic_rcs_m2(0.0)


# ---------------------------------------------------------------------
# Cube + Plate + Wall (share the plate broadside formula)
# ---------------------------------------------------------------------


def test_cube_broadside_uses_face_area() -> None:
    c = Cube(name="c", side_length_m=0.5)
    sigma = c.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = flat_plate_rcs_max_m2(0.5 * 0.5, _X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-9)


def test_plate_broadside_matches_flat_plate_formula() -> None:
    p = Plate(name="p", width_m=2.0, height_m=1.5)
    sigma = p.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = flat_plate_rcs_max_m2(2.0 * 1.5, _X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-9)


def test_wall_broadside_matches_plate() -> None:
    w = Wall(name="w", width_m=2.0, height_m=1.5)
    sigma = w.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = flat_plate_rcs_max_m2(2.0 * 1.5, _X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-9)


def test_plate_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValueError, match=r"width/height"):
        Plate(name="bad", width_m=0.0, height_m=1.0)


# ---------------------------------------------------------------------
# Cylinder
# ---------------------------------------------------------------------


def test_cylinder_broadside_delegates_to_rcs_single() -> None:
    c = Cylinder(name="c", radius_m=0.1, length_m=2.0)
    sigma = c.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = cylinder_rcs_broadside_m2(radius_m=0.1, length_m=2.0, wavelength_m=_X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-9)


# ---------------------------------------------------------------------
# Cone
# ---------------------------------------------------------------------


def test_cone_tip_on_rcs_matches_knott_formula() -> None:
    """Knott Ch. 6: sigma = (lambda^2 / 16 pi) * tan^4(alpha)."""
    c = Cone(name="c", base_radius_m=0.3, height_m=1.0)
    sigma = c.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    alpha = math.atan2(0.3, 1.0)
    expected = (_X_BAND_LAMBDA_M**2 / (16.0 * math.pi)) * math.tan(alpha) ** 4
    assert sigma == pytest.approx(expected, rel=1e-12)


def test_cone_slender_cone_rcs_is_very_small() -> None:
    """Very slender cone (alpha small) -> RCS << wavelength^2."""
    c = Cone(name="slender", base_radius_m=0.05, height_m=1.0)
    sigma = c.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    assert sigma < _X_BAND_LAMBDA_M**2 * 1e-4


# ---------------------------------------------------------------------
# Trihedral
# ---------------------------------------------------------------------


def test_trihedral_matches_corner_reflector_formula() -> None:
    t = Trihedral(name="t", side_length_m=0.3)
    sigma = t.analytic_rcs_m2(_X_BAND_LAMBDA_M)
    expected = trihedral_corner_rcs_m2(0.3, _X_BAND_LAMBDA_M)
    assert sigma == pytest.approx(expected, rel=1e-12)


# ---------------------------------------------------------------------
# Dynamics-only (no RCS)
# ---------------------------------------------------------------------


def test_point_has_no_analytic_rcs() -> None:
    p = Point(name="p", mass_kg=1.5)
    assert p.analytic_rcs_m2(_X_BAND_LAMBDA_M) is None


def test_plane_has_no_analytic_rcs() -> None:
    p = Plane(name="ground")
    assert p.analytic_rcs_m2(_X_BAND_LAMBDA_M) is None


def test_point_rejects_negative_mass() -> None:
    with pytest.raises(ValueError, match=r"mass_kg"):
        Point(name="bad", mass_kg=-1.0)
