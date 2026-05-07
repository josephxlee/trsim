"""Validation tests for :mod:`workbench.physics.propagation.fmcw`.

Coverage:

- Single-sweep beat frequency from range (analytic, several params).
- Doppler shift from radial velocity (X-band examples + sign).
- Triangle beat pair forward (range + velocity → up/down beats).
- Pairing inverse — round-trip ``(R, v) → (f_up, f_down) → (R, v)``.
- Resolution formulas (range / Doppler / velocity).
- Edge cases: zero range, zero velocity, receding target.

Tolerances:

- Beat / Doppler analytic match: 1e-6 Hz absolute (sub-µHz, well within
  IEEE 754 double-precision rounding).
- Round-trips: 1e-6 m / 1e-9 m/s.

The Octave script ``docs/matlab_validation/test_fmcw.m`` produces the
same reference values via the identical formulas; goldens stay in lockstep.
"""

from __future__ import annotations

import pytest

from workbench.physics.propagation.fmcw import (
    C_LIGHT_M_S,
    beat_freq_from_range,
    beat_pair_to_range_velocity,
    doppler_freq,
    doppler_resolution_hz,
    fmcw_triangle_beats,
    range_resolution_m,
    velocity_resolution_m_s,
    wavelength_m,
)

# ---------------------------------------------------------------------------
# Constants — speed of light (SI)
# ---------------------------------------------------------------------------


def test_speed_of_light_constant() -> None:
    """SI exact value (CODATA / SI 2019)."""
    assert C_LIGHT_M_S == 299_792_458.0


# ---------------------------------------------------------------------------
# Beat frequency from range (single sweep, stationary target)
# ---------------------------------------------------------------------------


def test_beat_freq_known_case_1km_100mhz_1ms() -> None:
    """R=1 km, B=100 MHz, T=1 ms → f_beat ≈ 667.128 kHz.

    f_beat = 2·R·B / (c·T) = 2·1000·1e8 / (299_792_458·1e-3)
           = 2e11 / 299_792.458 = 667128.18450... Hz
    """
    f_beat = beat_freq_from_range(
        range_m=1000.0,
        bandwidth_hz=100e6,
        sweep_period_s=1e-3,
    )
    expected = 2.0 * 1000.0 * 100e6 / (C_LIGHT_M_S * 1e-3)
    assert f_beat == pytest.approx(expected, abs=1e-6)
    assert f_beat == pytest.approx(667128.18450, abs=1e-3)


def test_beat_freq_zero_range() -> None:
    """Zero range → zero beat (pure direct-path coupling, no sweep delay)."""
    assert beat_freq_from_range(0.0, 100e6, 1e-3) == 0.0


def test_beat_freq_linear_in_range() -> None:
    """f_beat ∝ R for fixed (B, T)."""
    b1 = beat_freq_from_range(1000.0, 100e6, 1e-3)
    b2 = beat_freq_from_range(2000.0, 100e6, 1e-3)
    assert b2 == pytest.approx(2.0 * b1, abs=1e-6)


def test_beat_freq_linear_in_bandwidth() -> None:
    """f_beat ∝ B for fixed (R, T)."""
    b1 = beat_freq_from_range(1000.0, 50e6, 1e-3)
    b2 = beat_freq_from_range(1000.0, 100e6, 1e-3)
    assert b2 == pytest.approx(2.0 * b1, abs=1e-6)


def test_beat_freq_inverse_in_sweep_period() -> None:
    """f_beat ∝ 1/T for fixed (R, B)."""
    b1 = beat_freq_from_range(1000.0, 100e6, 1e-3)
    b2 = beat_freq_from_range(1000.0, 100e6, 2e-3)
    assert b2 == pytest.approx(0.5 * b1, abs=1e-6)


# ---------------------------------------------------------------------------
# Doppler shift
# ---------------------------------------------------------------------------


def test_doppler_xband_10_mps() -> None:
    """v=10 m/s @ 9.4 GHz X-band → f_D ≈ 627.1 Hz.

    f_D = 2·v·f_c / c = 2·10·9.4e9 / 299_792_458 = 627.1218... Hz
    """
    f_d = doppler_freq(v_radial_m_s=10.0, carrier_freq_hz=9.4e9)
    expected = 2.0 * 10.0 * 9.4e9 / C_LIGHT_M_S
    assert f_d == pytest.approx(expected, abs=1e-6)
    assert f_d == pytest.approx(627.1218, abs=1e-3)


def test_doppler_zero_velocity() -> None:
    """Stationary target → zero Doppler."""
    assert doppler_freq(0.0, 9.4e9) == 0.0


def test_doppler_sign_approaching_positive() -> None:
    """Positive radial velocity (approaching) → positive Doppler shift."""
    assert doppler_freq(50.0, 9.4e9) > 0.0


def test_doppler_sign_receding_negative() -> None:
    """Negative radial velocity (receding) → negative Doppler shift."""
    assert doppler_freq(-50.0, 9.4e9) < 0.0


# ---------------------------------------------------------------------------
# Triangle pair — forward (range, velocity) → (f_up, f_down)
# ---------------------------------------------------------------------------


def test_triangle_beats_stationary_target() -> None:
    """v=0 → f_up == f_down == f_range_only."""
    f_up, f_down = fmcw_triangle_beats(
        range_m=1000.0,
        v_radial_m_s=0.0,
        bandwidth_hz=100e6,
        sweep_period_s=1e-3,
        carrier_freq_hz=9.4e9,
    )
    f_range = beat_freq_from_range(1000.0, 100e6, 1e-3)
    assert f_up == pytest.approx(f_range, abs=1e-6)
    assert f_down == pytest.approx(f_range, abs=1e-6)


def test_triangle_beats_approaching_target_signs() -> None:
    """Approaching: f_up < f_range < f_down (per sign convention)."""
    f_up, f_down = fmcw_triangle_beats(
        range_m=1000.0,
        v_radial_m_s=20.0,  # approaching
        bandwidth_hz=100e6,
        sweep_period_s=1e-3,
        carrier_freq_hz=9.4e9,
    )
    f_range = beat_freq_from_range(1000.0, 100e6, 1e-3)
    f_d = doppler_freq(20.0, 9.4e9)
    assert f_up == pytest.approx(f_range - f_d, abs=1e-6)
    assert f_down == pytest.approx(f_range + f_d, abs=1e-6)
    assert f_up < f_range < f_down


# ---------------------------------------------------------------------------
# Triangle pair — inverse (f_up, f_down) → (range, velocity)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("range_m", "v_m_s"),
    [
        (1000.0, 0.0),  # stationary
        (1000.0, 20.0),  # approaching
        (1000.0, -30.0),  # receding
        (5000.0, 100.0),  # mid-range, fast
        (15_000.0, -15.0),  # far, slow
        (100.0, 5.0),  # near, slow
    ],
)
def test_round_trip_range_velocity(range_m: float, v_m_s: float) -> None:
    """``(R, v) → (f_up, f_down) → (R, v)`` to sub-mm / sub-mm/s."""
    bandwidth_hz = 100e6
    sweep_period_s = 1e-3
    carrier_freq_hz = 9.4e9
    f_up, f_down = fmcw_triangle_beats(
        range_m,
        v_m_s,
        bandwidth_hz,
        sweep_period_s,
        carrier_freq_hz,
    )
    r_back, v_back = beat_pair_to_range_velocity(
        f_up,
        f_down,
        bandwidth_hz,
        sweep_period_s,
        carrier_freq_hz,
    )
    assert r_back == pytest.approx(range_m, abs=1e-6)
    assert v_back == pytest.approx(v_m_s, abs=1e-9)


# ---------------------------------------------------------------------------
# Resolutions
# ---------------------------------------------------------------------------


def test_range_resolution_100mhz() -> None:
    """B=100 MHz → ΔR = c/2B ≈ 1.4990 m."""
    dr = range_resolution_m(100e6)
    expected = C_LIGHT_M_S / (2.0 * 100e6)
    assert dr == pytest.approx(expected, abs=1e-9)
    assert dr == pytest.approx(1.4990, abs=1e-3)


def test_range_resolution_1ghz_finer() -> None:
    """B=1 GHz -> ΔR ≈ 0.1499 m. 10x B = 1/10x ΔR."""
    dr = range_resolution_m(1e9)
    assert dr == pytest.approx(0.1499, abs=1e-3)


def test_doppler_resolution_inverse_observation() -> None:
    """Δf_D = 1 / T_obs."""
    assert doppler_resolution_hz(0.01) == pytest.approx(100.0, abs=1e-9)
    assert doppler_resolution_hz(0.1) == pytest.approx(10.0, abs=1e-9)


def test_velocity_resolution_xband_10ms() -> None:
    """f_c=9.4 GHz, T_obs=10 ms → Δv ≈ 1.595 m/s.

    Δv = c / (2·f_c·T_obs) = 299_792_458 / (2·9.4e9·1e-2) = 1.59464 m/s
    """
    dv = velocity_resolution_m_s(observation_period_s=1e-2, carrier_freq_hz=9.4e9)
    expected = C_LIGHT_M_S / (2.0 * 9.4e9 * 1e-2)
    assert dv == pytest.approx(expected, abs=1e-9)
    assert dv == pytest.approx(1.59464, abs=1e-4)


def test_wavelength_xband() -> None:
    """λ at 9.4 GHz ≈ 31.89 mm."""
    lam = wavelength_m(9.4e9)
    expected = C_LIGHT_M_S / 9.4e9
    assert lam == pytest.approx(expected, abs=1e-12)
    assert lam == pytest.approx(0.031893, abs=1e-5)
