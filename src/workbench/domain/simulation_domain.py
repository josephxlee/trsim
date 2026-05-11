"""Simulation-domain helpers — Map-aware terrain sampling (plan/11 § 11.11.7).

Phase 5.16 — MVP implementation of the bounds-safe terrain sampler that
the simulator and the :mod:`workbench.domain.coherence_validator` need
to evaluate "is this east/north on the map?" without risking IndexError.

Scope (MVP):

- :func:`sample_terrain_safe` returns the terrain elevation at an
  arbitrary ``(east, north)`` via bilinear interpolation; if the point
  lies outside the map's bounding box, it returns ``None``.
- Sea cells (``land_mask=False`` at the bracketing corners) snap to
  ``map.sea_surface.z_at_sea_m`` instead of the raw elevation grid —
  the Workbench Native Terrain format keeps a synthetic depth below
  ``land_mask=False`` cells (plan/11 § 11.10), and the simulator must
  not pick up that depth as a target altitude.

Out of scope for the MVP (plan/11 § 11.11.7 + plan/11 § 11.11.8):

- ``SimulationDomain`` Map-vs-domain containment + ``outside_environment``
  policy: the editor needs them at Phase 7 (DLC packaging); for now the
  caller only needs ``sample_terrain_safe``.
- 3-D containment (no altitude-bounds field on the Map MVP).

References:

- plan/11 § 11.11.7 — Simulation domain definition / Map-vs-domain
  checks.
- plan/11 § 11.10 — Workbench Native Terrain (land_mask semantics).
- plan/14 § 14.5 — Trajectory ⇄ terrain interplay.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from workbench.domain.map_resource import Map


def sample_terrain_safe(
    map_: Map,
    east_m: float,
    north_m: float,
) -> float | None:
    """Return terrain z at ``(east, north)`` or ``None`` if outside bounds.

    Uses bilinear interpolation on the four bracketing grid corners.
    If *any* of those four corners is a sea cell (``land_mask=False``),
    the function returns ``map.sea_surface.z_at_sea_m`` — the elevation
    grid stores synthetic depths below sea cells that the simulator
    should not surface as terrain heights.

    Args:
        map_: Map resource owning the terrain + bounds + sea surface.
        east_m: Query east coordinate [m] in the map's local ENU frame.
        north_m: Query north coordinate [m] in the map's local ENU frame.

    Returns:
        Bilinear terrain elevation [m] when ``(east, north)`` is inside
        ``map.bounds`` and brackets to land cells; the sea-surface z
        when any bracketing corner is a sea cell; ``None`` when the
        query lies outside the bounds.
    """
    b = map_.bounds
    if east_m < b.east_min_m or east_m > b.east_max_m:
        return None
    if north_m < b.north_min_m or north_m > b.north_max_m:
        return None

    terrain = map_.terrain
    g_east = terrain.grid_east_m
    g_north = terrain.grid_north_m

    if east_m < float(g_east[0]) or east_m > float(g_east[-1]):
        return None
    if north_m < float(g_north[0]) or north_m > float(g_north[-1]):
        return None

    # Locate bracketing indices: i0..i0+1 covers east_m, j0..j0+1 covers north_m.
    i0 = _bracket_index(g_east, east_m)
    j0 = _bracket_index(g_north, north_m)
    i1 = min(i0 + 1, g_east.size - 1)
    j1 = min(j0 + 1, g_north.size - 1)

    # Any sea cell among the four corners -> snap to sea-surface z.
    if not (
        terrain.land_mask[j0, i0]
        and terrain.land_mask[j0, i1]
        and terrain.land_mask[j1, i0]
        and terrain.land_mask[j1, i1]
    ):
        return float(map_.sea_surface.z_at_sea_m)

    # Bilinear interpolation. Degenerate axes (i0 == i1 or j0 == j1)
    # collapse to 1-D linear interp or the corner value.
    e0 = float(g_east[i0])
    e1 = float(g_east[i1])
    n0 = float(g_north[j0])
    n1 = float(g_north[j1])
    de = (east_m - e0) / (e1 - e0) if e1 != e0 else 0.0
    dn = (north_m - n0) / (n1 - n0) if n1 != n0 else 0.0
    z00 = float(terrain.elevation_m[j0, i0])
    z01 = float(terrain.elevation_m[j0, i1])
    z10 = float(terrain.elevation_m[j1, i0])
    z11 = float(terrain.elevation_m[j1, i1])
    z_south = z00 * (1.0 - de) + z01 * de
    z_north = z10 * (1.0 - de) + z11 * de
    return z_south * (1.0 - dn) + z_north * dn


def _bracket_index(grid: NDArray[np.float64], value: float) -> int:
    """Return ``i`` such that ``grid[i] <= value <= grid[i+1]`` (clamped)."""
    # np.searchsorted returns the insertion index; subtract 1 to bracket.
    idx = int(np.searchsorted(grid, value, side="right")) - 1
    return max(0, min(idx, int(grid.size) - 2))
