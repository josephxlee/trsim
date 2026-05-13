"""Planar-array element-power regression (Phase 5.7)."""

from __future__ import annotations

import math
from itertools import pairwise

import pytest

from workbench.physics.planar_array import element_power

_RTOL = 1e-12


@pytest.mark.parametrize("theta", [0.0, 30.0, 60.0, 90.0, 120.0])
@pytest.mark.parametrize("phi", [0.0, 30.0])
def test_isotropic_returns_unity_everywhere(theta: float, phi: float) -> None:
    assert element_power(theta_az_deg=theta, phi_el_deg=phi, kind="isotropic") == 1.0


def test_cos_at_boresight_is_unity() -> None:
    assert element_power(0.0, 0.0, kind="cos") == pytest.approx(1.0, rel=_RTOL)


@pytest.mark.parametrize(
    ("theta_deg", "expected"),
    [
        (30.0, math.cos(math.radians(30.0))),
        (45.0, math.cos(math.radians(45.0))),
        (60.0, 0.5),
        (89.999, math.cos(math.radians(89.999))),
    ],
)
def test_cos_matches_pure_cos_below_90(theta_deg: float, expected: float) -> None:
    p = element_power(theta_az_deg=theta_deg, phi_el_deg=0.0, kind="cos")
    assert p == pytest.approx(expected, rel=1e-10, abs=1e-12)


@pytest.mark.parametrize("theta_deg", [90.0, 90.1, 120.0, 179.0])
def test_cos_zero_at_or_beyond_90deg_back_hemisphere(theta_deg: float) -> None:
    assert element_power(theta_az_deg=theta_deg, phi_el_deg=0.0, kind="cos") == 0.0


def test_cos_uses_off_axis_angle_via_hypot() -> None:
    """element_power should depend on sqrt(theta^2 + phi^2), not theta alone."""
    p_axial = element_power(theta_az_deg=30.0, phi_el_deg=0.0, kind="cos")
    p_diag = element_power(
        theta_az_deg=30.0 / math.sqrt(2.0),
        phi_el_deg=30.0 / math.sqrt(2.0),
        kind="cos",
    )
    assert p_axial == pytest.approx(p_diag, rel=_RTOL)


def test_unknown_element_kind_rejected() -> None:
    with pytest.raises(ValueError, match=r"element_pattern kind"):
        element_power(theta_az_deg=0.0, phi_el_deg=0.0, kind="wizard")


def test_cos_is_non_increasing_with_off_axis() -> None:
    """Off-axis angle larger -> power not greater (concavity sanity)."""
    angles = [0.0, 10.0, 20.0, 30.0, 45.0, 60.0, 89.0]
    powers = [element_power(a, 0.0, kind="cos") for a in angles]
    for prev, curr in pairwise(powers):
        assert curr <= prev + 1e-12


# ---------- 5.7b — sign / quadrant symmetry + boundary lock ----------


@pytest.mark.parametrize("theta_deg", [10.0, 30.0, 60.0, 89.0])
def test_cos_symmetric_in_theta_sign(theta_deg: float) -> None:
    """element_power depends on |theta| via hypot, so flipping sign
    must leave the value invariant.
    """
    p_pos = element_power(theta_az_deg=theta_deg, phi_el_deg=0.0, kind="cos")
    p_neg = element_power(theta_az_deg=-theta_deg, phi_el_deg=0.0, kind="cos")
    assert p_pos == pytest.approx(p_neg, rel=_RTOL)


@pytest.mark.parametrize("phi_deg", [10.0, 30.0, 60.0, 89.0])
def test_cos_symmetric_in_phi_sign(phi_deg: float) -> None:
    """Mirror of the theta-sign test on the elevation axis."""
    p_pos = element_power(theta_az_deg=0.0, phi_el_deg=phi_deg, kind="cos")
    p_neg = element_power(theta_az_deg=0.0, phi_el_deg=-phi_deg, kind="cos")
    assert p_pos == pytest.approx(p_neg, rel=_RTOL)


def test_cos_four_quadrant_hypot_equivalence() -> None:
    """Four (theta, phi) points sharing the same |hypot(theta, phi)|
    (one per quadrant) must all return the same element_power. Pins
    the radial dependence beyond the single-axis sign tests above.
    """
    r_deg = 30.0
    samples = [
        (r_deg, 0.0),
        (-r_deg, 0.0),
        (0.0, r_deg),
        (0.0, -r_deg),
        (r_deg / math.sqrt(2.0), r_deg / math.sqrt(2.0)),
        (-r_deg / math.sqrt(2.0), -r_deg / math.sqrt(2.0)),
    ]
    values = [element_power(t, p, kind="cos") for t, p in samples]
    reference = values[0]
    for v in values[1:]:
        assert v == pytest.approx(reference, rel=_RTOL)


def test_cos_boundary_at_exactly_90_deg_is_zero_not_small() -> None:
    """Discontinuity check: 89.999° returns a tiny positive value, but
    exactly 90.0° clamps to a hard 0.0 (the back-hemisphere cut-off).
    """
    p_almost = element_power(theta_az_deg=89.999, phi_el_deg=0.0, kind="cos")
    p_at_boundary = element_power(theta_az_deg=90.0, phi_el_deg=0.0, kind="cos")
    assert p_almost > 0.0
    assert p_at_boundary == 0.0


def test_isotropic_independent_of_large_phi() -> None:
    """Isotropic element pattern is angle-independent even at the
    front-vs-back boundary (no back-hemisphere clamp applies).
    """
    for phi in (-179.0, -90.0, -45.0, 0.0, 45.0, 90.0, 179.0):
        assert element_power(theta_az_deg=0.0, phi_el_deg=phi, kind="isotropic") == 1.0
