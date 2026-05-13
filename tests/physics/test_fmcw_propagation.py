"""FMCW propagation regression vs golden dataset (Phase 5.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.propagation.fmcw import (
    beat_freq_from_range,
    beat_pair_to_range_velocity,
    doppler_freq,
    fmcw_triangle_beats,
    range_resolution_m,
    wavelength_m,
)

_DATASET = GoldenDataset.load(Path(__file__).parent / "golden" / "fmcw_propagation.json")
_RTOL = _DATASET.meta.rtol


def test_beat_freq_from_range_matches_golden_1km() -> None:
    sample = _DATASET.case("beat_1km_150MHz_1ms")
    f_b = beat_freq_from_range(
        range_m=sample.inputs["range_m"],
        bandwidth_hz=sample.inputs["bandwidth_hz"],
        sweep_period_s=sample.inputs["sweep_period_s"],
    )
    assert f_b == pytest.approx(sample.expected["beat_freq_hz"], rel=_RTOL)


def test_beat_freq_from_range_matches_golden_10km() -> None:
    sample = _DATASET.case("beat_10km_80MHz_1ms")
    f_b = beat_freq_from_range(
        range_m=sample.inputs["range_m"],
        bandwidth_hz=sample.inputs["bandwidth_hz"],
        sweep_period_s=sample.inputs["sweep_period_s"],
    )
    assert f_b == pytest.approx(sample.expected["beat_freq_hz"], rel=_RTOL)


def test_doppler_freq_matches_golden() -> None:
    sample = _DATASET.case("doppler_100mps_9_5GHz")
    f_d = doppler_freq(
        v_radial_m_s=sample.inputs["v_radial_m_s"],
        carrier_freq_hz=sample.inputs["carrier_freq_hz"],
    )
    assert f_d == pytest.approx(sample.expected["doppler_freq_hz"], rel=_RTOL)


def test_range_resolution_matches_golden() -> None:
    sample = _DATASET.case("range_resolution_150MHz")
    dr = range_resolution_m(bandwidth_hz=sample.inputs["bandwidth_hz"])
    assert dr == pytest.approx(sample.expected["range_resolution_m"], rel=_RTOL)


def test_wavelength_matches_golden() -> None:
    sample = _DATASET.case("wavelength_9_5GHz")
    lam = wavelength_m(carrier_freq_hz=sample.inputs["carrier_freq_hz"])
    assert lam == pytest.approx(sample.expected["wavelength_m"], rel=_RTOL)


def test_triangle_beats_round_trip_through_pairing() -> None:
    """Generate UP/DOWN beats then invert - should recover (R, v)."""
    range_m = 4500.0
    v_radial_m_s = 75.0
    bandwidth_hz = 120e6
    sweep_period_s = 0.8e-3
    carrier_freq_hz = 9.4e9

    f_up, f_down = fmcw_triangle_beats(
        range_m=range_m,
        v_radial_m_s=v_radial_m_s,
        bandwidth_hz=bandwidth_hz,
        sweep_period_s=sweep_period_s,
        carrier_freq_hz=carrier_freq_hz,
    )
    range_back, v_back = beat_pair_to_range_velocity(
        f_beat_up_hz=f_up,
        f_beat_down_hz=f_down,
        bandwidth_hz=bandwidth_hz,
        sweep_period_s=sweep_period_s,
        carrier_freq_hz=carrier_freq_hz,
    )
    assert range_back == pytest.approx(range_m, rel=1e-12)
    assert v_back == pytest.approx(v_radial_m_s, rel=1e-12)


def test_beat_freq_zero_range_is_zero() -> None:
    assert beat_freq_from_range(0.0, bandwidth_hz=150e6, sweep_period_s=1e-3) == 0.0


def test_doppler_sign_convention_positive_when_approaching() -> None:
    # The function under test treats positive v_radial as approaching.
    f_d = doppler_freq(v_radial_m_s=50.0, carrier_freq_hz=9.5e9)
    assert f_d > 0.0


# ---------- 5.2b — Closed-form scaling invariants ----------


def test_beat_freq_linear_in_range() -> None:
    """f_beat = 2 B R / (c T_s) -> doubling R doubles f_beat exactly."""
    base = beat_freq_from_range(range_m=1000.0, bandwidth_hz=150e6, sweep_period_s=1e-3)
    doubled = beat_freq_from_range(range_m=2000.0, bandwidth_hz=150e6, sweep_period_s=1e-3)
    assert doubled == pytest.approx(2.0 * base, rel=_RTOL)


def test_beat_freq_linear_in_bandwidth() -> None:
    """Doubling bandwidth (sweep slope) doubles beat frequency at fixed R."""
    base = beat_freq_from_range(range_m=1000.0, bandwidth_hz=80e6, sweep_period_s=1e-3)
    doubled = beat_freq_from_range(range_m=1000.0, bandwidth_hz=160e6, sweep_period_s=1e-3)
    assert doubled == pytest.approx(2.0 * base, rel=_RTOL)


def test_beat_freq_inverse_in_sweep_period() -> None:
    """Halving the sweep period (steeper slope) doubles beat frequency."""
    base = beat_freq_from_range(range_m=1000.0, bandwidth_hz=150e6, sweep_period_s=2e-3)
    halved_period = beat_freq_from_range(range_m=1000.0, bandwidth_hz=150e6, sweep_period_s=1e-3)
    assert halved_period == pytest.approx(2.0 * base, rel=_RTOL)


def test_doppler_freq_antisymmetric_in_velocity() -> None:
    """f_d(+v) = -f_d(-v) — positive radial velocity (approaching) gives
    positive doppler, negative (receding) gives the exact opposite.
    """
    f_d_pos = doppler_freq(v_radial_m_s=50.0, carrier_freq_hz=9.5e9)
    f_d_neg = doppler_freq(v_radial_m_s=-50.0, carrier_freq_hz=9.5e9)
    assert f_d_neg == pytest.approx(-f_d_pos, rel=_RTOL)


def test_range_resolution_inversely_proportional_to_bandwidth() -> None:
    """dr = c / (2 B) -> doubling bandwidth halves the range resolution."""
    base = range_resolution_m(bandwidth_hz=150e6)
    doubled = range_resolution_m(bandwidth_hz=300e6)
    assert doubled == pytest.approx(base / 2.0, rel=_RTOL)


def test_triangle_beats_stationary_target_yields_equal_up_down() -> None:
    """A stationary target (v_radial = 0) has zero doppler so f_up =
    f_down at any geometry. Locks the symmetry that the FMCW pairing
    stage relies on to flag "no doppler" candidates.
    """
    f_up, f_down = fmcw_triangle_beats(
        range_m=2500.0,
        v_radial_m_s=0.0,
        bandwidth_hz=120e6,
        sweep_period_s=1e-3,
        carrier_freq_hz=9.4e9,
    )
    assert f_up == pytest.approx(f_down, rel=_RTOL)


def test_triangle_beats_round_trip_with_receding_target() -> None:
    """Receding target (v_radial < 0) must invert through the
    UP/DOWN beat pair the same way as the existing approaching case.
    """
    range_m = 4500.0
    v_radial_m_s = -90.0  # receding
    bandwidth_hz = 120e6
    sweep_period_s = 0.8e-3
    carrier_freq_hz = 9.4e9

    f_up, f_down = fmcw_triangle_beats(
        range_m=range_m,
        v_radial_m_s=v_radial_m_s,
        bandwidth_hz=bandwidth_hz,
        sweep_period_s=sweep_period_s,
        carrier_freq_hz=carrier_freq_hz,
    )
    range_back, v_back = beat_pair_to_range_velocity(
        f_beat_up_hz=f_up,
        f_beat_down_hz=f_down,
        bandwidth_hz=bandwidth_hz,
        sweep_period_s=sweep_period_s,
        carrier_freq_hz=carrier_freq_hz,
    )
    assert range_back == pytest.approx(range_m, rel=1e-12)
    assert v_back == pytest.approx(v_radial_m_s, rel=1e-12)
