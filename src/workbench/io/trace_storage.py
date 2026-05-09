"""Trace storage — per-run track histories on disk (Phase 3.4).

Phase 3.4 — minimum viable track-trace persistence. Stores each
track's per-frame ``(sim_t_s, mean[6])`` plus its final
``covariance[6, 6]`` snapshot in a NumPy ``.npz`` archive.

We picked ``.npz`` over HDF5 / Parquet for the MVP:

- Stdlib + numpy only — no extra dep at the IO layer.
- Compressed by default (savez_compressed); a 60 s simulation with
  a handful of tracks lands well under 1 MiB.
- Human-inspectable via ``np.load(...).files``.

Trace layout per file:

- ``track_ids``: ``int64[N]``  — one entry per frame sample.
- ``sim_t_s``: ``float64[N]``  — simulation time per sample.
- ``mean``: ``float64[N, 6]``  — state vectors.
- ``status``: ``int64[N]``     — encoded TrackStatus (TENTATIVE=0,
  CONFIRMED=1, COASTING=2, LOST=3).

Each row is a single (track_id, sim_t_s) sample; multiple tracks
across many frames share one flat table — trivially filterable by
caller. Final covariance per track is **not** persisted at MVP to
keep the file small (callers needing the full Kalman state can
re-run with verbose recording, MVP+alpha).
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from workbench.domain.tracker.track_state import TrackState, TrackStatus

_STATUS_TO_INT: dict[TrackStatus, int] = {
    TrackStatus.TENTATIVE: 0,
    TrackStatus.CONFIRMED: 1,
    TrackStatus.COASTING: 2,
    TrackStatus.LOST: 3,
}
_INT_TO_STATUS: dict[int, TrackStatus] = {v: k for k, v in _STATUS_TO_INT.items()}


def write_traces(path: Path | str, snapshots: Iterable[TrackState]) -> int:
    """Write a flat trace table to ``path`` as compressed npz.

    Args:
        path: Output file (``.npz`` extension is conventional).
        snapshots: Iterable of every TrackState sample to persist.
            Order is preserved.

    Returns:
        Number of rows written.
    """
    rows = list(snapshots)
    if not rows:
        np.savez_compressed(
            str(path),
            track_ids=np.zeros(0, dtype=np.int64),
            sim_t_s=np.zeros(0, dtype=np.float64),
            mean=np.zeros((0, 6), dtype=np.float64),
            status=np.zeros(0, dtype=np.int64),
        )
        return 0
    track_ids = np.array([t.track_id for t in rows], dtype=np.int64)
    sim_t_s = np.array([t.sim_t_s for t in rows], dtype=np.float64)
    mean = np.stack([t.mean for t in rows], axis=0).astype(np.float64, copy=False)
    status = np.array([_STATUS_TO_INT[t.status] for t in rows], dtype=np.int64)
    np.savez_compressed(
        str(path),
        track_ids=track_ids,
        sim_t_s=sim_t_s,
        mean=mean,
        status=status,
    )
    return len(rows)


def read_traces(
    path: Path | str,
) -> tuple[NDArray[np.int64], NDArray[np.float64], NDArray[np.float64], NDArray[np.int64]]:
    """Inverse of :func:`write_traces`.

    Returns:
        ``(track_ids, sim_t_s, mean, status)`` arrays. ``status``
        carries the integer encoding — use :func:`decode_status`
        to convert back to :class:`TrackStatus`.
    """
    archive = np.load(str(path))
    return (
        archive["track_ids"].astype(np.int64),
        archive["sim_t_s"].astype(np.float64),
        archive["mean"].astype(np.float64),
        archive["status"].astype(np.int64),
    )


def decode_status(status_int: int) -> TrackStatus:
    """Convert the persisted integer back to :class:`TrackStatus`.

    Raises:
        KeyError: If ``status_int`` isn't one of 0..3.
    """
    return _INT_TO_STATUS[int(status_int)]
