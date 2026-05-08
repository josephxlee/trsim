"""Target entity and trajectory waypoints (plan/03 § 3.2.1g, plan/12 § 12.7).

Phase 2.3d — completes the placement family with movable targets. A
:class:`TargetEntity` is anything the radar tries to track: aircraft,
ships, ground vehicles, buoys (as floating-static targets), missiles,
ballistic objects. Buildings and the radar platform itself are NOT
targets — they use :class:`workbench.domain.building.BuildingEntity`
and (Phase 2.11) ``RadarPlatform`` respectively.

The trajectory is a tuple of :class:`TargetWaypoint` samples; v0.27
dynamics treats waypoints as **reference inputs** rather than exact
positions — actual motion is integrated by the dynamics solver
(Phase 2.4) so trajectories are guidance, not ground truth. The
altitude_m field's interpretation depends on the parent target's
motion_kind (plan/12 § 12.7.1).

Phase 2.3d is dataclass-only:

- the integrator lives in Phase 2.4 ``physics/dynamics/``;
- the multi-scatterer Glint extension (``ExtendedTarget``) lives in
  Phase 2.7 ``physics/reflection/extended_target.py``.

References:

- plan/03 § 3.2.1g — TargetEntity / TargetWaypoint dataclass.
- plan/12 § 12.7 — Target trajectory z-handling per motion_kind.
- plan/14 § 14.7 — Trajectory as dynamics reference (v0.27 semantics).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.types import PositionENU
from workbench.domain.wave_response import WaveResponseModel


@dataclass(frozen=True, slots=True)
class TargetWaypoint:
    """One sample on a target trajectory (plan/03 § 3.2.1g).

    Attributes:
        t_s: Time since simulation start [s]. Strictly increasing across
            a trajectory (validated by :class:`TargetEntity`).
        east_m: East coordinate in Map ENU [m].
        north_m: North coordinate in Map ENU [m].
        altitude_m: Vertical coordinate [m]. Interpretation depends on
            the parent target's ``motion_kind`` (plan/12 § 12.7.1):

            - ``SURFACE_VESSEL`` / ``FLOATING_STATIC``: ignored — runtime
              uses ``Map.sea_surface.z_at_sea_m`` plus wave_response.
            - ``AIRCRAFT`` / ``POWERED_FLIGHT`` / ``BALLISTIC``: absolute
              altitude in the Map's vertical reference.
            - ``GROUND_VEHICLE``: ignored — runtime samples DEM at the
              east/north position.

        heading_rad: Yaw from North, clockwise [rad]. Default 0.
    """

    t_s: float
    east_m: float
    north_m: float
    altitude_m: float
    heading_rad: float = 0.0


# Motion kinds that cannot be a target. Buildings / fixed installations
# are placed as BuildingEntity, not TargetEntity (plan/12 § 12.4).
_FORBIDDEN_TARGET_MOTION = frozenset({MotionKind.FIXED_GROUND})


@dataclass(frozen=True, slots=True)
class TargetEntity:
    """Movable radar target placed on a Map (plan/03 § 3.2.1g, v0.27).

    Wraps a :class:`PlacedEntity` (the common id + motion_kind + base
    position + attitude block) with target-specific trajectory and
    optional wave response.

    Attributes:
        placement: Common base placement. ``motion_kind`` must NOT be
            :class:`MotionKind.FIXED_GROUND` (that's a building / fixed
            installation, not a radar target).
        target_id: Integer ID assigned for tracking algorithms (distinct
            from ``placement.entity_id`` which is the Workspace string
            handle). Must be >= 0.
        trajectory: Tuple of :class:`TargetWaypoint`, at least one,
            with ``t_s`` strictly increasing.
        rcs_model: Identifier for the RCS model. Phase 2.7 introduces a
            dedicated RCS / ExtendedTarget type system; for now this is
            a placeholder string used by simple_aspect tests.
        wave_response: Mechanical sea-state response. Should be supplied
            for ``SURFACE_VESSEL`` / ``FLOATING_STATIC`` targets;
            ignored otherwise. Not strictly enforced — Editor flexibility.

    Raises:
        ValueError: If ``placement.motion_kind == FIXED_GROUND``,
            ``target_id < 0``, ``trajectory`` is empty, or trajectory
            ``t_s`` is not strictly increasing.
    """

    placement: PlacedEntity
    target_id: int
    trajectory: tuple[TargetWaypoint, ...]
    rcs_model: str = "simple_aspect"
    wave_response: WaveResponseModel | None = None

    def __post_init__(self) -> None:
        if self.placement.motion_kind in _FORBIDDEN_TARGET_MOTION:
            msg = (
                f"TargetEntity rejects placement.motion_kind = "
                f"{self.placement.motion_kind.name} "
                f"(use BuildingEntity for fixed installations)"
            )
            raise ValueError(msg)
        if self.target_id < 0:
            msg = f"target_id must be >= 0, got {self.target_id}"
            raise ValueError(msg)
        if not self.trajectory:
            msg = "trajectory must contain at least one waypoint"
            raise ValueError(msg)
        prev_t = float("-inf")
        for i, wp in enumerate(self.trajectory):
            if wp.t_s <= prev_t:
                msg = (
                    f"trajectory[{i}].t_s = {wp.t_s} not strictly "
                    f"increasing (prev = {prev_t})"
                )
                raise ValueError(msg)
            prev_t = wp.t_s


def make_default_aircraft_target(
    entity_id: str,
    target_id: int,
    east_m: float,
    north_m: float,
    altitude_m: float = 1000.0,
    *,
    velocity_east_mps: float = 100.0,
    velocity_north_mps: float = 0.0,
    duration_s: float = 60.0,
    rcs_model: str = "simple_aspect",
) -> TargetEntity:
    """Build a default airborne target — 2-waypoint straight-line.

    Trajectory: ``t=0`` at ``(east_m, north_m, altitude_m)``,
    ``t=duration_s`` after moving with constant ENU velocity for
    ``duration_s`` seconds at the same altitude.

    Useful for tests, Editor presets, and Phase 2.4 dynamics-solver
    smoke tests.

    Args:
        entity_id: Workspace-unique string identifier.
        target_id: Integer tracking ID (>= 0).
        east_m: Initial east coordinate [m].
        north_m: Initial north coordinate [m].
        altitude_m: Constant altitude [m].
        velocity_east_mps: East velocity [m/s].
        velocity_north_mps: North velocity [m/s].
        duration_s: Trajectory duration [s]. Must be > 0.
        rcs_model: RCS model string (placeholder until Phase 2.7).

    Returns:
        A :class:`TargetEntity` with ``motion_kind = AIRCRAFT``.

    Raises:
        ValueError: If ``duration_s <= 0``.
    """
    if duration_s <= 0.0:
        msg = f"duration_s must be > 0, got {duration_s}"
        raise ValueError(msg)

    # heading from East/North velocity (atan2(east, north) since
    # heading is clockwise-from-North in the radar AZ convention).
    heading_rad = math.atan2(velocity_east_mps, velocity_north_mps)

    return TargetEntity(
        placement=PlacedEntity(
            entity_id=entity_id,
            motion_kind=MotionKind.AIRCRAFT,
            base_position=PositionENU(x=east_m, y=north_m, z=altitude_m),
            base_heading_rad=heading_rad,
        ),
        target_id=target_id,
        trajectory=(
            TargetWaypoint(
                t_s=0.0,
                east_m=east_m,
                north_m=north_m,
                altitude_m=altitude_m,
                heading_rad=heading_rad,
            ),
            TargetWaypoint(
                t_s=duration_s,
                east_m=east_m + velocity_east_mps * duration_s,
                north_m=north_m + velocity_north_mps * duration_s,
                altitude_m=altitude_m,
                heading_rad=heading_rad,
            ),
        ),
        rcs_model=rcs_model,
    )
