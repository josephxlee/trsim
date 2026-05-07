"""Ray-tracing primitives — horizon distance, LOS check, two-ray geometry.

Phase 1.4 second propagation primitive. Pure geometric / atmospheric-refraction
relationships. No DEM sampling here — that's Application Layer (plan/02 § 2.5).

References:

- Skolnik, M. (2008). *Radar Handbook*, 3rd ed., Ch. 2 (propagation).
- ITU-R P.834 — effective Earth radius for tropospheric refraction.
- plan/15 § 15.5.4 — Atmospheric refraction (4/3 Earth).
- plan/16 § 16.3.5 — Refraction baseline (Q-BL5 closed).

Conventions:

- Heights ``h_m`` are measured **above the local horizontal tangent plane**
  (or above mean sea level — equivalent for Phase 1 flat-Earth two-ray).
- Ground distance ``d_m`` is the great-circle / surface distance between
  the two points' subpoints.
- The default ``k_factor = 4/3`` models standard atmospheric refraction
  (a downward-curved ray is reinterpreted as straight over a larger
  effective Earth). Set ``k_factor = 1`` for the bare geometric horizon.

All distances in **m**, dimensionless ``k_factor`` is unitless.
"""

from __future__ import annotations

import math
from typing import Final

R_EARTH_MEAN_M: Final[float] = 6_371_008.7714
"""WGS84 mean Earth radius [m]. Matches ``physics.geometry.haversine_distance_m``."""

K_FACTOR_DEFAULT: Final[float] = 4.0 / 3.0
"""Standard atmospheric refraction k-factor (plan/15 § 15.5.4, ITU-R P.834)."""


# ---------------------------------------------------------------------------
# Effective Earth radius and horizon distance
# ---------------------------------------------------------------------------


def effective_earth_radius_m(k_factor: float = K_FACTOR_DEFAULT) -> float:
    """Effective Earth radius ``k · R_E`` for refraction-corrected ray tracing.

    With ``k = 4/3`` (default) the actual curved ray is reinterpreted as a
    straight line over an enlarged Earth (≈ 8,495 km mean radius). This is
    the standard tropospheric "4/3 Earth" approximation.

    Args:
        k_factor: Multiplier for the geometric mean Earth radius.
            Default = 4/3 (standard atmosphere).

    Returns:
        Effective radius [m].
    """
    return k_factor * R_EARTH_MEAN_M


def horizon_distance_m(height_m: float, k_factor: float = K_FACTOR_DEFAULT) -> float:
    """Distance to the radio horizon for an observer at ``height_m``.

    ``d_horizon = sqrt(2 · k · R_E · h)``.

    The ubiquitous rule-of-thumb ``d_km ≈ 4.12 · sqrt(h_m)`` corresponds to
    ``k = 4/3`` with an Earth radius slightly above the mean
    (≈ 6378 km equatorial). Our exact result with the WGS84 mean is
    marginally smaller — see test goldens.

    Args:
        height_m: Observer height above local mean surface [m], must be ≥ 0.
        k_factor: Refraction multiplier. Default = 4/3.

    Returns:
        Horizon distance [m] (always ≥ 0).

    Raises:
        ValueError: If ``height_m < 0``.
    """
    if height_m < 0.0:
        msg = f"height_m must be >= 0, got {height_m}"
        raise ValueError(msg)
    return math.sqrt(2.0 * k_factor * R_EARTH_MEAN_M * height_m)


def radio_horizon_distance_m(
    h1_m: float,
    h2_m: float,
    k_factor: float = K_FACTOR_DEFAULT,
) -> float:
    """Maximum LOS surface distance between two elevated points.

    ``d_max = sqrt(2 · k · R_E · h1) + sqrt(2 · k · R_E · h2)``.

    If the actual ground distance between the subpoints is ≤ this value,
    the LOS clears the Earth's bulge (assuming a smooth spherical surface
    with refraction handled by ``k_factor``).

    Args:
        h1_m: Height of point 1 [m], ≥ 0.
        h2_m: Height of point 2 [m], ≥ 0.
        k_factor: Refraction multiplier.

    Returns:
        Sum of the two horizon distances [m].
    """
    return horizon_distance_m(h1_m, k_factor) + horizon_distance_m(h2_m, k_factor)


def is_above_horizon(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
    k_factor: float = K_FACTOR_DEFAULT,
) -> bool:
    """Boolean LOS check on a smooth spherical Earth.

    True iff ``ground_distance_m`` does not exceed the radio horizon for
    the height pair. **Does not** account for terrain or buildings —
    that requires a DEM (App Layer, plan/02).

    Args:
        h1_m: Height of point 1 [m], ≥ 0.
        h2_m: Height of point 2 [m], ≥ 0.
        ground_distance_m: Surface distance between subpoints [m], ≥ 0.
        k_factor: Refraction multiplier.

    Returns:
        ``True`` if LOS clears the Earth bulge for given heights and distance.
    """
    return ground_distance_m <= radio_horizon_distance_m(h1_m, h2_m, k_factor)


# ---------------------------------------------------------------------------
# Earth bulge — useful for ray-clearance / DEM-aware checks downstream
# ---------------------------------------------------------------------------


def earth_bulge_m(
    distance_from_a_m: float,
    distance_from_b_m: float,
    k_factor: float = K_FACTOR_DEFAULT,
) -> float:
    """Height of Earth's bulge above the chord connecting points A and B.

    ``h_bulge(x) = (d_a · d_b) / (2 · k · R_E)``  where ``x`` is anywhere
    on segment AB, ``d_a = |x - A|``, ``d_b = |x - B|``.

    Maximum at the midpoint: ``d_total² / (8 · k · R_E)``.

    Args:
        distance_from_a_m: Distance from A to evaluation point [m].
        distance_from_b_m: Distance from evaluation point to B [m].
        k_factor: Refraction multiplier.

    Returns:
        Bulge height above the AB chord [m] (always ≥ 0 for non-negative inputs).
    """
    return distance_from_a_m * distance_from_b_m / (2.0 * k_factor * R_EARTH_MEAN_M)


# ---------------------------------------------------------------------------
# Two-ray geometry — flat-Earth direct + image-source reflection
# ---------------------------------------------------------------------------


def direct_path_length_m(h1_m: float, h2_m: float, ground_distance_m: float) -> float:
    """3D Euclidean distance ignoring Earth curvature.

    ``d_direct = sqrt(d² + (h2 - h1)²)``.

    Used by the two-ray multipath model (plan/08 § 8.5b.1, plan/16 § 16.3.1).

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].

    Returns:
        Direct slant range [m].
    """
    return math.hypot(ground_distance_m, h2_m - h1_m)


def two_ray_reflected_path_length_m(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
) -> float:
    """Reflected path length via the image-source method (flat reflector).

    ``d_refl = sqrt(d² + (h1 + h2)²)``.

    The reflected ray is modelled as a straight line from the **mirror image**
    of the transmitter (at depth ``-h1``) to the receiver (at ``+h2``).
    Assumes a horizontal, perfectly specular reflector — appropriate for
    Phase 1 primitives. Sea-state roughness lives in plan/16 multipath.

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].

    Returns:
        Total reflected path length [m].
    """
    return math.hypot(ground_distance_m, h1_m + h2_m)


def two_ray_path_difference_m(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
) -> float:
    """Path-length difference Δ = reflected − direct.

    Used to compute the relative phase of the two-ray contribution.
    For the wavelength λ, the relative phase is ``2π · Δ / λ`` (plus the
    reflection-coefficient phase, typically ``π`` for soft-bounce sea).

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m].

    Returns:
        ``d_reflected − d_direct`` [m].
    """
    return two_ray_reflected_path_length_m(h1_m, h2_m, ground_distance_m) - direct_path_length_m(
        h1_m, h2_m, ground_distance_m,
    )


def two_ray_path_difference_approx_m(
    h1_m: float,
    h2_m: float,
    ground_distance_m: float,
) -> float:
    """Far-field approximation ``Δ ≈ 2 · h1 · h2 / d``.

    Valid when ``d >> h1, h2`` (typical for tracking radar at km-range
    against m-scale heights). Useful for rapid hand checks.

    Args:
        h1_m: Height of point 1 [m].
        h2_m: Height of point 2 [m].
        ground_distance_m: Horizontal distance [m], > 0.

    Returns:
        Approximate path difference [m].
    """
    return 2.0 * h1_m * h2_m / ground_distance_m
