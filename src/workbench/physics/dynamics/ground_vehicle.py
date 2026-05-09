"""Ground-vehicle kinematics — terrain-bound motion (plan/14 § 14.5.5).

Phase 2.4f (GROUND_VEHICLE half) — kinematic, **not** force-integrated.
The trajectory CSV drives horizontal motion; the DEM drives vertical
position; attitude is flat (no roll / pitch / wave coupling).

Why kinematic at MVP: GROUND_VEHICLE is explicitly tagged "MVP+alpha"
in plan/14 § 14.5.5 — only the v0.21 simple model is required for
v0.27 release. Force-based road dynamics (suspension, traction limits,
slope-induced acceleration) is deferred.

Z handling (plan/14 § 14.7.3): trajectory ``altitude_m`` is **ignored**
— the runtime samples DEM at the east/north position. This module
expects the caller to pass the resolved DEM altitude as ``dem_z_m``;
DEM lookup itself lives in the App-layer scenario (Phase 3).

References:

- plan/14 § 14.5.5 — GROUND_VEHICLE motion model (v0.21 retained).
- plan/14 § 14.7.3 — Trajectory z ignored for GROUND_VEHICLE.
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.physics.dynamics.reference import (
    Waypoint,
    interpolate_reference,
    reference_velocity_enu,
)
from workbench.physics.dynamics.rigid_body import RigidBodyState


@dataclass(frozen=True, slots=True)
class GroundVehicleDynamics:
    """Ground-vehicle kinematic parameters (plan/14 § 14.5.5).

    MVP holds only a placeholder ``max_speed_mps`` — used as a sanity
    cap by callers that want to validate trajectory feasibility.
    Default is large enough to never trip on user-provided road
    trajectories.

    Attributes:
        max_speed_mps: Speed sanity cap [m/s]. Default 60 m/s
            (~216 km/h, well above typical ground-vehicle speeds).
            Must be > 0.

    Raises:
        ValueError: If ``max_speed_mps <= 0``.
    """

    max_speed_mps: float = 60.0

    def __post_init__(self) -> None:
        if self.max_speed_mps <= 0.0:
            msg = f"max_speed_mps must be > 0, got {self.max_speed_mps}"
            raise ValueError(msg)


def ground_vehicle_pose(
    dynamics: GroundVehicleDynamics,
    trajectory: tuple[Waypoint, ...],
    *,
    dem_z_m: float,
    sim_t_s: float,
) -> RigidBodyState:
    """Compute the ground-vehicle state at ``sim_t_s``.

    - **xy**: linear interpolation of the trajectory waypoints.
    - **z**: ``dem_z_m`` (caller-supplied DEM lookup at the resolved
      east / north).
    - **velocity_xy**: piecewise-constant slope of the trajectory.
    - **velocity_up**: ``0`` (vertical follows DEM, no own dynamics).
    - **roll / pitch**: ``0`` (MVP — Level 2 will add slope-induced
      pitch and bank).
    - **yaw**: trajectory heading.

    The ``dynamics.max_speed_mps`` cap is **not** enforced here — it
    is exposed for callers (Editor / Validator) to flag infeasible
    trajectories before the simulation runs.

    Args:
        dynamics: Ground-vehicle kinematic parameters.
        trajectory: Reference trajectory (>= 1 waypoint).
        dem_z_m: DEM altitude at the resolved (east, north) [m].
        sim_t_s: Sample time [s].

    Returns:
        :class:`RigidBodyState` at ``sim_t_s``.

    Raises:
        ValueError: If ``trajectory`` is empty.
    """
    _ = dynamics  # max_speed_mps is informational at MVP — kept for symmetry
    ref = interpolate_reference(trajectory, sim_t_s)
    v_e, v_n, _ = reference_velocity_enu(trajectory, sim_t_s)
    return RigidBodyState(
        east_m=ref.east_m,
        north_m=ref.north_m,
        altitude_m=dem_z_m,
        velocity_east_mps=v_e,
        velocity_north_mps=v_n,
        velocity_up_mps=0.0,
        roll_rad=0.0,
        pitch_rad=0.0,
        yaw_rad=ref.heading_rad,
        sim_t_s=sim_t_s,
    )
