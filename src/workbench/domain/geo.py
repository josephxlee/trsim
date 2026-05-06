"""Geographic origin and vertical reference dataclasses.

The Map's :class:`GeoOrigin` defines the single anchor point for a Workspace's
ENU frame. Per plan/01 (불변 원칙) and plan/11 § 11.3.3, the origin is
immutable across a Workspace's lifetime — changing it requires "Save As New".

The :class:`VerticalReference` records the vertical datum (geoid/ellipsoid/local
MSL) so that DEM imports and altitude values are unambiguous (plan/11 § 11.4).

This module is pure data — no physics or coordinate math. Conversions and
distance calculations live in :mod:`workbench.physics.geometry`.

References:

- plan/03 § 3.2.1c — Map & Workbench Native Terrain (GeoOrigin in Map).
- plan/11 § 11.3 — WGS84 + ENU; § 11.4 — Vertical Reference.
- NIMA TR8350.2 — WGS84 ellipsoid (referenced by physics/geometry).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class VerticalRefType(Enum):
    """Vertical datum kind (plan/11 § 11.4).

    Members:
        EGM96: Earth Gravitational Model 1996 geoid — mean sea level.
            Default recommendation for AWS/SRTM/USGS DEMs (plan/11 § 11.4.4).
        ELLIPSOID_WGS84: Heights above the WGS84 ellipsoid (geocentric).
            Used by raw GPS output and most ECEF-based pipelines.
        MSL_LOCAL: A regional/local mean sea level definition.
            Used by some tide-gauge-aligned datasets.
        UNKNOWN: Datum not specified by the source. Editor must prompt
            the user before importing a DEM with this kind.
    """

    EGM96 = "egm96"
    ELLIPSOID_WGS84 = "ellipsoid_wgs84"
    MSL_LOCAL = "msl_local"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class VerticalReference:
    """Vertical datum specification.

    Attributes:
        kind: Which datum (see :class:`VerticalRefType`).
        description: Optional free-text annotation — source citation, accuracy
            estimate, or local geoid model name (e.g., "EGM2008 1' grid",
            "Inchon mean sea level 1995").
    """

    kind: VerticalRefType
    description: str = ""


@dataclass(frozen=True, slots=True)
class GeoOrigin:
    """Single absolute anchor for a Workspace's ENU frame (plan/11 § 11.3).

    The Map's GeoOrigin is **immutable** for the Workspace's lifetime.
    Changing it requires saving as a new Map (plan/11 § 11.3.3).

    All ENU coordinates in this Workspace are measured relative to this
    origin. The :mod:`workbench.physics.geometry` functions take the origin's
    ``(lat, lon, alt)`` tuple and convert other WGS84/ECEF points to ENU.

    Attributes:
        lat_deg: Latitude [°], positive North. Range ``[-90, 90]``.
        lon_deg: Longitude [°], positive East. Range ``(-180, 180]``.
        alt_m: Height [m], measured against ``vertical_ref``.
        vertical_ref: Vertical datum interpretation for ``alt_m``.

    Raises:
        ValueError: If ``lat_deg`` is outside ``[-90, 90]`` or ``lon_deg``
            is outside ``(-180, 180]``.
    """

    lat_deg: float
    lon_deg: float
    alt_m: float
    vertical_ref: VerticalReference = field(
        default_factory=lambda: VerticalReference(kind=VerticalRefType.EGM96),
    )

    def __post_init__(self) -> None:
        if not -90.0 <= self.lat_deg <= 90.0:
            msg = f"lat_deg must be in [-90, 90], got {self.lat_deg}"
            raise ValueError(msg)
        if not -180.0 < self.lon_deg <= 180.0:
            msg = f"lon_deg must be in (-180, 180], got {self.lon_deg}"
            raise ValueError(msg)
