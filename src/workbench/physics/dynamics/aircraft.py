"""Aircraft dynamics — heavier-than-air vehicle with autopilot
(plan/14 § 14.5.1).

Phase 2.4d — provides :class:`AircraftDynamics` and the
:func:`make_aircraft_force_fn` builder that composes gravity / drag /
lift / thrust / control into the single force callback consumed by the
RK4 solver.

Level 1 MVP simplifications (plan/14 § 14.2.2):

- 3DOF point-mass + outside forces.
- Attitude is derived from velocity by the solver
  (:func:`workbench.physics.dynamics.rigid_body.attitude_from_velocity`).
- Forward unit vector for thrust comes from the velocity direction
  (coordinated flight); when the target is essentially stationary it
  falls back to the body x-axis under the current ``yaw_rad`` (CW
  from North).
- ``max_load_factor_g`` translates into a per-axis force clamp on the
  control PD via ``F_max = m * g * max_load_factor_g`` — keeps the
  aircraft from "snapping" to a far-away reference point in one step.

References:

- plan/14 § 14.5.1 — AircraftDynamics dataclass.
- plan/14 § 14.4 — Force-field model.
- plan/14 § 14.7 — Trajectory as PD reference.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.forces import (
    G_STANDARD_M_PER_S2,
    ThrustProfile,
    control_force,
    drag_force,
    gravity_force,
    lift_force,
    thrust_force,
)
from workbench.physics.dynamics.reference import Waypoint, interpolate_reference
from workbench.physics.dynamics.rigid_body import STATIONARY_SPEED_MPS, RigidBodyState
from workbench.physics.dynamics.solver_rk4 import ForceFn


@dataclass(frozen=True, slots=True)
class AircraftDynamics:
    """Aircraft autopilot parameters (plan/14 § 14.5.1).

    Attributes:
        mass_kg: Aircraft mass [kg]. Must be > 0.
        thrust_profile: Engine thrust profile. CONSTANT for trim
            (auto-balance with drag) is the common case; CURVE for
            flight phases.
        drag_coef: Cd, dimensionless. Default 0.04 (clean airliner).
        reference_area_m2: Reference area (typically wing area) [m^2].
            Default 30.0.
        lift_coef: Reserved for Level 2 AoA-based lift. Default 0.4 —
            unused at Level 1 because :func:`lift_force` uses an
            altitude PD (plan/14 § 14.4.3 says "Level 2: AoA-based").
        kp_position: Horizontal position gain [N/m]. Default 0.5.
        kd_position: Horizontal velocity damping [N/(m/s)]. Default 0.3.
        kp_altitude: Altitude position gain [N/m]. Default 1.0.
        kd_altitude: Altitude velocity damping [N/(m/s)]. Default 0.5.
        max_climb_rate_mps: Reserved for an outer rate limiter
            (Phase 3 scenario). Stored here so all dynamics knobs live
            on one dataclass. Default 25.0.
        max_bank_deg: Reserved for Level 2 lateral dynamics. Default 60.
        max_load_factor_g: Per-axis maneuver g limit. The control PD
            output is clamped to ``m * g * max_load_factor_g`` per
            axis. Default 4.0 (typical airliner maneuver limit).

    Raises:
        ValueError: If ``mass_kg <= 0``, any coefficient is negative,
            or any limit is non-positive.
    """

    mass_kg: float
    thrust_profile: ThrustProfile
    drag_coef: float = 0.04
    reference_area_m2: float = 30.0
    lift_coef: float = 0.4
    kp_position: float = 0.5
    kd_position: float = 0.3
    kp_altitude: float = 1.0
    kd_altitude: float = 0.5
    max_climb_rate_mps: float = 25.0
    max_bank_deg: float = 60.0
    max_load_factor_g: float = 4.0

    def __post_init__(self) -> None:
        if self.mass_kg <= 0.0:
            msg = f"mass_kg must be > 0, got {self.mass_kg}"
            raise ValueError(msg)
        if self.drag_coef < 0.0:
            msg = f"drag_coef must be >= 0, got {self.drag_coef}"
            raise ValueError(msg)
        if self.reference_area_m2 <= 0.0:
            msg = f"reference_area_m2 must be > 0, got {self.reference_area_m2}"
            raise ValueError(msg)
        if self.lift_coef < 0.0:
            msg = f"lift_coef must be >= 0, got {self.lift_coef}"
            raise ValueError(msg)
        if self.kp_position < 0.0:
            msg = f"kp_position must be >= 0, got {self.kp_position}"
            raise ValueError(msg)
        if self.kd_position < 0.0:
            msg = f"kd_position must be >= 0, got {self.kd_position}"
            raise ValueError(msg)
        if self.kp_altitude < 0.0:
            msg = f"kp_altitude must be >= 0, got {self.kp_altitude}"
            raise ValueError(msg)
        if self.kd_altitude < 0.0:
            msg = f"kd_altitude must be >= 0, got {self.kd_altitude}"
            raise ValueError(msg)
        if self.max_climb_rate_mps <= 0.0:
            msg = f"max_climb_rate_mps must be > 0, got {self.max_climb_rate_mps}"
            raise ValueError(msg)
        if self.max_bank_deg <= 0.0:
            msg = f"max_bank_deg must be > 0, got {self.max_bank_deg}"
            raise ValueError(msg)
        if self.max_load_factor_g <= 0.0:
            msg = f"max_load_factor_g must be > 0, got {self.max_load_factor_g}"
            raise ValueError(msg)

    @property
    def max_control_force_n(self) -> float:
        """Per-axis control force clamp [N] — ``m * g * max_load_factor_g``."""
        return self.mass_kg * G_STANDARD_M_PER_S2 * self.max_load_factor_g


def forward_unit_vector(state: RigidBodyState) -> tuple[float, float, float]:
    """Body forward unit vector in ENU (coordinated flight).

    When the target moves faster than ``STATIONARY_SPEED_MPS`` the
    forward direction follows the velocity vector. Otherwise it
    derives from ``yaw_rad`` (CW from North), with zero pitch — i.e.
    the body x-axis lies horizontally pointing along the heading.

    Args:
        state: Current rigid-body state.

    Returns:
        Unit 3-tuple ``(east, north, up)``.
    """
    speed = state.speed_mps
    if speed >= STATIONARY_SPEED_MPS:
        return (
            state.velocity_east_mps / speed,
            state.velocity_north_mps / speed,
            state.velocity_up_mps / speed,
        )
    # Stationary fallback — use yaw, no pitch / roll contribution.
    return (math.sin(state.yaw_rad), math.cos(state.yaw_rad), 0.0)


def make_aircraft_force_fn(
    dynamics: AircraftDynamics,
    atm: AtmosphereState,
    trajectory: tuple[Waypoint, ...],
) -> ForceFn:
    """Build the total-force callback for an aircraft.

    Composes :func:`gravity_force` + :func:`drag_force` + :func:`lift_force`
    + :func:`thrust_force` + :func:`control_force` into a single
    :data:`ForceFn` for the RK4 solver. The trajectory is captured as
    a closure so the solver can call the result repeatedly without
    re-passing context.

    Args:
        dynamics: Aircraft parameters.
        atm: Atmosphere state (drives air density via ISA).
        trajectory: Reference trajectory (>= 1 waypoint).

    Returns:
        Callable ``state -> (F_east, F_north, F_up)`` [N].

    Raises:
        ValueError: If ``trajectory`` is empty.
    """
    if not trajectory:
        msg = "trajectory must contain at least one waypoint"
        raise ValueError(msg)

    max_ctrl = dynamics.max_control_force_n

    def force_fn(state: RigidBodyState) -> tuple[float, float, float]:
        ref = interpolate_reference(trajectory, state.sim_t_s)
        forward = forward_unit_vector(state)

        f_grav = gravity_force(dynamics.mass_kg)
        f_drag = drag_force(
            state.velocity_enu_mps,
            drag_coef=dynamics.drag_coef,
            reference_area_m2=dynamics.reference_area_m2,
            altitude_m=state.altitude_m,
            atm=atm,
        )
        f_lift = lift_force(
            mass_kg=dynamics.mass_kg,
            altitude_m=state.altitude_m,
            target_altitude_m=ref.altitude_m,
            velocity_up_mps=state.velocity_up_mps,
            kp_altitude=dynamics.kp_altitude,
            kd_altitude=dynamics.kd_altitude,
        )
        f_thrust = thrust_force(dynamics.thrust_profile, state.sim_t_s, forward)
        f_ctrl = control_force(
            east_m=state.east_m,
            north_m=state.north_m,
            velocity_east_mps=state.velocity_east_mps,
            velocity_north_mps=state.velocity_north_mps,
            ref_east_m=ref.east_m,
            ref_north_m=ref.north_m,
            kp_position=dynamics.kp_position,
            kd_position=dynamics.kd_position,
            max_accel_n=max_ctrl,
        )
        return (
            f_grav[0] + f_drag[0] + f_lift[0] + f_thrust[0] + f_ctrl[0],
            f_grav[1] + f_drag[1] + f_lift[1] + f_thrust[1] + f_ctrl[1],
            f_grav[2] + f_drag[2] + f_lift[2] + f_thrust[2] + f_ctrl[2],
        )

    return force_fn
