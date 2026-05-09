"""Unit tests for workbench.domain.tracker.* (Phase 2.8)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.domain.tracker.data_associator import (
    DEFAULT_GATING_THRESHOLD_CHI2,
    associate,
    mahalanobis_squared,
)
from workbench.domain.tracker.ekf import (
    EKFConfig,
    measurement_function,
    measurement_jacobian,
    process_noise_matrix,
    state_transition_matrix,
)
from workbench.domain.tracker.ekf import predict as ekf_predict
from workbench.domain.tracker.ekf import update as ekf_update
from workbench.domain.tracker.track_state import (
    MEASUREMENT_DIM,
    STATE_DIM,
    Detection,
    TrackState,
    TrackStatus,
)
from workbench.domain.tracker.ukf import UKFConfig
from workbench.domain.tracker.ukf import predict as ukf_predict
from workbench.domain.tracker.ukf import update as ukf_update

# ---------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------


def test_detection_construction() -> None:
    d = Detection(range_m=1000.0, az_rad=0.1, el_rad=0.05, sim_t_s=1.0)
    assert d.range_m == 1000.0
    assert math.isnan(d.doppler_mps)
    assert math.isnan(d.snr_db)


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"range_m": 0.0}, r"range_m"),
        ({"range_m": -1.0}, r"range_m"),
        ({"sim_t_s": -0.1}, r"sim_t_s"),
    ],
)
def test_detection_validation(override: dict, match: str) -> None:
    base = {"range_m": 1.0, "az_rad": 0.0, "el_rad": 0.0, "sim_t_s": 0.0}
    base.update(override)
    with pytest.raises(ValueError, match=match):
        Detection(**base)


def test_detection_to_enu_at_boresight() -> None:
    # az = 0 (forward = North), el = 0 -> (0, R, 0)
    d = Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)
    assert d.to_enu() == pytest.approx((0.0, 1000.0, 0.0), abs=1e-9)


def test_detection_to_enu_pure_east() -> None:
    d = Detection(range_m=1000.0, az_rad=math.pi / 2, el_rad=0.0, sim_t_s=0.0)
    east, north, up = d.to_enu()
    assert east == pytest.approx(1000.0, abs=1e-9)
    assert north == pytest.approx(0.0, abs=1e-9)
    assert up == pytest.approx(0.0, abs=1e-9)


def test_detection_to_enu_pure_up() -> None:
    d = Detection(range_m=1000.0, az_rad=0.0, el_rad=math.pi / 2, sim_t_s=0.0)
    _, _, up = d.to_enu()
    assert up == pytest.approx(1000.0, abs=1e-9)


# ---------------------------------------------------------------------
# TrackState
# ---------------------------------------------------------------------


def _track(track_id: int = 0, *, sim_t_s: float = 0.0) -> TrackState:
    mean = np.array([100.0, 200.0, 50.0, 10.0, -5.0, 0.0], dtype=np.float64)
    cov = np.eye(STATE_DIM, dtype=np.float64)
    return TrackState(
        track_id=track_id,
        mean=mean,
        covariance=cov,
        sim_t_s=sim_t_s,
        status=TrackStatus.TENTATIVE,
    )


def test_track_state_construction_defaults() -> None:
    t = _track()
    assert t.consecutive_misses == 0
    assert t.status is TrackStatus.TENTATIVE


def test_track_state_position_velocity_tuples() -> None:
    t = _track()
    assert t.position_enu_m == (100.0, 200.0, 50.0)
    assert t.velocity_enu_mps == (10.0, -5.0, 0.0)


def test_track_state_validates_mean_shape() -> None:
    with pytest.raises(ValueError, match=r"mean"):
        TrackState(
            track_id=0,
            mean=np.zeros(5, dtype=np.float64),
            covariance=np.eye(STATE_DIM, dtype=np.float64),
            sim_t_s=0.0,
        )


def test_track_state_validates_cov_shape() -> None:
    with pytest.raises(ValueError, match=r"covariance"):
        TrackState(
            track_id=0,
            mean=np.zeros(STATE_DIM, dtype=np.float64),
            covariance=np.zeros((4, 4), dtype=np.float64),
            sim_t_s=0.0,
        )


def test_track_state_validates_track_id_negative() -> None:
    with pytest.raises(ValueError, match=r"track_id"):
        TrackState(
            track_id=-1,
            mean=np.zeros(STATE_DIM, dtype=np.float64),
            covariance=np.eye(STATE_DIM, dtype=np.float64),
            sim_t_s=0.0,
        )


# ---------------------------------------------------------------------
# EKF — F / Q / h / H matrices
# ---------------------------------------------------------------------


def test_state_transition_matrix_shape_and_offdiag() -> None:
    f = state_transition_matrix(0.5)
    assert f.shape == (STATE_DIM, STATE_DIM)
    assert f[0, 3] == 0.5
    assert f[1, 4] == 0.5
    assert f[2, 5] == 0.5
    # Diagonal stays 1
    for i in range(STATE_DIM):
        assert f[i, i] == 1.0


def test_process_noise_matrix_zero_dt_is_zero() -> None:
    q = process_noise_matrix(0.0, accel_std_mps2=1.0)
    np.testing.assert_allclose(q, np.zeros((STATE_DIM, STATE_DIM)), atol=1e-15)


def test_process_noise_matrix_known_diag_at_dt_1() -> None:
    q = process_noise_matrix(1.0, accel_std_mps2=2.0)
    # sigma2 = 4. Position-position diag = 1/4 * 4 = 1.
    # Velocity-velocity diag = 1 * 4 = 4.
    assert q[0, 0] == pytest.approx(1.0, abs=1e-12)
    assert q[3, 3] == pytest.approx(4.0, abs=1e-12)


def test_measurement_function_known_value() -> None:
    state = np.array([0.0, 1000.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    z = measurement_function(state)
    assert z[0] == pytest.approx(1000.0, abs=1e-12)
    assert z[1] == pytest.approx(0.0, abs=1e-12)
    assert z[2] == pytest.approx(0.0, abs=1e-12)


def test_measurement_function_pure_east() -> None:
    state = np.array([1000.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    z = measurement_function(state)
    assert z[0] == pytest.approx(1000.0, abs=1e-12)
    assert z[1] == pytest.approx(math.pi / 2, abs=1e-12)


def test_measurement_jacobian_shape() -> None:
    state = np.array([100.0, 200.0, 50.0, 0.0, 0.0, 0.0], dtype=np.float64)
    h = measurement_jacobian(state)
    assert h.shape == (MEASUREMENT_DIM, STATE_DIM)
    # Velocity columns are zero
    np.testing.assert_allclose(h[:, 3:], np.zeros((3, 3)), atol=1e-15)


def test_measurement_jacobian_rejects_origin() -> None:
    state = np.zeros(STATE_DIM, dtype=np.float64)
    with pytest.raises(ValueError, match=r"range"):
        measurement_jacobian(state)


# ---------------------------------------------------------------------
# EKF predict / update
# ---------------------------------------------------------------------


def test_ekf_config_validation() -> None:
    with pytest.raises(ValueError):
        EKFConfig(process_noise_accel_std_mps2=0.0)


def test_ekf_predict_advances_position_by_velocity_dt() -> None:
    state = TrackState(
        track_id=0,
        mean=np.array([0.0, 0.0, 0.0, 10.0, 20.0, 0.0], dtype=np.float64),
        covariance=np.eye(STATE_DIM, dtype=np.float64),
        sim_t_s=0.0,
    )
    cfg = EKFConfig()
    pred = ekf_predict(state, dt_s=2.0, config=cfg)
    assert pred.mean[0] == pytest.approx(20.0, abs=1e-12)
    assert pred.mean[1] == pytest.approx(40.0, abs=1e-12)
    assert pred.sim_t_s == 2.0


def test_ekf_predict_inflates_covariance() -> None:
    state = _track()
    pred = ekf_predict(state, dt_s=1.0, config=EKFConfig())
    # Cov diagonal should grow.
    assert pred.covariance[0, 0] > state.covariance[0, 0]


def test_ekf_update_pulls_state_toward_measurement() -> None:
    # State at (0, 0, 0), measurement at (0, 1000, 0). Update should
    # pull position north.
    state = TrackState(
        track_id=0,
        mean=np.array([0.0, 100.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64),
        covariance=np.eye(STATE_DIM, dtype=np.float64) * 1000.0,
        sim_t_s=0.0,
    )
    detection = Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)
    cfg = EKFConfig(range_noise_std_m=1.0)
    posterior = ekf_update(state, detection, cfg)
    # Posterior north should be much closer to 1000 than 100.
    assert posterior.mean[1] > 500.0


def test_ekf_update_promotes_tentative_to_confirmed() -> None:
    state = _track()
    detection = Detection(range_m=200.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.5)
    cfg = EKFConfig()
    posterior = ekf_update(state, detection, cfg)
    assert posterior.status is TrackStatus.CONFIRMED
    assert posterior.consecutive_misses == 0


def test_ekf_update_resets_consecutive_misses() -> None:
    mean = np.array([0.0, 100.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    state = TrackState(
        track_id=0,
        mean=mean,
        covariance=np.eye(STATE_DIM, dtype=np.float64),
        sim_t_s=0.0,
        status=TrackStatus.COASTING,
        consecutive_misses=3,
    )
    detection = Detection(range_m=100.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.5)
    posterior = ekf_update(state, detection, EKFConfig())
    assert posterior.consecutive_misses == 0


# ---------------------------------------------------------------------
# UKF
# ---------------------------------------------------------------------


def test_ukf_config_alpha_validation() -> None:
    with pytest.raises(ValueError, match=r"alpha"):
        UKFConfig(alpha=0.0)
    with pytest.raises(ValueError, match=r"alpha"):
        UKFConfig(alpha=1.5)


def test_ukf_predict_matches_ekf_for_linear_dynamics() -> None:
    # CV dynamics is linear -> UKF.predict reduces to F x exactly
    # (we even reuse the F/Q closed form internally).
    state = _track()
    cfg_ekf = EKFConfig(process_noise_accel_std_mps2=2.0)
    cfg_ukf = UKFConfig(process_noise_accel_std_mps2=2.0)
    p_ekf = ekf_predict(state, dt_s=0.5, config=cfg_ekf)
    p_ukf = ukf_predict(state, dt_s=0.5, config=cfg_ukf)
    np.testing.assert_allclose(p_ekf.mean, p_ukf.mean, atol=1e-12)
    np.testing.assert_allclose(p_ekf.covariance, p_ukf.covariance, atol=1e-12)


def test_ukf_update_pulls_state_toward_measurement() -> None:
    # Same scenario as EKF update test — UKF should also drag the
    # state toward the measurement, possibly slightly differently
    # owing to nonlinear h.
    state = TrackState(
        track_id=0,
        mean=np.array([0.0, 100.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64),
        covariance=np.eye(STATE_DIM, dtype=np.float64) * 1000.0,
        sim_t_s=0.0,
    )
    detection = Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)
    cfg = UKFConfig(range_noise_std_m=1.0)
    posterior = ukf_update(state, detection, cfg)
    assert posterior.mean[1] > 500.0


def test_ukf_update_promotes_tentative_to_confirmed() -> None:
    state = _track()
    detection = Detection(range_m=200.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.5)
    posterior = ukf_update(state, detection, UKFConfig())
    assert posterior.status is TrackStatus.CONFIRMED


# ---------------------------------------------------------------------
# Data associator
# ---------------------------------------------------------------------


def test_default_gating_threshold() -> None:
    # Sanity-lock the constant — 99.7% chi-square 3 DOF.
    assert DEFAULT_GATING_THRESHOLD_CHI2 == pytest.approx(14.16, abs=1e-3)


def test_associate_empty_detections_returns_all_tracks_unassigned() -> None:
    res = associate(
        tracks=[_track(0), _track(1)],
        detections=[],
        range_noise_std_m=1.0,
        az_noise_std_rad=0.01,
        el_noise_std_rad=0.01,
    )
    assert res.track_to_detection == {}
    assert set(res.unassigned_tracks) == {0, 1}
    assert res.unassigned_detections == ()


def test_associate_empty_tracks_returns_all_detections_unassigned() -> None:
    detections = [Detection(range_m=10.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)]
    res = associate(
        tracks=[],
        detections=detections,
        range_noise_std_m=1.0,
        az_noise_std_rad=0.01,
        el_noise_std_rad=0.01,
    )
    assert res.unassigned_detections == (0,)


def _track_at(track_id: int, e: float, n: float, u: float) -> TrackState:
    mean = np.array([e, n, u, 0.0, 0.0, 0.0], dtype=np.float64)
    cov = np.eye(STATE_DIM, dtype=np.float64) * 100.0
    return TrackState(track_id=track_id, mean=mean, covariance=cov, sim_t_s=0.0)


def test_associate_one_to_one() -> None:
    # Two tracks, one near (0, 1000) and one near (0, -1000); two
    # detections matching each. Hungarian should pair them correctly.
    tracks = [_track_at(0, 0.0, 1000.0, 0.0), _track_at(1, 0.0, -1000.0, 0.0)]
    detections = [
        Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0),
        Detection(range_m=1000.0, az_rad=math.pi, el_rad=0.0, sim_t_s=0.0),
    ]
    res = associate(
        tracks=tracks,
        detections=detections,
        range_noise_std_m=10.0,
        az_noise_std_rad=math.radians(1.0),
        el_noise_std_rad=math.radians(1.0),
    )
    assert res.track_to_detection == {0: 0, 1: 1}
    assert res.unassigned_tracks == ()
    assert res.unassigned_detections == ()


def test_associate_gating_filters_far_pairs() -> None:
    # Track at (0, 1000), detection at (0, 100000) — way too far.
    tracks = [_track_at(0, 0.0, 1000.0, 0.0)]
    detections = [Detection(range_m=100000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)]
    res = associate(
        tracks=tracks,
        detections=detections,
        range_noise_std_m=10.0,
        az_noise_std_rad=math.radians(1.0),
        el_noise_std_rad=math.radians(1.0),
        gating_threshold_chi2=14.16,
    )
    assert res.track_to_detection == {}
    assert res.unassigned_tracks == (0,)
    assert res.unassigned_detections == (0,)


def test_mahalanobis_zero_at_perfect_match() -> None:
    # Track with covariance large; detection exactly at the predicted
    # measurement -> Mahalanobis = 0.
    track = _track_at(0, 0.0, 1000.0, 0.0)
    detection = Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)
    m2 = mahalanobis_squared(
        track,
        detection,
        range_noise_std_m=1.0,
        az_noise_std_rad=0.01,
        el_noise_std_rad=0.01,
    )
    assert m2 == pytest.approx(0.0, abs=1e-9)


def test_associate_validation() -> None:
    with pytest.raises(ValueError, match=r"range_noise_std_m"):
        associate(
            tracks=[_track()],
            detections=[Detection(range_m=100.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.0)],
            range_noise_std_m=0.0,
            az_noise_std_rad=0.01,
            el_noise_std_rad=0.01,
        )
