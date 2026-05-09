"""Unscented Kalman Filter — sigma-point variant of EKF (plan/03 § 3.2.1k).

Phase 2.8 — alternative to :mod:`workbench.domain.tracker.ekf` for
high-nonlinearity scenarios (high-g maneuvers, far ranges where the
spherical measurement function is steeply nonlinear). Same state /
measurement convention; different propagation: ``2 n + 1`` sigma points
through ``f`` / ``h`` instead of a Jacobian linearisation.

Sigma points (Julier & Uhlmann 1997):

- Spread parameter ``alpha`` (small for tight scaling, default 1e-3).
- Secondary scaling ``kappa`` (default 0).
- Distribution prior ``beta`` (default 2 = optimal for Gaussian).
- ``lambda = alpha^2 * (n + kappa) - n``, ``c = n + lambda``.
- ``W_m[0] = lambda / c``, ``W_c[0] = lambda / c + (1 - alpha^2 + beta)``.
- ``W_m[i] = W_c[i] = 1 / (2 c)`` for ``i = 1..2 n``.

Same constant-velocity dynamics + (range, az, el) measurement
function as the EKF (re-uses ``state_transition_matrix`` /
``process_noise_matrix`` / ``measurement_function``).

References:

- Julier & Uhlmann, *A New Extension of the Kalman Filter to Nonlinear
  Systems* (1997).
- Wan & van der Merwe, *The Unscented Kalman Filter for Nonlinear
  Estimation* (2000).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from workbench.domain.tracker.ekf import (
    measurement_function,
    process_noise_matrix,
    state_transition_matrix,
)
from workbench.domain.tracker.track_state import (
    MEASUREMENT_DIM,
    STATE_DIM,
    Detection,
    TrackState,
    TrackStatus,
)


@dataclass(frozen=True, slots=True)
class UKFConfig:
    """UKF tuning + sigma-point parameters.

    Attributes:
        process_noise_accel_std_mps2: Same as the EKF.
        range_noise_std_m / az_noise_std_rad / el_noise_std_rad: Same.
        alpha: Sigma-point spread, in (0, 1]. Default 1e-3.
        beta: Distribution prior. Default 2 (optimal for Gaussian).
        kappa: Secondary scaling. Default 0.

    Raises:
        ValueError: For non-positive stds, alpha out of (0, 1], or
            negative kappa.
    """

    process_noise_accel_std_mps2: float = 1.0
    range_noise_std_m: float = 5.0
    az_noise_std_rad: float = math.radians(0.5)
    el_noise_std_rad: float = math.radians(0.5)
    alpha: float = 1e-3
    beta: float = 2.0
    kappa: float = 0.0

    def __post_init__(self) -> None:
        if self.process_noise_accel_std_mps2 <= 0.0:
            msg = "process_noise_accel_std_mps2 must be > 0"
            raise ValueError(msg)
        if self.range_noise_std_m <= 0.0:
            msg = "range_noise_std_m must be > 0"
            raise ValueError(msg)
        if self.az_noise_std_rad <= 0.0:
            msg = "az_noise_std_rad must be > 0"
            raise ValueError(msg)
        if self.el_noise_std_rad <= 0.0:
            msg = "el_noise_std_rad must be > 0"
            raise ValueError(msg)
        if not 0.0 < self.alpha <= 1.0:
            msg = f"alpha must be in (0, 1], got {self.alpha}"
            raise ValueError(msg)
        if self.kappa < 0.0:
            msg = f"kappa must be >= 0, got {self.kappa}"
            raise ValueError(msg)


def _sigma_points_and_weights(
    mean: NDArray[np.float64],
    covariance: NDArray[np.float64],
    alpha: float,
    beta: float,
    kappa: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Generate ``2 n + 1`` sigma points and their weights.

    Returns ``(sigmas, w_mean, w_cov)`` where ``sigmas`` is shape
    ``(2 n + 1, n)``.
    """
    n = STATE_DIM
    lam = alpha * alpha * (n + kappa) - n
    c = n + lam
    # Cholesky of c * P. We use np.linalg.cholesky which expects PD.
    sqrt_cp = np.linalg.cholesky(c * covariance)

    sigmas = np.zeros((2 * n + 1, n), dtype=np.float64)
    sigmas[0] = mean
    for i in range(n):
        sigmas[1 + i] = mean + sqrt_cp[:, i]
        sigmas[1 + n + i] = mean - sqrt_cp[:, i]

    w_mean = np.full(2 * n + 1, 1.0 / (2.0 * c), dtype=np.float64)
    w_cov = np.full(2 * n + 1, 1.0 / (2.0 * c), dtype=np.float64)
    w_mean[0] = lam / c
    w_cov[0] = lam / c + (1.0 - alpha * alpha + beta)
    return sigmas, w_mean, w_cov


def predict(state: TrackState, dt_s: float, config: UKFConfig) -> TrackState:
    """One-step prediction via sigma-point propagation.

    The CV dynamics is linear, so for this MVP we re-use the EKF
    closed form (``F``, ``Q``). This keeps the predict step cheap
    and reserves the sigma-point machinery for the nonlinear update
    step where it matters.
    """
    if dt_s < 0.0:
        msg = f"dt_s must be >= 0, got {dt_s}"
        raise ValueError(msg)
    f = state_transition_matrix(dt_s)
    q = process_noise_matrix(dt_s, config.process_noise_accel_std_mps2)
    new_mean = f @ state.mean
    new_cov = f @ state.covariance @ f.T + q
    return TrackState(
        track_id=state.track_id,
        mean=new_mean,
        covariance=new_cov,
        sim_t_s=state.sim_t_s + dt_s,
        status=state.status,
        consecutive_misses=state.consecutive_misses,
    )


def update(state: TrackState, detection: Detection, config: UKFConfig) -> TrackState:
    """Sigma-point measurement update.

    1. Generate sigma points ``X_i`` from ``(mean, cov)``.
    2. Project through ``h``: ``Z_i = h(X_i)``.
    3. Predicted measurement ``z_pred = sum w_m_i Z_i``.
    4. ``P_zz = sum w_c_i (Z_i - z_pred)(Z_i - z_pred)^T + R``.
    5. ``P_xz = sum w_c_i (X_i - mean)(Z_i - z_pred)^T``.
    6. ``K = P_xz P_zz^-1``, ``mean' = mean + K (z - z_pred)``,
       ``P' = P - K P_zz K^T``.
    """
    sigmas, w_mean, w_cov = _sigma_points_and_weights(
        state.mean, state.covariance, config.alpha, config.beta, config.kappa
    )

    # Project sigma points through h
    z_sigmas = np.array([measurement_function(s) for s in sigmas], dtype=np.float64)

    # Predicted measurement (weighted mean). For azimuth we have to
    # be cycle-aware when sigmas straddle +/- pi; for the small spread
    # we use here that's almost never an issue, so a plain weighted
    # average is fine at MVP.
    z_pred = w_mean @ z_sigmas

    # Innovation covariance + cross covariance
    r_mat = np.diag(
        np.array(
            [
                config.range_noise_std_m**2,
                config.az_noise_std_rad**2,
                config.el_noise_std_rad**2,
            ],
            dtype=np.float64,
        )
    )
    p_zz = np.zeros((MEASUREMENT_DIM, MEASUREMENT_DIM), dtype=np.float64)
    p_xz = np.zeros((STATE_DIM, MEASUREMENT_DIM), dtype=np.float64)
    for i, s in enumerate(sigmas):
        dz = z_sigmas[i] - z_pred
        # Wrap azimuth difference.
        dz[1] = math.atan2(math.sin(dz[1]), math.cos(dz[1]))
        dx = s - state.mean
        p_zz += w_cov[i] * np.outer(dz, dz)
        p_xz += w_cov[i] * np.outer(dx, dz)
    p_zz += r_mat

    z_meas = np.array([detection.range_m, detection.az_rad, detection.el_rad], dtype=np.float64)
    innovation = z_meas - z_pred
    innovation[1] = math.atan2(math.sin(innovation[1]), math.cos(innovation[1]))

    kalman_gain = p_xz @ np.linalg.inv(p_zz)
    new_mean = state.mean + kalman_gain @ innovation
    new_cov = state.covariance - kalman_gain @ p_zz @ kalman_gain.T

    status = TrackStatus.CONFIRMED if state.status is TrackStatus.TENTATIVE else state.status
    return TrackState(
        track_id=state.track_id,
        mean=new_mean,
        covariance=new_cov,
        sim_t_s=detection.sim_t_s,
        status=status,
        consecutive_misses=0,
    )
