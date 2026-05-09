"""External-force model for target dynamics (plan/14 § 14.4).

Phase 2.4b — gravity, drag, lift, thrust, and reference-tracking
control. All functions are pure: they take the current state plus the
relevant parameters and return a force 3-tuple in the Map ENU frame.
The integrator (Phase 2.4c) sums them and advances the state.

Conventions:

- Forces are 3-tuples ``(east, north, up)`` in Newtons.
- Velocity inputs are ENU 3-tuples in m/s.
- Air density comes from
  :func:`workbench.physics.atmosphere.isa_density` so dynamics and
  propagation share one atmosphere model (plan/15 § 15.1 cross-influence).
- Newtons are tagged ``_n`` (e.g. ``thrust_n``) following the
  ``quantity_unit`` snake-case convention used elsewhere in the
  codebase (``mass_kg``, ``range_m``, ``velocity_mps``).

MVP scope (plan/14 § 14.2.2 Level 1):

- ``gravity_force``: standard 9.80665 m/s^2, no latitude / altitude
  dependence.
- ``drag_force``: ``F = -1/2 * rho * v^2 * Cd * A`` along ``-v_hat``.
- ``lift_force``: simple altitude PD (mg trim + altitude PD), purely
  vertical. AoA-based lift is Level 2.
- ``thrust_force``: ``ThrustProfile`` of kind ``CONSTANT`` (always-on)
  or ``CURVE`` (linear interpolation between samples). Multi-stage
  rockets are MVP+alpha.
- ``control_force``: PD on horizontal position (east/north only). The
  vertical channel is handled by ``lift_force`` to avoid double-PD on
  altitude.

References:

- plan/14 § 14.4 — Force-field model (gravity / drag / lift / thrust /
  control).
- plan/15 § 15.3 — Atmosphere model.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Final

from workbench.physics.atmosphere import AtmosphereState, isa_density

# Standard gravitational acceleration (ICAO 1976) [m/s^2].
# Same value as workbench.physics.atmosphere.ISA_G_M_PER_S2 — duplicated
# locally rather than imported because this module is force-centric and
# the import would create a cosmetic cross-dependency.
G_STANDARD_M_PER_S2: Final[float] = 9.80665

# Speed below which drag is treated as zero (matches plan/14 § 14.4.2
# example code: avoids ``v_hat = v / 0`` for stationary targets).
_DRAG_STATIONARY_SPEED_MPS: Final[float] = 0.01


# --- Gravity ----------------------------------------------------------


def gravity_force(mass_kg: float) -> tuple[float, float, float]:
    """Standard gravity in ENU [N] (plan/14 § 14.4.1).

    Returns ``(0, 0, -m * g)`` — gravity always points along ``-Up``.

    Args:
        mass_kg: Target mass [kg]. Must be > 0.

    Returns:
        Force 3-tuple ``(east, north, up)`` [N].

    Raises:
        ValueError: If ``mass_kg <= 0``.
    """
    if mass_kg <= 0.0:
        msg = f"mass_kg must be > 0, got {mass_kg}"
        raise ValueError(msg)
    return (0.0, 0.0, -mass_kg * G_STANDARD_M_PER_S2)


# --- Drag -------------------------------------------------------------


def drag_force(
    velocity_mps: tuple[float, float, float],
    drag_coef: float,
    reference_area_m2: float,
    altitude_m: float,
    atm: AtmosphereState,
) -> tuple[float, float, float]:
    """Aerodynamic drag in ENU [N] (plan/14 § 14.4.2).

    Magnitude: ``F = 1/2 * rho * v^2 * Cd * A``. Direction: opposite
    to the velocity vector (``-v_hat``). Air density comes from the
    shared ISA model in ``workbench.physics.atmosphere``.

    Args:
        velocity_mps: ENU velocity 3-tuple [m/s].
        drag_coef: Dimensionless drag coefficient ``Cd``. Must be >= 0.
        reference_area_m2: Reference area ``A`` (wing / cross-section)
            [m^2]. Must be > 0.
        altitude_m: Altitude above the Map vertical reference [m]. Used
            to look up ISA air density.
        atm: Map-level atmosphere state (sea-level T/P, rain).

    Returns:
        Force 3-tuple ``(east, north, up)`` [N].

    Raises:
        ValueError: If ``drag_coef < 0`` or ``reference_area_m2 <= 0``.
    """
    if drag_coef < 0.0:
        msg = f"drag_coef must be >= 0, got {drag_coef}"
        raise ValueError(msg)
    if reference_area_m2 <= 0.0:
        msg = f"reference_area_m2 must be > 0, got {reference_area_m2}"
        raise ValueError(msg)

    speed = math.sqrt(
        velocity_mps[0] * velocity_mps[0]
        + velocity_mps[1] * velocity_mps[1]
        + velocity_mps[2] * velocity_mps[2]
    )
    if speed < _DRAG_STATIONARY_SPEED_MPS:
        return (0.0, 0.0, 0.0)

    rho = isa_density(altitude_m, atm)
    f_mag = 0.5 * rho * speed * speed * drag_coef * reference_area_m2
    inv_speed = 1.0 / speed
    return (
        -f_mag * velocity_mps[0] * inv_speed,
        -f_mag * velocity_mps[1] * inv_speed,
        -f_mag * velocity_mps[2] * inv_speed,
    )


# --- Lift -------------------------------------------------------------


def lift_force(
    mass_kg: float,
    altitude_m: float,
    target_altitude_m: float,
    velocity_up_mps: float,
    *,
    kp_altitude: float,
    kd_altitude: float,
) -> tuple[float, float, float]:
    """Vertical lift force [N] (plan/14 § 14.4.3, MVP Level 1).

    Decomposes into two parts:

    - **Trim**: ``F = m * g`` along +Up — keeps the target level in
      steady flight.
    - **PD altitude tracker**: ``F = kp * (h_ref - h) - kd * v_up`` —
      drives altitude toward the reference. ``v_up`` damps overshoot.

    Both pieces are applied along the +Up axis. Lateral (lift)
    components from bank angle are Level 2 — at Level 1 the controller
    is purely vertical.

    Args:
        mass_kg: Target mass [kg]. Must be > 0.
        altitude_m: Current altitude [m].
        target_altitude_m: Reference altitude [m].
        velocity_up_mps: Current vertical velocity [m/s].
        kp_altitude: Altitude proportional gain [N/m]. Must be >= 0.
        kd_altitude: Altitude derivative (damping) gain [N/(m/s)].
            Must be >= 0.

    Returns:
        Force 3-tuple ``(east=0, north=0, up=F)`` [N].

    Raises:
        ValueError: If ``mass_kg <= 0`` or any gain is negative.
    """
    if mass_kg <= 0.0:
        msg = f"mass_kg must be > 0, got {mass_kg}"
        raise ValueError(msg)
    if kp_altitude < 0.0:
        msg = f"kp_altitude must be >= 0, got {kp_altitude}"
        raise ValueError(msg)
    if kd_altitude < 0.0:
        msg = f"kd_altitude must be >= 0, got {kd_altitude}"
        raise ValueError(msg)

    f_trim = mass_kg * G_STANDARD_M_PER_S2
    altitude_error = target_altitude_m - altitude_m
    f_control = kp_altitude * altitude_error - kd_altitude * velocity_up_mps
    return (0.0, 0.0, f_trim + f_control)


# --- Thrust -----------------------------------------------------------


class ThrustProfileKind(Enum):
    """Form of a thrust-time profile (plan/14 § 14.4.4)."""

    CONSTANT = "constant"
    CURVE = "curve"
    # STAGE = "stage"  # Multi-stage rockets — MVP+alpha (plan/14 § 14.4.4).


@dataclass(frozen=True, slots=True)
class ThrustProfile:
    """Time-varying thrust magnitude (plan/14 § 14.4.4).

    Two MVP forms:

    - ``CONSTANT``: ``thrust_at(t) = constant_thrust_n`` for all ``t``.
    - ``CURVE``: piecewise-linear interpolation across ``curve``
      samples ``((t_s, thrust_n), ...)``. Times must be strictly
      increasing. Outside the time range, the boundary value is held
      (no extrapolation).

    Attributes:
        kind: Profile form.
        constant_thrust_n: Thrust [N] when ``kind == CONSTANT``. Must
            be >= 0. Ignored otherwise.
        curve: ``((t_s, thrust_n), ...)`` samples when ``kind ==
            CURVE``. Length >= 2 with strictly increasing ``t_s`` and
            ``thrust_n >= 0``. Ignored otherwise.

    Raises:
        ValueError: On invalid combinations (negative thrust, missing
            curve samples, non-monotonic time, etc.).
    """

    kind: ThrustProfileKind
    constant_thrust_n: float = 0.0
    curve: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        if self.kind is ThrustProfileKind.CONSTANT:
            if self.constant_thrust_n < 0.0:
                msg = f"constant_thrust_n must be >= 0, got {self.constant_thrust_n}"
                raise ValueError(msg)
        elif self.kind is ThrustProfileKind.CURVE:
            if len(self.curve) < 2:
                msg = f"CURVE thrust profile needs at least 2 samples, got {len(self.curve)}"
                raise ValueError(msg)
            prev_t = float("-inf")
            for i, (t, n) in enumerate(self.curve):
                if t <= prev_t:
                    msg = f"curve[{i}].t_s = {t} not strictly increasing (prev = {prev_t})"
                    raise ValueError(msg)
                if n < 0.0:
                    msg = f"curve[{i}].thrust_n = {n} must be >= 0"
                    raise ValueError(msg)
                prev_t = t

    def thrust_at(self, sim_t_s: float) -> float:
        """Thrust magnitude at ``sim_t_s`` [N].

        - CONSTANT: returns ``constant_thrust_n`` for any ``sim_t_s``.
        - CURVE: linear interpolation between the two enclosing
          samples; clamps to the first/last value outside the range.
        """
        if self.kind is ThrustProfileKind.CONSTANT:
            return self.constant_thrust_n
        # CURVE
        first_t, first_n = self.curve[0]
        if sim_t_s <= first_t:
            return first_n
        last_t, last_n = self.curve[-1]
        if sim_t_s >= last_t:
            return last_n
        # Walk segments (curve is short — typically < 10 entries).
        for i in range(len(self.curve) - 1):
            t0, n0 = self.curve[i]
            t1, n1 = self.curve[i + 1]
            if t0 <= sim_t_s <= t1:
                # Linear interpolation. t1 > t0 is guaranteed by post-init.
                w = (sim_t_s - t0) / (t1 - t0)
                return n0 + w * (n1 - n0)
        # Unreachable — sim_t_s is bracketed by the two clamps above.
        return last_n


def thrust_force(
    profile: ThrustProfile,
    sim_t_s: float,
    forward_direction: tuple[float, float, float],
) -> tuple[float, float, float]:
    """Thrust force in ENU [N] (plan/14 § 14.4.4).

    ``F = thrust_at(t) * forward_unit_vector``. Caller is responsible
    for passing a unit vector — typically derived from
    :func:`workbench.physics.dynamics.rigid_body.attitude_from_velocity`
    or the body x-axis under the current attitude. We do **not**
    normalize for the caller because over an integration sub-step the
    forward direction is reused for several force calls and the
    callers can normalize once.

    Args:
        profile: Thrust profile.
        sim_t_s: Simulation time at which to sample the profile [s].
        forward_direction: Unit vector ``(east, north, up)`` along
            which thrust is applied.

    Returns:
        Force 3-tuple ``(east, north, up)`` [N].
    """
    f_mag = profile.thrust_at(sim_t_s)
    return (
        f_mag * forward_direction[0],
        f_mag * forward_direction[1],
        f_mag * forward_direction[2],
    )


# --- Control (reference-tracking PD on horizontal position) ----------


def control_force(
    east_m: float,
    north_m: float,
    velocity_east_mps: float,
    velocity_north_mps: float,
    ref_east_m: float,
    ref_north_m: float,
    *,
    kp_position: float,
    kd_position: float,
    max_accel_n: float,
) -> tuple[float, float, float]:
    """Horizontal reference-tracking PD force [N] (plan/14 § 14.4.5).

    Vertical channel is intentionally zero — altitude is closed by
    :func:`lift_force`. Horizontal force per axis:

    ``F_axis = clamp(kp * (ref - pos) - kd * v, +-max_accel_n)``

    The clamp keeps an aggressive reference change from producing
    physically impossible accelerations (``max_accel_n`` represents the
    target's maximum maneuver capability).

    Args:
        east_m: Current east position [m].
        north_m: Current north position [m].
        velocity_east_mps: Current east velocity [m/s].
        velocity_north_mps: Current north velocity [m/s].
        ref_east_m: Reference east position [m].
        ref_north_m: Reference north position [m].
        kp_position: Position gain [N/m]. Must be >= 0.
        kd_position: Velocity gain [N/(m/s)]. Must be >= 0.
        max_accel_n: Per-axis force clamp [N]. Must be >= 0.

    Returns:
        Force 3-tuple ``(east, north, up=0)`` [N].

    Raises:
        ValueError: If any gain or ``max_accel_n`` is negative.
    """
    if kp_position < 0.0:
        msg = f"kp_position must be >= 0, got {kp_position}"
        raise ValueError(msg)
    if kd_position < 0.0:
        msg = f"kd_position must be >= 0, got {kd_position}"
        raise ValueError(msg)
    if max_accel_n < 0.0:
        msg = f"max_accel_n must be >= 0, got {max_accel_n}"
        raise ValueError(msg)

    f_east = kp_position * (ref_east_m - east_m) - kd_position * velocity_east_mps
    f_north = kp_position * (ref_north_m - north_m) - kd_position * velocity_north_mps

    f_east = max(-max_accel_n, min(max_accel_n, f_east))
    f_north = max(-max_accel_n, min(max_accel_n, f_north))

    return (f_east, f_north, 0.0)
