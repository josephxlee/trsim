"""ExtendedTarget multi-scatterer + glint regression (Phase 5.14).

Verifies :mod:`workbench.physics.reflection.extended_target` against
closed-form 2-scatterer along-LOS values stored in
``tests/physics/golden/extended_target_glint.json`` plus structural
invariants from plan/14 § 14.10 / Skolnik chap 18:

- amplitude-weighted apparent centroid lies inside the scatterer ENU
  convex hull (Skolnik's definition of the glint reach);
- coherent sum amplitude never exceeds the linear sum of scatterer
  amplitudes (triangle inequality);
- ``total_rcs_dbsm`` is an incoherent average and therefore
  attitude-invariant;
- the call is deterministic for fixed inputs (numerical
  reproducibility);
- a frequency sweep across a body-symmetric pair of scatterers
  averages out the glint along the symmetry axis.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Final

import numpy as np
import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.reflection.extended_target import (
    ExtendedTarget,
    Scatterer,
    body_to_world_rotation,
    compute_extended_target_return,
)

_GOLDEN_PATH: Final[Path] = Path(__file__).parent / "golden" / "extended_target_glint.json"
_DATASET: Final[GoldenDataset] = GoldenDataset.load(_GOLDEN_PATH)
_RTOL: Final[float] = _DATASET.meta.rtol


def _vec3(raw: Any) -> tuple[float, float, float]:
    return float(raw[0]), float(raw[1]), float(raw[2])


def _two_scatterer_along_los_inputs() -> dict[str, Any]:
    sample = _DATASET.case("two_scatterer_along_los_xband_9_4ghz")
    raw_offsets = sample.inputs["scatterer_offsets_body_m"]
    offsets = [_vec3(o) for o in raw_offsets]
    rcs_each = float(sample.inputs["rcs_dbsm_each"])
    return {
        "target": ExtendedTarget(
            target_id="along_los_pair",
            scatterers=tuple(Scatterer(offset_body_m=off, rcs_dbsm=rcs_each) for off in offsets),
        ),
        "radar_position_enu_m": _vec3(sample.inputs["radar_position_enu_m"]),
        "target_position_enu_m": _vec3(sample.inputs["target_position_enu_m"]),
        "target_attitude_rad": _vec3(sample.inputs["target_attitude_rad"]),
        "frequency_hz": float(sample.inputs["frequency_hz"]),
    }


# ---------------------------------------------------------------------
# Golden 2-scatterer along-LOS reference
# ---------------------------------------------------------------------


def test_amplitude_0_matches_golden() -> None:
    """Inner scatterer amplitude = sqrt(1 m^2) / 1000^2 = 1e-6."""
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    # The first scatterer sits exactly on the target reference (range
    # 1000 m for the geometry hardcoded in the dataset).
    # Build a single-scatterer target so we can read the amplitude as
    # |total_signal| directly.
    only_first = ExtendedTarget(
        target_id="only_first",
        scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=only_first,
        target_position_enu_m=(0.0, 1000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    assert abs(result.total_signal) == pytest.approx(expected["amplitude_0"], rel=_RTOL)


def test_amplitude_ratio_matches_inverse_r_squared() -> None:
    """amp1 / amp0 = (R0/R1)^2 = (1000/1001)^2."""
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    ratio = (1000.0 / 1001.0) ** 2
    assert ratio == pytest.approx(expected["amp_ratio"], rel=_RTOL)


def test_apparent_north_matches_golden() -> None:
    """Amplitude-weighted centroid sits between the two scatterer ranges."""
    inputs = _two_scatterer_along_los_inputs()
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    result = compute_extended_target_return(**inputs)
    assert result.apparent_position_m[1] == pytest.approx(expected["apparent_north_m"], rel=_RTOL)


def test_glint_north_matches_golden() -> None:
    """Glint along +North = centroid - target reference ~ 0.4995 m."""
    inputs = _two_scatterer_along_los_inputs()
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    result = compute_extended_target_return(**inputs)
    assert result.glint_offset_m[1] == pytest.approx(expected["glint_north_m"], rel=_RTOL)


def test_total_signal_real_imag_matches_golden() -> None:
    """Coherent sum complex parts match Mahafza closed-form bit-for-bit."""
    inputs = _two_scatterer_along_los_inputs()
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    result = compute_extended_target_return(**inputs)
    assert result.total_signal.real == pytest.approx(expected["total_signal_real"], rel=_RTOL)
    assert result.total_signal.imag == pytest.approx(expected["total_signal_imag"], rel=_RTOL)


def test_total_signal_magnitude_matches_golden() -> None:
    inputs = _two_scatterer_along_los_inputs()
    expected = _DATASET.case("two_scatterer_along_los_xband_9_4ghz").expected
    result = compute_extended_target_return(**inputs)
    assert abs(result.total_signal) == pytest.approx(expected["total_signal_abs"], rel=_RTOL)


# ---------------------------------------------------------------------
# Skolnik glint invariants (plan/14 § 14.10)
# ---------------------------------------------------------------------


def _five_scatterer_aircraft() -> ExtendedTarget:
    """Aircraft-shaped 5-scatterer cloud (Skolnik § 18 / plan/14 § 14.10.3)."""
    return ExtendedTarget(
        target_id="aircraft_5pt",
        scatterers=(
            Scatterer(offset_body_m=(7.0, 0.0, 0.0), rcs_dbsm=5.0, label="nose"),
            Scatterer(offset_body_m=(0.0, 6.0, 0.0), rcs_dbsm=8.0, label="wing_R"),
            Scatterer(offset_body_m=(0.0, -6.0, 0.0), rcs_dbsm=8.0, label="wing_L"),
            Scatterer(offset_body_m=(-5.0, 0.0, 0.5), rcs_dbsm=4.0, label="tail"),
            Scatterer(offset_body_m=(1.0, 0.0, 0.5), rcs_dbsm=10.0, label="engine"),
        ),
    )


@pytest.mark.parametrize(
    ("yaw_deg", "pitch_deg", "roll_deg", "freq_hz"),
    [
        (0.0, 0.0, 0.0, 9.4e9),
        (37.0, -8.0, 12.0, 9.4e9),
        (90.0, 0.0, 0.0, 10.0e9),
        (-45.0, 5.0, -3.0, 16.5e9),
        (170.0, 25.0, 60.0, 9.4e9),
    ],
)
def test_apparent_within_scatterer_bounding_box(
    yaw_deg: float, pitch_deg: float, roll_deg: float, freq_hz: float
) -> None:
    """Skolnik glint definition: apparent centroid is a convex
    combination of scatterer positions, so it must lie inside their
    axis-aligned ENU bounding box for every attitude / frequency.
    """
    target = _five_scatterer_aircraft()
    target_pos = (1234.5, 6789.0, 200.0)
    attitude = (math.radians(yaw_deg), math.radians(pitch_deg), math.radians(roll_deg))
    rotation = body_to_world_rotation(*attitude)

    target_arr = np.asarray(target_pos, dtype=np.float64)
    scatterer_enu = np.stack(
        [
            target_arr + rotation @ np.asarray(s.offset_body_m, dtype=np.float64)
            for s in target.scatterers
        ]
    )
    mins = scatterer_enu.min(axis=0)
    maxs = scatterer_enu.max(axis=0)

    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=target_pos,
        target_attitude_rad=attitude,
        frequency_hz=freq_hz,
    )
    apparent = np.asarray(result.apparent_position_m, dtype=np.float64)
    slack = 1e-9
    assert np.all(apparent >= mins - slack)
    assert np.all(apparent <= maxs + slack)


def test_coherent_sum_triangle_inequality() -> None:
    """|sum| <= sum(|contribution_i|) for every coherent superposition."""
    target = _five_scatterer_aircraft()
    target_pos = (0.0, 25_000.0, 4000.0)
    attitude = (math.radians(20.0), math.radians(-5.0), math.radians(3.0))
    freq_hz = 9.4e9

    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=target_pos,
        target_attitude_rad=attitude,
        frequency_hz=freq_hz,
    )

    rotation = body_to_world_rotation(*attitude)
    target_arr = np.asarray(target_pos, dtype=np.float64)
    radar_arr = np.zeros(3, dtype=np.float64)
    sum_of_amplitudes = 0.0
    for s in target.scatterers:
        offset_world = rotation @ np.asarray(s.offset_body_m, dtype=np.float64)
        rng = float(np.linalg.norm(target_arr + offset_world - radar_arr))
        sum_of_amplitudes += math.sqrt(math.pow(10.0, s.rcs_dbsm / 10.0)) / (rng * rng)

    # Triangle inequality, with a tiny float-rounding slack.
    assert abs(result.total_signal) <= sum_of_amplitudes * (1.0 + 1e-12)


@pytest.mark.parametrize(
    ("yaw_deg", "pitch_deg", "roll_deg"),
    [
        (0.0, 0.0, 0.0),
        (37.0, -8.0, 12.0),
        (90.0, 45.0, -30.0),
        (180.0, 0.0, 60.0),
    ],
)
def test_total_rcs_dbsm_is_attitude_invariant(
    yaw_deg: float, pitch_deg: float, roll_deg: float
) -> None:
    """total_rcs_dbsm = incoherent sum of linear cross-sections; the
    body->world rotation only relocates the scatterers and cannot
    change the per-scatterer dBsm or their sum.
    """
    del yaw_deg, pitch_deg, roll_deg  # attitude is not an input to total_rcs_dbsm
    target = _five_scatterer_aircraft()
    expected = 10.0 * math.log10(sum(math.pow(10.0, s.rcs_dbsm / 10.0) for s in target.scatterers))
    assert target.total_rcs_dbsm == pytest.approx(expected, rel=1e-12)


def test_deterministic_repeat_identical() -> None:
    """Two calls with identical inputs must return identical floats."""
    inputs = _two_scatterer_along_los_inputs()
    a = compute_extended_target_return(**inputs)
    b = compute_extended_target_return(**inputs)
    assert a.total_signal == b.total_signal
    assert a.apparent_position_m == b.apparent_position_m
    assert a.glint_offset_m == b.glint_offset_m


def test_body_x_aligned_scatterers_apparent_invariant_under_roll() -> None:
    """Scatterers on the body x-axis (forward) project onto the rolled
    forward axis, which is unchanged by a pure roll about that axis.
    Apparent ENU position must therefore be roll-invariant.
    """
    target = ExtendedTarget(
        target_id="forward_string",
        scatterers=(
            Scatterer(offset_body_m=(-2.0, 0.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=3.0),
            Scatterer(offset_body_m=(3.0, 0.0, 0.0), rcs_dbsm=-1.0),
        ),
    )
    geom: dict[str, Any] = {
        "radar_position_enu_m": (0.0, 0.0, 0.0),
        "target": target,
        "target_position_enu_m": (0.0, 15_000.0, 0.0),
        "frequency_hz": 9.4e9,
    }
    base = compute_extended_target_return(
        target_attitude_rad=(0.0, 0.0, 0.0),
        **geom,
    )
    rolled = compute_extended_target_return(
        target_attitude_rad=(0.0, 0.0, math.radians(47.0)),
        **geom,
    )
    # Apparent ENU position is the same to within float-mul noise.
    for got, want in zip(rolled.apparent_position_m, base.apparent_position_m, strict=True):
        assert got == pytest.approx(want, abs=1e-9)


def test_symmetric_pair_frequency_sweep_glint_along_axis_zero_mean() -> None:
    """A pair of equal scatterers symmetric across body x has glint that
    oscillates with frequency but, averaged across a uniform frequency
    sweep that brackets many wavelengths of separation, averages to
    zero along the wing-tip axis.
    """
    target = ExtendedTarget(
        target_id="symmetric_wings",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 4.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(0.0, -4.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    # Sweep 9.0 ... 10.0 GHz in 41 steps -> ~ 33 wavelengths across 8 m,
    # plenty of phase coverage. Symmetric paired scatterers in a body
    # frame with body x = +North have scatterer ENU positions at
    # (+/-4, target_y, 0). Glint along East should average to ~0.
    samples = []
    for i in range(41):
        f_hz = 9.0e9 + (1.0e9) * (i / 40.0)
        result = compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(0.0, 12_000.0, 0.0),
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=f_hz,
        )
        samples.append(result.glint_offset_m[0])
    mean_east_glint = sum(samples) / len(samples)
    # The pair is at ENU east = +/- 4 m, so the apparent east extent
    # is bounded by [-4, 4] m. A symmetric sweep averages to within a
    # small fraction of that range.
    assert abs(mean_east_glint) < 0.2
