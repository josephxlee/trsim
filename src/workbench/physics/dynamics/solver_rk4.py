"""RK4 integrator for translational dynamics (plan/14 § 14.6).

Phase 2.4c — fourth-order Runge-Kutta step that advances a
:class:`workbench.physics.dynamics.rigid_body.RigidBodyState` under an
arbitrary force field. The force is supplied as a callback so the
solver stays decoupled from the per-target dynamics modules
(Phase 2.4d/e/f); each of those modules builds a force function from
its own parameters and hands it to the solver.

State variable: ``x = (position, velocity)`` with derivative
``x' = (velocity, force / mass)``. RK4 weights ``(1, 2, 2, 1) / 6``.

Attitude (roll / pitch / yaw) is **not** integrated at MVP Level 1:
after each step the new attitude is derived from the post-step
velocity vector via
:func:`workbench.physics.dynamics.rigid_body.attitude_from_velocity`
(coordinated-flight assumption, plan/14 § 14.2.2 / § 14.3.2).
Body-frame angular velocity is propagated unchanged — Level 2 will
add a separate rotational integrator.

Sub-step pattern (plan/14 § 14.6.2):

- Sim main step ``dt_main_s = 0.05`` (20 Hz, frame_rate).
- Dynamics sub-step ``dt_sub_s = 0.005`` (10 sub-steps per frame).
- :func:`integrate` exposes both knobs so callers can choose tighter
  sub-steps for fast targets (e.g. missiles) without changing the
  main scheduler.

References:

- plan/14 § 14.6 — Integration (RK4 + sub-step).
- plan/14 § 14.3.2 — Level 1 attitude_from_velocity simplification.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Final

from workbench.physics.dynamics.rigid_body import RigidBodyState, attitude_from_velocity

ForceFn = Callable[[RigidBodyState], tuple[float, float, float]]
"""Callable signature: ``state -> (F_east, F_north, F_up)`` [N].

Implementations are pure: they may close over per-target parameters
(mass, drag coefficient, atmosphere, thrust profile, ...) but must
not mutate external state during a step.
"""

# Default sub-step count (plan/14 § 14.6.2: main 0.05 s / sub 0.005 s).
DEFAULT_SUBSTEP_COUNT: Final[int] = 10


def rk4_step(
    state: RigidBodyState,
    force_fn: ForceFn,
    mass_kg: float,
    dt_s: float,
) -> RigidBodyState:
    """Advance ``state`` by ``dt_s`` using one RK4 step.

    Integrates position + velocity together. Attitude is recomputed
    from the post-step velocity (Level 1 coordinated flight); body
    angular velocity carries through unchanged.

    Args:
        state: Current rigid-body state.
        force_fn: Callable returning ``(F_east, F_north, F_up)`` [N]
            for a probed state. Called four times per step.
        mass_kg: Target mass [kg]. Must be > 0.
        dt_s: Step duration [s]. Must be > 0.

    Returns:
        New :class:`RigidBodyState` at ``sim_t_s + dt_s``.

    Raises:
        ValueError: If ``mass_kg <= 0`` or ``dt_s <= 0``.
    """
    if mass_kg <= 0.0:
        msg = f"mass_kg must be > 0, got {mass_kg}"
        raise ValueError(msg)
    if dt_s <= 0.0:
        msg = f"dt_s must be > 0, got {dt_s}"
        raise ValueError(msg)

    inv_mass = 1.0 / mass_kg
    half_dt = dt_s * 0.5

    # k1 — at the current state.
    v1 = state.velocity_enu_mps
    f1 = force_fn(state)
    a1 = (f1[0] * inv_mass, f1[1] * inv_mass, f1[2] * inv_mass)

    # k2 — half-step using k1.
    state_2 = _probe(state, v1, a1, half_dt)
    v2 = state_2.velocity_enu_mps
    f2 = force_fn(state_2)
    a2 = (f2[0] * inv_mass, f2[1] * inv_mass, f2[2] * inv_mass)

    # k3 — half-step using k2.
    state_3 = _probe(state, v2, a2, half_dt)
    v3 = state_3.velocity_enu_mps
    f3 = force_fn(state_3)
    a3 = (f3[0] * inv_mass, f3[1] * inv_mass, f3[2] * inv_mass)

    # k4 — full-step using k3.
    state_4 = _probe(state, v3, a3, dt_s)
    v4 = state_4.velocity_enu_mps
    f4 = force_fn(state_4)
    a4 = (f4[0] * inv_mass, f4[1] * inv_mass, f4[2] * inv_mass)

    sixth_dt = dt_s / 6.0
    new_east = state.east_m + sixth_dt * (v1[0] + 2.0 * v2[0] + 2.0 * v3[0] + v4[0])
    new_north = state.north_m + sixth_dt * (v1[1] + 2.0 * v2[1] + 2.0 * v3[1] + v4[1])
    new_up = state.altitude_m + sixth_dt * (v1[2] + 2.0 * v2[2] + 2.0 * v3[2] + v4[2])
    new_v_east = state.velocity_east_mps + sixth_dt * (a1[0] + 2.0 * a2[0] + 2.0 * a3[0] + a4[0])
    new_v_north = state.velocity_north_mps + sixth_dt * (a1[1] + 2.0 * a2[1] + 2.0 * a3[1] + a4[1])
    new_v_up = state.velocity_up_mps + sixth_dt * (a1[2] + 2.0 * a2[2] + 2.0 * a3[2] + a4[2])

    candidate = RigidBodyState(
        east_m=new_east,
        north_m=new_north,
        altitude_m=new_up,
        velocity_east_mps=new_v_east,
        velocity_north_mps=new_v_north,
        velocity_up_mps=new_v_up,
        roll_rad=state.roll_rad,
        pitch_rad=state.pitch_rad,
        yaw_rad=state.yaw_rad,
        angular_velocity_body_rad_s=state.angular_velocity_body_rad_s,
        sim_t_s=state.sim_t_s + dt_s,
    )
    new_roll, new_pitch, new_yaw = attitude_from_velocity(candidate)
    return RigidBodyState(
        east_m=new_east,
        north_m=new_north,
        altitude_m=new_up,
        velocity_east_mps=new_v_east,
        velocity_north_mps=new_v_north,
        velocity_up_mps=new_v_up,
        roll_rad=new_roll,
        pitch_rad=new_pitch,
        yaw_rad=new_yaw,
        angular_velocity_body_rad_s=state.angular_velocity_body_rad_s,
        sim_t_s=state.sim_t_s + dt_s,
    )


def integrate(
    state: RigidBodyState,
    force_fn: ForceFn,
    mass_kg: float,
    dt_main_s: float,
    *,
    n_substeps: int = DEFAULT_SUBSTEP_COUNT,
) -> RigidBodyState:
    """Advance ``state`` by ``dt_main_s`` using ``n_substeps`` RK4 sub-steps.

    Equal-spaced sub-stepping. The main scheduler typically calls this
    at the simulation frame rate (20 Hz, ``dt_main_s = 0.05``) with
    ``n_substeps = 10`` for the default 0.005 s dynamics step
    (plan/14 § 14.6.2).

    Args:
        state: Current state.
        force_fn: Force callback (see :data:`ForceFn`).
        mass_kg: Target mass [kg]. Must be > 0.
        dt_main_s: Total time to advance [s]. Must be > 0.
        n_substeps: Number of equal sub-steps. Must be >= 1.

    Returns:
        New :class:`RigidBodyState` at ``sim_t_s + dt_main_s``.

    Raises:
        ValueError: If ``n_substeps < 1`` (mass / dt validation
            happens inside :func:`rk4_step`).
    """
    if n_substeps < 1:
        msg = f"n_substeps must be >= 1, got {n_substeps}"
        raise ValueError(msg)
    dt_sub = dt_main_s / float(n_substeps)
    current = state
    for _ in range(n_substeps):
        current = rk4_step(current, force_fn, mass_kg, dt_sub)
    return current


def _probe(
    base: RigidBodyState,
    velocity: tuple[float, float, float],
    acceleration: tuple[float, float, float],
    dt: float,
) -> RigidBodyState:
    """Build an intermediate state for an RK4 mid-point evaluation.

    Advances position by ``velocity * dt`` and velocity by
    ``acceleration * dt``. Attitude / angular velocity / sim_t_s are
    preserved — the force functions of MVP Level 1 use only position
    and velocity (gravity / drag / lift / thrust / control), so a
    cheaper attitude-recompute is unnecessary inside the RK4 stages.
    """
    return RigidBodyState(
        east_m=base.east_m + velocity[0] * dt,
        north_m=base.north_m + velocity[1] * dt,
        altitude_m=base.altitude_m + velocity[2] * dt,
        velocity_east_mps=base.velocity_east_mps + acceleration[0] * dt,
        velocity_north_mps=base.velocity_north_mps + acceleration[1] * dt,
        velocity_up_mps=base.velocity_up_mps + acceleration[2] * dt,
        roll_rad=base.roll_rad,
        pitch_rad=base.pitch_rad,
        yaw_rad=base.yaw_rad,
        angular_velocity_body_rad_s=base.angular_velocity_body_rad_s,
        sim_t_s=base.sim_t_s,
    )
