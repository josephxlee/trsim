"""Simulation-domain helpers — Map-aware terrain sampling + domain bounds.

Phase 5.16 introduced :func:`sample_terrain_safe`. The Phase 4 UI cycle
(2026-05-13) adds the :class:`SimulationDomain` dataclass + the
:class:`OutsideEnvironment` enum defined by plan/11 § 11.11.3, which the
Map Editor / Scenario Composer panels surface to the user.

Scope (MVP):

- :func:`sample_terrain_safe` returns the terrain elevation at an
  arbitrary ``(east, north)`` via bilinear interpolation; if the point
  lies outside the map's bounding box, it returns ``None``.
- Sea cells (``land_mask=False`` at the bracketing corners) snap to
  ``map.sea_surface.z_at_sea_m`` instead of the raw elevation grid —
  the Workbench Native Terrain format keeps a synthetic depth below
  ``land_mask=False`` cells (plan/11 § 11.10), and the simulator must
  not pick up that depth as a target altitude.
- :class:`SimulationDomain` describes the outer East/North/altitude
  envelope inside which the simulator is allowed to propagate beams
  and targets. The precise ``Map`` lives inside that envelope; outside
  the map (but inside the domain) the :class:`OutsideEnvironment`
  policy decides how to model the terrain.

Out of scope for the MVP:

- Map ↔ SimulationDomain wiring on :class:`workbench.domain.map_resource.Map`
  — the dataclass is plumbed through Scenario / SimulationContext at a
  later cycle once the Editor flow signals which override is active.
- 3-D outside-environment shapes (the four MVP modes only describe a
  flat outside ground / sea).

References:

- plan/11 § 11.11.3 — ``SimulationDomain`` + ``OutsideEnvironment``
  data model.
- plan/11 § 11.11.7 — Simulation domain definition / Map-vs-domain
  checks.
- plan/11 § 11.10 — Workbench Native Terrain (land_mask semantics).
- plan/14 § 14.5 — Trajectory ⇄ terrain interplay.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

import numpy as np
from numpy.typing import NDArray

from workbench.domain.map_resource import Map, MapBounds


class OutsideEnvironment(StrEnum):
    """Outside-map terrain policy (plan/11 § 11.11.3).

    The Map carries precise terrain; positions outside the Map (but
    inside the :class:`SimulationDomain`) are evaluated against one of
    these simplified models.
    """

    OPEN_SEA = "open_sea"
    OPEN_LAND = "open_land"
    INFINITE_PLANE = "infinite_plane"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class SimulationDomain:
    """Outer East/North/altitude envelope of a scenario (plan/11 § 11.11.3).

    The simulator restricts beam propagation and target dynamics to this
    box; positions that escape the box raise ``OutsideSimulationDomainError``
    at evaluation time. The Map (precise terrain) lives strictly inside
    the domain — :meth:`contains_bounds` enforces that invariant when
    wiring a Map to a domain.

    Attributes:
        bounds_east: ``(east_min_m, east_max_m)`` in the scenario ENU
            frame [m]. ``east_max_m`` must exceed ``east_min_m``.
        bounds_north: ``(north_min_m, north_max_m)`` in the same frame.
        ceiling_alt_m: Upper altitude limit [m] (target ceiling).
        floor_alt_m: Lower altitude limit [m]; negative permits subsea
            sensors / vessels with explicit sub-sea trajectories.

    Raises:
        ValueError: If any axis collapses (max <= min) or
            ``ceiling_alt_m <= floor_alt_m`` or any field is non-finite.
    """

    bounds_east: tuple[float, float]
    bounds_north: tuple[float, float]
    ceiling_alt_m: float = 30000.0
    floor_alt_m: float = -100.0

    def __post_init__(self) -> None:
        e0, e1 = self.bounds_east
        n0, n1 = self.bounds_north
        for name, value in (
            ("bounds_east[0]", e0),
            ("bounds_east[1]", e1),
            ("bounds_north[0]", n0),
            ("bounds_north[1]", n1),
            ("ceiling_alt_m", self.ceiling_alt_m),
            ("floor_alt_m", self.floor_alt_m),
        ):
            if not math.isfinite(float(value)):
                msg = f"{name} must be finite, got {value!r}"
                raise ValueError(msg)
        if e1 <= e0:
            msg = f"bounds_east[1] must exceed bounds_east[0], got {e0} >= {e1}"
            raise ValueError(msg)
        if n1 <= n0:
            msg = f"bounds_north[1] must exceed bounds_north[0], got {n0} >= {n1}"
            raise ValueError(msg)
        if self.ceiling_alt_m <= self.floor_alt_m:
            msg = (
                "ceiling_alt_m must exceed floor_alt_m, got "
                f"{self.floor_alt_m} >= {self.ceiling_alt_m}"
            )
            raise ValueError(msg)

    @property
    def width_m(self) -> float:
        """East-West extent of the domain [m]."""
        return self.bounds_east[1] - self.bounds_east[0]

    @property
    def height_m(self) -> float:
        """North-South extent of the domain [m]."""
        return self.bounds_north[1] - self.bounds_north[0]

    @property
    def diagonal_m(self) -> float:
        """Length of the domain bounding-box diagonal [m]."""
        return math.hypot(self.width_m, self.height_m)

    def contains(
        self,
        east_m: float,
        north_m: float,
        altitude_m: float | None = None,
    ) -> bool:
        """Return True if ``(east, north [, altitude])`` lies inside the box.

        ``altitude_m=None`` skips the altitude check (planar containment).
        """
        if not (self.bounds_east[0] <= east_m <= self.bounds_east[1]):
            return False
        if not (self.bounds_north[0] <= north_m <= self.bounds_north[1]):
            return False
        return altitude_m is None or (self.floor_alt_m <= altitude_m <= self.ceiling_alt_m)

    def contains_bounds(self, map_bounds: MapBounds) -> bool:
        """Return True if every corner of ``map_bounds`` lies inside the domain."""
        return (
            self.bounds_east[0] <= map_bounds.east_min_m
            and map_bounds.east_max_m <= self.bounds_east[1]
            and self.bounds_north[0] <= map_bounds.north_min_m
            and map_bounds.north_max_m <= self.bounds_north[1]
        )

    @classmethod
    def from_map_bounds(
        cls,
        map_bounds: MapBounds,
        *,
        margin_m: float = 0.0,
        ceiling_alt_m: float = 30000.0,
        floor_alt_m: float = -100.0,
    ) -> SimulationDomain:
        """Construct a domain that wraps ``map_bounds`` plus an optional margin.

        Args:
            map_bounds: Map East/North axis-aligned bounding box.
            margin_m: Padding [m] applied symmetrically on each side.
                Must be non-negative.

        Raises:
            ValueError: If ``margin_m`` is negative.
        """
        if not math.isfinite(margin_m) or margin_m < 0.0:
            msg = f"margin_m must be non-negative finite, got {margin_m!r}"
            raise ValueError(msg)
        return cls(
            bounds_east=(
                map_bounds.east_min_m - margin_m,
                map_bounds.east_max_m + margin_m,
            ),
            bounds_north=(
                map_bounds.north_min_m - margin_m,
                map_bounds.north_max_m + margin_m,
            ),
            ceiling_alt_m=ceiling_alt_m,
            floor_alt_m=floor_alt_m,
        )


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
