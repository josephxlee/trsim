"""GNN data association regression (Phase 5.18).

Verifies the Hungarian + chi-square gated associator in
:mod:`workbench.domain.tracker.data_associator` on scenarios that the
single-pair / empty-input unit tests in
:mod:`tests.unit.domain.test_tracker` do not cover:

- a close detection inside the gate is assigned;
- a far detection outside the gate is dropped to ``unassigned_detections``;
- a two-track / two-detection ambiguous frame uses the Hungarian
  global optimum (no track or detection appears in two assignments);
- the azimuth wrap inside Mahalanobis still associates a detection
  whose az is +pi-eps with a track at -pi+eps;
- input validation rejects non-positive noise std and gating
  threshold.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.domain.tracker.data_associator import (
    DEFAULT_GATING_THRESHOLD_CHI2,
    associate,
    mahalanobis_squared,
)
from workbench.domain.tracker.track_state import Detection, TrackState

_NOISE = {
    "range_noise_std_m": 5.0,
    "az_noise_std_rad": math.radians(0.5),
    "el_noise_std_rad": math.radians(0.5),
}


def _track_at(track_id: int, e: float, n: float, u: float) -> TrackState:
    cov = np.diag(np.array([25.0, 25.0, 25.0, 4.0, 4.0, 4.0], dtype=np.float64))
    return TrackState(
        track_id=track_id,
        mean=np.array([e, n, u, 0.0, 0.0, 0.0], dtype=np.float64),
        covariance=cov,
        sim_t_s=0.0,
    )


def _detection_for(e: float, n: float, u: float, sim_t_s: float = 0.0) -> Detection:
    range_m = math.sqrt(e * e + n * n + u * u)
    return Detection(
        range_m=range_m,
        az_rad=math.atan2(e, n),
        el_rad=math.atan2(u, math.hypot(e, n)),
        sim_t_s=sim_t_s,
    )


# ---------------------------------------------------------------------
# Close pair -> assigned, far pair -> gated out
# ---------------------------------------------------------------------


def test_close_track_detection_pair_assigned() -> None:
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    detection = _detection_for(1000.5, 2000.5, 500.5)
    result = associate([track], [detection], **_NOISE)
    assert result.track_to_detection == {0: 0}
    assert result.unassigned_tracks == ()
    assert result.unassigned_detections == ()


def test_far_detection_outside_gate_is_dropped() -> None:
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    # Detection 5 km away in the wrong direction -> Mahalanobis huge.
    detection = _detection_for(6000.0, -1000.0, 500.0)
    result = associate([track], [detection], **_NOISE)
    assert result.track_to_detection == {}
    assert result.unassigned_tracks == (0,)
    assert result.unassigned_detections == (0,)


# ---------------------------------------------------------------------
# Hungarian global optimum
# ---------------------------------------------------------------------


def test_two_track_two_detection_no_double_assignment() -> None:
    """Each track and each detection appears at most once in the
    assignment dict — invariant required by every Hungarian-based
    associator regardless of cost layout.
    """
    track_a = _track_at(0, 1000.0, 2000.0, 500.0)
    track_b = _track_at(1, 1500.0, 2500.0, 500.0)
    det_near_a = _detection_for(1000.2, 2000.4, 500.1)
    det_near_b = _detection_for(1500.3, 2500.2, 500.4)

    result = associate([track_a, track_b], [det_near_a, det_near_b], **_NOISE)

    # Both pairs are well inside the gate; both must end up assigned,
    # and the assignment cannot double-book either side.
    assigned_track_ids = set(result.track_to_detection.keys())
    assigned_det_ids = set(result.track_to_detection.values())
    assert assigned_track_ids == {0, 1}
    assert assigned_det_ids == {0, 1}
    # And the cheaper assignment is the one that matches each track to
    # its physically closer detection.
    assert result.track_to_detection == {0: 0, 1: 1}


def test_two_tracks_one_detection_closer_track_wins() -> None:
    """Hungarian must give the lone detection to the cheaper track and
    park the other track in ``unassigned_tracks`` (no fallback to a
    distance-tie-breaker outside the cost matrix).
    """
    track_near = _track_at(0, 1000.0, 2000.0, 500.0)
    track_far = _track_at(1, 1100.0, 2000.0, 500.0)
    det = _detection_for(1000.3, 2000.2, 500.1)  # very close to track_near

    result = associate([track_near, track_far], [det], **_NOISE)
    assert result.track_to_detection == {0: 0}
    assert 1 in result.unassigned_tracks
    assert result.unassigned_detections == ()


# ---------------------------------------------------------------------
# Azimuth wrap inside the Mahalanobis cost
# ---------------------------------------------------------------------


def test_az_wrap_pair_at_pi_boundary_still_associates() -> None:
    """Track and detection sit on opposite sides of the +/- pi azimuth
    branch cut but are physically next to each other. The associator
    must wrap the innovation and still mark the pair as assigned.
    """
    # Track at azimuth ~ +pi (just east of due south)
    track_east_south = _track_at(0, 0.5, -1000.0, 200.0)
    # Detection at azimuth ~ -pi (just west of due south, ~ same point)
    detection_west_south = _detection_for(-0.5, -1000.0, 200.0)

    result = associate([track_east_south], [detection_west_south], **_NOISE)
    assert result.track_to_detection == {0: 0}


# ---------------------------------------------------------------------
# Mahalanobis squared closed-form for a perfectly-aligned pair
# ---------------------------------------------------------------------


def test_mahalanobis_zero_for_perfect_measurement() -> None:
    """Detection that exactly equals h(track.mean) -> innovation = 0
    -> Mahalanobis = 0.
    """
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    e, n, u = (
        float(track.mean[0]),
        float(track.mean[1]),
        float(track.mean[2]),
    )
    detection = _detection_for(e, n, u)
    cost = mahalanobis_squared(track, detection, **_NOISE)
    assert cost == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"range_noise_std_m": 0.0}, r"range_noise_std_m"),
        ({"range_noise_std_m": -1.0}, r"range_noise_std_m"),
        ({"az_noise_std_rad": 0.0}, r"az_noise_std_rad"),
        ({"el_noise_std_rad": -1e-9}, r"el_noise_std_rad"),
    ],
)
def test_associate_rejects_non_positive_noise(override: dict[str, float], match: str) -> None:
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    detection = _detection_for(1000.0, 2000.0, 500.0)
    kwargs = {**_NOISE, **override}
    with pytest.raises(ValueError, match=match):
        associate([track], [detection], **kwargs)


def test_associate_rejects_non_positive_gating_threshold() -> None:
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    detection = _detection_for(1000.0, 2000.0, 500.0)
    with pytest.raises(ValueError, match=r"gating_threshold_chi2"):
        associate([track], [detection], gating_threshold_chi2=0.0, **_NOISE)


def test_default_gating_threshold_constant_is_3dof_99_7_percentile() -> None:
    """Sanity-lock the imported chi-square percentile constant."""
    assert DEFAULT_GATING_THRESHOLD_CHI2 == pytest.approx(14.16, abs=0.005)
