"""Tracker maneuver scenario regression (Phase 5.22 + 5.22b).

Companion to ``tests/unit/domain/test_ekf_ukf_scenario.py`` (Phase
5.17). 5.17 verified single-step + multi-step behaviour on a pure
constant-velocity truth. This file adds the maneuver layer:

5.22 (existing) — instantaneous velocity step:
- Settled CV truth + perfect measurements drive both filters to
  near-zero innovation (no model bias).
- A 90 deg heading change produces innovation norms an order of
  magnitude larger — the maneuver-detection signature.
- On the velocity-step scenario EKF and UKF produce essentially the
  same RMSE because the constant-velocity F matrix dominates the
  error (no model nonlinearity for UKF to exploit beyond what EKF
  already gets from the Jacobian).
- Increasing process noise tightens tracking error during the
  maneuver (filter trusts measurements more, accepts the model
  mismatch faster).
- The full multi-frame run is deterministic for fixed inputs.

5.22b (this revision) — sustained coordinated turn:
- A constant-turn-rate (0.157 rad/s, ~9 deg/s, ~1.6 g centripetal)
  scenario applied after the settled prefix.
- The truth function preserves |v| and traces a circle of radius
  v / omega (sanity-lock on the Bar-Shalom CT closed-form).
- Sustained model-mismatch produces a *plateau* of large innovation
  (vs the transient spike of a single velocity step).
- The CV F matrix still dominates so EKF/UKF RMSE stay within a
  generous band (wider than the velocity-step case because the
  measurement-Jacobian linearisation error builds up over the turn).
- Higher process-noise std reduces post-entry RMSE (same direction
  as the velocity-step case).
- Deterministic under fixed truth.
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


# ---------------------------------------------------------------------
# 5.22b — coordinated-turn (sustained ~1.6 g maneuver)
# ---------------------------------------------------------------------

_OMEGA_TURN_RAD_S: Final[float] = 0.157
"""Coordinated-turn rate in rad/s (~9 deg/s). With v0 = 100 m/s this
gives a centripetal acceleration of 15.7 m/s^2 (~1.6 g) and a turn
radius of v / omega = 636.94 m. Sustained from frame 30 to frame 80
(5 s of turning, ~45 deg of arc)."""


def _truth_ct(k: int) -> np.ndarray:
    """Coordinated-turn truth: settled CV until ``_STEP_FRAME``, then
    constant turn rate ``_OMEGA_TURN_RAD_S`` about a vertical axis.

    Closed-form (Bar-Shalom Tracking ch.11, Sec.11.7.2 CT model with
    yaw rate omega):

        x(t) = x0 + (sin(w t)/w) vx0 - ((1 - cos(w t))/w) vy0
        y(t) = y0 + ((1 - cos(w t))/w) vx0 + (sin(w t)/w) vy0
        vx(t) = cos(w t) vx0 - sin(w t) vy0
        vy(t) = sin(w t) vx0 + cos(w t) vy0

    Vertical components are unchanged (z = 500, vz = 0).
    """
    t = k * _DT_S
    if k <= _STEP_FRAME:
        return np.array(
            [5000.0 + 100.0 * t, 5000.0, 500.0, 100.0, 0.0, 0.0],
            dtype=np.float64,
        )
    t0 = _STEP_FRAME * _DT_S
    dt = t - t0
    x0 = 5000.0 + 100.0 * t0
    y0 = 5000.0
    vx0 = 100.0
    vy0 = 0.0
    w = _OMEGA_TURN_RAD_S
    sin_wt = math.sin(w * dt)
    cos_wt = math.cos(w * dt)
    x = x0 + (sin_wt / w) * vx0 - ((1.0 - cos_wt) / w) * vy0
    y = y0 + ((1.0 - cos_wt) / w) * vx0 + (sin_wt / w) * vy0
    vx = cos_wt * vx0 - sin_wt * vy0
    vy = sin_wt * vx0 + cos_wt * vy0
    return np.array([x, y, 500.0, vx, vy, 0.0], dtype=np.float64)


def test_coordinated_turn_truth_preserves_speed() -> None:
    """A pure CT must keep |v| invariant — the only thing changing is
    velocity direction. Sample several post-entry frames and confirm
    |v| = 100 m/s (the entry speed) to rtol 1e-12.
    """
    for k in (35, 40, 50, 60, 70, 80):
        state = _truth_ct(k)
        speed = math.hypot(float(state[3]), float(state[4]))
        assert speed == pytest.approx(100.0, rel=1e-12)


def test_coordinated_turn_truth_traces_circle_of_correct_radius() -> None:
    """After the turn entry, the truth position must lie on a circle of
    radius v / omega around the turn center. For a left turn from +E
    heading at (x0, y0) the center sits at (x0, y0 + v/omega).
    """
    t0 = _STEP_FRAME * _DT_S
    x0 = 5000.0 + 100.0 * t0
    y0 = 5000.0
    radius = 100.0 / _OMEGA_TURN_RAD_S
    cx, cy = x0, y0 + radius
    for k in (35, 45, 55, 70, 80):
        state = _truth_ct(k)
        dx = float(state[0]) - cx
        dy = float(state[1]) - cy
        assert math.hypot(dx, dy) == pytest.approx(radius, rel=1e-9)


def test_coordinated_turn_innovation_plateau_post_entry() -> None:
    """Sustained CT produces a plateau of innovation (vs the single
    spike of a velocity step). Compare the mean innovation in a window
    well inside the turn (frames 45..60) against the settled prefix.
    """
    config = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    innov, _ = _run_ekf(_truth_ct, _N_FRAMES, config)
    pre_mean = float(np.mean(innov[:25]))
    plateau_mean = float(np.mean(innov[45:60]))
    assert plateau_mean > 1.0
    assert plateau_mean > 50.0 * (pre_mean + 1e-12)


def test_coordinated_turn_ekf_ukf_rmse_match() -> None:
    """On the CT scenario the CV F matrix still dominates both filters;
    EKF/UKF RMSE should match within a generous band. The band is wider
    than 5.22's velocity step (0.95..1.05) because the measurement-
    Jacobian linearisation error accumulates over the sustained turn.
    """
    e_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    u_cfg = ukf.UKFConfig(process_noise_accel_std_mps2=5.0)
    _, e_err = _run_ekf(_truth_ct, _N_FRAMES, e_cfg)
    u_err = _run_ukf(_truth_ct, _N_FRAMES, u_cfg)
    ratio = _rmse(u_err) / _rmse(e_err)
    assert 0.85 < ratio < 1.15, f"UKF/EKF ratio out of band: {ratio}"


def test_coordinated_turn_higher_process_noise_reduces_post_entry_error() -> None:
    """Same direction as 5.22's velocity-step result: increasing the
    process-noise std from 1 to 10 m/s^2 lowers post-entry RMSE — the
    filter trusts measurements more and accepts the CV-vs-CT model
    mismatch faster.
    """
    low_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=1.0)
    high_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=10.0)
    _, low_err = _run_ekf(_truth_ct, _N_FRAMES, low_cfg)
    _, high_err = _run_ekf(_truth_ct, _N_FRAMES, high_cfg)
    rmse_low_post = _rmse(low_err[35:])
    rmse_high_post = _rmse(high_err[35:])
    assert rmse_high_post < rmse_low_post


def test_coordinated_turn_run_is_deterministic() -> None:
    """Two CT runs with identical inputs return identical error sequences."""
    config = ekf.EKFConfig(process_noise_accel_std_mps2=5.0)
    _, errs_a = _run_ekf(_truth_ct, _N_FRAMES, config)
    _, errs_b = _run_ekf(_truth_ct, _N_FRAMES, config)
    for a, b in zip(errs_a, errs_b, strict=True):
        assert a == pytest.approx(b, abs=0.0)
