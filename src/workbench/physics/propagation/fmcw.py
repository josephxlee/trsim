"""FMCW Triangle waveform primitives — beat freq, Doppler, pairing.

Phase 1.3 first signal-processing module. Pure math relationships between
radar parameters and beat / Doppler frequencies. No signal synthesis or
FFT here — those wrap numpy and live in higher-level modules (Phase 2+).

References:

- Skolnik, M. (2008). *Radar Handbook*, 3rd ed., Ch. 7 (FMCW).
- Mahafza, B. (2013). *Radar Systems Analysis & Design Using MATLAB*, Ch. 5.
- plan/08 § 8.3 — TRsim FMCW Triangle waveform definition.

Sign convention (approaching target = positive radial velocity):

- Doppler shift: ``f_D = 2·v_r·f_c / c``  (positive when approaching).
- Sweep slope: ``alpha = B / T_sweep``  [Hz/s].
- Round-trip delay: ``tau = 2·R / c``  [s].
- UP sweep beat:   ``f_b_up   = alpha·tau - f_D``  (approaching target lowers up beat).
- DOWN sweep beat: ``f_b_down = alpha·tau + f_D``  (approaching target raises down beat).
- Pairing inverse:
    ``alpha·tau = (f_b_up + f_b_down) / 2``  -> range component.
    ``f_D = (f_b_down - f_b_up) / 2``  -> velocity component.

Range / velocity from pairing:

    ``R         = (alpha·tau) · c / (2·alpha) = f_R · c · T_sweep / (2·B)``
    ``v_radial  = f_D · c / (2·f_c)``

All frequencies in Hz, ranges in m, times in s, velocities in m/s, unless
the function name says otherwise.
"""

from __future__ import annotations

from typing import Final

C_LIGHT_M_S: Final[float] = 299_792_458.0
"""Speed of light in vacuum [m/s] (SI exact)."""


# ---------------------------------------------------------------------------
# Forward direction — physical observable from radar parameters
# ---------------------------------------------------------------------------


def beat_freq_from_range(
    range_m: float,
    bandwidth_hz: float,
    sweep_period_s: float,
) -> float:
    """Beat frequency for a stationary target on a single linear sweep.

    ``f_beat = alpha · tau = (B / T) · (2R / c) = 2·R·B / (c · T)``.

    Args:
        range_m: Target slant range [m], must be >= 0.
        bandwidth_hz: Sweep bandwidth ``B`` [Hz], > 0.
        sweep_period_s: Single-sweep duration ``T`` [s], > 0.

    Returns:
        Beat frequency [Hz] (always non-negative for non-negative inputs).
    """
    return 2.0 * range_m * bandwidth_hz / (C_LIGHT_M_S * sweep_period_s)


def doppler_freq(v_radial_m_s: float, carrier_freq_hz: float) -> float:
    """Two-way Doppler shift for a radial velocity.

    ``f_D = 2·v_r·f_c / c``.

    Args:
        v_radial_m_s: Radial velocity [m/s], positive when target approaches.
        carrier_freq_hz: Carrier frequency ``f_c`` [Hz].

    Returns:
        Doppler shift [Hz] (positive when approaching, negative when receding).
    """
    return 2.0 * v_radial_m_s * carrier_freq_hz / C_LIGHT_M_S


def fmcw_triangle_beats(
    range_m: float,
    v_radial_m_s: float,
    bandwidth_hz: float,
    sweep_period_s: float,
    carrier_freq_hz: float,
) -> tuple[float, float]:
    """Predict UP / DOWN beat frequencies for a moving target.

    ``f_b_up   = alpha·tau - f_D``
    ``f_b_down = alpha·tau + f_D``

    Useful for synthesising the expected beat pair from ground truth
    in tests, and for validating the pairing inverse via round-trip.

    Args:
        range_m: Target slant range [m].
        v_radial_m_s: Radial velocity [m/s], positive = approaching.
        bandwidth_hz: Sweep bandwidth ``B`` [Hz].
        sweep_period_s: Single-sweep duration ``T`` [s].
        carrier_freq_hz: Carrier frequency ``f_c`` [Hz].

    Returns:
        ``(f_beat_up_hz, f_beat_down_hz)``.
    """
    f_range = beat_freq_from_range(range_m, bandwidth_hz, sweep_period_s)
    f_doppler = doppler_freq(v_radial_m_s, carrier_freq_hz)
    return f_range - f_doppler, f_range + f_doppler


# ---------------------------------------------------------------------------
# Inverse direction — pairing two beats into range + velocity
# ---------------------------------------------------------------------------


def beat_pair_to_range_velocity(
    f_beat_up_hz: float,
    f_beat_down_hz: float,
    bandwidth_hz: float,
    sweep_period_s: float,
    carrier_freq_hz: float,
) -> tuple[float, float]:
    """FMCW Triangle pairing — recover range and radial velocity.

    Inverts :func:`fmcw_triangle_beats`. The pairing assumption is that
    both beats correspond to the same physical target on consecutive
    UP and DOWN sweeps (no MTI / migration during the pair).

    Args:
        f_beat_up_hz: UP sweep beat [Hz].
        f_beat_down_hz: DOWN sweep beat [Hz].
        bandwidth_hz: Sweep bandwidth ``B`` [Hz], > 0.
        sweep_period_s: Single-sweep duration ``T`` [s], > 0.
        carrier_freq_hz: Carrier frequency ``f_c`` [Hz], > 0.

    Returns:
        ``(range_m, v_radial_m_s)`` — radial velocity is positive when
        the target approaches.
    """
    f_range_hz = (f_beat_up_hz + f_beat_down_hz) / 2.0
    f_doppler_hz = (f_beat_down_hz - f_beat_up_hz) / 2.0
    range_m = f_range_hz * C_LIGHT_M_S * sweep_period_s / (2.0 * bandwidth_hz)
    v_radial_m_s = f_doppler_hz * C_LIGHT_M_S / (2.0 * carrier_freq_hz)
    return range_m, v_radial_m_s


# ---------------------------------------------------------------------------
# Resolutions — fundamental limits set by waveform parameters
# ---------------------------------------------------------------------------


def range_resolution_m(bandwidth_hz: float) -> float:
    """Range resolution from sweep bandwidth.

    ``ΔR = c / (2·B)``. E.g., ``B = 100 MHz`` → ``ΔR ≈ 1.4990 m``.

    Args:
        bandwidth_hz: Sweep bandwidth [Hz], > 0.

    Returns:
        Range resolution [m].
    """
    return C_LIGHT_M_S / (2.0 * bandwidth_hz)


def doppler_resolution_hz(observation_period_s: float) -> float:
    """Doppler frequency resolution from coherent processing interval.

    ``Δf_D = 1 / T_obs``.

    Args:
        observation_period_s: Total coherent observation time [s], > 0.

    Returns:
        Doppler frequency resolution [Hz].
    """
    return 1.0 / observation_period_s


def velocity_resolution_m_s(
    observation_period_s: float,
    carrier_freq_hz: float,
) -> float:
    """Radial velocity resolution from observation time and carrier.

    ``Δv = λ / (2·T_obs) = c / (2·f_c·T_obs)``.

    Args:
        observation_period_s: Total coherent observation time [s], > 0.
        carrier_freq_hz: Carrier frequency [Hz], > 0.

    Returns:
        Radial velocity resolution [m/s].
    """
    return C_LIGHT_M_S / (2.0 * carrier_freq_hz * observation_period_s)


def wavelength_m(carrier_freq_hz: float) -> float:
    """Wavelength ``λ = c / f_c`` [m]."""
    return C_LIGHT_M_S / carrier_freq_hz
