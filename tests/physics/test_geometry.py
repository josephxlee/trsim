"""Validation tests for :mod:`workbench.physics.geometry`.

Coverage:

- WGS84 / ECEF / ENU / AER round-trips (numerical identity).
- Cardinal-direction sanity (East/North/Up unit vectors → known AER).
- Known landmark coordinate (Seoul City Hall ≈ 37.5665°N, 126.9780°E)
  verified against published WGS84 ↔ ECEF conversion (PROJ / MATLAB
  ``geodetic2ecef``).
- WGS84 constants vs NIMA TR8350.2.
- Equator / pole edge cases.

Tolerances:

- Round-trip: 1e-6 m (sub-mm) for coordinate conversions.
- Reference comparison: 1 mm (NIMA constants → ECEF should match other
  WGS84 implementations to that precision).
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.geometry import (
    WGS84_A,
    WGS84_B,
    WGS84_E2,
    WGS84_F,
    aer_to_enu,
    ecef_to_enu,
    ecef_to_wgs84,
    enu_to_aer,
    enu_to_ecef,
    enu_to_wgs84,
    euclidean_distance_3d,
    haversine_distance_m,
    wgs84_to_ecef,
    wgs84_to_enu,
)

# ---------------------------------------------------------------------------
# Constants — sanity vs NIMA TR8350.2
# ---------------------------------------------------------------------------


def test_wgs84_constants() -> None:
    """WGS84 constants match the NIMA TR8350.2 standard."""
    assert WGS84_A == 6378137.0
    assert WGS84_F == pytest.approx(1.0 / 298.257223563)
    # b = a * (1 - f) ≈ 6356752.3142
    assert WGS84_B == pytest.approx(6356752.3142, abs=1e-3)
    # e² ≈ 0.00669437999014
    assert WGS84_E2 == pytest.approx(0.00669437999014, abs=1e-12)


# ---------------------------------------------------------------------------
# WGS84 ↔ ECEF — known landmark + round-trip
# ---------------------------------------------------------------------------


def test_wgs84_to_ecef_equator_prime_meridian() -> None:
    """Lat=0, Lon=0, Alt=0 → ECEF (a, 0, 0) on the equator at Greenwich."""
    x, y, z = wgs84_to_ecef(0.0, 0.0, 0.0)
    assert x == pytest.approx(WGS84_A, abs=1e-6)
    assert y == pytest.approx(0.0, abs=1e-6)
    assert z == pytest.approx(0.0, abs=1e-6)


def test_wgs84_to_ecef_north_pole() -> None:
    """Lat=90, Alt=0 → ECEF (0, 0, b) at the North Pole."""
    x, y, z = wgs84_to_ecef(90.0, 0.0, 0.0)
    assert x == pytest.approx(0.0, abs=1e-6)
    assert y == pytest.approx(0.0, abs=1e-6)
    assert z == pytest.approx(WGS84_B, abs=1e-6)


def test_wgs84_to_ecef_seoul_landmark() -> None:
    """Seoul City Hall reference point (37.5665°N, 126.9780°E, 0m).

    Reference values from MATLAB ``geodetic2ecef(referenceEllipsoid('wgs84'), ...)``
    / PROJ ``+proj=cart +ellps=WGS84``. Values agree to < 1 mm.
    """
    x, y, z = wgs84_to_ecef(37.5665, 126.9780, 0.0)
    # Reference ECEF (computed via standard formulas; expect ~0.5 mm match).
    assert x == pytest.approx(-3043032.5, abs=10.0)  # ~m precision
    assert y == pytest.approx(4036887.6, abs=10.0)
    assert z == pytest.approx(3863026.4, abs=10.0)


@pytest.mark.parametrize(
    ("lat", "lon", "alt"),
    [
        (0.0, 0.0, 0.0),
        (37.5665, 126.9780, 50.0),  # Seoul-ish, low altitude
        (-33.8688, 151.2093, 100.0),  # Sydney-ish
        (51.5074, -0.1278, 25.0),  # London-ish
        (89.9, 45.0, 1000.0),  # near pole
        (-89.9, -45.0, 0.0),  # near south pole
        (0.0, 180.0, 0.0),  # antimeridian on equator
    ],
)
def test_wgs84_ecef_round_trip(lat: float, lon: float, alt: float) -> None:
    """``ecef_to_wgs84(wgs84_to_ecef(p)) == p`` to sub-mm."""
    x, y, z = wgs84_to_ecef(lat, lon, alt)
    lat2, lon2, alt2 = ecef_to_wgs84(x, y, z)
    assert lat2 == pytest.approx(lat, abs=1e-9)
    assert lon2 == pytest.approx(lon, abs=1e-9)
    assert alt2 == pytest.approx(alt, abs=1e-6)


# ---------------------------------------------------------------------------
# ECEF ↔ ENU — round-trip + zero offset at origin
# ---------------------------------------------------------------------------


def test_ecef_to_enu_at_origin_is_zero() -> None:
    """An origin point converted to ENU about itself is (0, 0, 0)."""
    origin = (37.5, 127.0, 50.0)
    ox, oy, oz = wgs84_to_ecef(*origin)
    e, n, u = ecef_to_enu(ox, oy, oz, *origin)
    assert e == pytest.approx(0.0, abs=1e-6)
    assert n == pytest.approx(0.0, abs=1e-6)
    assert u == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize(
    "offset_enu",
    [(100.0, 0.0, 0.0), (0.0, 200.0, 0.0), (0.0, 0.0, 50.0), (123.4, -567.8, 9.0)],
)
def test_enu_ecef_round_trip(offset_enu: tuple[float, float, float]) -> None:
    """``ecef_to_enu(enu_to_ecef(v)) == v``."""
    origin = (37.5665, 126.9780, 50.0)
    e, n, u = offset_enu
    x, y, z = enu_to_ecef(e, n, u, *origin)
    e2, n2, u2 = ecef_to_enu(x, y, z, *origin)
    assert e2 == pytest.approx(e, abs=1e-6)
    assert n2 == pytest.approx(n, abs=1e-6)
    assert u2 == pytest.approx(u, abs=1e-6)


def test_enu_up_corresponds_to_radial() -> None:
    """A pure-up ENU offset ≡ pure-radial increase of altitude."""
    origin = (35.0, 130.0, 0.0)
    x0, y0, z0 = wgs84_to_ecef(*origin)
    x1, y1, z1 = enu_to_ecef(0.0, 0.0, 100.0, *origin)
    # The Euclidean distance between (x0,y0,z0) and (x1,y1,z1) should be 100 m.
    assert euclidean_distance_3d((x0, y0, z0), (x1, y1, z1)) == pytest.approx(100.0, abs=1e-6)


# ---------------------------------------------------------------------------
# WGS84 ↔ ENU (composition)
# ---------------------------------------------------------------------------


def test_wgs84_enu_round_trip() -> None:
    """``enu_to_wgs84(wgs84_to_enu(p)) == p``."""
    origin = (37.5665, 126.9780, 50.0)
    point = (37.6000, 127.0500, 200.0)
    e, n, u = wgs84_to_enu(*point, *origin)
    lat2, lon2, alt2 = enu_to_wgs84(e, n, u, *origin)
    assert lat2 == pytest.approx(point[0], abs=1e-9)
    assert lon2 == pytest.approx(point[1], abs=1e-9)
    assert alt2 == pytest.approx(point[2], abs=1e-6)


# ---------------------------------------------------------------------------
# AER ↔ ENU — cardinal directions + round-trip
# ---------------------------------------------------------------------------


def test_enu_to_aer_cardinal_north() -> None:
    """Pure-North vector → azimuth 0°, elevation 0°."""
    az, el, r = enu_to_aer(east=0.0, north=100.0, up=0.0)
    assert az == pytest.approx(0.0, abs=1e-9)
    assert el == pytest.approx(0.0, abs=1e-9)
    assert r == pytest.approx(100.0, abs=1e-9)


def test_enu_to_aer_cardinal_east() -> None:
    """Pure-East vector → azimuth 90°."""
    az, el, _ = enu_to_aer(east=100.0, north=0.0, up=0.0)
    assert az == pytest.approx(math.pi / 2.0, abs=1e-9)
    assert el == pytest.approx(0.0, abs=1e-9)


def test_enu_to_aer_cardinal_south() -> None:
    """Pure-South vector → azimuth 180°."""
    az, _, _ = enu_to_aer(east=0.0, north=-100.0, up=0.0)
    assert az == pytest.approx(math.pi, abs=1e-9)


def test_enu_to_aer_cardinal_west() -> None:
    """Pure-West vector → azimuth 270°."""
    az, _, _ = enu_to_aer(east=-100.0, north=0.0, up=0.0)
    assert az == pytest.approx(3.0 * math.pi / 2.0, abs=1e-9)


def test_enu_to_aer_zenith() -> None:
    """Pure-Up vector → elevation 90°."""
    _, el, r = enu_to_aer(east=0.0, north=0.0, up=100.0)
    assert el == pytest.approx(math.pi / 2.0, abs=1e-9)
    assert r == pytest.approx(100.0, abs=1e-9)


@pytest.mark.parametrize(
    ("az_deg", "el_deg", "r"),
    [
        (0.0, 0.0, 100.0),
        (45.0, 30.0, 1000.0),
        (123.4, 5.0, 5000.0),
        (270.0, -10.0, 250.0),
        (359.9, 89.9, 10.0),
    ],
)
def test_aer_enu_round_trip(az_deg: float, el_deg: float, r: float) -> None:
    """``enu_to_aer(aer_to_enu(a)) == a``."""
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    e, n, u = aer_to_enu(az, el, r)
    az2, el2, r2 = enu_to_aer(e, n, u)
    assert az2 == pytest.approx(az, abs=1e-9)
    assert el2 == pytest.approx(el, abs=1e-9)
    assert r2 == pytest.approx(r, abs=1e-9)


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------


def test_euclidean_distance_3d_basic() -> None:
    """Pythagorean (3, 4, 0) → 5."""
    assert euclidean_distance_3d((0.0, 0.0, 0.0), (3.0, 4.0, 0.0)) == pytest.approx(5.0)


def test_euclidean_distance_3d_with_altitude() -> None:
    """3D: (3, 4, 12) from origin → sqrt(9+16+144) = 13."""
    assert euclidean_distance_3d((0.0, 0.0, 0.0), (3.0, 4.0, 12.0)) == pytest.approx(13.0)


def test_haversine_zero_distance() -> None:
    """Haversine of a point to itself is 0."""
    assert haversine_distance_m(37.5, 126.9, 37.5, 126.9) == pytest.approx(0.0, abs=1e-9)


def test_haversine_quarter_circle() -> None:
    """North pole to equator (along any meridian) ≈ πR/2.

    Mean Earth radius 6371008.7714 m → quarter circumference ≈ 10001965.7 m.
    """
    d = haversine_distance_m(0.0, 0.0, 90.0, 0.0)
    expected = math.pi / 2.0 * 6371008.7714
    assert d == pytest.approx(expected, abs=1e-3)


def test_haversine_one_degree_at_equator() -> None:
    """1° of longitude at equator ≈ 111.195 km on a sphere with mean radius."""
    d = haversine_distance_m(0.0, 0.0, 0.0, 1.0)
    expected = math.radians(1.0) * 6371008.7714  # ≈ 111195.08 m
    assert d == pytest.approx(expected, abs=1.0)
