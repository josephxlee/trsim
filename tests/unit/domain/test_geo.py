"""Unit tests for :mod:`workbench.domain.geo`."""

from __future__ import annotations

import pytest

from workbench.domain.geo import GeoOrigin, VerticalReference, VerticalRefType

# ---------------------------------------------------------------------------
# VerticalRefType enum
# ---------------------------------------------------------------------------


def test_vertical_ref_type_members() -> None:
    """Enum has exactly 4 members per plan/11 § 11.4."""
    members = {m.name for m in VerticalRefType}
    assert members == {"EGM96", "ELLIPSOID_WGS84", "MSL_LOCAL", "UNKNOWN"}


def test_vertical_ref_type_values() -> None:
    """Enum values are stable lowercase strings (TOML-friendly)."""
    assert VerticalRefType.EGM96.value == "egm96"
    assert VerticalRefType.ELLIPSOID_WGS84.value == "ellipsoid_wgs84"
    assert VerticalRefType.MSL_LOCAL.value == "msl_local"
    assert VerticalRefType.UNKNOWN.value == "unknown"


# ---------------------------------------------------------------------------
# VerticalReference dataclass
# ---------------------------------------------------------------------------


def test_vertical_reference_creation_minimal() -> None:
    """Minimal construction uses kind only (description defaults to empty)."""
    vr = VerticalReference(kind=VerticalRefType.EGM96)
    assert vr.kind is VerticalRefType.EGM96
    assert vr.description == ""


def test_vertical_reference_creation_with_description() -> None:
    """Description annotates the source / accuracy."""
    vr = VerticalReference(
        kind=VerticalRefType.MSL_LOCAL,
        description="Inchon mean sea level 1995",
    )
    assert vr.kind is VerticalRefType.MSL_LOCAL
    assert vr.description == "Inchon mean sea level 1995"


def test_vertical_reference_immutable() -> None:
    """frozen=True forbids mutation."""
    vr = VerticalReference(kind=VerticalRefType.EGM96)
    with pytest.raises((AttributeError, TypeError)):
        vr.kind = VerticalRefType.UNKNOWN  # type: ignore[misc]


def test_vertical_reference_equality() -> None:
    """Two VerticalReferences with same kind+description compare equal."""
    a = VerticalReference(kind=VerticalRefType.EGM96, description="a")
    b = VerticalReference(kind=VerticalRefType.EGM96, description="a")
    c = VerticalReference(kind=VerticalRefType.EGM96, description="b")
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# GeoOrigin dataclass
# ---------------------------------------------------------------------------


def test_geo_origin_creation_seoul() -> None:
    """GeoOrigin stores Seoul City Hall coordinates with default EGM96."""
    o = GeoOrigin(lat_deg=37.5665, lon_deg=126.9780, alt_m=50.0)
    assert o.lat_deg == 37.5665
    assert o.lon_deg == 126.9780
    assert o.alt_m == 50.0
    assert o.vertical_ref.kind is VerticalRefType.EGM96
    assert o.vertical_ref.description == ""


def test_geo_origin_creation_explicit_vertical_ref() -> None:
    """Explicit VerticalReference overrides the EGM96 default."""
    vr = VerticalReference(
        kind=VerticalRefType.ELLIPSOID_WGS84,
        description="Raw GPS output",
    )
    o = GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=100.0, vertical_ref=vr)
    assert o.vertical_ref is vr
    assert o.vertical_ref.kind is VerticalRefType.ELLIPSOID_WGS84


def test_geo_origin_immutable() -> None:
    """frozen=True forbids mutation (plan/11 § 11.3.3 — origin invariant)."""
    o = GeoOrigin(lat_deg=37.5665, lon_deg=126.9780, alt_m=0.0)
    with pytest.raises((AttributeError, TypeError)):
        o.lat_deg = 0.0  # type: ignore[misc]


def test_geo_origin_equality() -> None:
    """Two GeoOrigins with identical fields compare equal."""
    a = GeoOrigin(lat_deg=37.0, lon_deg=127.0, alt_m=0.0)
    b = GeoOrigin(lat_deg=37.0, lon_deg=127.0, alt_m=0.0)
    c = GeoOrigin(lat_deg=37.0, lon_deg=127.0, alt_m=1.0)
    assert a == b
    assert a != c


# ---------------------------------------------------------------------------
# GeoOrigin validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lat", [-90.0, -45.0, 0.0, 37.5665, 90.0])
def test_geo_origin_lat_in_range(lat: float) -> None:
    """Latitude is accepted in the closed interval [-90, 90]."""
    o = GeoOrigin(lat_deg=lat, lon_deg=0.0, alt_m=0.0)
    assert o.lat_deg == lat


@pytest.mark.parametrize("lat", [-90.001, 90.001, -180.0, 180.0])
def test_geo_origin_lat_out_of_range_raises(lat: float) -> None:
    """Latitude outside [-90, 90] raises ValueError."""
    with pytest.raises(ValueError, match="lat_deg must be in"):
        GeoOrigin(lat_deg=lat, lon_deg=0.0, alt_m=0.0)


@pytest.mark.parametrize("lon", [-179.99, -90.0, 0.0, 90.0, 180.0])
def test_geo_origin_lon_in_range(lon: float) -> None:
    """Longitude is accepted in the half-open interval (-180, 180]."""
    o = GeoOrigin(lat_deg=0.0, lon_deg=lon, alt_m=0.0)
    assert o.lon_deg == lon


@pytest.mark.parametrize("lon", [-180.0, -180.001, 180.001, 360.0])
def test_geo_origin_lon_out_of_range_raises(lon: float) -> None:
    """Longitude outside (-180, 180] raises ValueError.

    Note ``-180`` is excluded (use ``+180`` for the antimeridian); ``+180``
    is included to keep the interval half-open.
    """
    with pytest.raises(ValueError, match="lon_deg must be in"):
        GeoOrigin(lat_deg=0.0, lon_deg=lon, alt_m=0.0)


def test_geo_origin_altitude_unconstrained() -> None:
    """Altitude has no hard range — DEMs may include negative or high values."""
    GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=-432.0)  # Dead Sea floor
    GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=8848.0)  # Mt. Everest
    GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=400_000.0)  # ISS-ish
