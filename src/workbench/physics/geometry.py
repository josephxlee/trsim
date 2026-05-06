"""Geometry primitives — coordinate conversions, distance, bearing, AER ↔ ENU.

Phase 1 first primitive module. Pure functions, ``numpy`` / ``math`` only.
No domain or Qt dependency.

Coverage:

- WGS84 ↔ ECEF (Earth-Centered Earth-Fixed)
- ECEF ↔ ENU (East-North-Up, local tangent plane)
- WGS84 ↔ ENU (composition)
- ENU ↔ AER (Azimuth / Elevation / Range)
- 3D Euclidean distance / bearing helpers
- Haversine great-circle distance (sphere approx.)

References:

- WGS84 ellipsoid constants: NIMA TR8350.2 (2000).
- Closed-form ECEF → WGS84: Bowring (1976), Heikkinen (1982). We use the
  Bowring iteration-free form (sufficient for sub-mm at all altitudes used
  in this project — < 100 km).
- ENU convention: x = East, y = North, z = Up (right-handed).
- Azimuth: degrees clockwise from North in the East-North plane. Elevation:
  angle above the horizon. This matches plan/11 § 11.3 and standard radar
  convention (NOT mathematical "phi from x-axis").

All angles are returned in **radians** unless the function name says ``_deg``.
All distances are in **meters**.
"""

from __future__ import annotations

import math
from typing import Final

# ---------------------------------------------------------------------------
# WGS84 ellipsoid constants (NIMA TR8350.2)
# ---------------------------------------------------------------------------

WGS84_A: Final[float] = 6378137.0
"""Semi-major axis [m]."""

WGS84_F: Final[float] = 1.0 / 298.257223563
"""Flattening (dimensionless)."""

WGS84_B: Final[float] = WGS84_A * (1.0 - WGS84_F)
"""Semi-minor axis [m]."""

WGS84_E2: Final[float] = WGS84_F * (2.0 - WGS84_F)
"""First eccentricity squared, e^2 = 2f - f^2."""

WGS84_EP2: Final[float] = WGS84_E2 / (1.0 - WGS84_E2)
"""Second eccentricity squared, e'^2 = e^2 / (1 - e^2)."""


# ---------------------------------------------------------------------------
# WGS84 ↔ ECEF
# ---------------------------------------------------------------------------


def wgs84_to_ecef(lat_deg: float, lon_deg: float, alt_m: float) -> tuple[float, float, float]:
    """Convert WGS84 geodetic ``(lat, lon, alt)`` to ECEF ``(x, y, z)``.

    Args:
        lat_deg: Latitude [°], positive North.
        lon_deg: Longitude [°], positive East.
        alt_m: Height above WGS84 ellipsoid [m].

    Returns:
        ``(x, y, z)`` ECEF Cartesian coordinates [m].
    """
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    x = (n + alt_m) * cos_lat * cos_lon
    y = (n + alt_m) * cos_lat * sin_lon
    z = (n * (1.0 - WGS84_E2) + alt_m) * sin_lat
    return x, y, z


def ecef_to_wgs84(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Convert ECEF ``(x, y, z)`` to WGS84 geodetic ``(lat_deg, lon_deg, alt_m)``.

    Uses the Bowring closed-form (no iteration). Accuracy is sub-millimetre
    for all altitudes used in this project (< 100 km).

    Args:
        x: ECEF X [m].
        y: ECEF Y [m].
        z: ECEF Z [m].

    Returns:
        ``(lat_deg, lon_deg, alt_m)``.
    """
    p = math.sqrt(x * x + y * y)
    lon = math.atan2(y, x)

    # Bowring's auxiliary latitude
    theta = math.atan2(z * WGS84_A, p * WGS84_B)
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    lat = math.atan2(
        z + WGS84_EP2 * WGS84_B * sin_theta * sin_theta * sin_theta,
        p - WGS84_E2 * WGS84_A * cos_theta * cos_theta * cos_theta,
    )
    sin_lat = math.sin(lat)
    n = WGS84_A / math.sqrt(1.0 - WGS84_E2 * sin_lat * sin_lat)
    alt = p / math.cos(lat) - n

    return math.degrees(lat), math.degrees(lon), alt


# ---------------------------------------------------------------------------
# ECEF ↔ ENU
# ---------------------------------------------------------------------------


def ecef_to_enu(
    x: float,
    y: float,
    z: float,
    origin_lat_deg: float,
    origin_lon_deg: float,
    origin_alt_m: float,
) -> tuple[float, float, float]:
    """Convert ECEF point to ENU about a WGS84 origin.

    Args:
        x, y, z: Target point ECEF [m].
        origin_lat_deg, origin_lon_deg, origin_alt_m: Origin in WGS84.

    Returns:
        ``(east, north, up)`` [m].
    """
    ox, oy, oz = wgs84_to_ecef(origin_lat_deg, origin_lon_deg, origin_alt_m)
    dx = x - ox
    dy = y - oy
    dz = z - oz

    lat = math.radians(origin_lat_deg)
    lon = math.radians(origin_lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    east = -sin_lon * dx + cos_lon * dy
    north = -sin_lat * cos_lon * dx - sin_lat * sin_lon * dy + cos_lat * dz
    up = cos_lat * cos_lon * dx + cos_lat * sin_lon * dy + sin_lat * dz
    return east, north, up


def enu_to_ecef(
    east: float,
    north: float,
    up: float,
    origin_lat_deg: float,
    origin_lon_deg: float,
    origin_alt_m: float,
) -> tuple[float, float, float]:
    """Convert ENU vector at an origin to absolute ECEF coordinates.

    Args:
        east, north, up: ENU components [m].
        origin_lat_deg, origin_lon_deg, origin_alt_m: Origin in WGS84.

    Returns:
        ``(x, y, z)`` ECEF [m].
    """
    ox, oy, oz = wgs84_to_ecef(origin_lat_deg, origin_lon_deg, origin_alt_m)

    lat = math.radians(origin_lat_deg)
    lon = math.radians(origin_lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    sin_lon = math.sin(lon)
    cos_lon = math.cos(lon)

    dx = -sin_lon * east - sin_lat * cos_lon * north + cos_lat * cos_lon * up
    dy = cos_lon * east - sin_lat * sin_lon * north + cos_lat * sin_lon * up
    dz = cos_lat * north + sin_lat * up

    return ox + dx, oy + dy, oz + dz


# ---------------------------------------------------------------------------
# WGS84 ↔ ENU (composition)
# ---------------------------------------------------------------------------


def wgs84_to_enu(
    lat_deg: float,
    lon_deg: float,
    alt_m: float,
    origin_lat_deg: float,
    origin_lon_deg: float,
    origin_alt_m: float,
) -> tuple[float, float, float]:
    """Convert WGS84 point to ENU about an origin (composition)."""
    x, y, z = wgs84_to_ecef(lat_deg, lon_deg, alt_m)
    return ecef_to_enu(x, y, z, origin_lat_deg, origin_lon_deg, origin_alt_m)


def enu_to_wgs84(
    east: float,
    north: float,
    up: float,
    origin_lat_deg: float,
    origin_lon_deg: float,
    origin_alt_m: float,
) -> tuple[float, float, float]:
    """Convert ENU vector at an origin to absolute WGS84 (composition)."""
    x, y, z = enu_to_ecef(east, north, up, origin_lat_deg, origin_lon_deg, origin_alt_m)
    return ecef_to_wgs84(x, y, z)


# ---------------------------------------------------------------------------
# ENU ↔ AER (azimuth / elevation / range)
# ---------------------------------------------------------------------------


def enu_to_aer(east: float, north: float, up: float) -> tuple[float, float, float]:
    """Convert an ENU vector to azimuth / elevation / range.

    Azimuth is measured clockwise from North in the horizontal plane —
    the standard radar convention (NOT mathematical phi).

    Args:
        east, north, up: ENU components [m].

    Returns:
        ``(az_rad, el_rad, range_m)``.
        ``az_rad`` is in ``[0, 2π)``; ``el_rad`` in ``[-π/2, π/2]``.
    """
    horizontal = math.hypot(east, north)
    range_m = math.hypot(horizontal, up)
    az_rad = math.atan2(east, north) % (2.0 * math.pi)
    el_rad = math.atan2(up, horizontal) if horizontal > 0.0 or up != 0.0 else 0.0
    return az_rad, el_rad, range_m


def aer_to_enu(az_rad: float, el_rad: float, range_m: float) -> tuple[float, float, float]:
    """Convert azimuth / elevation / range to ENU vector.

    Args:
        az_rad: Azimuth [rad], clockwise from North.
        el_rad: Elevation [rad], above horizon.
        range_m: Slant range [m].

    Returns:
        ``(east, north, up)`` [m].
    """
    cos_el = math.cos(el_rad)
    east = range_m * cos_el * math.sin(az_rad)
    north = range_m * cos_el * math.cos(az_rad)
    up = range_m * math.sin(el_rad)
    return east, north, up


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------


def euclidean_distance_3d(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
) -> float:
    """3D Euclidean distance between two points [m]."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dz = p2[2] - p1[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def haversine_distance_m(
    lat1_deg: float,
    lon1_deg: float,
    lat2_deg: float,
    lon2_deg: float,
    earth_radius_m: float = 6371008.7714,
) -> float:
    """Great-circle distance on a sphere (mean Earth radius) [m].

    Uses the haversine formula. Accuracy ≈ 0.5% (sphere vs ellipsoid).
    For sub-percent accuracy at tracking-radar ranges (< 200 km), this is
    acceptable as a primitive — use ECEF/ENU paths for the main pipeline.

    Args:
        lat1_deg, lon1_deg: Point 1.
        lat2_deg, lon2_deg: Point 2.
        earth_radius_m: Sphere radius [m]. Default = WGS84 mean radius.

    Returns:
        Surface distance [m].
    """
    lat1 = math.radians(lat1_deg)
    lat2 = math.radians(lat2_deg)
    dlat = math.radians(lat2_deg - lat1_deg)
    dlon = math.radians(lon2_deg - lon1_deg)
    sin_dlat_2 = math.sin(dlat / 2.0)
    sin_dlon_2 = math.sin(dlon / 2.0)
    a = sin_dlat_2 * sin_dlat_2 + math.cos(lat1) * math.cos(lat2) * sin_dlon_2 * sin_dlon_2
    c = 2.0 * math.asin(math.sqrt(a))
    return earth_radius_m * c
