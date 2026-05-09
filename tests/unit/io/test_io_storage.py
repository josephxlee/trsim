"""Unit tests for workbench.io.run_storage + trace_storage (Phase 3.4)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import numpy as np
import pytest

from workbench.domain.tracker.track_state import (
    STATE_DIM,
    TrackState,
    TrackStatus,
)
from workbench.domain.types import RunTerminationReason
from workbench.io.run_storage import (
    ResourceRefs,
    RunManifest,
    load_manifest,
    save_manifest,
    utc_now_iso,
)
from workbench.io.trace_storage import decode_status, read_traces, write_traces

# ---------------------------------------------------------------------
# RunManifest
# ---------------------------------------------------------------------


def _refs() -> ResourceRefs:
    return ResourceRefs(
        map_hash="sha256:aa",
        radar_hash="sha256:bb",
        target_hashes=("sha256:cc",),
    )


def test_run_manifest_construction() -> None:
    m = RunManifest(
        run_id="run_001",
        scenario_id="A_Base",
        resource_refs=_refs(),
        termination_reason=RunTerminationReason.COMPLETED,
        sim_t_end_s=60.0,
    )
    assert m.run_id == "run_001"
    assert m.metadata == {}


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"run_id": ""}, r"run_id"),
        ({"scenario_id": ""}, r"scenario_id"),
        ({"sim_t_start_s": -1.0}, r"sim_t_start_s"),
        ({"sim_t_end_s": -1.0, "sim_t_start_s": 0.0}, r"sim_t_end_s"),
        ({"n_lineage_commands": -5}, r"n_lineage_commands"),
    ],
)
def test_run_manifest_validation(override: dict, match: str) -> None:
    base = {
        "run_id": "x",
        "scenario_id": "y",
        "resource_refs": _refs(),
        "termination_reason": RunTerminationReason.COMPLETED,
    }
    base.update(override)
    with pytest.raises(ValueError, match=match):
        RunManifest(**base)


def test_save_and_load_manifest_round_trip() -> None:
    m = RunManifest(
        run_id="run_001",
        scenario_id="A_Base",
        resource_refs=_refs(),
        termination_reason=RunTerminationReason.USER_STOPPED,
        sim_t_start_s=0.0,
        sim_t_end_s=12.5,
        wall_t_start_iso="2026-05-09T10:00:00Z",
        wall_t_end_iso="2026-05-09T10:00:13Z",
        n_lineage_commands=42,
        metadata={"note": "smoke"},
    )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "manifest.json"
        save_manifest(m, out)
        loaded = load_manifest(out)
    assert loaded == m


def test_save_manifest_writes_valid_json() -> None:
    m = RunManifest(
        run_id="r",
        scenario_id="s",
        resource_refs=_refs(),
        termination_reason=RunTerminationReason.COMPLETED,
    )
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "manifest.json"
        save_manifest(m, out)
        data = json.loads(out.read_text(encoding="utf-8"))
    assert data["run_id"] == "r"
    assert data["resource_refs"]["map"] == "sha256:aa"
    assert data["termination_reason"] == "completed"
    assert data["resource_refs"]["targets"] == ["sha256:cc"]


def test_utc_now_iso_format() -> None:
    s = utc_now_iso()
    # 2026-05-09T22:30:00Z — 20 chars total (4-2-2 T 2-2-2 Z).
    assert len(s) == 20
    assert s.endswith("Z")
    assert "T" in s


# ---------------------------------------------------------------------
# Trace storage
# ---------------------------------------------------------------------


def _track(
    track_id: int, sim_t_s: float, status: TrackStatus = TrackStatus.CONFIRMED
) -> TrackState:
    mean = np.full(STATE_DIM, float(track_id), dtype=np.float64)
    cov = np.eye(STATE_DIM, dtype=np.float64)
    return TrackState(
        track_id=track_id,
        mean=mean,
        covariance=cov,
        sim_t_s=sim_t_s,
        status=status,
    )


def test_write_traces_empty_creates_zero_row_archive() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "traces.npz"
        n = write_traces(out, [])
        assert n == 0
        ids, ts, mean, status = read_traces(out)
        assert ids.shape == (0,)
        assert ts.shape == (0,)
        assert mean.shape == (0, STATE_DIM)
        assert status.shape == (0,)


def test_write_then_read_traces_round_trip() -> None:
    snapshots = [
        _track(0, 0.0, TrackStatus.TENTATIVE),
        _track(0, 0.05, TrackStatus.CONFIRMED),
        _track(1, 0.05, TrackStatus.CONFIRMED),
        _track(0, 0.10, TrackStatus.COASTING),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "traces.npz"
        n = write_traces(out, snapshots)
        assert n == 4
        ids, ts, mean, status = read_traces(out)
    np.testing.assert_array_equal(ids, [0, 0, 1, 0])
    np.testing.assert_allclose(ts, [0.0, 0.05, 0.05, 0.10])
    # mean encodes track_id (helper sets each component to track_id)
    np.testing.assert_allclose(mean[:, 0], [0, 0, 1, 0])
    np.testing.assert_array_equal(status, [0, 1, 1, 2])


def test_decode_status_round_trip() -> None:
    for st in TrackStatus:
        # Encode then decode via the integer mapping.
        snap = _track(0, 0.0, status=st)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "x.npz"
            write_traces(out, [snap])
            _, _, _, status_int = read_traces(out)
        assert decode_status(int(status_int[0])) is st


def test_decode_status_unknown_raises() -> None:
    with pytest.raises(KeyError):
        decode_status(99)
