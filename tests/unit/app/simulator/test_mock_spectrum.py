"""MockSpectrumGenerator unit tests (Phase 4 L2)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.app.simulator import (
    DEFAULT_FREQ_MAX_HZ,
    DEFAULT_FREQ_MIN_HZ,
    DEFAULT_N_BINS,
    MockSpectrumFrame,
    MockSpectrumGenerator,
)

# ---------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------


def test_default_constructor_has_axis_in_expected_range() -> None:
    gen = MockSpectrumGenerator()
    freqs = gen.freqs_hz()
    assert freqs.shape == (DEFAULT_N_BINS,)
    assert freqs[0] == pytest.approx(DEFAULT_FREQ_MIN_HZ)
    assert freqs[-1] == pytest.approx(DEFAULT_FREQ_MAX_HZ)
    # Monotone non-decreasing.
    assert np.all(np.diff(freqs) >= 0.0)


def test_constructor_rejects_negative_freq_min() -> None:
    with pytest.raises(ValueError, match=r"freq_min_hz must be >= 0"):
        MockSpectrumGenerator(freq_min_hz=-1.0)


def test_constructor_rejects_inverted_band() -> None:
    with pytest.raises(ValueError, match=r"freq_max_hz .* must exceed freq_min_hz"):
        MockSpectrumGenerator(freq_min_hz=1.0e6, freq_max_hz=5.0e5)


def test_constructor_rejects_too_few_bins() -> None:
    with pytest.raises(ValueError, match=r"n_bins must be >= 8"):
        MockSpectrumGenerator(n_bins=4)


def test_constructor_rejects_peak_outside_axis() -> None:
    with pytest.raises(ValueError, match=r"peak_base_hz .* must lie in"):
        MockSpectrumGenerator(freq_min_hz=0.0, freq_max_hz=1.0e6, peak_base_hz=2.0e6)


def test_constructor_rejects_negative_sweep_amplitude() -> None:
    with pytest.raises(ValueError, match=r"peak_sweep_hz must be >= 0"):
        MockSpectrumGenerator(peak_sweep_hz=-1.0)


def test_constructor_rejects_zero_sweep_period() -> None:
    with pytest.raises(ValueError, match=r"sweep_period_s must be > 0"):
        MockSpectrumGenerator(sweep_period_s=0.0)


def test_constructor_rejects_zero_peak_width() -> None:
    with pytest.raises(ValueError, match=r"peak_width_hz must be > 0"):
        MockSpectrumGenerator(peak_width_hz=0.0)


def test_constructor_rejects_negative_noise_std() -> None:
    with pytest.raises(ValueError, match=r"noise_std_db must be >= 0"):
        MockSpectrumGenerator(noise_std_db=-0.5)


# ---------------------------------------------------------------------
# Peak motion
# ---------------------------------------------------------------------


def test_peak_freq_at_zero_is_base() -> None:
    gen = MockSpectrumGenerator()
    up, down = gen.peak_freq_at(0.0)
    # sin(0) = 0 → both peaks sit on the base frequency.
    assert up == pytest.approx(7.5e5)
    assert down == pytest.approx(7.5e5)


def test_peak_freq_at_quarter_period_is_max_offset() -> None:
    gen = MockSpectrumGenerator(sweep_period_s=4.0, peak_base_hz=1.0e6, peak_sweep_hz=2.0e5)
    up, down = gen.peak_freq_at(1.0)  # quarter period, sin = 1
    assert up == pytest.approx(1.0e6 + 2.0e5)
    assert down == pytest.approx(1.0e6 - 2.0e5)


def test_peak_freq_axis_average_is_constant() -> None:
    """No Doppler in mock — (up + down)/2 stays at peak_base over time."""
    gen = MockSpectrumGenerator(peak_base_hz=1.0e6)
    for t in (0.1, 0.5, 1.3, 2.7, 3.9):
        up, down = gen.peak_freq_at(t)
        assert (up + down) / 2.0 == pytest.approx(1.0e6)


def test_peak_sweep_caps_to_keep_peak_inside_axis() -> None:
    """A peak_sweep_hz larger than the headroom is silently capped."""
    gen = MockSpectrumGenerator(
        freq_min_hz=0.0,
        freq_max_hz=1.0e6,
        peak_base_hz=2.0e5,
        peak_sweep_hz=5.0e5,  # would push peak to 7e5 or negative
    )
    # Drive past quarter period in both directions — peak must stay inside.
    for t in (0.0, 1.0, 2.0, 3.0):
        up, down = gen.peak_freq_at(t)
        assert 0.0 <= up <= 1.0e6
        assert 0.0 <= down <= 1.0e6


# ---------------------------------------------------------------------
# spectrum_for arrays
# ---------------------------------------------------------------------


def test_spectrum_for_returns_matching_shapes() -> None:
    gen = MockSpectrumGenerator()
    frame = gen.spectrum_for(0.123)
    assert isinstance(frame, MockSpectrumFrame)
    assert frame.freqs_hz.shape == (DEFAULT_N_BINS,)
    assert frame.up_mag_db.shape == frame.freqs_hz.shape
    assert frame.down_mag_db.shape == frame.freqs_hz.shape
    assert frame.sim_t_s == pytest.approx(0.123)


def test_spectrum_for_rejects_negative_sim_t_s() -> None:
    gen = MockSpectrumGenerator()
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        gen.spectrum_for(-0.001)


def test_spectrum_for_is_deterministic_per_sim_t_s() -> None:
    """Same sim_t_s -> bit-identical arrays (panel can re-paint without flicker)."""
    gen = MockSpectrumGenerator()
    a = gen.spectrum_for(0.5)
    b = gen.spectrum_for(0.5)
    np.testing.assert_array_equal(a.up_mag_db, b.up_mag_db)
    np.testing.assert_array_equal(a.down_mag_db, b.down_mag_db)


def test_different_sim_t_s_yields_different_arrays() -> None:
    gen = MockSpectrumGenerator()
    a = gen.spectrum_for(0.5)
    b = gen.spectrum_for(0.5 + 1.0 / 60.0)
    # Some samples must differ — peak has moved and noise re-seeded.
    assert not np.array_equal(a.up_mag_db, b.up_mag_db)


def test_peak_dominates_noise_at_centre_frequency() -> None:
    """At the peak frequency the up curve should sit well above the noise floor."""
    gen = MockSpectrumGenerator(peak_height_db=20.0, noise_floor_db=-60.0, noise_std_db=0.5)
    frame = gen.spectrum_for(0.0)
    # Up peak at base frequency = 7.5e5 by default.
    centre_idx = int(np.argmin(np.abs(frame.freqs_hz - frame.up_peak_freq_hz)))
    far_idx = 0  # well away from the peak
    assert frame.up_mag_db[centre_idx] > frame.up_mag_db[far_idx] + 15.0


def test_seed_changes_noise_realisation() -> None:
    gen_a = MockSpectrumGenerator(rng_seed=1)
    gen_b = MockSpectrumGenerator(rng_seed=2)
    a = gen_a.spectrum_for(0.5)
    b = gen_b.spectrum_for(0.5)
    # Peaks are seed-independent; arrays should differ because noise differs.
    assert a.up_peak_freq_hz == pytest.approx(b.up_peak_freq_hz)
    assert not np.array_equal(a.up_mag_db, b.up_mag_db)


def test_noise_std_zero_gives_smooth_curve() -> None:
    gen = MockSpectrumGenerator(noise_std_db=0.0)
    frame = gen.spectrum_for(0.0)
    # With noise off the up-sweep curve is the Gaussian peak — at the
    # endpoints it must equal the noise floor to within float precision.
    expected_floor = -60.0
    assert frame.up_mag_db[0] == pytest.approx(expected_floor, abs=0.5)
    assert frame.up_mag_db[-1] == pytest.approx(expected_floor, abs=0.5)


def test_frame_freqs_is_independent_copy() -> None:
    """Mutating the returned freqs array must not affect the next call."""
    gen = MockSpectrumGenerator()
    frame = gen.spectrum_for(0.0)
    frame.freqs_hz[0] = math.pi
    fresh = gen.freqs_hz()
    assert fresh[0] == pytest.approx(DEFAULT_FREQ_MIN_HZ)
