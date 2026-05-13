"""CFAR detector regression (Phase 5.10).

Plan/04 § 4.3 Phase 5 #17 (OS-CFAR vs CA-CFAR). Skolnik IRS 3e § 7.4:
``alpha = N * (Pfa ** (-1/N) - 1)`` for the square-law detector with
exponential noise.
"""

from __future__ import annotations

import math
from itertools import pairwise

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


# ---------- 5.10b — asymptotic alpha + OS-vs-CA distinction ----------


def test_alpha_ca_asymptotic_limit_at_large_n() -> None:
    """For large N the closed-form alpha = N*(Pfa^(-1/N) - 1) collapses
    to the well-known limit ``-ln(Pfa)`` (Skolnik IRS 3e § 7.4):
        lim_{N->inf} N*(Pfa^(-1/N) - 1) = -ln(Pfa).
    At N=10000, Pfa=1e-3, the closed-form must hit -ln(1e-3) ~ 6.908
    within 0.1% relative.
    """
    pfa = 1e-3
    alpha_large = alpha_ca_for_pfa(pfa, 10_000)
    assert alpha_large == pytest.approx(-math.log(pfa), rel=1e-3)


def test_alpha_ca_monotonic_in_n_at_fixed_pfa() -> None:
    """alpha is monotonically decreasing in N at fixed Pfa — averaging
    over more training cells lets the threshold sit closer to the
    asymptotic ``-ln(Pfa)`` (smaller multiplier needed). Lock the
    monotonic direction across a 4 .. 1024 sweep.
    """
    pfa = 1e-3
    n_sweep = (4, 8, 16, 32, 128, 1024)
    alphas = [alpha_ca_for_pfa(pfa, n) for n in n_sweep]
    for a_hi, a_lo in pairwise(alphas):
        assert a_hi > a_lo, f"non-monotonic: {alphas}"


def test_ca_cfar_fails_near_strong_interferer() -> None:
    """A weak target ~6x background sits inside the training window of
    a far stronger neighbour (100x background). CA-CFAR's arithmetic-
    mean training estimate is dragged up by the interferer and the
    weak target's threshold balloons past it — it goes undetected.

    This is the canonical "masked weak target" scenario where OS-CFAR
    has a structural advantage (test below).
    """
    power = np.ones(64, dtype=np.float64)
    power[30] = 6.0  # weak target
    power[40] = 100.0  # strong interferer inside idx-30's training window
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert not bool(mask[30]), "CA-CFAR should be masked by the strong interferer"


def test_os_cfar_recovers_weak_target_despite_strong_interferer() -> None:
    """Same scenario as the CA-CFAR failure: the OS-CFAR k-th sorted
    training cell sits in the noise plateau (not the interferer), so
    the weak target at idx 30 passes the threshold.
    """
    power = np.ones(64, dtype=np.float64)
    power[30] = 6.0
    power[40] = 100.0
    # n_train=8 left + 8 right = 16 sorted cells; k_index=10 picks the
    # 10th smallest (well below the strong interferer at sorted[15]).
    mask = os_cfar_1d(power, n_guard=2, n_train=8, k_index=10, alpha=5.0)
    assert bool(mask[30]), "OS-CFAR should recover the weak target"


def test_ca_cfar_detects_two_adjacent_spikes_inside_guard() -> None:
    """Adjacent target pair separated by less than 2*n_guard cells.
    Each spike sits in the other's guard region (not the training
    window), so the background mean stays clean and both detections
    fire.
    """
    power = np.ones(64, dtype=np.float64)
    power[30] = 20.0
    power[31] = 20.0  # adjacent: inside idx-30's n_guard=2 region
    mask = ca_cfar_1d(power, n_guard=2, n_train=8, alpha=5.0)
    assert bool(mask[30])
    assert bool(mask[31])
    assert int(mask.sum()) == 2
