"""Powered-flight dynamics — missile / drone (plan/14 § 14.5.2).

Phase 2.4e (POWERED_FLIGHT half) — thrust-driven vehicle that can
optionally track a trajectory waypoint reference.

Differences from :class:`workbench.physics.dynamics.aircraft.AircraftDynamics`:

- **Higher drag** (default 0.3 vs 0.04) — missiles have small wings,
  blunt bodies, larger Cd.
- **Smaller reference area** (default 0.1 m^2 vs 30) — missile cross
  section vs airliner wing area.
- **Lift defaults to zero** — missiles fly off thrust, not lift. Set
  ``lift_coef > 0`` for cruise missiles with wings.
- **Higher max load factor** (20 g vs 4 g) — high-g maneuvering.
- **Optional trajectory tracking** via ``use_trajectory_as_reference``.
  When ``False``, the ``thrust_profile`` plus initial conditions
  decide motion (similar to a programmed boost-glide trajectory
  without active steering).

Lift in this MVP is still the simple altitude PD trim from
:func:`workbench.physics.dynamics.forces.lift_force` (with
``kp_altitude = kd_altitude = 0`` reducing it to pure trim ``F = m * g``).
A non-zero ``lift_coef`` is reserved for Level 2 AoA-based lift —
plan/14 § 14.4.3.

References:

- plan/14 § 14.5.2 — PoweredFlightDynamics dataclass.
- plan/14 § 14.4 — Force-field model.
- plan/14 § 14.7.2 — Trajectory may be used as reference (option).
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.aircraft import forward_unit_vector
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
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import ForceFn


@dataclass(frozen=True, slots=True)
class PoweredFlightDynamics:
    """Powered-flight (missile / drone) parameters (plan/14 § 14.5.2).

    Attributes:
        mass_kg: Vehicle mass [kg]. Must be > 0.
        thrust_profile: Engine thrust profile (CONSTANT or CURVE).
        drag_coef: Cd, dimensionless. Default 0.3 (typical missile).
        reference_area_m2: Reference area [m^2]. Default 0.1.
        lift_coef: Reserved for Level 2 AoA lift. Default 0.
        kp_position: Horizontal position gain [N/m]. Default 5.0
            (more aggressive than aircraft to handle high-g maneuvers).
        kd_position: Horizontal velocity damping [N/(m/s)]. Default 2.0.
        kp_altitude: Altitude gain [N/m]. Default 5.0.
        kd_altitude: Altitude damping [N/(m/s)]. Default 2.0.
        max_load_factor_g: Per-axis maneuver g limit. Default 20.0.
        use_trajectory_as_reference: When ``True`` the trajectory is
            treated as a PD reference and ``control_force`` is applied;
            when ``False`` only thrust + drag + gravity + lift trim
            integrate (boost-glide style). Default ``True``.

    Raises:
        ValueError: If ``mass_kg <= 0``, any coefficient is negative,
            or ``max_load_factor_g <= 0``.
    """

    mass_kg: float
    thrust_profile: ThrustProfile
    drag_coef: float = 0.3
    reference_area_m2: float = 0.1
    lift_coef: float = 0.0
    kp_position: float = 5.0
    kd_position: float = 2.0
    kp_altitude: float = 5.0
    kd_altitude: float = 2.0
    max_load_factor_g: float = 20.0
    use_trajectory_as_reference: bool = True

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
        if self.max_load_factor_g <= 0.0:
            msg = f"max_load_factor_g must be > 0, got {self.max_load_factor_g}"
            raise ValueError(msg)

    @property
    def max_control_force_n(self) -> float:
        """Per-axis control force clamp [N] — ``m * g * max_load_factor_g``."""
        return self.mass_kg * G_STANDARD_M_PER_S2 * self.max_load_factor_g


def make_powered_flight_force_fn(
    dynamics: PoweredFlightDynamics,
    atm: AtmosphereState,
    trajectory: tuple[Waypoint, ...],
) -> ForceFn:
    """Build the total-force callback for a powered-flight target.

    Always sums gravity + drag + lift trim + thrust. Adds
    ``control_force`` only when ``use_trajectory_as_reference`` is
    ``True``.

    Args:
        dynamics: PoweredFlightDynamics parameters.
        atm: Atmosphere state.
        trajectory: Reference trajectory (>= 1 waypoint).

    Returns:
        Callable ``state -> (F_east, F_north, F_up)`` [N].

    Raises:
        ValueError: If ``trajectory`` is empty.
    """
    if not trajectory:
        msg = "trajectory must contain at least one waypoint"
        raise ValueError(msg)

    use_ref = dynamics.use_trajectory_as_reference
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

        if use_ref:
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
        else:
            f_ctrl = (0.0, 0.0, 0.0)

        return (
            f_grav[0] + f_drag[0] + f_lift[0] + f_thrust[0] + f_ctrl[0],
            f_grav[1] + f_drag[1] + f_lift[1] + f_thrust[1] + f_ctrl[1],
            f_grav[2] + f_drag[2] + f_lift[2] + f_thrust[2] + f_ctrl[2],
        )

    return force_fn
