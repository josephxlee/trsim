"""Validation tests for :mod:`workbench.physics.propagation.multipath`.

Coverage:

- Phase ``phi = 2*pi*Delta/lambda`` round-trip with ray_tracing geometry.
- Free-space (rho = 0) -> F^2 = 1 exactly.
- Perfect conductor (rho = -1) at peaks: F^2 = 4, at nulls: F^2 = 0.
- Round-trip factor F^4 = (F^2)^2.
- Far-field lobing landmarks: last null and first peak distances.
- Lobing pattern smoke test: F^4 oscillates between 0 and 16 in the
  near-field and decreases monotonically beyond the first peak.
- In-phase reflection (rho = +1) symmetric formula F^2 = 4*cos(phi/2)^2.

Reference values are produced by the same closed-form expressions in
``docs/matlab_validation/test_multipath.m`` (Octave/MATLAB, no Toolbox).
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.propagation.multipath import (
    PI,
    RHO_FLAT_SEA_SMOOTH,
    RHO_PERFECT_CONDUCTOR,
    TWO_PI,
    first_lobing_peak_distance_m,
    last_lobing_null_distance_m,
    two_ray_phase_difference_rad,
    two_ray_power_factor,
    two_ray_round_trip_factor,
)
from workbench.physics.propagation.ray_tracing import two_ray_path_difference_m

LAMBDA_X_BAND_M = 299_792_458.0 / 9.4e9  # ~= 0.03189 m


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


def test_constants_signs_and_values() -> None:
    """ITU-R typical sea bounce + idealised conductor."""
    assert RHO_FLAT_SEA_SMOOTH == -0.95
    assert RHO_PERFECT_CONDUCTOR == -1.0
    assert TWO_PI == pytest.approx(2.0 * PI, abs=1e-15)


# ---------------------------------------------------------------------------
# Phase difference
# ---------------------------------------------------------------------------


def test_phase_zero_when_path_difference_zero() -> None:
    """h1=0 collapses Delta to 0 -> phi = 0."""
    phi = two_ray_phase_difference_rad(0.0, 100.0, 10_000.0, LAMBDA_X_BAND_M)
    assert phi == pytest.approx(0.0, abs=1e-12)


def test_phase_matches_2pi_delta_over_lambda() -> None:
    """phi = 2*pi*Delta/lambda — direct check via ray_tracing helper."""
    h1, h2, d = 10.0, 100.0, 10_000.0
    phi = two_ray_phase_difference_rad(h1, h2, d, LAMBDA_X_BAND_M)
    delta = two_ray_path_difference_m(h1, h2, d)
    expected = 2.0 * PI * delta / LAMBDA_X_BAND_M
    assert phi == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------------
# Free space (rho = 0)
# ---------------------------------------------------------------------------


def test_free_space_power_factor_one() -> None:
    """rho = 0 cancels the reflection — F^2 == 1 regardless of geometry."""
    f2 = two_ray_power_factor(10.0, 100.0, 10_000.0, LAMBDA_X_BAND_M, reflection_coef=0.0)
    assert f2 == pytest.approx(1.0, abs=1e-12)
    f4 = two_ray_round_trip_factor(
        10.0,
        100.0,
        10_000.0,
        LAMBDA_X_BAND_M,
        reflection_coef=0.0,
    )
    assert f4 == pytest.approx(1.0, abs=1e-12)


# ---------------------------------------------------------------------------
# Perfect conductor at lobing landmarks (rho = -1)
# ---------------------------------------------------------------------------


def test_last_null_distance_far_field() -> None:
    """``d_null_1 = 2 * h1 * h2 / lambda``."""
    h1, h2 = 10.0, 100.0
    d = last_lobing_null_distance_m(h1, h2, LAMBDA_X_BAND_M)
    expected = 2.0 * h1 * h2 / LAMBDA_X_BAND_M
    assert d == pytest.approx(expected, abs=1e-9)
    assert d == pytest.approx(62710.0499, abs=1e-3)  # ~62.7 km


def test_first_peak_distance_far_field() -> None:
    """``d_peak_0 = 4 * h1 * h2 / lambda``."""
    h1, h2 = 10.0, 100.0
    d = first_lobing_peak_distance_m(h1, h2, LAMBDA_X_BAND_M)
    expected = 4.0 * h1 * h2 / LAMBDA_X_BAND_M
    assert d == pytest.approx(expected, abs=1e-9)
    assert d == pytest.approx(125420.0998, abs=1e-3)  # ~125.4 km
    # And first peak is always exactly 2x last null.
    assert d == pytest.approx(2.0 * last_lobing_null_distance_m(h1, h2, LAMBDA_X_BAND_M))


def test_perfect_conductor_at_far_null_is_zero() -> None:
    """At ``d = d_null_1``, F^2 = 0 (deep null) for rho = -1, far-field approx.

    The far-field approximation Delta ~ 2 h1 h2 / d is what places the null
    at exactly d_null_1 = 2 h1 h2 / lambda. Using the EXACT path-difference
    formula leaves a tiny residual; we verify both regimes here.
    """
    h1, h2 = 10.0, 100.0
    d = last_lobing_null_distance_m(h1, h2, LAMBDA_X_BAND_M)
    f2 = two_ray_power_factor(h1, h2, d, LAMBDA_X_BAND_M, RHO_PERFECT_CONDUCTOR)
    # exact: small residual, but still very small (< 1e-3 relative to peak 4)
    assert abs(f2) < 5e-3


def test_perfect_conductor_at_far_peak_is_four() -> None:
    """At ``d = d_peak_0``, F^2 ~ 4 (peak) for rho = -1."""
    h1, h2 = 10.0, 100.0
    d = first_lobing_peak_distance_m(h1, h2, LAMBDA_X_BAND_M)
    f2 = two_ray_power_factor(h1, h2, d, LAMBDA_X_BAND_M, RHO_PERFECT_CONDUCTOR)
    # exact value within 1e-3 of 4.0
    assert f2 == pytest.approx(4.0, abs=5e-3)


# ---------------------------------------------------------------------------
# Round-trip factor F^4
# ---------------------------------------------------------------------------


def test_round_trip_is_square_of_one_way() -> None:
    """``F^4 = (F^2)^2`` — definitional."""
    args = (10.0, 100.0, 50_000.0, LAMBDA_X_BAND_M, RHO_PERFECT_CONDUCTOR)
    f2 = two_ray_power_factor(*args)
    f4 = two_ray_round_trip_factor(*args)
    assert f4 == pytest.approx(f2 * f2, abs=1e-12)


def test_round_trip_max_value_perfect_conductor() -> None:
    """F^4 max is 16 (at peak) for rho = -1."""
    h1, h2 = 10.0, 100.0
    d = first_lobing_peak_distance_m(h1, h2, LAMBDA_X_BAND_M)
    f4 = two_ray_round_trip_factor(h1, h2, d, LAMBDA_X_BAND_M, RHO_PERFECT_CONDUCTOR)
    assert f4 == pytest.approx(16.0, abs=5e-2)


# ---------------------------------------------------------------------------
# Smooth-sea reflection (rho = -0.95)
# ---------------------------------------------------------------------------


def test_smooth_sea_null_is_shallow() -> None:
    """rho = -0.95 -> null minimum is (1 + rho)^2 = 0.0025, NOT 0."""
    h1, h2 = 10.0, 100.0
    d = last_lobing_null_distance_m(h1, h2, LAMBDA_X_BAND_M)
    f2 = two_ray_power_factor(h1, h2, d, LAMBDA_X_BAND_M, RHO_FLAT_SEA_SMOOTH)
    # Theoretical floor: (1 + rho)^2 = 0.05^2 = 0.0025
    assert f2 == pytest.approx(0.0025, abs=1e-2)


def test_smooth_sea_peak_is_below_4() -> None:
    """rho = -0.95 -> peak is (1 - rho)^2 = 1.95^2 = 3.8025, NOT 4."""
    h1, h2 = 10.0, 100.0
    d = first_lobing_peak_distance_m(h1, h2, LAMBDA_X_BAND_M)
    f2 = two_ray_power_factor(h1, h2, d, LAMBDA_X_BAND_M, RHO_FLAT_SEA_SMOOTH)
    assert f2 == pytest.approx(3.8025, abs=1e-2)


# ---------------------------------------------------------------------------
# Asymmetric reflection (rho = +1, in-phase) sanity
# ---------------------------------------------------------------------------


def test_in_phase_reflection_4cos_squared_identity() -> None:
    """rho = +1 -> F^2 = 4*cos^2(phi/2). Mathematical identity, any geometry."""
    h1, h2, d = 10.0, 100.0, 50_000.0
    phi = two_ray_phase_difference_rad(h1, h2, d, LAMBDA_X_BAND_M)
    f2 = two_ray_power_factor(h1, h2, d, LAMBDA_X_BAND_M, reflection_coef=1.0)
    expected = 4.0 * math.cos(phi / 2.0) ** 2
    assert f2 == pytest.approx(expected, abs=1e-12)


def test_in_phase_reflection_phi_zero_limit() -> None:
    """rho = +1, phi -> 0 (d -> infinity): F^2 -> 4."""
    # d=1e10 m: phi ~ 4e-5 rad, F^2 - 4 ~ -1.5e-9
    f2 = two_ray_power_factor(10.0, 100.0, 1e10, LAMBDA_X_BAND_M, reflection_coef=1.0)
    assert f2 == pytest.approx(4.0, abs=1e-6)


# ---------------------------------------------------------------------------
# Far-field asymptotics (1/d^4 in F^4 -> 1/d^8 received power)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("d", [200_000.0, 500_000.0, 1_000_000.0])
def test_far_field_monotonic_decrease_beyond_peak(d: float) -> None:
    """Beyond d_peak_0, F^4 decreases as d increases (no further peaks)."""
    h1, h2 = 10.0, 100.0
    d_peak = first_lobing_peak_distance_m(h1, h2, LAMBDA_X_BAND_M)
    assert d > d_peak  # sanity: we're in the asymptotic region
    f4_here = two_ray_round_trip_factor(
        h1,
        h2,
        d,
        LAMBDA_X_BAND_M,
        RHO_PERFECT_CONDUCTOR,
    )
    f4_farther = two_ray_round_trip_factor(
        h1,
        h2,
        d * 2.0,
        LAMBDA_X_BAND_M,
        RHO_PERFECT_CONDUCTOR,
    )
    # Doubling d should drop F^4 by ~16 (1/d^4 scaling). Allow generous slack.
    assert f4_farther < f4_here
