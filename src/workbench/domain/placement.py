"""Placement and motion primitives — MotionKind, PlacedEntity, CurrentPose.

Phase 2.3a — base/current pose split (plan/12 § 12.4) and the seven
MotionKind categories from plan/03 § 3.2.1d / plan/14 (v0.21 + v0.27).

Design split (v0.21):

- :class:`PlacedEntity` carries the **Editor-time static** placement
  (``base_position``, ``base_heading_rad``, ...). It does not change
  during a simulation run.
- :class:`CurrentPose` carries the **runtime dynamic** pose during a Sim
  (``position`` + ``velocity`` + heading + pitch + roll + Time tag).
  It is recomputed per frame by the dynamics solver / wave response /
  scenario reference, but never overwrites the entity's base placement.

Why two types instead of mutating one: Editor saves only ``base_*``;
Sim PAUSED keeps both visible side-by-side; rerunning a scenario
regenerates ``CurrentPose`` from ``base_*`` plus dynamics.

References:

- plan/03 § 3.2.1d — Placement & Motion dataclass.
- plan/12 § 12.3-12.4 — MotionKind 7 + base/current split.
- plan/14 — Dynamics model (v0.27 reference + integrated motion).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workbench.domain.types import PositionENU, Time, VelocityENU


class MotionKind(Enum):
    """Entity motion category (plan/12 § 12.3, expanded v0.21 -> v0.27).

    The seven categories cover every entity TRsim can place:

    - FIXED_GROUND: Buildings / radars on land that never move.
    - GROUND_VEHICLE: Cars / trucks on roads (MVP+alpha; routing TBD).
    - SURFACE_VESSEL: Ships under way; uses sea-state wave response.
    - FLOATING_STATIC: Anchored ships / buoys; same vertical wave response
        as SURFACE_VESSEL but no horizontal motion.
    - AIRCRAFT: Heavier-than-air with autopilot (waypoint + max climb rate
        + bank limit). v0.27 — replaces the old AIRBORNE category.
    - POWERED_FLIGHT: Thrust-driven (missile / drone). Trajectory is a
        reference; dynamics solver applies thrust + drag (v0.27).
    - BALLISTIC: Initial conditions only; ignores trajectory beyond launch
        — gravity + drag integrate the rest (v0.27).

    The string values are the canonical TOML/JSON representation.
    """

    FIXED_GROUND = "fixed_ground"
    GROUND_VEHICLE = "ground_vehicle"
    SURFACE_VESSEL = "surface_vessel"
    FLOATING_STATIC = "floating_static"
    AIRCRAFT = "aircraft"
    POWERED_FLIGHT = "powered_flight"
    BALLISTIC = "ballistic"


@dataclass(frozen=True, slots=True)
class PlacedEntity:
    """Common Editor-time static placement (plan/12 § 12.4.1).

    Every Editor resource that can be placed in the Map has a
    :class:`PlacedEntity` block — radars, buildings, targets, fixed
    obstacles. The motion-kind-specific subclasses (Building / Target / ...)
    add fields on top of this base.

    Attributes:
        entity_id: Stable identifier within the Workspace
            (e.g. ``"radar_host_01"``, ``"target_001"``).
        motion_kind: Which motion category this entity belongs to.
        base_position: Static placement in Map ENU [m].
        base_heading_rad: Yaw from North, clockwise [rad]. Default 0.
        base_pitch_rad: Pitch above horizon [rad]. Default 0.
        base_roll_rad: Roll about the heading axis [rad]. Default 0.
    """

    entity_id: str
    motion_kind: MotionKind
    base_position: PositionENU
    base_heading_rad: float = 0.0
    base_pitch_rad: float = 0.0
    base_roll_rad: float = 0.0

    def __post_init__(self) -> None:
        if not self.entity_id:
            msg = "entity_id must be a non-empty string"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CurrentPose:
    """Runtime pose during a Sim run (plan/12 § 12.4.2).

    Recomputed every frame by the dynamics solver, scenario reference,
    or wave response model. Distinct from :class:`PlacedEntity` so that
    pausing the Sim and returning to Editor still shows the entity's
    static base placement, not its last simulated frame.

    Attributes:
        position: Pose position in Map ENU [m].
        velocity: ENU velocity at this frame [m/s].
        heading_rad: Instantaneous yaw [rad].
        pitch_rad: Instantaneous pitch [rad].
        roll_rad: Instantaneous roll [rad].
        timestamp: Sim time at which this pose was sampled.
    """

    position: PositionENU
    velocity: VelocityENU
    heading_rad: float
    pitch_rad: float
    roll_rad: float
    timestamp: Time
