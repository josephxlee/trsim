"""Global Nearest Neighbor (GNN) data associator (plan/03 § 3.2.1k).

Phase 2.8 — assigns each :class:`Detection` to at most one
:class:`TrackState` per frame, minimising total Mahalanobis distance
under the constraint that no detection or track participates in more
than one assignment. Hungarian (Kuhn-Munkres) optimisation via
``scipy.optimize.linear_sum_assignment``.

Gating:

- Each (track, detection) cost is the squared Mahalanobis distance
  ``y^T S^-1 y`` where ``y = z - h(x)`` and ``S = H P H^T + R``.
- Pairs with cost > ``gating_threshold_chi2`` are excluded
  (assigned an infinite cost) — the threshold defaults to a 99.7%
  chi-square percentile for 3 measurement dimensions (~ 14.16).

Output:

- ``track_to_detection``: mapping ``track_index -> detection_index``
  for every assignment that survives gating.
- ``unassigned_tracks`` / ``unassigned_detections``: index sets that
  the caller (Pipeline) feeds into track-management policy
  (COASTING for unassigned tracks, new track init for unassigned
  detections).

References:

- Bar-Shalom, *Estimation with Applications to Tracking*, ch.7 (data
  association).
- Blackman & Popoli, *Design and Analysis of Modern Tracking Systems*,
  ch.7.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import linear_sum_assignment

from workbench.domain.tracker.ekf import (
    measurement_function,
    measurement_jacobian,
)
from workbench.domain.tracker.track_state import (
    MEASUREMENT_DIM,
    Detection,
    TrackState,
)

# 99.7% percentile of chi-square with 3 DOF (range, az, el).
DEFAULT_GATING_THRESHOLD_CHI2: Final[float] = 14.16


@dataclass(frozen=True, slots=True)
class AssociationResult:
    """Output of :func:`associate`.

    Attributes:
        track_to_detection: ``track_index -> detection_index`` for
            assignments that passed gating.
        unassigned_tracks: Track indices with no detection.
        unassigned_detections: Detection indices not used.
    """

    track_to_detection: dict[int, int]
    unassigned_tracks: tuple[int, ...]
    unassigned_detections: tuple[int, ...]


def _measurement_noise_matrix(
    range_std_m: float, az_std_rad: float, el_std_rad: float
) -> NDArray[np.float64]:
    return np.diag(
        np.array(
            [range_std_m**2, az_std_rad**2, el_std_rad**2],
            dtype=np.float64,
        )
    )


def mahalanobis_squared(
    track: TrackState,
    detection: Detection,
    *,
    range_noise_std_m: float,
    az_noise_std_rad: float,
    el_noise_std_rad: float,
) -> float:
    """Squared Mahalanobis distance between a track prediction and a measurement.

    ``y^T (H P H^T + R)^-1 y`` with ``y = z - h(x)``. Azimuth difference
    is wrapped to ``(-pi, +pi]``.
    """
    h_mat = measurement_jacobian(track.mean)
    r_mat = _measurement_noise_matrix(range_noise_std_m, az_noise_std_rad, el_noise_std_rad)
    s_mat = h_mat @ track.covariance @ h_mat.T + r_mat

    z_pred = measurement_function(track.mean)
    z_meas = np.array([detection.range_m, detection.az_rad, detection.el_rad], dtype=np.float64)
    innovation = z_meas - z_pred
    innovation[1] = math.atan2(math.sin(innovation[1]), math.cos(innovation[1]))

    s_inv = np.linalg.inv(s_mat)
    return float(innovation @ s_inv @ innovation)


def associate(
    tracks: list[TrackState],
    detections: list[Detection],
    *,
    range_noise_std_m: float,
    az_noise_std_rad: float,
    el_noise_std_rad: float,
    gating_threshold_chi2: float = DEFAULT_GATING_THRESHOLD_CHI2,
) -> AssociationResult:
    """Assign detections to tracks using Hungarian + chi-square gating.

    Args:
        tracks: Active tracks (typically the post-prediction set).
        detections: Frame detections.
        range_noise_std_m / az_noise_std_rad / el_noise_std_rad:
            Measurement noise standard deviations matching the EKF/UKF
            config used in the same pipeline.
        gating_threshold_chi2: Pairs with squared Mahalanobis distance
            above this are forbidden. Default 14.16 (99.7% chi-square,
            3 DOF).

    Returns:
        :class:`AssociationResult`.

    Raises:
        ValueError: If any noise std is non-positive or the gating
            threshold is non-positive.
    """
    if range_noise_std_m <= 0.0:
        msg = "range_noise_std_m must be > 0"
        raise ValueError(msg)
    if az_noise_std_rad <= 0.0:
        msg = "az_noise_std_rad must be > 0"
        raise ValueError(msg)
    if el_noise_std_rad <= 0.0:
        msg = "el_noise_std_rad must be > 0"
        raise ValueError(msg)
    if gating_threshold_chi2 <= 0.0:
        msg = "gating_threshold_chi2 must be > 0"
        raise ValueError(msg)
    if not tracks or not detections:
        return AssociationResult(
            track_to_detection={},
            unassigned_tracks=tuple(range(len(tracks))),
            unassigned_detections=tuple(range(len(detections))),
        )

    n_tracks = len(tracks)
    n_detections = len(detections)
    cost = np.full((n_tracks, n_detections), np.inf, dtype=np.float64)
    for i, t in enumerate(tracks):
        for j, d in enumerate(detections):
            m2 = mahalanobis_squared(
                t,
                d,
                range_noise_std_m=range_noise_std_m,
                az_noise_std_rad=az_noise_std_rad,
                el_noise_std_rad=el_noise_std_rad,
            )
            if m2 <= gating_threshold_chi2:
                cost[i, j] = m2

    # linear_sum_assignment requires a finite cost matrix. Replace
    # infinity with a very large number so the algorithm runs, then
    # filter out assignments that landed on those impossible cells.
    big = 1e18
    cost_finite = np.where(np.isinf(cost), big, cost)
    row_ind, col_ind = linear_sum_assignment(cost_finite)

    track_to_detection: dict[int, int] = {}
    used_tracks: set[int] = set()
    used_detections: set[int] = set()
    for r, c in zip(row_ind, col_ind, strict=True):
        if cost_finite[r, c] >= big:
            continue
        track_to_detection[int(r)] = int(c)
        used_tracks.add(int(r))
        used_detections.add(int(c))

    unassigned_tracks = tuple(i for i in range(n_tracks) if i not in used_tracks)
    unassigned_detections = tuple(j for j in range(n_detections) if j not in used_detections)
    return AssociationResult(
        track_to_detection=track_to_detection,
        unassigned_tracks=unassigned_tracks,
        unassigned_detections=unassigned_detections,
    )


_ = MEASUREMENT_DIM  # re-export-friendly: imported for downstream tests
