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
