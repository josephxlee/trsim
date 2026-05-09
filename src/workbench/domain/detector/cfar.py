"""Constant False Alarm Rate detectors — CA / OS (plan/03 § 3.2.1j).

Phase 2.9 — first-pass detection stage. Two textbook variants:

- **CA-CFAR (cell-averaging)**: threshold = ``alpha * mean(training cells)``.
  Optimal in homogeneous Gaussian-noise backgrounds; underperforms when
  another target sits in the training window (target masking).
- **OS-CFAR (order-statistic)**: threshold = ``alpha * k-th sorted
  training cell``. Robust to target masking and clutter edges at the
  cost of higher noise threshold (~1-2 dB CFAR loss).

Layout:

- 1-D versions (``ca_cfar_1d``, ``os_cfar_1d``) operate on a single
  power axis (range OR doppler).
- 2-D versions (``ca_cfar_2d``) operate on a range-doppler map with
  separate guard / training extents per axis.
- ``alpha_ca_for_pfa(pfa, n_total)`` returns the CA-CFAR scaling
  factor for a desired probability of false alarm under a square-law
  detector + exponential noise (Skolnik IRS 3e § 7.4):
  ``alpha = N * (Pfa ** (-1/N) - 1)``.

References:

- Skolnik, *Introduction to Radar Systems* 3e, ch.7 (CFAR).
- Rohling, "Radar CFAR thresholding in clutter and multiple target
  situations" (1983) — OS-CFAR.
- Mahafza, *Radar Systems Analysis and Design Using MATLAB*, ch.10.
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------
# Threshold scaling helpers
# ---------------------------------------------------------------------


def alpha_ca_for_pfa(pfa: float, n_total: int) -> float:
    """CA-CFAR scaling factor for a target false-alarm probability.

    Square-law detector + exponential noise:
    ``alpha = N * (Pfa ** (-1/N) - 1)`` (Skolnik IRS 3e § 7.4).

    Args:
        pfa: Desired probability of false alarm in (0, 1).
        n_total: Total training cells (both sides). Must be >= 1.

    Returns:
        Threshold multiplier applied to the training-cell mean.

    Raises:
        ValueError: If pfa is not in (0, 1) or n_total < 1.
    """
    if not 0.0 < pfa < 1.0:
        msg = f"pfa must be in (0, 1), got {pfa}"
        raise ValueError(msg)
    if n_total < 1:
        msg = f"n_total must be >= 1, got {n_total}"
        raise ValueError(msg)
    return float(n_total) * (math.pow(pfa, -1.0 / n_total) - 1.0)


# ---------------------------------------------------------------------
# 1-D CFARs
# ---------------------------------------------------------------------


def _validate_1d_window(power: NDArray[np.float64], n_guard: int, n_train: int) -> None:
    if power.ndim != 1:
        msg = f"power must be 1-D, got shape {power.shape}"
        raise ValueError(msg)
    if n_guard < 0:
        msg = f"n_guard must be >= 0, got {n_guard}"
        raise ValueError(msg)
    if n_train < 1:
        msg = f"n_train must be >= 1, got {n_train}"
        raise ValueError(msg)
    half_window = n_guard + n_train
    if power.size <= 2 * half_window:
        msg = (
            f"power length {power.size} is too small for n_guard={n_guard} + "
            f"n_train={n_train} (need > {2 * half_window})"
        )
        raise ValueError(msg)


def ca_cfar_1d(
    power: NDArray[np.float64],
    *,
    n_guard: int,
    n_train: int,
    alpha: float,
) -> NDArray[np.bool_]:
    """1-D CA-CFAR detection mask.

    For each cell ``i`` with at least ``n_guard + n_train`` neighbours
    on both sides, the training cells are
    ``power[i - n_guard - n_train : i - n_guard]`` and
    ``power[i + n_guard + 1 : i + n_guard + n_train + 1]``. The threshold
    is ``alpha * mean(training)``. Cells too close to either edge are
    flagged ``False`` (not detected) since the window doesn't fit.

    Args:
        power: Detected power vector (linear scale, non-negative).
        n_guard: Guard cells on each side of the CUT.
        n_train: Training cells on each side of the CUT.
        alpha: Threshold multiplier (use :func:`alpha_ca_for_pfa` to
            translate a Pfa target).

    Returns:
        Boolean mask of the same shape as ``power``; ``True`` where
        the cell exceeds the local CA-CFAR threshold.
    """
    _validate_1d_window(power, n_guard, n_train)
    if alpha < 0.0:
        msg = f"alpha must be >= 0, got {alpha}"
        raise ValueError(msg)

    n = power.size
    half = n_guard + n_train
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(half, n - half):
        left = power[i - half : i - n_guard]
        right = power[i + n_guard + 1 : i + half + 1]
        train_mean = (left.sum() + right.sum()) / (2 * n_train)
        threshold = alpha * float(train_mean)
        mask[i] = bool(power[i] > threshold)
    return mask


def os_cfar_1d(
    power: NDArray[np.float64],
    *,
    n_guard: int,
    n_train: int,
    k_index: int,
    alpha: float,
) -> NDArray[np.bool_]:
    """1-D OS-CFAR detection mask.

    Same windowing as CA-CFAR; threshold uses the ``k_index``-th sorted
    training cell (0 = smallest, ``2 * n_train - 1`` = largest).
    Rohling-style OS uses ``k ~ 0.75 * (2 * n_train)`` for a good
    target-masking / CFAR-loss compromise.

    Args:
        power: Detected power vector.
        n_guard: Guard cells per side.
        n_train: Training cells per side.
        k_index: Order index in [0, 2 * n_train - 1].
        alpha: Threshold multiplier on the order statistic.

    Returns:
        Boolean detection mask.
    """
    _validate_1d_window(power, n_guard, n_train)
    if alpha < 0.0:
        msg = f"alpha must be >= 0, got {alpha}"
        raise ValueError(msg)
    if not 0 <= k_index < 2 * n_train:
        msg = f"k_index must be in [0, {2 * n_train - 1}], got {k_index}"
        raise ValueError(msg)

    n = power.size
    half = n_guard + n_train
    mask = np.zeros(n, dtype=np.bool_)
    for i in range(half, n - half):
        left = power[i - half : i - n_guard]
        right = power[i + n_guard + 1 : i + half + 1]
        train = np.concatenate((left, right))
        sorted_train = np.sort(train)
        order_stat = float(sorted_train[k_index])
        threshold = alpha * order_stat
        mask[i] = bool(power[i] > threshold)
    return mask


# ---------------------------------------------------------------------
# 2-D CA-CFAR (range x doppler)
# ---------------------------------------------------------------------


def ca_cfar_2d(
    power: NDArray[np.float64],
    *,
    n_guard_r: int,
    n_train_r: int,
    n_guard_d: int,
    n_train_d: int,
    alpha: float,
) -> NDArray[np.bool_]:
    """2-D CA-CFAR for a range-doppler map.

    Square (rectangular) reference window with separate guard /
    training extents along each axis. Training cells are everything
    inside the outer window minus the guard region (a cross shape:
    we use the rectangular ring, the standard textbook form).

    Args:
        power: 2-D power array shape ``(n_range, n_doppler)``.
        n_guard_r / n_train_r: Range-axis guard / training cells per side.
        n_guard_d / n_train_d: Doppler-axis guard / training cells per side.
        alpha: Threshold multiplier.

    Returns:
        Boolean mask of the same shape; ``True`` where the cell beats
        the local mean times ``alpha``.
    """
    if power.ndim != 2:
        msg = f"power must be 2-D, got shape {power.shape}"
        raise ValueError(msg)
    if alpha < 0.0:
        msg = f"alpha must be >= 0, got {alpha}"
        raise ValueError(msg)
    for name, val in (
        ("n_guard_r", n_guard_r),
        ("n_guard_d", n_guard_d),
    ):
        if val < 0:
            msg = f"{name} must be >= 0, got {val}"
            raise ValueError(msg)
    for name, val in (("n_train_r", n_train_r), ("n_train_d", n_train_d)):
        if val < 1:
            msg = f"{name} must be >= 1, got {val}"
            raise ValueError(msg)

    n_r, n_d = power.shape
    half_r = n_guard_r + n_train_r
    half_d = n_guard_d + n_train_d
    if n_r <= 2 * half_r or n_d <= 2 * half_d:
        msg = (
            f"power shape {power.shape} too small for window "
            f"({half_r} per range side, {half_d} per doppler side)"
        )
        raise ValueError(msg)

    mask = np.zeros((n_r, n_d), dtype=np.bool_)
    # Total reference cells = outer rect area - inner (guard+CUT) rect area.
    outer_r = 2 * half_r + 1
    outer_d = 2 * half_d + 1
    inner_r = 2 * n_guard_r + 1
    inner_d = 2 * n_guard_d + 1
    n_train_total = outer_r * outer_d - inner_r * inner_d
    for i in range(half_r, n_r - half_r):
        for j in range(half_d, n_d - half_d):
            outer = power[i - half_r : i + half_r + 1, j - half_d : j + half_d + 1]
            inner = power[i - n_guard_r : i + n_guard_r + 1, j - n_guard_d : j + n_guard_d + 1]
            train_sum = float(outer.sum()) - float(inner.sum())
            train_mean = train_sum / n_train_total
            mask[i, j] = bool(power[i, j] > alpha * train_mean)
    return mask
