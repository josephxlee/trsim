"""Ballistic dynamics — free-fall / unpowered projectile (plan/14 § 14.5.3).

Phase 2.4e (BALLISTIC half) — gravity and drag only. No thrust, no
lift, no control. Initial conditions (position from
:class:`workbench.domain.placement.PlacedEntity.base_position`,
velocity from :attr:`BallisticDynamics.initial_velocity_mps`) decide
the entire trajectory; trajectory CSV is **ignored** (plan/14 §
14.7.2).

Spin (``spin_rate_rps``) is recorded for future RCS coupling
(Phase 2.7 ExtendedTarget) but does not affect translational dynamics
at MVP Level 1.

References:

- plan/14 § 14.5.3 — BallisticDynamics dataclass.
- plan/14 § 14.7.2 — Trajectory ignored for BALLISTIC.
- plan/14 § 14.9.1 — Energy conservation invariant
  (KE + PE constant when drag = 0).
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.physics.atmosphere import AtmosphereState
from workbench.physics.dynamics.forces import drag_force, gravity_force
from workbench.physics.dynamics.rigid_body import RigidBodyState
from workbench.physics.dynamics.solver_rk4 import ForceFn


@dataclass(frozen=True, slots=True)
class BallisticDynamics:
    """Free-flight projectile parameters (plan/14 § 14.5.3).

    Attributes:
        mass_kg: Projectile mass [kg]. Must be > 0.
        drag_coef: Drag coefficient. Default 0.4 (typical artillery
            shell). Set to 0 for vacuum ballistics (energy-conservation
            checks).
        reference_area_m2: Reference area [m^2]. Default 0.05.
        initial_velocity_mps: Initial ENU velocity at launch [m/s].
            Default ``(0, 0, 0)`` — caller must override for any
            useful ballistic trajectory.
        spin_rate_rps: Self-rotation rate [rev/s]. Reserved for
            RCS-side micro-Doppler coupling (Phase 2.7); ignored by
            the Level 1 translational dynamics.

    Raises:
        ValueError: If ``mass_kg <= 0``, ``drag_coef < 0``, or
            ``reference_area_m2 <= 0``.
    """

    mass_kg: float
    drag_coef: float = 0.4
    reference_area_m2: float = 0.05
    initial_velocity_mps: tuple[float, float, float] = (0.0, 0.0, 0.0)
    spin_rate_rps: float = 0.0

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
        if len(self.initial_velocity_mps) != 3:
            msg = (
                f"initial_velocity_mps must be a 3-tuple, got "
                f"length {len(self.initial_velocity_mps)}"
            )
            raise ValueError(msg)


def make_ballistic_force_fn(
    dynamics: BallisticDynamics,
    atm: AtmosphereState,
) -> ForceFn:
    """Build the gravity + drag force callback for a ballistic target.

    No thrust, no lift, no control — these are by definition zero for
    a ballistic trajectory.

    Args:
        dynamics: Ballistic parameters.
        atm: Atmosphere state (drives air density via ISA).

    Returns:
        Callable ``state -> (F_east, F_north, F_up)`` [N].
    """
    f_grav = gravity_force(dynamics.mass_kg)

    def force_fn(state: RigidBodyState) -> tuple[float, float, float]:
        f_drag = drag_force(
            state.velocity_enu_mps,
            drag_coef=dynamics.drag_coef,
            reference_area_m2=dynamics.reference_area_m2,
            altitude_m=state.altitude_m,
            atm=atm,
        )
        return (f_grav[0] + f_drag[0], f_grav[1] + f_drag[1], f_grav[2] + f_drag[2])

    return force_fn
