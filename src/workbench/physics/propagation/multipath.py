"""Two-ray multipath RF primitives — phase, reflection, lobing power factor.

Phase 1.6 — closes the v0.34 baseline reinforcement (plan/16 § 16.3.1,
plan/08 § 8.5b.1, Q-BL1). Builds on the path-length geometry from
:mod:`workbench.physics.propagation.ray_tracing`.

References:

- Skolnik, M. (2008). *Radar Handbook*, 3rd ed., Ch. 26 (sea reflection).
- Mahafza, B. (2013). *Radar Systems Analysis*, Ch. 14 (multipath).
- Barton, D. (2013). *Radar Equations for Modern Radar*, Ch. 4.
- ITU-R P.527 — electrical characteristics of the surface of the Earth.

Convention (sign of reflection coefficient):

- A negative ``rho`` encodes the **pi reflection phase** for soft-bounce
  reflection at low grazing angles over a sea or smooth surface.
  ``rho = -1`` is the idealised perfect conductor.
- For X-band horizontal polarisation over flat sea at low grazing,
  ``rho`` magnitude is typically 0.85 .. 0.97 (sea state dependent);
  the sign is conventionally negative in the formulas below.

Two-ray power factor (one-way, voltage):

    F = | 1 + rho * exp(i * phi) |
    F^2 = 1 + rho^2 + 2 * rho * cos(phi)
    phi = 2*pi*Delta / lambda  (path-difference phase, no reflection phase added)

For ``rho = -1`` this simplifies via cos(phi) <-> -cos identities to:

    F^2 = 4 * sin(phi/2)^2 = 4 * sin(pi * Delta / lambda)^2

The round-trip factor in the radar equation is ``F^4 = (F^2)^2`` (one F^2
on outbound, one on the return).

Far-field lobing (uses ``Delta ~ 2 h1 h2 / d``):

- nulls (rho = -1): ``2*h1*h2 / d = n*lambda``, n = 1, 2, 3, ...
    -> the **largest-d** null sits at ``d_null_1 = 2*h1*h2 / lambda``
- peaks (rho = -1): ``2*h1*h2 / d = (n + 1/2) * lambda``
    -> the **largest-d** peak sits at ``d_peak_0 = 4*h1*h2 / lambda``
- For ``d > d_peak_0`` no further peaks: F^4 falls monotonically as
  ``1/d^4``, so the round-trip return falls as ``1/d^8`` instead of
  the free-space ``1/d^4`` — the classic "fourth-power loss law" for
  low-altitude over-water tracking.
"""

from __future__ import annotations

import math
from typing import Final

from workbench.physics.propagation.ray_tracing import two_ray_path_difference_m

PI: Final[float] = math.pi
TWO_PI: Final[float] = 2.0 * math.pi

RHO_FLAT_SEA_SMOOTH: Final[float] = -0.95
"""Reflection coefficient for low-grazing X-band over smooth sea (ITU-R P.527 typical)."""

RHO_PERFECT_CONDUCTOR: Final[float] = -1.0
"""Idealised perfect conductor (used for analytic null/peak verification)."""


# ---------------------------------------------------------------------------
# Phase difference between the two rays
# ---------------------------------------------------------------------------


def two_ray_phase_difference_rad(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
    wavelength_m: float,
) -> float:
    """Path-difference phase ``phi = 2*pi*Delta / lambda`` [rad].

    Excludes the reflection-coefficient phase (which is built into the
    sign of ``rho`` in the power-factor functions below).

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Phase ``phi`` [rad] (always >= 0 for non-negative geometry).
    """
    delta = two_ray_path_difference_m(h1_m, h2_m, ground_distance_m)
    return TWO_PI * delta / wavelength_m


# ---------------------------------------------------------------------------
# Combined power factors
# ---------------------------------------------------------------------------


def two_ray_power_factor(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
    wavelength_m: float,
    reflection_coef: float = RHO_FLAT_SEA_SMOOTH,
) -> float:
    """One-way coherent superposition factor ``F^2``.

    ``F^2 = |1 + rho * exp(i*phi)|^2 = 1 + rho^2 + 2 * rho * cos(phi)``.

    For ``rho = 0`` (no surface reflection) this is exactly 1 — free space.
    For ``rho = -1`` and ``phi = 2*pi*n``, ``F^2 = 0`` (deep null).
    For ``rho = -1`` and ``phi = (2n+1)*pi``, ``F^2 = 4`` (peak; +6 dB).

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].
        wavelength_m: Radar wavelength [m].
        reflection_coef: Surface reflection coefficient ``rho`` (signed).

    Returns:
        One-way power factor ``F^2`` (dimensionless, range 0 .. 4 for |rho|=1).
    """
    phi = two_ray_phase_difference_rad(h1_m, h2_m, ground_distance_m, wavelength_m)
    return 1.0 + reflection_coef * reflection_coef + 2.0 * reflection_coef * math.cos(phi)


def two_ray_round_trip_factor(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
    wavelength_m: float,
    reflection_coef: float = RHO_FLAT_SEA_SMOOTH,
) -> float:
    """Round-trip multipath factor ``F^4`` for the radar equation.

    The transmit and receive paths each pick up a one-way ``F^2``, so the
    received echo power is multiplied by ``F^4 = (F^2)^2`` relative to the
    free-space case.

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].
        wavelength_m: Radar wavelength [m].
        reflection_coef: ``rho`` (signed).

    Returns:
        Round-trip factor ``F^4`` (range 0 .. 16 for |rho|=1).
    """
    f2 = two_ray_power_factor(
        h1_m,
        h2_m,
        ground_distance_m,
        wavelength_m,
        reflection_coef,
    )
    return f2 * f2


# ---------------------------------------------------------------------------
# Far-field lobing landmarks (rho = -1 idealisation)
# ---------------------------------------------------------------------------


def last_lobing_null_distance_m(
    h1_m: float,
    h2_m: float,
    wavelength_m: float,
) -> float:
    """Largest-d null in the far-field lobing pattern (rho = -1 limit).

    ``d_null_1 = 2 * h1 * h2 / lambda``.

    Beyond this distance no further nulls appear; ``F^4`` decays
    monotonically as ``1/d^4`` (-> ``1/d^8`` two-way received power).

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Distance [m] of the farthest-out null.
    """
    return 2.0 * h1_m * h2_m / wavelength_m


def first_lobing_peak_distance_m(
    h1_m: float,
    h2_m: float,
    wavelength_m: float,
) -> float:
    """Largest-d peak in the far-field lobing pattern (rho = -1 limit).

    ``d_peak_0 = 4 * h1 * h2 / lambda``.

    Sits between the last null and infinity. ``F^4`` reaches its
    asymptotic peak value of 16 here.

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Distance [m] of the farthest-out peak.
    """
    return 4.0 * h1_m * h2_m / wavelength_m
