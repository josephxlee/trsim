"""Unit tests for :mod:`workbench.domain.map_resource`."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.domain.geo import GeoOrigin
from workbench.domain.map_resource import (
    Map,
    MapBounds,
    SeaSurface,
    WorkbenchTerrain,
)


def _sample_terrain(n_north: int = 3, n_east: int = 4) -> WorkbenchTerrain:
    """Helper: build a 3x4 terrain grid with a half-sea / half-land mask."""
    east = np.linspace(0.0, 300.0, n_east, dtype=np.float64)
    north = np.linspace(0.0, 200.0, n_north, dtype=np.float64)
    elevation = np.zeros((n_north, n_east), dtype=np.float64)
    elevation[1, :] = 5.0
    elevation[2, :] = 10.0
    land_mask = np.ones((n_north, n_east), dtype=np.bool_)
    land_mask[0, :] = False  # bottom row = sea
    return WorkbenchTerrain(
        grid_east_m=east,
        grid_north_m=north,
        elevation_m=elevation,
        land_mask=land_mask,
        resolution_m=100.0,
    )


# ---------------------------------------------------------------------------
# MapBounds
# ---------------------------------------------------------------------------


def test_map_bounds_creation() -> None:
    """MapBounds stores east/north min/max correctly."""
    b = MapBounds(east_min_m=0.0, east_max_m=10_000.0, north_min_m=0.0, north_max_m=5_000.0)
    assert b.width_m == pytest.approx(10_000.0)
    assert b.height_m == pytest.approx(5_000.0)


def test_map_bounds_immutable() -> None:
    """MapBounds is frozen."""
    b = MapBounds(0.0, 100.0, 0.0, 100.0)
    with pytest.raises((AttributeError, TypeError)):
        b.east_max_m = 200.0  # type: ignore[misc]


def test_map_bounds_east_inverted_raises() -> None:
    """east_max <= east_min raises ValueError."""
    with pytest.raises(ValueError, match="east_max_m must exceed"):
        MapBounds(east_min_m=10.0, east_max_m=10.0, north_min_m=0.0, north_max_m=100.0)


def test_map_bounds_north_inverted_raises() -> None:
    """north_max <= north_min raises ValueError."""
    with pytest.raises(ValueError, match="north_max_m must exceed"):
        MapBounds(east_min_m=0.0, east_max_m=100.0, north_min_m=50.0, north_max_m=10.0)


# ---------------------------------------------------------------------------
# SeaSurface
# ---------------------------------------------------------------------------


def test_sea_surface_defaults() -> None:
    """Default SeaSurface uses sea_state=3, z=0, amplitude=0.5, period=5s."""
    s = SeaSurface()
    assert s.z_at_sea_m == 0.0
    assert s.sea_state == 3
    assert s.wave_amplitude_m == 0.5
    assert s.wave_period_s == 5.0


def test_sea_surface_immutable() -> None:
    """SeaSurface is frozen."""
    s = SeaSurface()
    with pytest.raises((AttributeError, TypeError)):
        s.sea_state = 7  # type: ignore[misc]


@pytest.mark.parametrize("invalid_sea_state", [-1, 10, 100])
def test_sea_surface_invalid_sea_state(invalid_sea_state: int) -> None:
    """Sea state outside [0, 9] raises ValueError."""
    with pytest.raises(ValueError, match="sea_state must be in"):
        SeaSurface(sea_state=invalid_sea_state)


def test_sea_surface_negative_amplitude_raises() -> None:
    """Negative wave amplitude raises ValueError."""
    with pytest.raises(ValueError, match="wave_amplitude_m"):
        SeaSurface(wave_amplitude_m=-0.1)


def test_sea_surface_zero_period_raises() -> None:
    """Zero or negative wave period raises ValueError."""
    with pytest.raises(ValueError, match="wave_period_s"):
        SeaSurface(wave_period_s=0.0)


# ---------------------------------------------------------------------------
# WorkbenchTerrain
# ---------------------------------------------------------------------------


def test_terrain_creation() -> None:
    """3x4 terrain stores grid arrays + elevation + mask correctly."""
    t = _sample_terrain()
    assert t.elevation_m.shape == (3, 4)
    assert t.land_mask.shape == (3, 4)
    assert t.resolution_m == 100.0


def test_terrain_arrays_become_readonly() -> None:
    """__post_init__ marks ndarrays as read-only (immutable contract)."""
    t = _sample_terrain()
    with pytest.raises(ValueError, match=r"read-only|assignment destination"):
        t.elevation_m[0, 0] = 999.0
    with pytest.raises(ValueError, match=r"read-only|assignment destination"):
        t.land_mask[0, 0] = True


def test_terrain_mask_distinguishes_land_sea() -> None:
    """land_mask=True for land, False for sea — sample terrain has half each."""
    t = _sample_terrain()
    assert bool(t.land_mask[0, 0]) is False  # sea row
    assert bool(t.land_mask[2, 3]) is True  # land row


def test_terrain_shape_mismatch_raises() -> None:
    """elevation_m shape inconsistent with grid arrays raises."""
    east = np.linspace(0.0, 100.0, 5, dtype=np.float64)  # 5 columns
    north = np.linspace(0.0, 100.0, 3, dtype=np.float64)  # 3 rows
    bad_elevation = np.zeros((3, 4), dtype=np.float64)  # wrong shape (3, 4) vs (3, 5)
    land_mask = np.ones((3, 4), dtype=np.bool_)
    with pytest.raises(ValueError, match=r"elevation_m\.shape"):
        WorkbenchTerrain(
            grid_east_m=east,
            grid_north_m=north,
            elevation_m=bad_elevation,
            land_mask=land_mask,
            resolution_m=25.0,
        )


def test_terrain_mask_shape_mismatch_raises() -> None:
    """land_mask shape != elevation_m shape raises."""
    east = np.linspace(0.0, 100.0, 4, dtype=np.float64)
    north = np.linspace(0.0, 100.0, 3, dtype=np.float64)
    elevation = np.zeros((3, 4), dtype=np.float64)
    bad_mask = np.ones((4, 4), dtype=np.bool_)
    with pytest.raises(ValueError, match=r"land_mask\.shape"):
        WorkbenchTerrain(
            grid_east_m=east,
            grid_north_m=north,
            elevation_m=elevation,
            land_mask=bad_mask,
            resolution_m=33.0,
        )


def test_terrain_zero_resolution_raises() -> None:
    """Non-positive resolution_m raises."""
    east = np.linspace(0.0, 100.0, 4, dtype=np.float64)
    north = np.linspace(0.0, 100.0, 3, dtype=np.float64)
    elevation = np.zeros((3, 4), dtype=np.float64)
    mask = np.ones((3, 4), dtype=np.bool_)
    with pytest.raises(ValueError, match="resolution_m"):
        WorkbenchTerrain(
            grid_east_m=east,
            grid_north_m=north,
            elevation_m=elevation,
            land_mask=mask,
            resolution_m=0.0,
        )


# ---------------------------------------------------------------------------
# Map (top-level resource)
# ---------------------------------------------------------------------------


def test_map_creation() -> None:
    """Map combines GeoOrigin, MapBounds, terrain, default SeaSurface."""
    origin = GeoOrigin(lat_deg=37.5665, lon_deg=126.9780, alt_m=0.0)
    bounds = MapBounds(
        east_min_m=0.0,
        east_max_m=10_000.0,
        north_min_m=0.0,
        north_max_m=10_000.0,
    )
    terrain = _sample_terrain()
    m = Map(
        map_id="east_coast_50km",
        geo_origin=origin,
        bounds=bounds,
        terrain=terrain,
    )
    assert m.map_id == "east_coast_50km"
    assert m.geo_origin is origin
    assert m.bounds.width_m == 10_000.0
    assert isinstance(m.sea_surface, SeaSurface)  # default applied
    assert m.content_hash == ""


def test_map_immutable() -> None:
    """Map is frozen — cannot replace map_id."""
    origin = GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=0.0)
    bounds = MapBounds(0.0, 100.0, 0.0, 100.0)
    m = Map(map_id="x", geo_origin=origin, bounds=bounds, terrain=_sample_terrain())
    with pytest.raises((AttributeError, TypeError)):
        m.map_id = "y"  # type: ignore[misc]


def test_map_empty_id_raises() -> None:
    """Empty map_id is rejected."""
    origin = GeoOrigin(lat_deg=0.0, lon_deg=0.0, alt_m=0.0)
    bounds = MapBounds(0.0, 100.0, 0.0, 100.0)
    with pytest.raises(ValueError, match="map_id"):
        Map(
            map_id="",
            geo_origin=origin,
            bounds=bounds,
            terrain=_sample_terrain(),
        )
