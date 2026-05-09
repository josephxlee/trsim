"""Rigid-body state for 6DOF target dynamics (plan/14 § 14.3).

Phase 2.4a — first slice of the dynamics package. Provides the immutable
:class:`RigidBodyState` carrier used by the RK4 solver (Phase 2.4c) and
the per-motion-kind dynamics modules (Phase 2.4d/e/f), plus the
``attitude_from_velocity`` helper that derives attitude from the velocity
vector under the **coordinated-flight** assumption used at MVP Level 1
(plan/14 § 14.2.2).

Attitude convention (TRsim-wide, plan/12 § 12.4):

- ``yaw_rad`` follows the project ``heading_rad`` convention — yaw
  measured **clockwise from North** about +Up. Matches
  :class:`workbench.domain.placement.PlacedEntity.base_heading_rad` /
  :class:`workbench.domain.placement.CurrentPose.heading_rad`, so
  conversion at the dynamics-solver boundary is identity.
- ``pitch_rad`` is positive nose-up.
- ``roll_rad`` is right-wing-down (standard aerospace).
- Body angular velocity is in the body frame ``(p, q, r)`` order
  (roll-rate, pitch-rate, yaw-rate) — relevant from Phase 2.4 Level 2,
  not used by Level 1 attitude_from_velocity.

The plan/14 § 14.3.1 sketch names the yaw/pitch/roll fields without
fixing the rotation direction; we follow the rest of the project to
avoid dual conventions.

References:

- plan/14 § 14.3 — 6DOF rigid body representation.
- plan/14 § 14.2.2 — Level 1 MVP simplification (3DOF point-mass +
  attitude from velocity).
- plan/12 § 12.4 — PlacedEntity / CurrentPose heading convention.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

# Speed below which attitude_from_velocity refuses to update yaw/pitch
# (otherwise atan2 / asin of a vanishing velocity is numerically wild).
# Plan/14 § 14.3.2 hard-codes 0.01 m/s; we expose it as a constant.
STATIONARY_SPEED_MPS: Final[float] = 0.01


@dataclass(frozen=True, slots=True)
class RigidBodyState:
    """Instantaneous 6DOF state of a dynamic target (plan/14 § 14.3.1).

    Position and velocity are expressed in the Map ENU frame; attitude
    Euler angles use the TRsim project convention (yaw CW from North,
    pitch nose-up, roll right-wing-down).

    Phase 2.4a is dataclass-only — the integrator (Phase 2.4c) consumes
    this state, the per-kind dynamics modules (Phase 2.4d/e/f) emit it.

    Attributes:
        east_m: East coordinate in Map ENU [m].
        north_m: North coordinate in Map ENU [m].
        altitude_m: Up coordinate in Map ENU [m].
        velocity_east_mps: ENU east velocity [m/s].
        velocity_north_mps: ENU north velocity [m/s].
        velocity_up_mps: ENU up velocity [m/s].
        roll_rad: Roll about the heading axis (right-wing-down) [rad].
        pitch_rad: Pitch above the horizon (nose-up) [rad].
        yaw_rad: Yaw from North, clockwise [rad]. Same convention as
            :class:`workbench.domain.placement.CurrentPose.heading_rad`.
        angular_velocity_body_rad_s: Body-frame angular velocity tuple
            ``(p, q, r)`` — roll-rate, pitch-rate, yaw-rate [rad/s].
            Length must be 3. Level 1 MVP leaves these at zero.
        sim_t_s: Simulation timestamp at which this state was sampled
            [s]. Must be >= 0.

    Raises:
        ValueError: If ``angular_velocity_body_rad_s`` is not a 3-tuple
            or ``sim_t_s`` is negative.
    """

    east_m: float
    north_m: float
    altitude_m: float

    velocity_east_mps: float
    velocity_north_mps: float
    velocity_up_mps: float

    roll_rad: float
    pitch_rad: float
    yaw_rad: float

    angular_velocity_body_rad_s: tuple[float, float, float] = (0.0, 0.0, 0.0)
    sim_t_s: float = 0.0

    def __post_init__(self) -> None:
        if len(self.angular_velocity_body_rad_s) != 3:
            msg = (
                f"angular_velocity_body_rad_s must be a 3-tuple, got "
                f"length {len(self.angular_velocity_body_rad_s)}"
            )
            raise ValueError(msg)
        if self.sim_t_s < 0.0:
            msg = f"sim_t_s must be >= 0, got {self.sim_t_s}"
            raise ValueError(msg)

    @property
    def speed_mps(self) -> float:
        """Total ENU speed [m/s] — ``sqrt(vE^2 + vN^2 + vU^2)``."""
        return math.sqrt(
            self.velocity_east_mps * self.velocity_east_mps
            + self.velocity_north_mps * self.velocity_north_mps
            + self.velocity_up_mps * self.velocity_up_mps
        )

    @property
    def horizontal_speed_mps(self) -> float:
        """Ground-track speed [m/s] — ``sqrt(vE^2 + vN^2)``."""
        return math.hypot(self.velocity_east_mps, self.velocity_north_mps)

    @property
    def position_enu_m(self) -> tuple[float, float, float]:
        """Position 3-tuple ``(east, north, up)`` [m]."""
        return (self.east_m, self.north_m, self.altitude_m)

    @property
    def velocity_enu_mps(self) -> tuple[float, float, float]:
        """Velocity 3-tuple ``(vE, vN, vU)`` [m/s]."""
        return (self.velocity_east_mps, self.velocity_north_mps, self.velocity_up_mps)


def attitude_from_velocity(state: RigidBodyState) -> tuple[float, float, float]:
    """Derive ``(roll, pitch, yaw)`` from the velocity vector.

    Implements plan/14 § 14.3.2 Level 1 MVP coordinated-flight
    assumption: the body forward axis aligns with the velocity vector,
    so yaw and pitch fall out of the velocity components and roll is
    forced to zero.

    Conventions (matches :class:`RigidBodyState`):

    - ``yaw = atan2(velocity_east, velocity_north)`` — CW from North.
    - ``pitch = asin(velocity_up / speed)`` — positive nose-up.
    - ``roll = 0`` — Level 2 will compute roll from lateral acceleration.

    When the speed is below :data:`STATIONARY_SPEED_MPS` the function
    returns the existing attitude unchanged (no information in a
    vanishing velocity vector).

    Args:
        state: Source state. Position is unused; only velocity and the
            existing attitude (for the stationary-fallback case) matter.

    Returns:
        ``(roll_rad, pitch_rad, yaw_rad)`` 3-tuple in the TRsim
        attitude convention.
    """
    speed = state.speed_mps
    if speed < STATIONARY_SPEED_MPS:
        return (state.roll_rad, state.pitch_rad, state.yaw_rad)
    yaw = math.atan2(state.velocity_east_mps, state.velocity_north_mps)
    # Clamp asin argument to [-1, 1] — speed is sqrt of squares so the
    # ratio cannot exceed 1 in real arithmetic, but float rounding can
    # produce 1.0000000001 for purely vertical velocities.
    sin_pitch = state.velocity_up_mps / speed
    sin_pitch = max(-1.0, min(1.0, sin_pitch))
    pitch = math.asin(sin_pitch)
    roll = 0.0
    return (roll, pitch, yaw)
