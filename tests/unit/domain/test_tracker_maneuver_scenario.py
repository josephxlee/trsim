"""Tracker maneuver scenario regression (Phase 5.22).

Companion to ``tests/unit/domain/test_ekf_ukf_scenario.py`` (Phase
5.17). 5.17 verified single-step + multi-step behaviour on a pure
constant-velocity truth. This file adds the maneuver layer:

- Settled CV truth + perfect measurements drive both filters to
  near-zero innovation (no model bias);
- A sudden velocity step (90 deg heading change) produces innovation
  norms an order of magnitude larger — the maneuver-detection
  signature;
- On the velocity-step scenario EKF and UKF produce essentially the
  same RMSE because the constant-velocity F matrix dominates the
  error (no model nonlinearity for UKF to exploit beyond what EKF
  already gets from the Jacobian);
- Increasing process noise tightens tracking error during the
  maneuver (filter trusts measurements more, accepts the model
  mismatch faster);
- The full multi-frame run is deterministic for fixed inputs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Final

import numpy as np
import pytest

from workbench.domain.tracker import ekf, ukf
from workbench.domain.tracker.track_state import Detection, TrackState

_DT_S: Final[float] = 0.1
_N_FRAMES: Final[int] = 80
_STEP_FRAME: Final[int] = 30  # frame index where heading flips


def _truth_cv(k: int) -> np.ndarray:
    """Pure CV truth for the settled scenario."""
    t = k * _DT_S
    return np.array(
        [5000.0 + 100.0 * t, 5000.0, 500.0, 100.0, 0.0, 0.0],
        dtype=np.float64,
    )


def _truth_step(k: int) -> np.ndarray:
    """Velocity step at ``_STEP_FRAME``: heading flips +E -> +N."""
    t = k * _DT_S
    if k <= _STEP_FRAME:
        return np.array(
            [5000.0 + 100.0 * t, 5000.0, 500.0, 100.0, 0.0, 0.0],
            dtype=np.float64,
        )
    t0 = _STEP_FRAME * _DT_S
    return np.array(
        [
            5000.0 + 100.0 * t0,
            5000.0 + 200.0 * (t - t0),
            500.0,
            0.0,
            200.0,
            0.0,
        ],
        dtype=np.float64,
    )


def _det_for(state: np.ndarray, sim_t_s: float) -> Detection:
    e, n, u = float(state[0]), float(state[1]), float(state[2])
    return Detection(
        range_m=math.sqrt(e * e + n * n + u * u),
        az_rad=math.atan2(e, n),
        el_rad=math.atan2(u, math.hypot(e, n)),
        sim_t_s=sim_t_s,
    )


def _initial_track_at_truth(truth0: np.ndarray) -> TrackState:
    cov = np.diag(np.array([25.0, 25.0, 25.0, 4.0, 4.0, 4.0], dtype=np.float64))
    return TrackState(track_id=0, mean=truth0.copy(), covariance=cov, sim_t_s=0.0)


def _run_ekf(
    truth_fn: Callable[[int], np.ndarray],
    n_frames: int,
    config: ekf.EKFConfig,
) -> tuple[list[float], list[float]]:
    """Run EKF; return (innovation_norms, position_errors) per frame."""
    track = _initial_track_at_truth(truth_fn(0))
    innov_norms: list[float] = []
    pos_errs: list[float] = []
    for k in range(1, n_frames + 1):
        predicted = ekf.predict(track, _DT_S, config)
        det = _det_for(truth_fn(k), k * _DT_S)
        z_pred = ekf.measurement_function(predicted.mean)
        z_meas = np.array([det.range_m, det.az_rad, det.el_rad], dtype=np.float64)
        innov = z_meas - z_pred
        innov[1] = math.atan2(math.sin(innov[1]), math.cos(innov[1]))
        innov_norms.append(float(np.linalg.norm(innov)))
        track = ekf.update(predicted, det, config)
        pos_errs.append(float(np.linalg.norm(track.mean[:3] - truth_fn(k)[:3])))
    return innov_norms, pos_errs


def _run_ukf(
    truth_fn: Callable[[int], np.ndarray],
    n_frames: int,
    config: ukf.UKFConfig,
) -> list[float]:
    track = _initial_track_at_truth(truth_fn(0))
    pos_errs: list[float] = []
    for k in range(1, n_frames + 1):
        predicted = ukf.predict(track, _DT_S, config)
        det = _det_for(truth_fn(k), k * _DT_S)
        track = ukf.update(predicted, det, config)
        pos_errs.append(float(np.linalg.norm(track.mean[:3] - truth_fn(k)[:3])))
    return pos_errs


def _rmse(values: list[float]) -> float:
    arr = np.asarray(values, dtype=np.float64)
    return float(math.sqrt(float(np.mean(arr * arr))))


# ---------------------------------------------------------------------
# Settled-CV: innovation -> ~0
# ---------------------------------------------------------------------


def test_settled_cv_innovation_goes_to_zero() -> None:
    """When truth is exactly CV and the filter is initialised at truth,
    perfect measurements give vanishing innovation — the EKF tracks
    the truth without bias.
    """
    config = ekf.EKFConfig()
    innov, _ = _run_ekf(_truth_cv, 30, config)
    # After 30 perfect frames the innovation norm must be machine-zero.
    assert max(innov[-10:]) < 1e-9


# ---------------------------------------------------------------------
# Maneuver detection signature
# ---------------------------------------------------------------------


def test_velocity_step_innovation_spikes_post_maneuver() -> None:
    """The 90-deg velocity step at frame 30 creates a sustained model
    mismatch. Post-step innovation must dwarf the pre-step level —
    this is the signature an outer pipeline uses for maneuver detection.
    """
    config = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    innov, _ = _run_ekf(_truth_step, _N_FRAMES, config)
    pre_mean = float(np.mean(innov[:25]))
    post_mean = float(np.mean(innov[35:]))
    # Pre is essentially zero; post should be at least an order of
    # magnitude larger in absolute terms.
    assert post_mean > 1.0
    assert post_mean > 100.0 * (pre_mean + 1e-12)


# ---------------------------------------------------------------------
# EKF ~ UKF on the maneuver scenario
# ---------------------------------------------------------------------


def test_ekf_ukf_rmse_match_on_velocity_step() -> None:
    """On the velocity-step scenario the CV F matrix is the dominant
    source of error for both filters. The Jacobian-linearised EKF
    and the sigma-point UKF therefore deliver near-identical RMSE
    — UKF/EKF ratio must stay inside [0.95, 1.05].
    """
    e_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    u_cfg = ukf.UKFConfig(process_noise_accel_std_mps2=5.0)
    _, e_err = _run_ekf(_truth_step, _N_FRAMES, e_cfg)
    u_err = _run_ukf(_truth_step, _N_FRAMES, u_cfg)
    ratio = _rmse(u_err) / _rmse(e_err)
    assert 0.95 < ratio < 1.05


# ---------------------------------------------------------------------
# Higher process noise tightens tracking under maneuver
# ---------------------------------------------------------------------


def test_higher_process_noise_reduces_post_maneuver_error() -> None:
    """Increasing process-noise std lets the filter trust measurements
    more — post-maneuver RMSE shrinks. A monotonic relationship is
    too strong to guarantee in general, but doubling sigma_a from
    1 m/s^2 to 10 m/s^2 measurably reduces the error after the step.
    """
    low_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=1.0)
    high_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=10.0)
    _, low_err = _run_ekf(_truth_step, _N_FRAMES, low_cfg)
    _, high_err = _run_ekf(_truth_step, _N_FRAMES, high_cfg)
    rmse_low_post = _rmse(low_err[35:])
    rmse_high_post = _rmse(high_err[35:])
    assert rmse_high_post < rmse_low_post


# ---------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------


def test_maneuver_run_is_deterministic() -> None:
    """Two runs with identical inputs return identical sequences."""
    config = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    _, errs_a = _run_ekf(_truth_step, _N_FRAMES, config)
    _, errs_b = _run_ekf(_truth_step, _N_FRAMES, config)
    for a, b in zip(errs_a, errs_b, strict=True):
        assert a == pytest.approx(b, abs=0.0)
