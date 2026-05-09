"""Unit tests for workbench.domain.detector.cfar (Phase 2.9)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.domain.detector.cfar import (
    alpha_ca_for_pfa,
    ca_cfar_1d,
    ca_cfar_2d,
    os_cfar_1d,
)

# ---------------------------------------------------------------------
# alpha_ca_for_pfa
# ---------------------------------------------------------------------


def test_alpha_known_value() -> None:
    # Pfa = 1e-4, N = 16 -> alpha = 16 * (1e-4 ** (-1/16) - 1)
    expected = 16.0 * (math.pow(1e-4, -1.0 / 16.0) - 1.0)
    assert alpha_ca_for_pfa(1e-4, 16) == pytest.approx(expected, rel=1e-12)


def test_alpha_more_training_cells_lower_threshold() -> None:
    # For the same Pfa, more training cells -> tighter (smaller) alpha.
    a8 = alpha_ca_for_pfa(1e-4, 8)
    a32 = alpha_ca_for_pfa(1e-4, 32)
    assert a8 > a32


@pytest.mark.parametrize(
    ("pfa", "n_total"),
    [
        (0.0, 16),
        (1.0, 16),
        (-0.1, 16),
        (1.5, 16),
        (1e-4, 0),
        (1e-4, -1),
    ],
)
def test_alpha_validation(pfa: float, n_total: int) -> None:
    with pytest.raises(ValueError):
        alpha_ca_for_pfa(pfa, n_total)


# ---------------------------------------------------------------------
# ca_cfar_1d
# ---------------------------------------------------------------------


def test_ca_cfar_1d_uniform_noise_no_detection() -> None:
    # Uniform power 1.0 -> training mean = 1.0; threshold = alpha * 1.0;
    # for alpha = 5 nothing should exceed.
    power = np.full(100, 1.0, dtype=np.float64)
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert not mask.any()


def test_ca_cfar_1d_strong_target_detected() -> None:
    power = np.full(100, 1.0, dtype=np.float64)
    power[50] = 100.0  # strong target
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert mask[50]


def test_ca_cfar_1d_target_below_threshold_not_detected() -> None:
    power = np.full(100, 1.0, dtype=np.float64)
    power[50] = 4.0  # below alpha=5.0 threshold
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert not mask[50]


def test_ca_cfar_1d_edge_cells_not_flagged() -> None:
    # Cells within half-window of either edge should always be False.
    power = np.full(50, 1.0, dtype=np.float64)
    power[0] = 1000.0
    power[-1] = 1000.0
    mask = ca_cfar_1d(power, n_guard=2, n_train=4, alpha=2.0)
    half = 2 + 4
    assert not mask[:half].any()
    assert not mask[-half:].any()


def test_ca_cfar_1d_pfa_calibration() -> None:
    # Per-Skolnik analysis: with calibrated alpha and exponential
    # noise, observed false-alarm rate should approach Pfa for large
    # samples. We test on a broad sample with a relaxed bound.
    rng = np.random.default_rng(42)
    n = 5000
    power = rng.exponential(scale=1.0, size=n).astype(np.float64)
    pfa = 1e-2
    n_train = 16
    alpha = alpha_ca_for_pfa(pfa, 2 * n_train)
    mask = ca_cfar_1d(power, n_guard=2, n_train=n_train, alpha=alpha)
    # exclude edges
    edge = 2 + n_train
    interior = mask[edge : n - edge]
    fa_rate = float(interior.mean())
    # Should be close to pfa within an order of magnitude (sample
    # variability is large for Pfa = 1e-2 over ~5k cells).
    assert fa_rate < 5.0 * pfa
    assert fa_rate > 0.1 * pfa


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"n_guard": -1}, r"n_guard"),
        ({"n_train": 0}, r"n_train"),
        ({"alpha": -1.0}, r"alpha"),
    ],
)
def test_ca_cfar_1d_validation(kwargs: dict, match: str) -> None:
    base = {
        "power": np.ones(100, dtype=np.float64),
        "n_guard": 2,
        "n_train": 8,
        "alpha": 5.0,
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        ca_cfar_1d(**base)


def test_ca_cfar_1d_too_short_array_rejected() -> None:
    with pytest.raises(ValueError, match=r"too small"):
        ca_cfar_1d(np.ones(5, dtype=np.float64), n_guard=2, n_train=8, alpha=5.0)


def test_ca_cfar_1d_rejects_non_1d() -> None:
    with pytest.raises(ValueError, match=r"1-D"):
        ca_cfar_1d(np.ones((10, 10), dtype=np.float64), n_guard=2, n_train=4, alpha=5.0)


# ---------------------------------------------------------------------
# os_cfar_1d
# ---------------------------------------------------------------------


def test_os_cfar_1d_uniform_no_detection() -> None:
    power = np.full(100, 1.0, dtype=np.float64)
    mask = os_cfar_1d(power, n_guard=2, n_train=8, k_index=12, alpha=2.0)
    assert not mask.any()


def test_os_cfar_1d_strong_target_detected() -> None:
    power = np.full(100, 1.0, dtype=np.float64)
    power[50] = 100.0
    mask = os_cfar_1d(power, n_guard=2, n_train=8, k_index=12, alpha=2.0)
    assert mask[50]


def test_os_cfar_1d_robust_to_one_clutter_target() -> None:
    # Two equal-magnitude targets within the same training window.
    # CA-CFAR would mask one; OS-CFAR with k_index < the inflated
    # cells survives.
    power = np.full(100, 1.0, dtype=np.float64)
    power[48] = 50.0
    power[52] = 50.0
    # OS with k=12 (75th percentile of 16-cell window) ignores both
    # targets in the threshold computation, so each remains detectable.
    mask = os_cfar_1d(power, n_guard=2, n_train=8, k_index=11, alpha=3.0)
    assert mask[48]
    assert mask[52]


@pytest.mark.parametrize(
    "k_index",
    [-1, 16],  # n_train=8 -> 2*n_train = 16 cells
)
def test_os_cfar_1d_invalid_k_index(k_index: int) -> None:
    with pytest.raises(ValueError, match=r"k_index"):
        os_cfar_1d(
            np.ones(100, dtype=np.float64),
            n_guard=2,
            n_train=8,
            k_index=k_index,
            alpha=2.0,
        )


# ---------------------------------------------------------------------
# ca_cfar_2d
# ---------------------------------------------------------------------


def test_ca_cfar_2d_uniform_no_detection() -> None:
    power = np.full((30, 30), 1.0, dtype=np.float64)
    mask = ca_cfar_2d(
        power,
        n_guard_r=1,
        n_train_r=4,
        n_guard_d=1,
        n_train_d=4,
        alpha=4.0,
    )
    assert not mask.any()


def test_ca_cfar_2d_strong_target_detected() -> None:
    power = np.full((30, 30), 1.0, dtype=np.float64)
    power[15, 15] = 100.0
    mask = ca_cfar_2d(
        power,
        n_guard_r=1,
        n_train_r=4,
        n_guard_d=1,
        n_train_d=4,
        alpha=4.0,
    )
    assert mask[15, 15]


def test_ca_cfar_2d_edges_excluded() -> None:
    power = np.full((20, 20), 1.0, dtype=np.float64)
    power[0, 0] = 1000.0
    power[19, 19] = 1000.0
    mask = ca_cfar_2d(
        power,
        n_guard_r=1,
        n_train_r=2,
        n_guard_d=1,
        n_train_d=2,
        alpha=4.0,
    )
    # Edge cells must not be flagged (window can't fit).
    assert not mask[0, 0]
    assert not mask[19, 19]


def test_ca_cfar_2d_rejects_non_2d() -> None:
    with pytest.raises(ValueError, match=r"2-D"):
        ca_cfar_2d(
            np.ones(50, dtype=np.float64),
            n_guard_r=1,
            n_train_r=4,
            n_guard_d=1,
            n_train_d=4,
            alpha=4.0,
        )


def test_ca_cfar_2d_too_small_rejected() -> None:
    with pytest.raises(ValueError, match=r"too small"):
        ca_cfar_2d(
            np.ones((5, 5), dtype=np.float64),
            n_guard_r=1,
            n_train_r=4,
            n_guard_d=1,
            n_train_d=4,
            alpha=4.0,
        )
