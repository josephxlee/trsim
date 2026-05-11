"""CFAR detector regression (Phase 5.10).

Plan/04 § 4.3 Phase 5 #17 (OS-CFAR vs CA-CFAR). Skolnik IRS 3e § 7.4:
``alpha = N * (Pfa ** (-1/N) - 1)`` for the square-law detector with
exponential noise.
"""

from __future__ import annotations

import numpy as np
import pytest

from workbench.domain.detector.cfar import (
    alpha_ca_for_pfa,
    ca_cfar_1d,
    os_cfar_1d,
)

_RTOL = 1e-12


# ---------- alpha_ca_for_pfa ----------


@pytest.mark.parametrize(
    ("pfa", "n_total", "expected"),
    [
        (1e-4, 16, 12.452470560622764),
        (1e-6, 32, 17.277648833903747),
        (1e-3, 8, 10.97098964529324),
    ],
)
def test_alpha_ca_matches_closed_form(pfa: float, n_total: int, expected: float) -> None:
    assert alpha_ca_for_pfa(pfa, n_total) == pytest.approx(expected, rel=_RTOL)


def test_alpha_monotonic_in_inverse_pfa() -> None:
    """Lower Pfa demands a higher threshold."""
    a_loose = alpha_ca_for_pfa(1e-2, 16)
    a_tight = alpha_ca_for_pfa(1e-6, 16)
    assert a_tight > a_loose


@pytest.mark.parametrize("bad_pfa", [0.0, 1.0, -0.1, 1.5])
def test_alpha_rejects_pfa_outside_open_unit(bad_pfa: float) -> None:
    with pytest.raises(ValueError, match=r"pfa"):
        alpha_ca_for_pfa(bad_pfa, 16)


@pytest.mark.parametrize("bad_n", [0, -1])
def test_alpha_rejects_non_positive_n(bad_n: int) -> None:
    with pytest.raises(ValueError, match=r"n_total"):
        alpha_ca_for_pfa(1e-4, bad_n)


# ---------- ca_cfar_1d ----------


def test_ca_cfar_detects_obvious_spike() -> None:
    """A 100x spike on a 1.0 background should fire."""
    power = np.ones(64, dtype=np.float64)
    power[32] = 100.0
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert bool(mask[32])
    # No false alarms elsewhere - the noise plateau is flat.
    assert int(mask.sum()) == 1


def test_ca_cfar_ignores_pure_noise_with_reasonable_alpha() -> None:
    rng = np.random.default_rng(seed=42)
    # Exponential noise mean ~ 1.0.
    noise = rng.exponential(scale=1.0, size=2048).astype(np.float64)
    # Pfa target 1e-3 with N_total = 32 -> alpha ~ 10.97. Should keep
    # the empirical false-alarm count modest.
    alpha = alpha_ca_for_pfa(1e-3, 32)
    mask = ca_cfar_1d(noise, n_guard=2, n_train=16, alpha=alpha)
    fa = int(mask.sum())
    # Expected false alarms ~ 2 over 2048 cells; allow generous slack.
    assert fa < 20


def test_ca_cfar_edge_cells_are_false() -> None:
    """Cells too close to the edge cannot fit the window."""
    power = np.ones(32, dtype=np.float64)
    power[3] = 50.0  # spike inside the edge-guard region
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    # n_guard+n_train = 10, so cells 0..9 and 22..31 are always False.
    assert not bool(mask[3])
    assert not bool(mask[0])
    assert not bool(mask[31])


def test_ca_cfar_rejects_bad_inputs() -> None:
    power = np.ones(64, dtype=np.float64)
    with pytest.raises(ValueError, match=r"n_guard"):
        ca_cfar_1d(power, n_guard=-1, n_train=8, alpha=5.0)
    with pytest.raises(ValueError, match=r"n_train"):
        ca_cfar_1d(power, n_guard=2, n_train=0, alpha=5.0)
    with pytest.raises(ValueError, match=r"alpha"):
        ca_cfar_1d(power, n_guard=2, n_train=8, alpha=-1.0)
    small = np.ones(8, dtype=np.float64)
    with pytest.raises(ValueError, match=r"too small"):
        ca_cfar_1d(small, n_guard=2, n_train=8, alpha=5.0)


# ---------- os_cfar_1d ----------


def test_os_cfar_detects_spike_amid_clutter() -> None:
    """OS-CFAR should still find the spike when training cells include
    other strong returns (clutter edges)."""
    power = np.ones(64, dtype=np.float64)
    # Add three spurious bumps that would distort CA-CFAR's mean.
    power[20] = 20.0
    power[24] = 25.0
    power[28] = 30.0
    # Target spike at the centre is much larger.
    power[40] = 300.0
    mask = os_cfar_1d(power, n_guard=2, n_train=10, k_index=14, alpha=5.0)
    assert bool(mask[40])


def test_os_cfar_2d_shape_unsupported_raises() -> None:
    bad = np.ones((4, 4), dtype=np.float64)
    with pytest.raises(ValueError, match=r"1-D"):
        os_cfar_1d(bad, n_guard=1, n_train=2, k_index=2, alpha=5.0)
