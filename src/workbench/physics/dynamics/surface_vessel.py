"""Surface-vessel kinematics — sea-state coupled motion (plan/14 § 14.5.4).

Phase 2.4f (SURFACE_VESSEL half) — kinematic, **not** force-integrated.
The trajectory CSV drives horizontal motion directly (no PD reference
tracking); the sea-state environment drives vertical heave + roll +
pitch via a second-order coupling defined per entity (plan/12 § 12.5).

Why kinematic at MVP: surface vessels in a tracking-radar simulator
move slowly relative to the radar's update rate; user-supplied waypoint
trajectories are precise enough as ground truth. The wave-coupled
attitude wobble is what actually matters for echo modulation.
Force-based ship dynamics (acceleration limits, displacement-based
drag) is MVP+alpha (plan/14 § 14.5.4).

Z handling (plan/14 § 14.7.3): trajectory ``altitude_m`` is **ignored**
— the simulation z is ``sea_surface_z_m + heave_oscillation``.

References:

- plan/14 § 14.5.4 — SURFACE_VESSEL motion model.
- plan/12 § 12.5 — SeaStateEnvironment / WaveResponseModel split.
- plan/03 § 3.2.1e — WaveResponseModel domain dataclass (the
  physics-side :class:`WaveCoupling` mirrors its three factor fields).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from workbench.physics.dynamics.reference import (
    Waypoint,
    interpolate_reference,
    reference_velocity_enu,
)
from workbench.physics.dynamics.rigid_body import RigidBodyState


@dataclass(frozen=True, slots=True)
class WaveCoupling:
    """Per-entity wave-coupling factors (plan/12 § 12.5.2).

    Physics-layer mirror of the three factor fields on
    :class:`workbench.domain.wave_response.WaveResponseModel`.
    Duplicated here so the physics layer does not import from domain
    (plan/02 § 2.5).

    Attributes:
        heave_factor: Vertical-axis coupling [0..1]. ``0`` is rigid;
            ``1`` heaves the full surface amplitude.
        pitch_factor: Pitch coupling [rad / m wave amplitude]. Must
            be >= 0.
        roll_factor: Roll coupling [rad / m wave amplitude]. Must be
            >= 0.

    Raises:
        ValueError: If any factor is outside its valid range.
    """

    heave_factor: float = 0.0
    pitch_factor: float = 0.0
    roll_factor: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.heave_factor <= 1.0:
            msg = f"heave_factor must be in [0, 1], got {self.heave_factor}"
            raise ValueError(msg)
        if self.pitch_factor < 0.0:
            msg = f"pitch_factor must be >= 0, got {self.pitch_factor}"
            raise ValueError(msg)
        if self.roll_factor < 0.0:
            msg = f"roll_factor must be >= 0, got {self.roll_factor}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SurfaceVesselDynamics:
    """Surface-vessel kinematic parameters (plan/14 § 14.5.4).

    Attributes:
        wave_coupling: Per-entity heave / pitch / roll factors.
    """

    wave_coupling: WaveCoupling


def wave_oscillation(
    coupling: WaveCoupling,
    wave_amplitude_m: float,
    wave_period_s: float,
    sim_t_s: float,
) -> tuple[float, float, float]:
    """Sinusoidal wave heave + roll + pitch at ``sim_t_s``.

    Single-frequency model: ``base = A * sin(omega * t)`` where
    ``omega = 2 * pi / period`` and ``A`` is the sea-surface
    amplitude. The coupling factors scale ``base`` into entity-frame
    heave [m] and roll / pitch [rad].

    Phase between roll and pitch is intentionally zero in this MVP —
    they oscillate together. A more realistic model (90-deg phase,
    different periods for pitch vs heave) is MVP+alpha.

    Args:
        coupling: Per-entity wave coupling factors.
        wave_amplitude_m: Sea-surface amplitude [m].
        wave_period_s: Wave period [s]. ``<= 0`` returns no oscillation.
        sim_t_s: Sample time [s].

    Returns:
        ``(heave_m, roll_rad, pitch_rad)``.
    """
    if wave_period_s <= 0.0 or wave_amplitude_m == 0.0:
        return (0.0, 0.0, 0.0)
    omega = 2.0 * math.pi / wave_period_s
    base = wave_amplitude_m * math.sin(omega * sim_t_s)
    return (
        coupling.heave_factor * base,
        coupling.roll_factor * base,
        coupling.pitch_factor * base,
    )


def wave_heave_velocity_mps(
    coupling: WaveCoupling,
    wave_amplitude_m: float,
    wave_period_s: float,
    sim_t_s: float,
) -> float:
    """Vertical heave velocity [m/s] — derivative of :func:`wave_oscillation`.

    ``v_heave = omega * A * heave_factor * cos(omega * t)``. Used to
    populate ``velocity_up_mps`` so radar Doppler picks up the
    vertical wobble.
    """
    if wave_period_s <= 0.0 or wave_amplitude_m == 0.0:
        return 0.0
    omega = 2.0 * math.pi / wave_period_s
    return coupling.heave_factor * wave_amplitude_m * omega * math.cos(omega * sim_t_s)


def surface_vessel_pose(
    dynamics: SurfaceVesselDynamics,
    trajectory: tuple[Waypoint, ...],
    *,
    sea_surface_z_m: float,
    wave_amplitude_m: float,
    wave_period_s: float,
    sim_t_s: float,
) -> RigidBodyState:
    """Compute the surface-vessel state at ``sim_t_s``.

    - **xy**: linear interpolation of the trajectory waypoints (no
      force-based PD).
    - **z**: ``sea_surface_z_m + heave_oscillation`` (trajectory
      ``altitude_m`` is ignored — plan/14 § 14.7.3).
    - **velocity_xy**: piecewise-constant slope of the trajectory.
    - **velocity_up**: time derivative of the heave oscillation.
    - **roll / pitch**: wave coupling at ``sim_t_s``.
    - **yaw**: trajectory heading.

    Args:
        dynamics: Surface-vessel kinematic parameters.
        trajectory: Reference trajectory (>= 1 waypoint).
        sea_surface_z_m: Map sea-surface vertical reference [m].
        wave_amplitude_m: Sea-surface amplitude [m]. ``0`` for calm.
        wave_period_s: Wave period [s]. Must be > 0 if amplitude > 0.
        sim_t_s: Sample time [s].

    Returns:
        :class:`RigidBodyState` at ``sim_t_s``.

    Raises:
        ValueError: If ``trajectory`` is empty.
    """
    ref = interpolate_reference(trajectory, sim_t_s)
    v_e, v_n, _ = reference_velocity_enu(trajectory, sim_t_s)
    heave, roll, pitch = wave_oscillation(
        dynamics.wave_coupling, wave_amplitude_m, wave_period_s, sim_t_s
    )
    v_up = wave_heave_velocity_mps(dynamics.wave_coupling, wave_amplitude_m, wave_period_s, sim_t_s)
    return RigidBodyState(
        east_m=ref.east_m,
        north_m=ref.north_m,
        altitude_m=sea_surface_z_m + heave,
        velocity_east_mps=v_e,
        velocity_north_mps=v_n,
        velocity_up_mps=v_up,
        roll_rad=roll,
        pitch_rad=pitch,
        yaw_rad=ref.heading_rad,
        sim_t_s=sim_t_s,
    )
