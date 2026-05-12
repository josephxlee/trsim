"""GNN data association regression (Phase 5.18 + 5.18b).

Verifies the Hungarian + chi-square gated associator in
:mod:`workbench.domain.tracker.data_associator` on scenarios that the
single-pair / empty-input unit tests in
:mod:`tests.unit.domain.test_tracker` do not cover.

5.18 (existing):
- close detection inside the gate is assigned;
- far detection outside the gate is dropped;
- two-track / two-detection Hungarian global optimum (no double-book);
- two-tracks-one-detection: closer track wins;
- azimuth wrap inside Mahalanobis still associates +pi-eps with -pi+eps;
- Mahalanobis = 0 for a perfectly-aligned pair;
- input validation (non-positive noise std / threshold).

5.18b (this revision):
- 4-track / 4-detection dense scene: every pair matched, no double-book;
- 3-track / 4-detection mixed scene: extra clutter detection lands in
  ``unassigned_detections`` while the three valid pairs match;
- boundary gating just *below* the 14.16 default chi^2 threshold ->
  pair is assigned (offset calibrated against the unit-sigma_r chi^2
  so the test is robust to the H P H^T contribution);
- boundary gating just *above* the threshold -> pair is dropped;
- Mahalanobis chi^2 is quadratic in the radial innovation: doubling
  the offset multiplies chi^2 by 4 (closed-form lock).
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


# ---------------------------------------------------------------------
# 5.18b — dense scenes + boundary gating + Mahalanobis closed-form
# ---------------------------------------------------------------------


def _radial_detection_at(track: TrackState, range_offset_m: float) -> Detection:
    """Place a detection along the same line-of-sight as the track,
    offset by ``range_offset_m`` from the track's range.

    Because the detection is a scalar multiple of the track position
    vector, both az and el innovations are exactly zero. The chi^2
    therefore reduces to ``(range_offset / range_noise_std_m)^2`` —
    a clean handle for boundary tests and Mahalanobis lock-ins.
    """
    e_t = float(track.mean[0])
    n_t = float(track.mean[1])
    u_t = float(track.mean[2])
    range_t = math.sqrt(e_t * e_t + n_t * n_t + u_t * u_t)
    lam = (range_t + range_offset_m) / range_t
    return _detection_for(lam * e_t, lam * n_t, lam * u_t)


def test_dense_4_track_4_detection_assigns_all_pairs() -> None:
    """Four well-separated tracks each with a single nearby detection.
    Hungarian must produce a complete one-to-one match (no track or
    detection unassigned, no double-book).
    """
    tracks = [
        _track_at(0, 1000.0, 2000.0, 500.0),
        _track_at(1, 2000.0, 3000.0, 500.0),
        _track_at(2, 3000.0, 4000.0, 500.0),
        _track_at(3, 4000.0, 5000.0, 500.0),
    ]
    detections = [
        _detection_for(1000.3, 2000.2, 500.1),
        _detection_for(2000.4, 3000.1, 500.2),
        _detection_for(3000.1, 4000.3, 500.0),
        _detection_for(4000.2, 5000.4, 500.3),
    ]
    result = associate(tracks, detections, **_NOISE)
    assert result.track_to_detection == {0: 0, 1: 1, 2: 2, 3: 3}
    assert result.unassigned_tracks == ()
    assert result.unassigned_detections == ()


def test_3_tracks_4_detections_extra_detection_is_unassigned() -> None:
    """Three tracks, four detections. The fourth detection is physically
    distant from every track (out of gate everywhere); Hungarian must
    leave it in ``unassigned_detections`` while still pairing the other
    three correctly.
    """
    tracks = [
        _track_at(0, 1000.0, 2000.0, 500.0),
        _track_at(1, 2000.0, 3000.0, 500.0),
        _track_at(2, 3000.0, 4000.0, 500.0),
    ]
    detections = [
        _detection_for(1000.3, 2000.2, 500.1),
        _detection_for(2000.4, 3000.1, 500.2),
        _detection_for(3000.1, 4000.3, 500.0),
        _detection_for(8000.0, -2000.0, 500.0),  # clutter, far from everything
    ]
    result = associate(tracks, detections, **_NOISE)
    assert result.track_to_detection == {0: 0, 1: 1, 2: 2}
    assert result.unassigned_tracks == ()
    assert result.unassigned_detections == (3,)


def _calibrated_offset_for_chi2(track: TrackState, target_chi2: float) -> float:
    """Find the radial offset (m) that puts chi^2 at ``target_chi2``.

    chi^2 is quadratic in offset (the innovation covariance is fixed
    for a given track), so a single measurement at the unit-sigma_r
    offset is enough to back out the proportionality constant for
    this track. Used by the boundary-gating tests so they remain
    valid regardless of the track-position-dependent H P H^T term.
    """
    sigma_r = _NOISE["range_noise_std_m"]
    chi2_at_sigma_r = mahalanobis_squared(track, _radial_detection_at(track, sigma_r), **_NOISE)
    return sigma_r * math.sqrt(target_chi2 / chi2_at_sigma_r)


def test_boundary_gating_just_below_threshold_assigns() -> None:
    """A radial offset that yields chi^2 ~ 14.15 (below the 14.16
    default) must produce an assignment. The offset is calibrated
    against the unit-sigma_r measurement so this test is robust to
    the H P H^T contribution that scales with track position.
    """
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    offset = _calibrated_offset_for_chi2(track, 14.15)
    detection = _radial_detection_at(track, offset)
    chi2 = mahalanobis_squared(track, detection, **_NOISE)
    assert chi2 == pytest.approx(14.15, rel=1e-9)
    assert chi2 < DEFAULT_GATING_THRESHOLD_CHI2
    result = associate([track], [detection], **_NOISE)
    assert result.track_to_detection == {0: 0}


def test_boundary_gating_just_above_threshold_drops() -> None:
    """A radial offset that yields chi^2 ~ 14.17 (above the 14.16
    default) must be dropped. Same calibration approach as the
    just-below test.
    """
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    offset = _calibrated_offset_for_chi2(track, 14.17)
    detection = _radial_detection_at(track, offset)
    chi2 = mahalanobis_squared(track, detection, **_NOISE)
    assert chi2 == pytest.approx(14.17, rel=1e-9)
    assert chi2 > DEFAULT_GATING_THRESHOLD_CHI2
    result = associate([track], [detection], **_NOISE)
    assert result.track_to_detection == {}
    assert result.unassigned_tracks == (0,)
    assert result.unassigned_detections == (0,)


def test_chi2_is_quadratic_in_radial_offset() -> None:
    """The Mahalanobis distance squared is quadratic in the radial
    innovation: chi^2(2 * d) = 4 * chi^2(d) when az/el components are
    zero. Lock the linearity of the innovation covariance.
    """
    track = _track_at(0, 1000.0, 2000.0, 500.0)
    sigma_r = _NOISE["range_noise_std_m"]
    chi2_d = mahalanobis_squared(track, _radial_detection_at(track, sigma_r), **_NOISE)
    chi2_2d = mahalanobis_squared(track, _radial_detection_at(track, 2.0 * sigma_r), **_NOISE)
    assert chi2_2d == pytest.approx(4.0 * chi2_d, rel=1e-9)
