"""Multi-scatterer extended target with glint (plan/14 § 14.10).

Phase 2.7 — replaces the v0.27 point-target model with a coherent sum
of body-frame scatterers. Glint (the wandering of the apparent target
centroid as scatterer phases combine and recombine) emerges
automatically from the sum and drives the angle-noise term that the
monopulse tracker (Phase 2.6b / 2.8) has to fight.

Body frame convention (aerospace standard):

- ``x`` forward (along the nose axis).
- ``y`` right (right wing for an aircraft, starboard for a ship).
- ``z`` down (toward the ground at zero attitude).

World frame is ENU (Map). Attitude angles follow the project
convention (plan/12 § 12.4): ``yaw`` = clockwise from North about the
Up axis, ``pitch`` nose-up, ``roll`` right-wing-down. At zero
attitude the body axes line up as

- body x (forward) = +North
- body y (right)   = +East
- body z (down)    = -Up

so :func:`body_to_world_rotation` returns the matrix that takes a
body offset and produces an ENU offset, ready to be added to the
target's ENU position.

Scope (plan/14 § 14.10.7 MVP):

- Per-scatterer constant RCS (dBsm) and body-frame offset.
- Body → world rotation by current attitude.
- Coherent sum of scatterer phases (round-trip 4 pi R / lambda).
- Amplitude-weighted apparent centroid (glint).

Out of MVP (plan/14 § 14.10.7 MVP+alpha):

- Aspect-dependent / frequency-dependent / polarimetric scatterer RCS.
- Micro-Doppler from rotating parts (rotor, propeller).
- Range glint (range jitter from extended target spread).
- Stochastic Swerling fluctuation layered on top.

References:

- plan/14 § 14.10 — Multi-scatterer + Glint MVP.
- Skolnik, *Radar Handbook* 3e, ch.18 — Glint / angle noise.
- Mahafza, *Radar Systems Analysis and Design Using MATLAB*, ch.13.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray

C_LIGHT_M_S: Final[float] = 299_792_458.0
"""SI exact speed of light [m/s]. Shared with antenna / fmcw / multipath."""


# ---------------------------------------------------------------------
# Scatterer / ExtendedTarget dataclasses
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Scatterer:
    """Single body-frame scatterer (plan/14 § 14.10.2).

    Attributes:
        offset_body_m: Position in body frame
            ``(x_forward, y_right, z_down)`` [m]. Length must be 3.
        rcs_dbsm: Linear RCS at this point [dBsm]. Combined with the
            other scatterers via coherent phase sum at the radar.
        label: Optional debug tag (e.g. ``"nose"``, ``"wing_tip_left"``).
            Editor presets fill this; runtime ignores it.

    Raises:
        ValueError: If ``offset_body_m`` is not a 3-tuple.
    """

    offset_body_m: tuple[float, float, float]
    rcs_dbsm: float
    label: str = ""

    def __post_init__(self) -> None:
        if len(self.offset_body_m) != 3:
            msg = f"offset_body_m must be a 3-tuple, got length {len(self.offset_body_m)}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ExtendedTarget:
    """Multi-scatterer extended target (plan/14 § 14.10.2).

    Attributes:
        target_id: Stable identifier — typically reused from
            :class:`workbench.domain.target.TargetEntity.placement.entity_id`
            but kept as a free string here so the physics layer does
            not depend on domain (plan/02 § 2.5).
        scatterers: Tuple of body-frame :class:`Scatterer` samples,
            length >= 1. MVP presets use 3-5 (plan/14 § 14.10.3).

    Raises:
        ValueError: If ``target_id`` is empty or ``scatterers`` is empty.
    """

    target_id: str
    scatterers: tuple[Scatterer, ...]

    def __post_init__(self) -> None:
        if not self.target_id:
            msg = "target_id must be a non-empty string"
            raise ValueError(msg)
        if not self.scatterers:
            msg = "scatterers must contain at least one Scatterer"
            raise ValueError(msg)

    @property
    def total_rcs_dbsm(self) -> float:
        """Incoherent-average total RCS [dBsm] (plan/14 § 14.10.2).

        ``10 * log10(sum(10 ** (s.rcs_dbsm / 10)))`` — equivalent to
        adding the linear cross-sections and converting back.
        """
        rcs_linear = sum(math.pow(10.0, s.rcs_dbsm / 10.0) for s in self.scatterers)
        return 10.0 * math.log10(rcs_linear)


@dataclass(frozen=True, slots=True)
class ScatteringResult:
    """Output of :func:`compute_extended_target_return`.

    Attributes:
        total_signal: Coherent sum of scatterer contributions [complex].
            ``|total_signal|`` is the relative amplitude reaching the
            radar; ``arg(total_signal)`` carries the phase used by
            monopulse and Doppler models.
        apparent_position_m: Amplitude-weighted centroid in ENU [m].
            What the tracker actually points at.
        glint_offset_m: ``apparent_position_m - target_state position``
            in ENU [m]. The instantaneous angle-noise contribution.
    """

    total_signal: complex
    apparent_position_m: tuple[float, float, float]
    glint_offset_m: tuple[float, float, float]


# ---------------------------------------------------------------------
# Body -> ENU rotation
# ---------------------------------------------------------------------


def body_to_world_rotation(
    yaw_rad: float,
    pitch_rad: float,
    roll_rad: float,
) -> NDArray[np.float64]:
    """Body-frame to ENU rotation matrix.

    Body frame: ``x`` forward, ``y`` right, ``z`` down. World: ENU.
    Angles follow the project convention — yaw CW from North about
    +Up, pitch nose-up, roll right-wing-down.

    At zero attitude:

    - body x (forward) -> +North = (0, 1, 0) ENU
    - body y (right)   -> +East  = (1, 0, 0) ENU
    - body z (down)    -> -Up    = (0, 0, -1) ENU

    Composition order (intrinsic ZYX): yaw, then pitch about the
    rotated right axis, then roll about the rotated forward axis.

    Args:
        yaw_rad: CW from North about Up [rad].
        pitch_rad: Nose-up about right [rad].
        roll_rad: Right-wing-down about forward [rad].

    Returns:
        ``3 x 3`` numpy array ``R`` such that
        ``offset_world_enu = R @ offset_body``.
    """
    sy = math.sin(yaw_rad)
    cy = math.cos(yaw_rad)
    sp = math.sin(pitch_rad)
    cp = math.cos(pitch_rad)
    sr = math.sin(roll_rad)
    cr = math.cos(roll_rad)

    # body axes in ENU before applying roll
    bx = np.array([sy * cp, cy * cp, sp], dtype=np.float64)
    by_no_roll = np.array([cy, -sy, 0.0], dtype=np.float64)
    bz_no_roll = np.array([sy * sp, cy * sp, -cp], dtype=np.float64)

    # roll rotates body y / body z about body x
    by = by_no_roll * cr + bz_no_roll * sr
    bz = -by_no_roll * sr + bz_no_roll * cr

    # column-stacked rotation matrix
    return np.column_stack((bx, by, bz))


# ---------------------------------------------------------------------
# Coherent multi-scatterer return
# ---------------------------------------------------------------------


def compute_extended_target_return(
    radar_position_enu_m: tuple[float, float, float],
    target: ExtendedTarget,
    target_position_enu_m: tuple[float, float, float],
    target_attitude_rad: tuple[float, float, float],
    frequency_hz: float,
) -> ScatteringResult:
    """Coherent sum of scatterer contributions (plan/14 § 14.10.4).

    For each scatterer:

    1. Rotate body offset to ENU via :func:`body_to_world_rotation`.
    2. Place the scatterer at ``target_position + offset_world``.
    3. Round-trip phase ``phi = 4 pi R / lambda``.
    4. Amplitude ``A = sqrt(sigma_linear) / R^2`` (1/R^2 spreading; the
       monostatic radar equation is ``Pr ~ sigma / R^4``, so the
       amplitude scales as ``sqrt(sigma) / R^2``).
    5. Contribution ``A * exp(-j phi)``.

    Apparent centroid = ``sum(|contribution_i| * pos_i) / sum(|contribution_i|)``
    — amplitude-weighted, identical to the Skolnik definition of
    apparent target position. Glint is the offset between the
    apparent centroid and the target reference point.

    Args:
        radar_position_enu_m: Radar position in Map ENU [m].
        target: Body-frame scatterer cloud.
        target_position_enu_m: Target reference position in Map ENU [m].
            Glint offset is measured from this point.
        target_attitude_rad: ``(yaw, pitch, roll)`` in the project
            convention (CW-from-N / nose-up / right-wing-down).
        frequency_hz: Radar carrier frequency [Hz]. Must be > 0.

    Returns:
        :class:`ScatteringResult` with total_signal, apparent_position_m,
        glint_offset_m.

    Raises:
        ValueError: If ``frequency_hz <= 0`` or any scatterer falls
            on top of the radar (zero range -> divide-by-zero).
    """
    if frequency_hz <= 0.0:
        msg = f"frequency_hz must be > 0, got {frequency_hz}"
        raise ValueError(msg)

    yaw, pitch, roll = target_attitude_rad
    rotation = body_to_world_rotation(yaw, pitch, roll)
    target_pos = np.asarray(target_position_enu_m, dtype=np.float64)
    radar_pos = np.asarray(radar_position_enu_m, dtype=np.float64)
    wavelength = C_LIGHT_M_S / frequency_hz

    coherent_sum = 0j
    weighted_position = np.zeros(3, dtype=np.float64)
    total_amplitude = 0.0

    for s in target.scatterers:
        offset_body = np.asarray(s.offset_body_m, dtype=np.float64)
        scatterer_pos = target_pos + rotation @ offset_body
        delta = scatterer_pos - radar_pos
        range_m = float(np.linalg.norm(delta))
        if range_m == 0.0:
            msg = f"scatterer '{s.label}' coincides with radar (range = 0); cannot compute return."
            raise ValueError(msg)

        # Round-trip phase: 2 * (one-way) = 4 pi R / lambda.
        phase = 4.0 * math.pi * range_m / wavelength
        amplitude = math.sqrt(math.pow(10.0, s.rcs_dbsm / 10.0)) / (range_m * range_m)
        contribution = amplitude * complex(math.cos(phase), -math.sin(phase))

        coherent_sum += contribution
        weight = abs(contribution)
        weighted_position += weight * scatterer_pos
        total_amplitude += weight

    # Pathological else-branch — total_amplitude == 0 only if every
    # scatterer is infinitely far. We already reject zero range, so
    # the divisor is positive in practice; the fallback to target_pos
    # exists to keep the ScatteringResult well-formed in that limit.
    apparent = weighted_position / total_amplitude if total_amplitude > 0.0 else target_pos.copy()

    glint = apparent - target_pos

    return ScatteringResult(
        total_signal=coherent_sum,
        apparent_position_m=(float(apparent[0]), float(apparent[1]), float(apparent[2])),
        glint_offset_m=(float(glint[0]), float(glint[1]), float(glint[2])),
    )
