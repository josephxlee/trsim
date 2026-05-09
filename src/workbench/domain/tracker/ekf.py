"""Extended Kalman Filter — constant-velocity ENU model (plan/03 § 3.2.1k).

Phase 2.8 — minimum-viable EKF for 6D position/velocity tracking with
spherical (range, az, el) measurements. Default for "weak nonlinearity"
targets per plan/03 (UKF takes over for high-g maneuvering targets).

State: ``x = [e, n, u, vE, vN, vU]`` [m, m/s].
Process model: constant velocity. ``F(dt) = [[I3, dt*I3], [0, I3]]``.
Process noise: discrete white-noise acceleration, ``Q(dt) = sigma_a^2 *
[[dt^4/4 * I3, dt^3/2 * I3], [dt^3/2 * I3, dt^2 * I3]]``.

Measurement: ``z = h(x) = [range, az, el]`` (Jacobian computed
analytically below). Doppler is not in the measurement vector at MVP
to keep the Jacobian compact; it can be added at MVP+alpha as a
4-row variant.

Conventions:
- az = atan2(east, north) (CW from N — matches project heading).
- el = atan2(up, sqrt(e^2 + n^2)).
- range > 0 (we reject 0-range measurements via the Detection
  validation).

References:

- Bar-Shalom, *Estimation with Applications to Tracking and Navigation*,
  ch.4 / ch.10 (CV model).
- plan/03 § 3.2.1k — TRsim tracker abstraction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from workbench.domain.tracker.track_state import (
    MEASUREMENT_DIM,
    STATE_DIM,
    Detection,
    TrackState,
    TrackStatus,
)


@dataclass(frozen=True, slots=True)
class EKFConfig:
    """EKF tuning parameters.

    Attributes:
        process_noise_accel_std_mps2: Process-noise standard deviation
            interpreted as a white-noise-acceleration RMS [m/s^2]. Larger
            values let the filter chase aggressive maneuvers but trust
            the dynamics less.
        range_noise_std_m: Range measurement std [m].
        az_noise_std_rad: Azimuth measurement std [rad].
        el_noise_std_rad: Elevation measurement std [rad].

    Raises:
        ValueError: For any non-positive std.
    """

    process_noise_accel_std_mps2: float = 1.0
    range_noise_std_m: float = 5.0
    az_noise_std_rad: float = math.radians(0.5)
    el_noise_std_rad: float = math.radians(0.5)

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


# ---------------------------------------------------------------------
# State transition + process noise (constant-velocity)
# ---------------------------------------------------------------------


def state_transition_matrix(dt_s: float) -> NDArray[np.float64]:
    """``F(dt)`` for the 6D constant-velocity model."""
    f = np.eye(STATE_DIM, dtype=np.float64)
    f[0, 3] = dt_s
    f[1, 4] = dt_s
    f[2, 5] = dt_s
    return f


def process_noise_matrix(dt_s: float, accel_std_mps2: float) -> NDArray[np.float64]:
    """``Q(dt)`` — discrete white-noise-acceleration model (Bar-Shalom 6.3.3)."""
    sigma2 = accel_std_mps2 * accel_std_mps2
    dt2 = dt_s * dt_s
    dt3 = dt_s * dt2
    dt4 = dt_s * dt3
    q = np.zeros((STATE_DIM, STATE_DIM), dtype=np.float64)
    # Position-position block: dt^4/4
    q[0:3, 0:3] = np.eye(3) * (dt4 / 4.0)
    # Position-velocity / velocity-position cross: dt^3/2
    q[0:3, 3:6] = np.eye(3) * (dt3 / 2.0)
    q[3:6, 0:3] = np.eye(3) * (dt3 / 2.0)
    # Velocity-velocity: dt^2
    q[3:6, 3:6] = np.eye(3) * dt2
    return q * sigma2


# ---------------------------------------------------------------------
# Measurement function + Jacobian
# ---------------------------------------------------------------------


def measurement_function(state_mean: NDArray[np.float64]) -> NDArray[np.float64]:
    """``h(x) = [range, az, el]`` from ENU position."""
    e, n, u = float(state_mean[0]), float(state_mean[1]), float(state_mean[2])
    range_m = math.sqrt(e * e + n * n + u * u)
    az = math.atan2(e, n)
    horiz = math.hypot(e, n)
    el = math.atan2(u, horiz)
    return np.array([range_m, az, el], dtype=np.float64)


def measurement_jacobian(state_mean: NDArray[np.float64]) -> NDArray[np.float64]:
    """``H = dh/dx`` evaluated at ``state_mean``.

    Shape ``(3, 6)``. Velocity columns are zero (range/az/el depend
    only on position at the MVP — no Doppler row).
    """
    e, n, u = float(state_mean[0]), float(state_mean[1]), float(state_mean[2])
    range_m = math.sqrt(e * e + n * n + u * u)
    if range_m == 0.0:
        msg = "measurement Jacobian undefined at origin (range = 0)"
        raise ValueError(msg)
    horiz = math.hypot(e, n)

    h = np.zeros((MEASUREMENT_DIM, STATE_DIM), dtype=np.float64)
    # d(range) / d(e, n, u) = (e, n, u) / range
    h[0, 0] = e / range_m
    h[0, 1] = n / range_m
    h[0, 2] = u / range_m
    # az = atan2(e, n) -> d/de = n / (e^2 + n^2), d/dn = -e / (e^2 + n^2)
    if horiz > 0.0:
        h[1, 0] = n / (e * e + n * n)
        h[1, 1] = -e / (e * e + n * n)
        # el = atan2(u, horiz) -> d/de = -e*u / (range^2 * horiz),
        # d/dn = -n*u / (range^2 * horiz), d/du = horiz / range^2
        h[2, 0] = -e * u / (range_m * range_m * horiz)
        h[2, 1] = -n * u / (range_m * range_m * horiz)
        h[2, 2] = horiz / (range_m * range_m)
    # else: target directly above radar — az/el degenerate. We leave
    # the rows zero, which is the right thing for the EKF's posterior
    # — those measurements carry no info from this geometry.
    return h


# ---------------------------------------------------------------------
# EKF predict / update
# ---------------------------------------------------------------------


def predict(state: TrackState, dt_s: float, config: EKFConfig) -> TrackState:
    """One-step prediction: ``x' = F x``, ``P' = F P F^T + Q``.

    Args:
        state: Prior state.
        dt_s: Time advance [s]. Must be >= 0.
        config: EKF tuning.

    Returns:
        Predicted :class:`TrackState`.
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


def update(state: TrackState, detection: Detection, config: EKFConfig) -> TrackState:
    """Measurement update step.

    Innovation: ``y = z - h(x)``. Innovation covariance: ``S = H P H^T + R``.
    Kalman gain: ``K = P H^T S^-1``. Posterior: ``x' = x + K y``,
    ``P' = (I - K H) P``.

    The azimuth innovation is wrapped into ``(-pi, +pi]`` to avoid
    1-cycle jumps at the +/- pi boundary.

    Args:
        state: Prior state (typically the predicted state).
        detection: Measurement at this frame.
        config: EKF tuning.

    Returns:
        Posterior :class:`TrackState` with ``consecutive_misses = 0``
        and status escalated TENTATIVE -> CONFIRMED on first update
        (the lifecycle policy is intentionally simple at MVP — a
        proper M-of-N rule lives at the Pipeline layer).
    """
    h_mat = measurement_jacobian(state.mean)
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

    z_pred = measurement_function(state.mean)
    z_meas = np.array([detection.range_m, detection.az_rad, detection.el_rad], dtype=np.float64)
    innovation = z_meas - z_pred
    # Wrap azimuth innovation to (-pi, +pi].
    innovation[1] = math.atan2(math.sin(innovation[1]), math.cos(innovation[1]))

    s_mat = h_mat @ state.covariance @ h_mat.T + r_mat
    kalman_gain = state.covariance @ h_mat.T @ np.linalg.inv(s_mat)
    new_mean = state.mean + kalman_gain @ innovation
    eye = np.eye(STATE_DIM, dtype=np.float64)
    new_cov = (eye - kalman_gain @ h_mat) @ state.covariance

    status = TrackStatus.CONFIRMED if state.status is TrackStatus.TENTATIVE else state.status
    return TrackState(
        track_id=state.track_id,
        mean=new_mean,
        covariance=new_cov,
        sim_t_s=detection.sim_t_s,
        status=status,
        consecutive_misses=0,
    )
