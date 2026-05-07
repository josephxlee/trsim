"""Validation tests for :mod:`workbench.physics.propagation.ray_tracing`.

Coverage:

- Effective Earth radius (default 4/3, alternate values).
- Horizon distance — analytic ``sqrt(2·k·R_E·h)`` for several heights.
- Geometric vs 4/3-Earth horizon (refraction extends LOS).
- Bistatic radio horizon = sum of individual horizons.
- ``is_above_horizon`` boolean cases (clear / blocked / boundary).
- Earth bulge midpoint / quarter-point / endpoints.
- Two-ray geometry: direct, reflected, exact Δ, far-field ≈ 2h₁h₂/d.

Tolerances:

- Distance / length analytic match: 1e-6 m (sub-µm) for IEEE 754 doubles.
- Far-field ≈ check: relative error < 1e-3 when ``d >> h``.
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.propagation.ray_tracing import (
    K_FACTOR_DEFAULT,
    R_EARTH_MEAN_M,
    direct_path_length_m,
    earth_bulge_m,
    effective_earth_radius_m,
    horizon_distance_m,
    is_above_horizon,
    radio_horizon_distance_m,
    two_ray_path_difference_approx_m,
    two_ray_path_difference_m,
    two_ray_reflected_path_length_m,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants_match_expected() -> None:
    """WGS84 mean radius and 4/3 default."""
    assert R_EARTH_MEAN_M == 6_371_008.7714
    assert K_FACTOR_DEFAULT == pytest.approx(4.0 / 3.0)


def test_effective_earth_radius_default() -> None:
    """4/3 Earth radius ≈ 8,494,678.36 m."""
    expected = 4.0 / 3.0 * 6_371_008.7714
    assert effective_earth_radius_m() == pytest.approx(expected, abs=1e-6)
    assert effective_earth_radius_m() == pytest.approx(8494678.3619, abs=1e-3)


def test_effective_earth_radius_geometric() -> None:
    """k=1 returns the bare mean Earth radius."""
    assert effective_earth_radius_m(k_factor=1.0) == R_EARTH_MEAN_M


# ---------------------------------------------------------------------------
# Horizon distance — analytic formula and edge cases
# ---------------------------------------------------------------------------


def test_horizon_distance_zero_height() -> None:
    """At h=0 the horizon is at the observer."""
    assert horizon_distance_m(0.0) == 0.0


def test_horizon_distance_negative_raises() -> None:
    """Negative height is rejected."""
    with pytest.raises(ValueError, match="height_m must be"):
        horizon_distance_m(-1.0)


def test_horizon_distance_100m_4_3_earth() -> None:
    """h=100 m, k=4/3 → ~41,219 m. Standard tropospheric horizon."""
    d = horizon_distance_m(100.0)
    expected = math.sqrt(2.0 * (4.0 / 3.0) * R_EARTH_MEAN_M * 100.0)
    assert d == pytest.approx(expected, abs=1e-6)
    assert d == pytest.approx(41219.36, abs=1.0)


def test_horizon_distance_100m_geometric() -> None:
    """h=100 m, k=1 → ~35,696 m. Bare geometric horizon (no refraction)."""
    d = horizon_distance_m(100.0, k_factor=1.0)
    expected = math.sqrt(2.0 * 1.0 * R_EARTH_MEAN_M * 100.0)
    assert d == pytest.approx(expected, abs=1e-6)
    assert d == pytest.approx(35696.40, abs=1.0)


def test_horizon_distance_refraction_extends() -> None:
    """k=4/3 horizon is farther than k=1 horizon (refraction bends rays down)."""
    h = 50.0
    assert horizon_distance_m(h, k_factor=4.0 / 3.0) > horizon_distance_m(h, k_factor=1.0)


@pytest.mark.parametrize(
    ("height_m", "expected_km_4_3"),
    [
        (1.0, 4.122),  # 1 m → ~4.12 km
        (10.0, 13.037),  # 10 m → ~13.04 km
        (100.0, 41.219),  # 100 m → ~41.22 km
        (1000.0, 130.366),  # 1 km → ~130.4 km
        (10_000.0, 412.255),  # 10 km → ~412 km
    ],
)
def test_horizon_distance_table(height_m: float, expected_km_4_3: float) -> None:
    """Tabulated horizon distances for k=4/3."""
    d_km = horizon_distance_m(height_m) / 1000.0
    assert d_km == pytest.approx(expected_km_4_3, abs=0.01)


# ---------------------------------------------------------------------------
# Bistatic / radio horizon
# ---------------------------------------------------------------------------


def test_radio_horizon_is_sum() -> None:
    """``radio_horizon = horizon(h1) + horizon(h2)``."""
    h1, h2 = 10.0, 100.0
    expected = horizon_distance_m(h1) + horizon_distance_m(h2)
    assert radio_horizon_distance_m(h1, h2) == pytest.approx(expected, abs=1e-9)


def test_radio_horizon_symmetric() -> None:
    """Order of arguments doesn't matter."""
    a = radio_horizon_distance_m(10.0, 100.0)
    b = radio_horizon_distance_m(100.0, 10.0)
    assert a == pytest.approx(b, abs=1e-9)


# ---------------------------------------------------------------------------
# is_above_horizon
# ---------------------------------------------------------------------------


def test_is_above_horizon_clear() -> None:
    """Within radio horizon → LOS clear."""
    assert is_above_horizon(h1_m=100.0, h2_m=100.0, ground_distance_m=10_000.0) is True


def test_is_above_horizon_blocked() -> None:
    """Beyond radio horizon → LOS blocked."""
    assert is_above_horizon(h1_m=10.0, h2_m=10.0, ground_distance_m=200_000.0) is False


def test_is_above_horizon_boundary_inclusive() -> None:
    """Exactly at horizon is treated as clear (≤)."""
    radio_h = radio_horizon_distance_m(10.0, 100.0)
    assert is_above_horizon(10.0, 100.0, radio_h) is True


# ---------------------------------------------------------------------------
# Earth bulge
# ---------------------------------------------------------------------------


def test_earth_bulge_zero_at_endpoints() -> None:
    """At an endpoint (d_a=0 or d_b=0) the bulge is zero."""
    assert earth_bulge_m(0.0, 5000.0) == 0.0
    assert earth_bulge_m(5000.0, 0.0) == 0.0


def test_earth_bulge_midpoint_10km_4_3_earth() -> None:
    """10 km segment, midpoint, k=4/3 → ~1.471 m bulge.

    h_bulge_max = d² / (8·k·R_E) = (10_000)² / (8 · 4/3 · 6_371_008.77)
                = 1.4714... m
    """
    bulge = earth_bulge_m(distance_from_a_m=5000.0, distance_from_b_m=5000.0)
    expected = (10_000.0**2) / (8.0 * (4.0 / 3.0) * R_EARTH_MEAN_M)
    assert bulge == pytest.approx(expected, abs=1e-9)
    assert bulge == pytest.approx(1.4714, abs=1e-3)


def test_earth_bulge_geometric_larger() -> None:
    """k=1 (no refraction) gives more bulge than k=4/3."""
    refracted = earth_bulge_m(5000.0, 5000.0, k_factor=4.0 / 3.0)
    geometric = earth_bulge_m(5000.0, 5000.0, k_factor=1.0)
    assert geometric > refracted


# ---------------------------------------------------------------------------
# Two-ray geometry
# ---------------------------------------------------------------------------


def test_direct_path_pythagorean() -> None:
    """``d_direct = sqrt(d² + (h2-h1)²)``."""
    # 3-4-5 triangle: d=4, dh=3 → direct=5
    assert direct_path_length_m(0.0, 3.0, 4.0) == pytest.approx(5.0, abs=1e-12)


def test_direct_path_same_height_equals_ground() -> None:
    """Same-height points → direct == ground distance."""
    assert direct_path_length_m(50.0, 50.0, 1000.0) == pytest.approx(1000.0, abs=1e-12)


def test_reflected_path_uses_image_source() -> None:
    """``d_refl = sqrt(d² + (h1+h2)²)``."""
    # h1+h2 = 100, d = 100 → refl = sqrt(2)*100 ≈ 141.42
    assert two_ray_reflected_path_length_m(40.0, 60.0, 100.0) == pytest.approx(
        math.sqrt(20_000.0), abs=1e-12,
    )


def test_path_difference_exact_vs_approx_far_field() -> None:
    """When d >> h₁,h₂ the exact Δ matches the 2h₁h₂/d approximation."""
    h1, h2 = 10.0, 100.0
    d = 50_000.0  # 50 km — far field for these heights
    exact = two_ray_path_difference_m(h1, h2, d)
    approx = two_ray_path_difference_approx_m(h1, h2, d)
    assert exact == pytest.approx(approx, rel=1e-3)


def test_path_difference_far_field_value() -> None:
    """``Δ ≈ 2·10·100 / 10_000 = 0.2 m`` for typical sea-bounce setup."""
    approx = two_ray_path_difference_approx_m(10.0, 100.0, 10_000.0)
    assert approx == pytest.approx(0.2, abs=1e-12)


def test_path_difference_zero_when_one_height_zero() -> None:
    """One height = 0 → no reflected geometry advantage; Δ collapses.

    With h1=0: direct = sqrt(d² + h2²) = reflected = sqrt(d² + h2²) → Δ = 0.
    """
    assert two_ray_path_difference_m(0.0, 100.0, 10_000.0) == pytest.approx(0.0, abs=1e-12)
    assert two_ray_path_difference_approx_m(0.0, 100.0, 10_000.0) == 0.0
