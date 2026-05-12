"""High-g sustained turn tracker regression (Phase 5.22+).

Companion to ``test_tracker_maneuver_scenario.py`` (Phase 5.22). The
original 5.22 file covered a single velocity step (90 deg heading
flip) — one-shot model mismatch. This file adds the *sustained* high-g
maneuver layer: a 9-G coordinated turn that holds for the full run
window, giving the CV tracker model mismatch every single frame.

Scenario:

- Truth is a level, constant-speed horizontal turn.
- ``a_c = 9 * 9.81 m/s^2`` centripetal, ``V = 300 m/s`` tangential.
- Turn radius ``R = V^2 / a_c ~= 1019 m`` (military aircraft limit).
- Period ``T = 2 pi V / a_c ~= 21.3 s``.
- Window covers half a turn (10 s @ dt = 0.05 s = 200 frames) so the
  velocity vector rotates 180 deg — every single CV-model assumption
  is wrong every single frame.

Invariants verified:

- Position RMSE stays bounded by the turn radius (filter is not
  divergent under sustained mismatch — proves the CV F-matrix +
  measurement update still pulls the estimate toward the truth).
- EKF and UKF deliver comparable RMSE (CV-mismatch dominates; the
  Jacobian linearisation and sigma-point propagation give the same
  answer on the linear CV F-matrix to within ~20%).
- Larger process-noise std improves tracking under sustained
  maneuver (the filter trusts measurements more, accepts the model
  mismatch faster).
- Heading at run end has actually flipped ~180 deg (sanity-lock on
  the truth generator).
- Run is fully deterministic for fixed inputs.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Final

import numpy as np
import pytest

from workbench.domain.tracker import ekf, ukf
from workbench.domain.tracker.track_state import Detection, TrackState

_G_MS2: Final[float] = 9.80665
_N_G: Final[float] = 9.0
_A_CENTRIPETAL: Final[float] = _N_G * _G_MS2  # m/s^2
_V_TANGENTIAL: Final[float] = 300.0  # m/s
_TURN_RADIUS_M: Final[float] = _V_TANGENTIAL * _V_TANGENTIAL / _A_CENTRIPETAL
_OMEGA_RAD_S: Final[float] = _A_CENTRIPETAL / _V_TANGENTIAL  # ~0.2942 rad/s
_DT_S: Final[float] = 0.05
_N_FRAMES: Final[int] = 200  # 10 s; half a turn.
_BASE_E_M: Final[float] = 0.0
_BASE_N_M: Final[float] = 15_000.0  # turn center 15 km north of radar
_BASE_U_M: Final[float] = 500.0  # constant altitude


def _truth_9g_turn(k: int) -> np.ndarray:
    """Level coordinated 9-G turn truth at frame ``k``.

    At ``t=0`` the target sits east of the turn centre at offset
    ``(0, R)`` relative to ``(_BASE_E_M, _BASE_N_M)`` with velocity
    pointing east. Center of turn is the ``BASE`` point in ENU.
    """
    t = k * _DT_S
    theta = _OMEGA_RAD_S * t
    e = _BASE_E_M + _TURN_RADIUS_M * math.sin(theta)
    n = _BASE_N_M + _TURN_RADIUS_M * math.cos(theta)
    u = _BASE_U_M
    ve = _V_TANGENTIAL * math.cos(theta)
    vn = -_V_TANGENTIAL * math.sin(theta)
    vu = 0.0
    return np.array([e, n, u, ve, vn, vu], dtype=np.float64)


def _det_for(state: np.ndarray, sim_t_s: float) -> Detection:
    e, n, u = float(state[0]), float(state[1]), float(state[2])
    return Detection(
        range_m=math.sqrt(e * e + n * n + u * u),
        az_rad=math.atan2(e, n),
        el_rad=math.atan2(u, math.hypot(e, n)),
        sim_t_s=sim_t_s,
    )


def _initial_track(truth0: np.ndarray) -> TrackState:
    cov = np.diag(np.array([100.0, 100.0, 25.0, 25.0, 25.0, 25.0], dtype=np.float64))
    return TrackState(track_id=0, mean=truth0.copy(), covariance=cov, sim_t_s=0.0)


def _run_ekf(
    truth_fn: Callable[[int], np.ndarray],
    n_frames: int,
    config: ekf.EKFConfig,
) -> list[float]:
    """Run EKF; return per-frame horizontal position errors."""
    track = _initial_track(truth_fn(0))
    pos_errs: list[float] = []
    for k in range(1, n_frames + 1):
        predicted = ekf.predict(track, _DT_S, config)
        det = _det_for(truth_fn(k), k * _DT_S)
        track = ekf.update(predicted, det, config)
        truth = truth_fn(k)
        # Horizontal-plane error — altitude is held constant.
        dx = track.mean[0] - truth[0]
        dy = track.mean[1] - truth[1]
        pos_errs.append(float(math.hypot(dx, dy)))
    return pos_errs


def _run_ukf(
    truth_fn: Callable[[int], np.ndarray],
    n_frames: int,
    config: ukf.UKFConfig,
) -> list[float]:
    track = _initial_track(truth_fn(0))
    pos_errs: list[float] = []
    for k in range(1, n_frames + 1):
        predicted = ukf.predict(track, _DT_S, config)
        det = _det_for(truth_fn(k), k * _DT_S)
        track = ukf.update(predicted, det, config)
        truth = truth_fn(k)
        dx = track.mean[0] - truth[0]
        dy = track.mean[1] - truth[1]
        pos_errs.append(float(math.hypot(dx, dy)))
    return pos_errs


def _rmse(values: list[float]) -> float:
    arr = np.asarray(values, dtype=np.float64)
    return float(math.sqrt(float(np.mean(arr * arr))))


# ---------------------------------------------------------------------
# Sanity-lock: truth generator produces the half-turn we expect
# ---------------------------------------------------------------------


def test_turn_radius_matches_closed_form() -> None:
    """R = V^2 / a_c with a_c = 9G * 9.80665 — sanity-lock the geometry
    so later invariants reference a known number."""
    assert _TURN_RADIUS_M == pytest.approx(1019.7162129779282, rel=1e-12)


def test_truth_heading_rotates_by_omega_times_window() -> None:
    """After the run window the velocity vector must have rotated by
    exactly ``omega * N * dt`` rad relative to t=0. With the chosen
    constants this works out to ~2.942 rad, well past 90 deg.
    """
    truth0 = _truth_9g_turn(0)
    truth_end = _truth_9g_turn(_N_FRAMES)
    a0 = math.atan2(float(truth0[3]), float(truth0[4]))
    a_end = math.atan2(float(truth_end[3]), float(truth_end[4]))
    delta = abs(((a_end - a0 + math.pi) % (2.0 * math.pi)) - math.pi)
    expected = _OMEGA_RAD_S * _N_FRAMES * _DT_S
    assert delta == pytest.approx(expected, rel=1e-9)
    # And it must exceed 90 deg, so every CV-direction assumption flips.
    assert delta > math.pi / 2.0


def test_truth_speed_is_constant() -> None:
    """Coordinated turn — speed magnitude must equal ``V`` at every
    frame within float epsilon."""
    for k in (0, 50, 100, 150, _N_FRAMES):
        v = _truth_9g_turn(k)
        speed = math.hypot(float(v[3]), float(v[4]))
        assert speed == pytest.approx(_V_TANGENTIAL, rel=1e-12)


# ---------------------------------------------------------------------
# CV tracker survives sustained 9-G mismatch
# ---------------------------------------------------------------------


def test_ekf_position_error_bounded_by_turn_radius() -> None:
    """Sustained 9-G turn — the CV F-matrix is wrong every frame, but
    the measurement update keeps the RMSE bounded by the turn radius
    R (~1 km). A larger RMSE would indicate filter divergence rather
    than the expected lag.
    """
    config = ekf.EKFConfig(process_noise_accel_std_mps2=80.0)
    errs = _run_ekf(_truth_9g_turn, _N_FRAMES, config)
    rmse = _rmse(errs)
    assert rmse < _TURN_RADIUS_M


def test_ukf_position_error_bounded_by_turn_radius() -> None:
    """Same invariant for UKF — sigma-point propagation must not
    diverge under the same sustained model mismatch.
    """
    config = ukf.UKFConfig(process_noise_accel_std_mps2=80.0)
    errs = _run_ukf(_truth_9g_turn, _N_FRAMES, config)
    rmse = _rmse(errs)
    assert rmse < _TURN_RADIUS_M


# ---------------------------------------------------------------------
# EKF ~ UKF on sustained turn (CV F-matrix dominates)
# ---------------------------------------------------------------------


def test_ekf_ukf_rmse_ratio_within_20pct_on_sustained_9g() -> None:
    """On the sustained 9-G scenario the CV F-matrix is the dominant
    source of error for both filters. Both end up with similar RMSE
    — UKF/EKF ratio inside [0.8, 1.25]. Looser than the velocity-step
    scenario (5.22) because sustained mismatch amplifies the small
    second-order differences between the two filter formulations.
    """
    e_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=80.0)
    u_cfg = ukf.UKFConfig(process_noise_accel_std_mps2=80.0)
    e_errs = _run_ekf(_truth_9g_turn, _N_FRAMES, e_cfg)
    u_errs = _run_ukf(_truth_9g_turn, _N_FRAMES, u_cfg)
    ratio = _rmse(u_errs) / _rmse(e_errs)
    assert 0.8 < ratio < 1.25


# ---------------------------------------------------------------------
# Process-noise tuning under sustained maneuver
# ---------------------------------------------------------------------


def test_higher_process_noise_reduces_rmse_under_sustained_9g() -> None:
    """Doubling sigma_a from 20 to 100 m/s^2 lets the filter accept
    the model mismatch faster -> RMSE decreases under sustained 9-G.
    """
    low_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=20.0)
    high_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=100.0)
    low_errs = _run_ekf(_truth_9g_turn, _N_FRAMES, low_cfg)
    high_errs = _run_ekf(_truth_9g_turn, _N_FRAMES, high_cfg)
    assert _rmse(high_errs) < _rmse(low_errs)


def test_very_low_process_noise_grows_rmse_under_sustained_9g() -> None:
    """Conversely — too-low sigma_a starves the filter of process
    flexibility and RMSE blows up. Provides a useful upper-bound
    sanity check the tuning is in fact informative.
    """
    tight_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=0.5)
    loose_cfg = ekf.EKFConfig(process_noise_accel_std_mps2=80.0)
    tight_errs = _run_ekf(_truth_9g_turn, _N_FRAMES, tight_cfg)
    loose_errs = _run_ekf(_truth_9g_turn, _N_FRAMES, loose_cfg)
    assert _rmse(tight_errs) > _rmse(loose_errs)


# ---------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------


def test_high_g_run_is_deterministic() -> None:
    """Two runs with identical inputs return identical error sequences."""
    config = ekf.EKFConfig(process_noise_accel_std_mps2=80.0)
    a = _run_ekf(_truth_9g_turn, _N_FRAMES, config)
    b = _run_ekf(_truth_9g_turn, _N_FRAMES, config)
    for ea, eb in zip(a, b, strict=True):
        assert ea == pytest.approx(eb, abs=0.0)
