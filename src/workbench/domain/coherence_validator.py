"""Coherence validator — cross-resource consistency checks (plan/11 § 11.7).

Phase 5.15 — MVP implementation of the validator block defined in
plan/11 § 11.7 / § 11.11.7. The Editor / Simulator pipelines call these
functions when resources change so that geometry-vs-content mismatches
surface as warnings before a Run starts (plan/13 § 13.8.3).

Scope (MVP, plan/11 § 11.7.2):

- Map: terrain grid lies inside the bounds; sea cells have an elevation
  at or below the sea surface; the map has at least some land or some
  sea (an empty terrain class is reported as INFO).
- Targets: every waypoint lies inside the map bounds; aircraft / powered
  flight / ballistic waypoints sit above the local terrain; surface
  vessel / floating static waypoints sit close to the sea surface.
- Buildings: every building base lies inside the map bounds.

Out of scope for the MVP (deferred to plan/11 § 11.7.2 MVP+alpha):

- Vertical-reference round-trip warnings (the Map class does not yet
  carry a `vertical_reference` field).
- Per-anchor-mode building checks (plan/12 § 12.8 — needs the runtime
  terrain sampler the simulator owns).
- Coastline-vs-sea-surface consistency (no coastline structure yet).

References:

- plan/11 § 11.7 — Coherence Validator definition.
- plan/11 § 11.11.7 — Simulation domain check (lives in
  :mod:`workbench.domain.simulation_domain`).
- plan/13 § 13.8.3 — When the validator runs (Editor save / Simulator
  transition).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workbench.domain.building import BuildingEntity
from workbench.domain.map_resource import Map
from workbench.domain.placement import MotionKind
from workbench.domain.simulation_domain import sample_terrain_safe
from workbench.domain.target import TargetEntity


class ValidatorSeverity(Enum):
    """Severity rung for a single coherence message (plan/11 § 11.7.3).

    The simulator's Run-gate uses ``ERROR`` as the block condition.
    ``WARN`` is surfaced in the UI but does not block. ``INFO`` is
    diagnostic only.
    """

    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ValidatorMessage:
    """One coherence message produced by a validator function.

    Attributes:
        severity: :class:`ValidatorSeverity` rung.
        code: Stable machine-readable identifier (e.g.
            ``"map.sea_cell_above_surface"``). Editor uses this to
            de-duplicate messages across consecutive runs.
        message: Human-readable description, free-form.
    """

    severity: ValidatorSeverity
    code: str
    message: str


# ---------------------------------------------------------------------
# Map coherence
# ---------------------------------------------------------------------


def validate_map(map_: Map) -> tuple[ValidatorMessage, ...]:
    """Return coherence messages for a single :class:`Map`.

    Three checks (plan/11 § 11.7.2 MVP):

    1. The terrain grid lies inside ``map.bounds`` (rejects an
       inconsistency between the terrain extent and the declared
       bounds).
    2. Sea cells (``land_mask=False``) carry an elevation at or below
       ``sea_surface.z_at_sea_m`` — a sea cell above the sea level is
       a content mistake.
    3. The terrain has at least one land cell *or* at least one sea
       cell (an all-NaN / all-masked terrain is reported as INFO).

    Args:
        map_: Map resource to inspect.

    Returns:
        Tuple of :class:`ValidatorMessage`. Empty tuple = clean map.
    """
    messages: list[ValidatorMessage] = []

    # Check 1: terrain grid lies inside bounds.
    g_east = map_.terrain.grid_east_m
    g_north = map_.terrain.grid_north_m
    b = map_.bounds
    if float(g_east.min()) < b.east_min_m - 1e-6 or float(g_east.max()) > b.east_max_m + 1e-6:
        messages.append(
            ValidatorMessage(
                ValidatorSeverity.ERROR,
                "map.terrain_east_outside_bounds",
                (
                    f"terrain east extent [{float(g_east.min())}, {float(g_east.max())}] "
                    f"leaves bounds [{b.east_min_m}, {b.east_max_m}]"
                ),
            )
        )
    if float(g_north.min()) < b.north_min_m - 1e-6 or float(g_north.max()) > b.north_max_m + 1e-6:
        messages.append(
            ValidatorMessage(
                ValidatorSeverity.ERROR,
                "map.terrain_north_outside_bounds",
                (
                    f"terrain north extent [{float(g_north.min())}, {float(g_north.max())}] "
                    f"leaves bounds [{b.north_min_m}, {b.north_max_m}]"
                ),
            )
        )

    # Check 2: sea cells must not sit above the sea surface.
    sea_mask = ~map_.terrain.land_mask
    if bool(sea_mask.any()):
        sea_elev_max = float(map_.terrain.elevation_m[sea_mask].max())
        if sea_elev_max > map_.sea_surface.z_at_sea_m + 1e-6:
            messages.append(
                ValidatorMessage(
                    ValidatorSeverity.WARN,
                    "map.sea_cell_above_surface",
                    (
                        f"sea cell elevation {sea_elev_max} m exceeds "
                        f"sea_surface.z_at_sea_m {map_.sea_surface.z_at_sea_m} m"
                    ),
                )
            )

    # Check 3: terrain has only land or only sea.
    if not bool(map_.terrain.land_mask.any()):
        messages.append(
            ValidatorMessage(
                ValidatorSeverity.INFO,
                "map.no_land_cells",
                "terrain has no land cells (all sea); confirm this is intentional",
            )
        )
    elif not bool(sea_mask.any()):
        messages.append(
            ValidatorMessage(
                ValidatorSeverity.INFO,
                "map.no_sea_cells",
                "terrain has no sea cells (all land); SeaSurface is unused",
            )
        )

    return tuple(messages)


# ---------------------------------------------------------------------
# Target coherence (plan/11 § 11.7.2 + plan/12 § 12.7.1)
# ---------------------------------------------------------------------


_AIRBORNE_MOTION = frozenset({MotionKind.AIRCRAFT, MotionKind.POWERED_FLIGHT, MotionKind.BALLISTIC})

_SURFACE_MOTION = frozenset({MotionKind.SURFACE_VESSEL, MotionKind.FLOATING_STATIC})


def validate_targets(
    targets: tuple[TargetEntity, ...],
    map_: Map,
    *,
    sea_altitude_tolerance_m: float = 1.0,
) -> tuple[ValidatorMessage, ...]:
    """Return coherence messages for the target list against a Map.

    Three checks (plan/11 § 11.7.2 MVP):

    1. Every waypoint east/north lies inside ``map.bounds``.
    2. Airborne waypoints (AIRCRAFT / POWERED_FLIGHT / BALLISTIC) sit
       strictly above the local terrain (waypoint altitude > terrain
       elevation at the waypoint's east/north).
    3. Surface waypoints (SURFACE_VESSEL / FLOATING_STATIC) sit close
       to ``sea_surface.z_at_sea_m`` — runtime ignores the altitude
       for these motion kinds (plan/12 § 12.7.1), but a large value
       in the editor is a content mistake worth flagging.

    Args:
        targets: Tuple of targets in the scenario.
        map_: Map resource against which positions are validated.
        sea_altitude_tolerance_m: How far surface waypoint altitudes
            may deviate from ``sea_surface.z_at_sea_m`` before a WARN
            is emitted. Default 1 m.

    Returns:
        Tuple of :class:`ValidatorMessage`. Empty tuple = clean target list.
    """
    messages: list[ValidatorMessage] = []
    b = map_.bounds
    sea_z = map_.sea_surface.z_at_sea_m

    for target in targets:
        motion = target.placement.motion_kind
        for i, wp in enumerate(target.trajectory):
            # Check 1: bounds.
            if not (
                b.east_min_m <= wp.east_m <= b.east_max_m
                and b.north_min_m <= wp.north_m <= b.north_max_m
            ):
                messages.append(
                    ValidatorMessage(
                        ValidatorSeverity.ERROR,
                        "target.waypoint_outside_bounds",
                        (
                            f"target_id={target.target_id} waypoint[{i}] @t={wp.t_s}s "
                            f"({wp.east_m}, {wp.north_m}) leaves map bounds"
                        ),
                    )
                )
                continue  # bounds-outside waypoint cannot be sampled

            # Check 2: airborne waypoint must sit above terrain.
            if motion in _AIRBORNE_MOTION:
                terrain_z = sample_terrain_safe(map_, wp.east_m, wp.north_m)
                if terrain_z is not None and wp.altitude_m <= terrain_z:
                    messages.append(
                        ValidatorMessage(
                            ValidatorSeverity.ERROR,
                            "target.airborne_below_terrain",
                            (
                                f"target_id={target.target_id} waypoint[{i}] @t={wp.t_s}s "
                                f"altitude={wp.altitude_m} m at or below terrain z={terrain_z} m"
                            ),
                        )
                    )

            # Check 3: surface waypoint must sit near sea surface.
            if motion in _SURFACE_MOTION and abs(wp.altitude_m - sea_z) > sea_altitude_tolerance_m:
                messages.append(
                    ValidatorMessage(
                        ValidatorSeverity.WARN,
                        "target.surface_altitude_far_from_sea",
                        (
                            f"target_id={target.target_id} waypoint[{i}] @t={wp.t_s}s "
                            f"altitude={wp.altitude_m} m differs from "
                            f"sea_surface.z_at_sea_m={sea_z} m by more than "
                            f"{sea_altitude_tolerance_m} m"
                        ),
                    )
                )

    return tuple(messages)


# ---------------------------------------------------------------------
# Building coherence
# ---------------------------------------------------------------------


def validate_buildings(
    buildings: tuple[BuildingEntity, ...],
    map_: Map,
) -> tuple[ValidatorMessage, ...]:
    """Return coherence messages for a building list against a Map.

    One MVP check: every building base east/north lies inside
    ``map.bounds``. Anchor-mode-specific checks (EXPLICIT_ALT vs.
    terrain) live in the simulator runtime (plan/12 § 12.8).

    Args:
        buildings: Tuple of buildings on the map.
        map_: Map resource against which positions are validated.

    Returns:
        Tuple of :class:`ValidatorMessage`. Empty tuple = clean list.
    """
    messages: list[ValidatorMessage] = []
    b = map_.bounds

    for building in buildings:
        e = building.placement.base_position.x
        n = building.placement.base_position.y
        if not (b.east_min_m <= e <= b.east_max_m and b.north_min_m <= n <= b.north_max_m):
            messages.append(
                ValidatorMessage(
                    ValidatorSeverity.ERROR,
                    "building.base_outside_bounds",
                    (
                        f"building '{building.placement.entity_id}' base "
                        f"({e}, {n}) leaves map bounds"
                    ),
                )
            )

    return tuple(messages)


# ---------------------------------------------------------------------
# Combined helper (Editor save / Simulator transition gate)
# ---------------------------------------------------------------------


def has_errors(messages: tuple[ValidatorMessage, ...]) -> bool:
    """``True`` iff any message in ``messages`` has ERROR severity.

    The simulator-transition gate uses this to decide whether to block
    a Run (plan/11 § 11.7.3 — "오류가 있으면 ... Simulator 전환 차단").
    """
    return any(m.severity is ValidatorSeverity.ERROR for m in messages)
