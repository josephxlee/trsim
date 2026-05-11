"""Pipeline probe-hook tests (Phase 6.4b)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pytest

from workbench.domain.pipeline import PipelineConfig, ProbeCallback, step
from workbench.domain.tracker.track_state import Detection, TrackState


def _track(track_id: int = 0) -> TrackState:
    cov = np.diag(np.array([25.0, 25.0, 25.0, 4.0, 4.0, 4.0], dtype=np.float64))
    mean = np.array([1000.0, 2000.0, 500.0, 30.0, 50.0, 5.0], dtype=np.float64)
    return TrackState(track_id=track_id, mean=mean, covariance=cov, sim_t_s=0.0)


def _detection_near(track: TrackState, sim_t_s: float) -> Detection:
    e, n, u = float(track.mean[0]), float(track.mean[1]), float(track.mean[2])
    return Detection(
        range_m=math.sqrt(e * e + n * n + u * u),
        az_rad=math.atan2(e, n),
        el_rad=math.atan2(u, math.hypot(e, n)),
        sim_t_s=sim_t_s,
    )


# ---------------------------------------------------------------------
# Backward compatibility (no probes argument)
# ---------------------------------------------------------------------


def test_step_works_without_probes_argument() -> None:
    """The legacy step() call (no probes kw) keeps working."""
    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    result, next_id = step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
    )
    assert len(result) == 1
    assert next_id == 1


# ---------------------------------------------------------------------
# Probe firing
# ---------------------------------------------------------------------


def test_predict_probe_receives_predicted_tracks_and_dt() -> None:
    captured: dict[str, Any] = {}

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        captured["stage"] = stage
        captured["payload"] = dict(payload)

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"predict": cb},
    )
    assert captured["stage"] == "predict"
    payload = captured["payload"]
    assert len(payload["predicted_tracks"]) == 1
    assert payload["dt_s"] == pytest.approx(0.1, abs=1e-12)


def test_associate_probe_receives_predicted_detections_and_result() -> None:
    captured: dict[str, Any] = {}

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        captured["stage"] = stage
        captured["payload"] = dict(payload)

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"associate": cb},
    )
    assert captured["stage"] == "associate"
    payload = captured["payload"]
    assert len(payload["predicted_tracks"]) == 1
    assert payload["detections"] == [det]
    assert 0 in payload["result"].track_to_detection


def test_update_probe_receives_updated_tracks_and_assoc_map() -> None:
    captured: dict[str, Any] = {}

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        captured["stage"] = stage
        captured["payload"] = dict(payload)

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"update": cb},
    )
    assert captured["stage"] == "update"
    payload = captured["payload"]
    assert len(payload["updated_tracks"]) == 1
    assert payload["associations"] == {0: 0}


def test_spawn_probe_fires_when_unassociated_detection_exists() -> None:
    captured: dict[str, Any] = {}

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        captured["stage"] = stage
        captured["payload"] = dict(payload)

    # No tracks -> the detection is unassociated -> spawns a new track.
    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"spawn": cb},
    )
    assert captured["stage"] == "spawn"
    payload = captured["payload"]
    assert len(payload["spawned_tracks"]) == 1
    assert payload["spawn_detection_indices"] == [0]


def test_spawn_probe_fires_with_empty_payload_when_nothing_spawned() -> None:
    """The probe still fires every frame even if no spawn happened —
    the dataset builder can count idle frames.
    """
    seen: list[Mapping[str, Any]] = []

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        seen.append(dict(payload))

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"spawn": cb},
    )
    assert len(seen) == 1
    assert seen[0]["spawned_tracks"] == []
    assert seen[0]["spawn_detection_indices"] == []


# ---------------------------------------------------------------------
# Multiple stages + ordering
# ---------------------------------------------------------------------


def test_all_four_stage_probes_fire_in_order() -> None:
    order: list[str] = []

    def make_cb(_name: str) -> ProbeCallback:
        def cb(stage: str, _payload: Mapping[str, Any]) -> None:
            order.append(stage)

        return cb

    track = _track(0)
    det_assoc = _detection_near(track, sim_t_s=0.1)
    # Add a second detection far away to also trigger spawn.
    det_far = Detection(range_m=5000.0, az_rad=1.0, el_rad=0.1, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det_assoc, det_far],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={
            "predict": make_cb("p"),
            "associate": make_cb("a"),
            "update": make_cb("u"),
            "spawn": make_cb("s"),
        },
    )
    assert order == ["predict", "associate", "update", "spawn"]


# ---------------------------------------------------------------------
# Exception propagation
# ---------------------------------------------------------------------


def test_probe_exception_propagates_to_caller() -> None:
    """A buggy probe must surface immediately — no silent swallowing."""

    def bad(_stage: str, _payload: Mapping[str, Any]) -> None:
        msg = "probe failed"
        raise RuntimeError(msg)

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    with pytest.raises(RuntimeError, match=r"probe failed"):
        step(
            tracks=[track],
            detections=[det],
            next_track_id=1,
            dt_s=0.1,
            config=PipelineConfig(),
            probes={"predict": bad},
        )


# ---------------------------------------------------------------------
# Unknown stage names are ignored (forward compatibility)
# ---------------------------------------------------------------------


def test_unknown_stage_name_is_silently_ignored() -> None:
    """Future stage names ("classifier", "preproc", etc.) shipped by
    DLC plugins should not cause an error when the host pipeline does
    not recognise them.
    """
    calls: list[str] = []

    def cb(stage: str, _payload: Mapping[str, Any]) -> None:
        calls.append(stage)

    track = _track(0)
    det = _detection_near(track, sim_t_s=0.1)
    step(
        tracks=[track],
        detections=[det],
        next_track_id=1,
        dt_s=0.1,
        config=PipelineConfig(),
        probes={"classifier": cb},  # unknown to this Pipeline
    )
    assert calls == []
