"""MockRangeDopplerGenerator unit tests (Phase 4 L3)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.app.simulator import (
    DEFAULT_DOPPLER_MAX_MPS,
    DEFAULT_DOPPLER_MIN_MPS,
    DEFAULT_N_DOPPLER_BINS,
    DEFAULT_N_RANGE_BINS,
    DEFAULT_RANGE_MAX_M,
    DEFAULT_RANGE_MIN_M,
    MockRangeDopplerFrame,
    MockRangeDopplerGenerator,
)

# ---------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------


def test_default_constructor_has_expected_axes() -> None:
    gen = MockRangeDopplerGenerator()
    r = gen.range_axis_m()
    d = gen.doppler_axis_mps()
    assert r.shape == (DEFAULT_N_RANGE_BINS,)
    assert d.shape == (DEFAULT_N_DOPPLER_BINS,)
    assert r[0] == pytest.approx(DEFAULT_RANGE_MIN_M)
    assert r[-1] == pytest.approx(DEFAULT_RANGE_MAX_M)
    assert d[0] == pytest.approx(DEFAULT_DOPPLER_MIN_MPS)
    assert d[-1] == pytest.approx(DEFAULT_DOPPLER_MAX_MPS)
    assert np.all(np.diff(r) >= 0.0)
    assert np.all(np.diff(d) >= 0.0)


def test_constructor_rejects_negative_range_min() -> None:
    with pytest.raises(ValueError, match=r"range_min_m must be >= 0"):
        MockRangeDopplerGenerator(range_min_m=-1.0)


def test_constructor_rejects_inverted_range_band() -> None:
    with pytest.raises(ValueError, match=r"range_max_m .* must exceed range_min_m"):
        MockRangeDopplerGenerator(range_min_m=1000.0, range_max_m=500.0)


def test_constructor_rejects_inverted_doppler_band() -> None:
    with pytest.raises(ValueError, match=r"doppler_max_mps .* must exceed doppler_min_mps"):
        MockRangeDopplerGenerator(doppler_min_mps=10.0, doppler_max_mps=-10.0)


def test_constructor_rejects_too_few_range_bins() -> None:
    with pytest.raises(ValueError, match=r"n_range_bins must be >= 8"):
        MockRangeDopplerGenerator(n_range_bins=4)


def test_constructor_rejects_too_few_doppler_bins() -> None:
    with pytest.raises(ValueError, match=r"n_doppler_bins must be >= 8"):
        MockRangeDopplerGenerator(n_doppler_bins=4)


def test_constructor_rejects_range_base_outside_axis() -> None:
    with pytest.raises(ValueError, match=r"range_base_m .* must lie in"):
        MockRangeDopplerGenerator(range_min_m=0.0, range_max_m=1000.0, range_base_m=2000.0)


def test_constructor_rejects_doppler_base_outside_axis() -> None:
    with pytest.raises(ValueError, match=r"doppler_base_mps .* must lie in"):
        MockRangeDopplerGenerator(
            doppler_min_mps=-10.0, doppler_max_mps=10.0, doppler_base_mps=50.0
        )


def test_constructor_rejects_negative_range_sweep() -> None:
    with pytest.raises(ValueError, match=r"range_sweep_m must be >= 0"):
        MockRangeDopplerGenerator(range_sweep_m=-1.0)


def test_constructor_rejects_zero_range_period() -> None:
    with pytest.raises(ValueError, match=r"range_period_s must be > 0"):
        MockRangeDopplerGenerator(range_period_s=0.0)


def test_constructor_rejects_zero_doppler_period() -> None:
    with pytest.raises(ValueError, match=r"doppler_period_s must be > 0"):
        MockRangeDopplerGenerator(doppler_period_s=0.0)


def test_constructor_rejects_zero_range_peak_width() -> None:
    with pytest.raises(ValueError, match=r"peak_width_range_m must be > 0"):
        MockRangeDopplerGenerator(peak_width_range_m=0.0)


def test_constructor_rejects_zero_doppler_peak_width() -> None:
    with pytest.raises(ValueError, match=r"peak_width_doppler_mps must be > 0"):
        MockRangeDopplerGenerator(peak_width_doppler_mps=0.0)


def test_constructor_rejects_negative_noise_std() -> None:
    with pytest.raises(ValueError, match=r"noise_std_db must be >= 0"):
        MockRangeDopplerGenerator(noise_std_db=-0.1)


# ---------------------------------------------------------------------
# Peak motion
# ---------------------------------------------------------------------


def test_peak_position_at_zero_is_base_plus_cosine_max() -> None:
    """sin(0)=0 → range = base, cos(0)=1 → doppler = base + sweep."""
    gen = MockRangeDopplerGenerator(
        range_base_m=5_000.0,
        range_sweep_m=2_000.0,
        doppler_base_mps=0.0,
        doppler_sweep_mps=20.0,
    )
    r, d = gen.peak_position_at(0.0)
    assert r == pytest.approx(5_000.0)
    assert d == pytest.approx(20.0)


def test_peak_position_traces_lissajous() -> None:
    """Independent periods → two-axis trajectory."""
    gen = MockRangeDopplerGenerator(range_period_s=4.0, doppler_period_s=6.0, range_base_m=5_000.0)
    positions = [gen.peak_position_at(t) for t in (0.0, 0.25, 0.5, 1.0, 2.0)]
    # No two timestamps share the same (range, doppler) pair.
    assert len(set(positions)) == len(positions)


def test_peak_position_caps_to_axes() -> None:
    """Over-amplitude sweeps are silently capped."""
    gen = MockRangeDopplerGenerator(
        range_min_m=0.0,
        range_max_m=1_000.0,
        range_base_m=200.0,
        range_sweep_m=5_000.0,
        doppler_min_mps=-10.0,
        doppler_max_mps=10.0,
        doppler_base_mps=0.0,
        doppler_sweep_mps=100.0,
    )
    for t in (0.0, 1.0, 2.0, 3.0):
        r, d = gen.peak_position_at(t)
        assert 0.0 <= r <= 1_000.0
        assert -10.0 <= d <= 10.0


# ---------------------------------------------------------------------
# heatmap_for arrays
# ---------------------------------------------------------------------


def test_heatmap_for_returns_matching_shapes() -> None:
    gen = MockRangeDopplerGenerator()
    frame = gen.heatmap_for(0.5)
    assert isinstance(frame, MockRangeDopplerFrame)
    assert frame.heatmap_db.shape == (DEFAULT_N_RANGE_BINS, DEFAULT_N_DOPPLER_BINS)
    assert frame.range_axis_m.shape == (DEFAULT_N_RANGE_BINS,)
    assert frame.doppler_axis_mps.shape == (DEFAULT_N_DOPPLER_BINS,)
    assert frame.sim_t_s == pytest.approx(0.5)


def test_heatmap_for_rejects_negative_sim_t_s() -> None:
    gen = MockRangeDopplerGenerator()
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        gen.heatmap_for(-0.001)


def test_heatmap_for_is_deterministic_per_sim_t_s() -> None:
    gen = MockRangeDopplerGenerator()
    a = gen.heatmap_for(1.0)
    b = gen.heatmap_for(1.0)
    np.testing.assert_array_equal(a.heatmap_db, b.heatmap_db)


def test_different_sim_t_s_yields_different_heatmap() -> None:
    gen = MockRangeDopplerGenerator()
    a = gen.heatmap_for(1.0)
    b = gen.heatmap_for(1.0 + 1.0 / 60.0)
    assert not np.array_equal(a.heatmap_db, b.heatmap_db)


def test_peak_dominates_noise_at_peak_cell() -> None:
    gen = MockRangeDopplerGenerator(peak_height_db=30.0, noise_floor_db=-60.0, noise_std_db=0.5)
    frame = gen.heatmap_for(0.0)
    r_idx = int(np.argmin(np.abs(frame.range_axis_m - frame.peak_range_m)))
    d_idx = int(np.argmin(np.abs(frame.doppler_axis_mps - frame.peak_doppler_mps)))
    centre = float(frame.heatmap_db[r_idx, d_idx])
    corner = float(frame.heatmap_db[0, 0])
    assert centre > corner + 20.0


def test_noise_std_zero_gives_smooth_corner() -> None:
    gen = MockRangeDopplerGenerator(noise_std_db=0.0)
    frame = gen.heatmap_for(0.0)
    # With noise off the corner far from the peak should equal the
    # noise floor to within float precision.
    assert frame.heatmap_db[0, 0] == pytest.approx(-60.0, abs=0.5)


def test_seed_changes_noise_realisation() -> None:
    gen_a = MockRangeDopplerGenerator(rng_seed=1)
    gen_b = MockRangeDopplerGenerator(rng_seed=2)
    a = gen_a.heatmap_for(0.5)
    b = gen_b.heatmap_for(0.5)
    assert a.peak_range_m == pytest.approx(b.peak_range_m)
    assert not np.array_equal(a.heatmap_db, b.heatmap_db)


def test_n_bins_properties() -> None:
    gen = MockRangeDopplerGenerator(n_range_bins=32, n_doppler_bins=16)
    assert gen.n_range_bins == 32
    assert gen.n_doppler_bins == 16


def test_axis_arrays_are_independent_copies() -> None:
    gen = MockRangeDopplerGenerator()
    r = gen.range_axis_m()
    r[0] = -1.0
    fresh = gen.range_axis_m()
    assert fresh[0] == pytest.approx(DEFAULT_RANGE_MIN_M)
