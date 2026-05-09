"""Unit tests for workbench.domain.scenario + pipeline (Phase 2.10)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.domain.geo import GeoOrigin
from workbench.domain.map_resource import (
    Map,
    MapBounds,
    SeaSurface,
    WorkbenchTerrain,
)
from workbench.domain.pipeline import PipelineConfig, step
from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.platform import RadarPlatform, TrackerKind
from workbench.domain.scenario import Scenario
from workbench.domain.target import make_default_aircraft_target
from workbench.domain.tracker.track_state import (
    STATE_DIM,
    Detection,
    TrackState,
    TrackStatus,
)
from workbench.domain.types import PositionENU
from workbench.physics.atmosphere import AtmosphereState

# ---------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------


def _map() -> Map:
    grid_east = np.array([0.0, 100.0], dtype=np.float64)
    grid_north = np.array([0.0, 100.0], dtype=np.float64)
    elev = np.zeros((2, 2), dtype=np.float64)
    land = np.ones((2, 2), dtype=np.bool_)
    terrain = WorkbenchTerrain(
        grid_east_m=grid_east,
        grid_north_m=grid_north,
        elevation_m=elev,
        land_mask=land,
        resolution_m=100.0,
    )
    return Map(
        map_id="test_map",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=126.9, alt_m=0.0),
        bounds=MapBounds(east_min_m=0.0, east_max_m=100.0, north_min_m=0.0, north_max_m=100.0),
        terrain=terrain,
        sea_surface=SeaSurface(),
    )


def _platform(platform_id: str = "radar_01") -> RadarPlatform:
    return RadarPlatform(
        platform_id=platform_id,
        placement=PlacedEntity(
            entity_id=platform_id,
            motion_kind=MotionKind.FIXED_GROUND,
            base_position=PositionENU(x=0.0, y=0.0, z=10.0),
        ),
        antenna_id="parabolic_1m",
        carrier_frequency_hz=9.4e9,
    )


def _scenario(**overrides: object) -> Scenario:
    base: dict[str, object] = {
        "scenario_id": "test_scenario",
        "map": _map(),
        "atmosphere": AtmosphereState(),
        "targets": (
            make_default_aircraft_target(
                entity_id="t1",
                target_id=1,
                east_m=0.0,
                north_m=5000.0,
                altitude_m=1000.0,
            ),
        ),
        "platforms": (_platform(),),
        "duration_s": 10.0,
    }
    base.update(overrides)
    return Scenario(**base)  # type: ignore[arg-type]


def test_scenario_construction_defaults() -> None:
    s = _scenario()
    assert s.frame_rate_hz == 20.0
    assert s.timing.mode == "sim_time"


def test_scenario_frame_dt_and_n_frames() -> None:
    s = _scenario(duration_s=5.0, frame_rate_hz=10.0)
    assert s.frame_dt_s == 0.1
    assert s.n_frames == 50


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"scenario_id": ""}, r"scenario_id"),
        ({"platforms": ()}, r"platform"),
        ({"duration_s": 0.0}, r"duration_s"),
        ({"frame_rate_hz": 0.0}, r"frame_rate_hz"),
    ],
)
def test_scenario_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _scenario(**override)


def test_scenario_empty_targets_allowed() -> None:
    # Calibration scenarios have no targets — must not raise.
    s = _scenario(targets=())
    assert s.targets == ()


# ---------------------------------------------------------------------
# Pipeline.step
# ---------------------------------------------------------------------


def test_pipeline_config_defaults() -> None:
    c = PipelineConfig()
    assert c.tracker_kind is TrackerKind.EKF
    assert c.max_misses_before_lost == 5


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"max_misses_before_lost": 0}, r"max_misses_before_lost"),
        ({"new_track_init_position_var": 0.0}, r"new_track_init_position_var"),
        ({"new_track_init_velocity_var": 0.0}, r"new_track_init_velocity_var"),
    ],
)
def test_pipeline_config_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        PipelineConfig(**override)


def test_step_spawns_tentative_tracks_for_new_detections() -> None:
    detections = [
        Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.05),
        Detection(range_m=2000.0, az_rad=0.5, el_rad=0.1, sim_t_s=0.05),
    ]
    new_tracks, next_id = step(
        tracks=[],
        detections=detections,
        next_track_id=0,
        dt_s=0.05,
        config=PipelineConfig(),
    )
    assert len(new_tracks) == 2
    assert next_id == 2
    assert all(t.status is TrackStatus.TENTATIVE for t in new_tracks)


def _make_track(track_id: int = 0, *, north: float = 1000.0) -> TrackState:
    mean = np.array([0.0, north, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)
    cov = np.eye(STATE_DIM, dtype=np.float64) * 100.0
    return TrackState(
        track_id=track_id,
        mean=mean,
        covariance=cov,
        sim_t_s=0.0,
        status=TrackStatus.CONFIRMED,
    )


def test_step_associates_detection_to_existing_track() -> None:
    track = _make_track(0, north=1000.0)
    # Detection close to the track's predicted measurement.
    det = Detection(range_m=1000.5, az_rad=0.001, el_rad=0.0, sim_t_s=0.05)
    new_tracks, _ = step(
        tracks=[track],
        detections=[det],
        next_track_id=10,
        dt_s=0.05,
        config=PipelineConfig(),
    )
    assert len(new_tracks) == 1
    assert new_tracks[0].track_id == 0
    assert new_tracks[0].consecutive_misses == 0
    assert new_tracks[0].status is TrackStatus.CONFIRMED


def test_step_drops_tracks_after_max_misses() -> None:
    track = _make_track(0)
    cfg = PipelineConfig(max_misses_before_lost=2)
    # Frame 1: no detections - track misses go from 0 -> 1, status COASTING.
    tracks, _ = step([track], [], 10, dt_s=0.05, config=cfg)
    assert len(tracks) == 1
    assert tracks[0].consecutive_misses == 1
    assert tracks[0].status is TrackStatus.COASTING

    # Frame 2: misses -> 2, hits threshold -> dropped (LOST).
    tracks, _ = step(tracks, [], 10, dt_s=0.05, config=cfg)
    assert tracks == []


def test_step_increments_next_track_id_only_for_new() -> None:
    track = _make_track(5)
    det = Detection(range_m=1000.0, az_rad=0.0, el_rad=0.0, sim_t_s=0.05)
    # Detection associates with the existing track -> no spawn.
    _, next_id = step([track], [det], 10, dt_s=0.05, config=PipelineConfig())
    assert next_id == 10  # unchanged


def test_step_validation() -> None:
    with pytest.raises(ValueError, match=r"dt_s"):
        step([], [], 0, dt_s=0.0, config=PipelineConfig())
    with pytest.raises(ValueError, match=r"next_track_id"):
        step([], [], -1, dt_s=0.05, config=PipelineConfig())


def test_step_ukf_path_executes() -> None:
    # Smoke test that selecting UKF runs both predict + update branches.
    cfg = PipelineConfig(tracker_kind=TrackerKind.UKF)
    track = _make_track(0)
    det = Detection(range_m=1000.5, az_rad=0.001, el_rad=0.0, sim_t_s=0.05)
    new_tracks, _ = step([track], [det], 10, dt_s=0.05, config=cfg)
    assert len(new_tracks) == 1
    # State updated toward the detection.
    assert math.isfinite(new_tracks[0].mean[1])
