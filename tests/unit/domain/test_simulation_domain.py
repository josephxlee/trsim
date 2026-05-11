"""sample_terrain_safe tests (Phase 5.16)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.domain.geo import GeoOrigin
from workbench.domain.map_resource import Map, MapBounds, SeaSurface, WorkbenchTerrain
from workbench.domain.simulation_domain import sample_terrain_safe


def _flat_land_map(
    elevation: float = 100.0,
    sea_surface_z: float = 0.0,
    *,
    sea_corner: tuple[int, int] | None = None,
) -> Map:
    """3x3 grid spanning E=[0,200], N=[0,200]; default all-land flat 100m."""
    g_east = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    g_north = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    elev = np.full((3, 3), elevation, dtype=np.float64)
    land = np.ones((3, 3), dtype=np.bool_)
    if sea_corner is not None:
        j, i = sea_corner
        elev[j, i] = sea_surface_z - 50.0  # synthetic depth under sea cell
        land[j, i] = False
    terrain = WorkbenchTerrain(
        grid_east_m=g_east,
        grid_north_m=g_north,
        elevation_m=elev,
        land_mask=land,
        resolution_m=100.0,
    )
    return Map(
        map_id="flat_test",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=127.0, alt_m=0.0),
        bounds=MapBounds(0.0, 200.0, 0.0, 200.0),
        terrain=terrain,
        sea_surface=SeaSurface(z_at_sea_m=sea_surface_z),
    )


def _sloped_land_map() -> Map:
    """3x3 grid where elevation rises linearly with east (0 -> 200 m)."""
    g_east = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    g_north = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    # elevation[j, i] = g_east[i] (slope east-bound)
    elev = np.tile(g_east[np.newaxis, :], (3, 1))
    land = np.ones((3, 3), dtype=np.bool_)
    terrain = WorkbenchTerrain(
        grid_east_m=g_east,
        grid_north_m=g_north,
        elevation_m=elev,
        land_mask=land,
        resolution_m=100.0,
    )
    return Map(
        map_id="slope_test",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=127.0, alt_m=0.0),
        bounds=MapBounds(0.0, 200.0, 0.0, 200.0),
        terrain=terrain,
    )


# ---------------------------------------------------------------------
# Inside / outside bounds
# ---------------------------------------------------------------------


def test_inside_bounds_flat_terrain_returns_elevation() -> None:
    m = _flat_land_map(elevation=87.0)
    assert sample_terrain_safe(m, 50.0, 50.0) == pytest.approx(87.0, abs=1e-12)


def test_outside_bounds_east_returns_none() -> None:
    m = _flat_land_map()
    assert sample_terrain_safe(m, 250.0, 100.0) is None


def test_outside_bounds_north_returns_none() -> None:
    m = _flat_land_map()
    assert sample_terrain_safe(m, 100.0, -10.0) is None


def test_on_boundary_returns_elevation() -> None:
    """Sampling at the bounds edges is inside, not outside."""
    m = _flat_land_map(elevation=42.0)
    assert sample_terrain_safe(m, 0.0, 0.0) == pytest.approx(42.0, abs=1e-12)
    assert sample_terrain_safe(m, 200.0, 200.0) == pytest.approx(42.0, abs=1e-12)


# ---------------------------------------------------------------------
# Bilinear interpolation
# ---------------------------------------------------------------------


def test_bilinear_interp_at_grid_corner_returns_corner_value() -> None:
    m = _sloped_land_map()
    # corner (e=100, n=100) -> elevation = 100 m
    assert sample_terrain_safe(m, 100.0, 100.0) == pytest.approx(100.0, abs=1e-12)


def test_bilinear_interp_midcell_returns_midpoint_elevation() -> None:
    """Cell (e=0..100, n=0..100) with sloped elev e -> midpoint e=50,
    n=50 yields elevation = 50 m (east-axis slope, north invariant).
    """
    m = _sloped_land_map()
    assert sample_terrain_safe(m, 50.0, 50.0) == pytest.approx(50.0, abs=1e-12)


def test_bilinear_interp_is_linear_in_east() -> None:
    """On the sloped map, elevation must equal the east coordinate
    along the whole 0..200 range (within the same north line).
    """
    m = _sloped_land_map()
    for e in (12.5, 73.0, 150.0, 199.0):
        assert sample_terrain_safe(m, e, 100.0) == pytest.approx(e, abs=1e-12)


# ---------------------------------------------------------------------
# Sea-cell snapping
# ---------------------------------------------------------------------


def test_sea_corner_snaps_to_sea_surface_z() -> None:
    """If any bracketing corner is sea (land_mask=False), the returned
    z is sea_surface.z_at_sea_m, not the raw elevation grid value.
    """
    m = _flat_land_map(elevation=100.0, sea_surface_z=0.0, sea_corner=(0, 0))
    # Query inside the cell that brackets (0,0) — must snap to 0 m
    # (the cell's raw elevation has a synthetic -50 m depth).
    got = sample_terrain_safe(m, 30.0, 30.0)
    assert got == pytest.approx(0.0, abs=1e-12)


def test_far_from_sea_corner_keeps_land_elevation() -> None:
    """Sea cell at (0,0); a query in the bottom-right cell (i0=1,j0=1)
    has no sea corner -> regular land bilinear.
    """
    m = _flat_land_map(elevation=100.0, sea_surface_z=0.0, sea_corner=(0, 0))
    assert sample_terrain_safe(m, 150.0, 150.0) == pytest.approx(100.0, abs=1e-12)
