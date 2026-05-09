"""RadarPipeline — per-frame tracker orchestrator (Phase 2.10).

Phase 2.10 MVP — the predict / associate / update slice of the radar
data flow, decoupled from the physics returns and from the
schedule. The Pipeline is a stateful holder of active tracks; each
frame it consumes a list of detections from the detection stage
(physics + CFAR, Phase 2.7 / 2.9) and emits the updated track set.

Design:

- Stateless functions in :mod:`workbench.domain.tracker.ekf` /
  :mod:`workbench.domain.tracker.ukf` /
  :mod:`workbench.domain.tracker.data_associator` do the math.
- This module sequences them: predict every track to the new frame
  time, associate against new detections, update on hits, escalate
  status / age out missing tracks.

Track lifecycle (MVP — minimal, expand at Phase 3):

- New unassociated detections spawn TENTATIVE tracks initialised at
  the detection's ENU position with zero velocity and a wide
  covariance.
- Associated tracks become CONFIRMED on first update.
- Unassigned tracks increment ``consecutive_misses`` and transition
  CONFIRMED -> COASTING immediately. After ``max_misses`` consecutive
  misses they become LOST and are removed from the active set.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from workbench.domain.platform import TrackerKind
from workbench.domain.tracker.data_associator import associate
from workbench.domain.tracker.ekf import EKFConfig
from workbench.domain.tracker.ekf import predict as ekf_predict
from workbench.domain.tracker.ekf import update as ekf_update
from workbench.domain.tracker.track_state import (
    STATE_DIM,
    Detection,
    TrackState,
    TrackStatus,
)
from workbench.domain.tracker.ukf import UKFConfig
from workbench.domain.tracker.ukf import predict as ukf_predict
from workbench.domain.tracker.ukf import update as ukf_update


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    """RadarPipeline tuning.

    Attributes:
        tracker_kind: EKF or UKF.
        ekf_config: EKF config (used when tracker_kind is EKF).
        ukf_config: UKF config (used when tracker_kind is UKF).
        max_misses_before_lost: Mark a track LOST after this many
            consecutive frames without an association. Default 5.
        new_track_init_velocity_var: Diagonal velocity-cov variance
            for newly seeded tracks (no prior velocity info). Default
            ``(100 m/s)^2`` — wide.
        new_track_init_position_var: Diagonal position-cov variance
            for newly seeded tracks. Default ``(50 m)^2``.

    Raises:
        ValueError: For non-positive thresholds / variances.
    """

    tracker_kind: TrackerKind = TrackerKind.EKF
    ekf_config: EKFConfig = field(default_factory=EKFConfig)
    ukf_config: UKFConfig = field(default_factory=UKFConfig)
    max_misses_before_lost: int = 5
    new_track_init_velocity_var: float = 1e4
    new_track_init_position_var: float = 2.5e3

    def __post_init__(self) -> None:
        if self.max_misses_before_lost < 1:
            msg = f"max_misses_before_lost must be >= 1, got {self.max_misses_before_lost}"
            raise ValueError(msg)
        if self.new_track_init_velocity_var <= 0.0:
            msg = "new_track_init_velocity_var must be > 0"
            raise ValueError(msg)
        if self.new_track_init_position_var <= 0.0:
            msg = "new_track_init_position_var must be > 0"
            raise ValueError(msg)


def _spawn_track(
    track_id: int,
    detection: Detection,
    config: PipelineConfig,
) -> TrackState:
    """Initialise a TENTATIVE track from an unassociated detection.

    Position from ``Detection.to_enu()``, zero initial velocity, wide
    diagonal covariance taken from the pipeline config.
    """
    pos = detection.to_enu()
    mean = np.array([pos[0], pos[1], pos[2], 0.0, 0.0, 0.0], dtype=np.float64)
    cov = np.zeros((STATE_DIM, STATE_DIM), dtype=np.float64)
    cov[0, 0] = config.new_track_init_position_var
    cov[1, 1] = config.new_track_init_position_var
    cov[2, 2] = config.new_track_init_position_var
    cov[3, 3] = config.new_track_init_velocity_var
    cov[4, 4] = config.new_track_init_velocity_var
    cov[5, 5] = config.new_track_init_velocity_var
    return TrackState(
        track_id=track_id,
        mean=mean,
        covariance=cov,
        sim_t_s=detection.sim_t_s,
        status=TrackStatus.TENTATIVE,
    )


def _measurement_noise_for_associate(config: PipelineConfig) -> tuple[float, float, float]:
    """Pick the (range, az, el) noise stds matching the active filter."""
    if config.tracker_kind is TrackerKind.UKF:
        return (
            config.ukf_config.range_noise_std_m,
            config.ukf_config.az_noise_std_rad,
            config.ukf_config.el_noise_std_rad,
        )
    return (
        config.ekf_config.range_noise_std_m,
        config.ekf_config.az_noise_std_rad,
        config.ekf_config.el_noise_std_rad,
    )


def step(
    tracks: list[TrackState],
    detections: list[Detection],
    next_track_id: int,
    dt_s: float,
    config: PipelineConfig,
) -> tuple[list[TrackState], int]:
    """One pipeline frame: predict + associate + update + lifecycle.

    Args:
        tracks: Active tracks at the start of the frame.
        detections: Detections produced by physics + CFAR for this frame.
        next_track_id: Identifier for the next spawned track. Returned
            unchanged if no new track spawned, otherwise incremented.
        dt_s: Frame duration [s]. Must be > 0.
        config: Pipeline tuning.

    Returns:
        ``(updated_tracks, next_track_id_after_spawn)``. LOST tracks
        are dropped from the returned list.

    Raises:
        ValueError: For ``dt_s <= 0`` or ``next_track_id < 0``.
    """
    if dt_s <= 0.0:
        msg = f"dt_s must be > 0, got {dt_s}"
        raise ValueError(msg)
    if next_track_id < 0:
        msg = f"next_track_id must be >= 0, got {next_track_id}"
        raise ValueError(msg)

    # 1. Predict every active track to this frame's time.
    if config.tracker_kind is TrackerKind.UKF:
        predicted = [ukf_predict(t, dt_s, config.ukf_config) for t in tracks]
    else:
        predicted = [ekf_predict(t, dt_s, config.ekf_config) for t in tracks]

    # 2. Associate.
    range_std, az_std, el_std = _measurement_noise_for_associate(config)
    assoc = associate(
        tracks=predicted,
        detections=detections,
        range_noise_std_m=range_std,
        az_noise_std_rad=az_std,
        el_noise_std_rad=el_std,
    )

    # 3. Update assigned tracks; coast / age unassigned ones.
    next_tracks: list[TrackState] = []
    for i, predicted_track in enumerate(predicted):
        if i in assoc.track_to_detection:
            j = assoc.track_to_detection[i]
            det = detections[j]
            if config.tracker_kind is TrackerKind.UKF:
                updated = ukf_update(predicted_track, det, config.ukf_config)
            else:
                updated = ekf_update(predicted_track, det, config.ekf_config)
            next_tracks.append(updated)
        else:
            misses = predicted_track.consecutive_misses + 1
            if misses >= config.max_misses_before_lost:
                # Drop — LOST tracks are not returned.
                continue
            new_status = (
                TrackStatus.COASTING
                if predicted_track.status is TrackStatus.CONFIRMED
                else predicted_track.status
            )
            next_tracks.append(
                TrackState(
                    track_id=predicted_track.track_id,
                    mean=predicted_track.mean,
                    covariance=predicted_track.covariance,
                    sim_t_s=predicted_track.sim_t_s,
                    status=new_status,
                    consecutive_misses=misses,
                )
            )

    # 4. Spawn a TENTATIVE track for each unassociated detection.
    for j in assoc.unassigned_detections:
        next_tracks.append(_spawn_track(next_track_id, detections[j], config))
        next_track_id += 1

    return next_tracks, next_track_id
