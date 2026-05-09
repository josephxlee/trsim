"""Monopulse 4-channel angle estimation (plan/08 § 8.5a.4 / § 8.5a.6).

Phase 2.6b — converts the four RX channels (Σ, Δaz, Δel, Δ²) into
azimuth / elevation angle errors. Two layers:

- :func:`monopulse_error_from_channels` operates on raw complex
  channel samples (``sigma``, ``delta_az``, ``delta_el``) and the
  per-axis monopulse slopes. This is the core formula and is the
  building block higher-level pipelines call.
- :func:`monopulse_error_extended` computes the same error from a
  full :class:`workbench.physics.reflection.extended_target.ExtendedTarget`
  + radar geometry — sums each scatterer's contribution to the four
  channels and feeds the result into the core formula. This is the
  glint-aware variant that ties together Phase 2.6b and Phase 2.7.

Slope conventions (plan/08 § 8.5a.4):

- ``error_az_rad ~ k_az * Re(delta_az / sigma)``
- ``error_el_rad ~ k_el * Re(delta_el / sigma)``

The slopes ``k_az`` / ``k_el`` are calibration constants that map the
dimensionless ratio into a small-angle error. Typical values are
~1.4 rad per unit ratio for a quad-feed parabolic dish; planar-array
sub-aperture monopulse can be higher. Calibration / boresight-offset
correction is MVP+alpha (plan/08 § 8.5a.4 ``boresight_calibration``).

References:

- Sherman & Barton, *Monopulse Principles and Techniques* 2e.
- Skolnik, *Radar Handbook* 3e, ch.18 — monopulse + glint coupling.
- plan/08 § 8.5a.4 / § 8.5a.6 — TRsim monopulse abstraction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from workbench.physics.reflection.extended_target import (
    C_LIGHT_M_S,
    ExtendedTarget,
    body_to_world_rotation,
)


@dataclass(frozen=True, slots=True)
class MonopulseError:
    """Output of :func:`monopulse_error_from_channels`.

    Attributes:
        error_az_rad: Azimuth angle error from boresight [rad].
            Positive convention follows the slope sign — typically
            target right of boresight gives positive error.
        error_el_rad: Elevation angle error from boresight [rad].
            Positive convention: target above boresight.
        sum_amplitude: ``|sigma|`` — useful for downstream SNR /
            CFAR diagnostics.
    """

    error_az_rad: float
    error_el_rad: float
    sum_amplitude: float


def monopulse_error_from_channels(
    sigma: complex,
    delta_az: complex,
    delta_el: complex,
    *,
    slope_az: float,
    slope_el: float,
) -> MonopulseError:
    """Core monopulse error formula (plan/08 § 8.5a.4).

    ``error_axis = slope_axis * Re(delta_axis / sigma)``.

    The real part is taken because amplitude-comparison monopulse
    expects in-phase components (Sherman & Barton ch.4); the
    imaginary part picks up phase-comparison error which is treated
    elsewhere (MVP+alpha).

    Args:
        sigma: Complex sum-channel sample.
        delta_az: Complex azimuth-difference channel sample.
        delta_el: Complex elevation-difference channel sample.
        slope_az: Calibration slope ``k_az`` [rad / unitless ratio].
            Must be > 0.
        slope_el: Calibration slope ``k_el``. Must be > 0.

    Returns:
        :class:`MonopulseError`.

    Raises:
        ValueError: If ``slope_az`` / ``slope_el`` is non-positive,
            or ``|sigma|`` is zero (division by zero).
    """
    if slope_az <= 0.0:
        msg = f"slope_az must be > 0, got {slope_az}"
        raise ValueError(msg)
    if slope_el <= 0.0:
        msg = f"slope_el must be > 0, got {slope_el}"
        raise ValueError(msg)
    sum_amp = abs(sigma)
    if sum_amp == 0.0:
        msg = "sigma channel has zero magnitude — monopulse error undefined."
        raise ValueError(msg)

    # Re(Delta / Sigma) = Re(Delta * conj(Sigma)) / |Sigma|^2.
    sigma_conj = sigma.conjugate()
    sigma_pow = sum_amp * sum_amp
    ratio_az = (delta_az * sigma_conj).real / sigma_pow
    ratio_el = (delta_el * sigma_conj).real / sigma_pow

    return MonopulseError(
        error_az_rad=slope_az * ratio_az,
        error_el_rad=slope_el * ratio_el,
        sum_amplitude=sum_amp,
    )


# ---------------------------------------------------------------------
# Extended-target glint-aware variant
# ---------------------------------------------------------------------


def monopulse_error_extended(
    radar_position_enu_m: tuple[float, float, float],
    target: ExtendedTarget,
    target_position_enu_m: tuple[float, float, float],
    target_attitude_rad: tuple[float, float, float],
    frequency_hz: float,
    *,
    slope_az: float,
    slope_el: float,
    boresight_az_rad: float,
    boresight_el_rad: float,
) -> MonopulseError:
    """Glint-aware monopulse error for a multi-scatterer target.

    Builds the four channels from the scatterer cloud:

    - For each scatterer compute its ENU position (rotation + offset)
      and the ``(az, el)`` direction-cosines relative to the radar.
    - Project ``(az - boresight_az, el - boresight_el)`` to give a
      small off-axis angle ``(d_az, d_el)``.
    - Channel weights (small-angle approximation, plan/08 § 8.5a.4):
      sigma += amp * exp(-j phase),
      delta_az += d_az * amp * exp(-j phase),
      delta_el += d_el * amp * exp(-j phase).
    - Feed the resulting Σ / Δaz / Δel into
      :func:`monopulse_error_from_channels`.

    The angle-noise component (glint) emerges naturally from the
    coherent sum — same mechanism as
    :func:`workbench.physics.reflection.extended_target.compute_extended_target_return`.

    Args:
        radar_position_enu_m: Radar position in Map ENU [m].
        target: Body-frame scatterer cloud.
        target_position_enu_m: Target reference position [m].
        target_attitude_rad: ``(yaw, pitch, roll)``.
        frequency_hz: Carrier [Hz]. > 0.
        slope_az / slope_el: Monopulse slopes [rad / unit ratio].
        boresight_az_rad: Antenna pointing azimuth (CW from N) [rad].
        boresight_el_rad: Antenna pointing elevation [rad].

    Returns:
        :class:`MonopulseError` with the synthesised error angles.

    Raises:
        ValueError: If frequency / slopes invalid, or any scatterer
            falls on the radar (zero range).
    """
    if frequency_hz <= 0.0:
        msg = f"frequency_hz must be > 0, got {frequency_hz}"
        raise ValueError(msg)

    yaw, pitch, roll = target_attitude_rad
    rotation = body_to_world_rotation(yaw, pitch, roll)
    target_pos = np.asarray(target_position_enu_m, dtype=np.float64)
    radar_pos = np.asarray(radar_position_enu_m, dtype=np.float64)
    wavelength = C_LIGHT_M_S / frequency_hz

    sigma = 0j
    delta_az = 0j
    delta_el = 0j

    for s in target.scatterers:
        offset_body = np.asarray(s.offset_body_m, dtype=np.float64)
        scatterer_pos = target_pos + rotation @ offset_body
        delta_pos = scatterer_pos - radar_pos
        range_m = float(np.linalg.norm(delta_pos))
        if range_m == 0.0:
            msg = f"scatterer '{s.label}' coincides with radar (range = 0); monopulse undefined."
            raise ValueError(msg)

        # Direction cosines from radar (ENU vector → az / el).
        d_east = float(delta_pos[0])
        d_north = float(delta_pos[1])
        d_up = float(delta_pos[2])
        # Project (E, N) onto horizontal plane for azimuth (CW from N).
        scatterer_az_rad = math.atan2(d_east, d_north)
        horiz = math.hypot(d_east, d_north)
        scatterer_el_rad = math.atan2(d_up, horiz)

        # Off-boresight angles (small-angle approx — wraps unhandled).
        d_az = scatterer_az_rad - boresight_az_rad
        d_el = scatterer_el_rad - boresight_el_rad

        # Round-trip phase + amplitude (same as compute_extended_target_return).
        phase = 4.0 * math.pi * range_m / wavelength
        amplitude = math.sqrt(math.pow(10.0, s.rcs_dbsm / 10.0)) / (range_m * range_m)
        contribution = amplitude * complex(math.cos(phase), -math.sin(phase))

        sigma += contribution
        delta_az += d_az * contribution
        delta_el += d_el * contribution

    return monopulse_error_from_channels(
        sigma,
        delta_az,
        delta_el,
        slope_az=slope_az,
        slope_el=slope_el,
    )
