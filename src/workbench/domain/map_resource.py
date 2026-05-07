"""Map resource dataclasses — bounds, sea surface, native terrain, Map.

Phase 2.2 first dataclasses for the Map resource (plan/03 § 3.2.1c,
plan/11 § 11.10). The Workbench Native Terrain format (v0.22) replaces
direct DEM samples with an explicit ``land_mask`` so sub-aerial pixels
under water never leak negative depths into the simulation.

References:

- plan/03 § 3.2.1c — Scenario / Map / WorkbenchTerrain dataclasses.
- plan/11 § 11.10 — Workbench Native Map Format (v0.22).
- plan/12 § 12.5 — Wave response (environment vs entity split).

Design notes:

- :class:`WorkbenchTerrain` holds **numpy** grids; we mark the ``setflags
  write=False`` in ``__post_init__`` so the standard "treat as immutable"
  contract holds even though numpy arrays are technically mutable.
- ``frozen=True, slots=True`` everywhere — replacing fields after
  construction is forbidden (raises ``FrozenInstanceError``).
- Domain layer never imports Qt or visualisation libraries.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from numpy.typing import NDArray

from workbench.domain.geo import GeoOrigin


@dataclass(frozen=True, slots=True)
class MapBounds:
    """East-North axis-aligned bounding box of the Map's terrain.

    All four coordinates are in the Map's local ENU frame (m), measured
    against the :class:`workbench.domain.geo.GeoOrigin`.

    Raises:
        ValueError: If max <= min on either axis.
    """

    east_min_m: float
    east_max_m: float
    north_min_m: float
    north_max_m: float

    def __post_init__(self) -> None:
        if self.east_max_m <= self.east_min_m:
            msg = f"east_max_m must exceed east_min_m, got {self.east_min_m} >= {self.east_max_m}"
            raise ValueError(msg)
        if self.north_max_m <= self.north_min_m:
            msg = (
                f"north_max_m must exceed north_min_m, got {self.north_min_m} >= {self.north_max_m}"
            )
            raise ValueError(msg)

    @property
    def width_m(self) -> float:
        """East-West extent [m]."""
        return self.east_max_m - self.east_min_m

    @property
    def height_m(self) -> float:
        """North-South extent [m]."""
        return self.north_max_m - self.north_min_m


@dataclass(frozen=True, slots=True)
class SeaSurface:
    """Local sea surface model (plan/12 § 12.5).

    Attributes:
        z_at_sea_m: Nominal sea-level z [m] in the Map's vertical reference.
        sea_state: WMO sea-state index (0 = calm, 9 = phenomenal).
        wave_amplitude_m: Mean half-amplitude of surface waves [m].
        wave_period_s: Dominant wave period [s].
    """

    z_at_sea_m: float = 0.0
    sea_state: int = 3
    wave_amplitude_m: float = 0.5
    wave_period_s: float = 5.0

    def __post_init__(self) -> None:
        if not 0 <= self.sea_state <= 9:
            msg = f"sea_state must be in [0, 9] (WMO), got {self.sea_state}"
            raise ValueError(msg)
        if self.wave_amplitude_m < 0.0:
            msg = f"wave_amplitude_m must be >= 0, got {self.wave_amplitude_m}"
            raise ValueError(msg)
        if self.wave_period_s <= 0.0:
            msg = f"wave_period_s must be > 0, got {self.wave_period_s}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class WorkbenchTerrain:
    """Workbench Native Terrain (plan/11 § 11.10, v0.22).

    A regular grid in the Map's ENU frame. Each ``(north_idx, east_idx)``
    cell carries an ``elevation_m`` value and a ``land_mask`` boolean.
    ``land_mask=False`` means the cell is sea — the simulation must use
    :class:`SeaSurface` ``z_at_sea_m`` instead of ``elevation_m`` there.

    Attributes:
        grid_east_m: 1-D array of ``E`` East-axis sample positions [m].
        grid_north_m: 1-D array of ``N`` North-axis sample positions [m].
        elevation_m: 2-D ``(N, E)`` array of sampled elevations [m].
        land_mask: 2-D ``(N, E)`` boolean — ``True`` = land, ``False`` = sea.
        resolution_m: Nominal grid spacing [m] (informational; the grid
            arrays are authoritative).
        source_dem_hash: Hex digest of the source DEM file. Empty string
            for synthetic / test terrain.

    Raises:
        ValueError: If the array shapes are inconsistent with each other
            or with ``grid_east_m`` / ``grid_north_m``.

    Notes:
        We call ``setflags(write=False)`` on each array in ``__post_init__``
        so that the "treat as immutable" contract holds at the numpy level
        too. Construction time is the only place arrays may be mutated.
    """

    grid_east_m: NDArray[np.float64]
    grid_north_m: NDArray[np.float64]
    elevation_m: NDArray[np.float64]
    land_mask: NDArray[np.bool_]
    resolution_m: float
    source_dem_hash: str = ""

    def __post_init__(self) -> None:
        if self.grid_east_m.ndim != 1:
            msg = f"grid_east_m must be 1-D, got ndim={self.grid_east_m.ndim}"
            raise ValueError(msg)
        if self.grid_north_m.ndim != 1:
            msg = f"grid_north_m must be 1-D, got ndim={self.grid_north_m.ndim}"
            raise ValueError(msg)
        if self.elevation_m.ndim != 2:
            msg = f"elevation_m must be 2-D, got ndim={self.elevation_m.ndim}"
            raise ValueError(msg)
        if self.land_mask.ndim != 2:
            msg = f"land_mask must be 2-D, got ndim={self.land_mask.ndim}"
            raise ValueError(msg)

        expected_shape = (self.grid_north_m.size, self.grid_east_m.size)
        if self.elevation_m.shape != expected_shape:
            msg = (
                f"elevation_m.shape {self.elevation_m.shape} does not match "
                f"(len(grid_north_m), len(grid_east_m)) = {expected_shape}"
            )
            raise ValueError(msg)
        if self.land_mask.shape != expected_shape:
            msg = (
                f"land_mask.shape {self.land_mask.shape} does not match "
                f"elevation_m.shape {expected_shape}"
            )
            raise ValueError(msg)
        if self.resolution_m <= 0.0:
            msg = f"resolution_m must be > 0, got {self.resolution_m}"
            raise ValueError(msg)

        # Lock arrays as read-only (defence-in-depth for the immutable contract).
        self.grid_east_m.setflags(write=False)
        self.grid_north_m.setflags(write=False)
        self.elevation_m.setflags(write=False)
        self.land_mask.setflags(write=False)


@dataclass(frozen=True, slots=True)
class Map:
    """Top-level Map resource (plan/03 § 3.2.1c).

    Combines a :class:`GeoOrigin` (the absolute anchor), a :class:`MapBounds`
    (the rectangular extent in the local ENU frame), a :class:`WorkbenchTerrain`
    (the elevation + land/sea grid), and a :class:`SeaSurface` (water model
    used wherever ``land_mask=False``).

    Attributes:
        map_id: Stable identifier (e.g. ``"east_coast_50km"``); used by
            scenario references and content hashing.
        geo_origin: WGS84 anchor for the Map's ENU frame.
        bounds: ENU-frame bounding box of the terrain.
        terrain: Workbench Native Terrain grid.
        sea_surface: Sea-level model used by sea cells of the terrain.
        content_hash: SHA-256 hex digest covering the Map's persisted
            content (TOML + npz). Empty string for newly constructed Maps.
    """

    map_id: str
    geo_origin: GeoOrigin
    bounds: MapBounds
    terrain: WorkbenchTerrain
    sea_surface: SeaSurface = field(default_factory=SeaSurface)
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.map_id:
            msg = "map_id must be a non-empty string"
            raise ValueError(msg)
