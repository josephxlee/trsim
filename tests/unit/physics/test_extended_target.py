"""Unit tests for workbench.physics.reflection.extended_target (Phase 2.7)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.physics.reflection.extended_target import (
    C_LIGHT_M_S,
    ExtendedTarget,
    Scatterer,
    ScatteringResult,
    body_to_world_rotation,
    compute_extended_target_return,
)

# ---------------------------------------------------------------------
# Scatterer
# ---------------------------------------------------------------------


def test_scatterer_default_label() -> None:
    s = Scatterer(offset_body_m=(1.0, 2.0, 3.0), rcs_dbsm=5.0)
    assert s.label == ""


def test_scatterer_explicit_label() -> None:
    s = Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0, label="nose")
    assert s.label == "nose"


def test_scatterer_rejects_short_offset() -> None:
    with pytest.raises(ValueError, match=r"offset_body_m"):
        Scatterer(offset_body_m=(1.0, 2.0), rcs_dbsm=0.0)  # type: ignore[arg-type]


def test_scatterer_rejects_long_offset() -> None:
    with pytest.raises(ValueError, match=r"offset_body_m"):
        Scatterer(offset_body_m=(1.0, 2.0, 3.0, 4.0), rcs_dbsm=0.0)  # type: ignore[arg-type]


def test_scatterer_is_frozen() -> None:
    s = Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0)
    with pytest.raises(Exception):  # noqa: B017
        s.rcs_dbsm = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------
# ExtendedTarget
# ---------------------------------------------------------------------


def test_extended_target_construction() -> None:
    target = ExtendedTarget(
        target_id="fighter_jet_01",
        scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),),
    )
    assert target.target_id == "fighter_jet_01"
    assert len(target.scatterers) == 1


def test_extended_target_rejects_empty_target_id() -> None:
    with pytest.raises(ValueError, match=r"target_id"):
        ExtendedTarget(
            target_id="",
            scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),),
        )


def test_extended_target_rejects_empty_scatterers() -> None:
    with pytest.raises(ValueError, match=r"scatterers"):
        ExtendedTarget(target_id="x", scatterers=())


def test_total_rcs_dbsm_two_zero_dbsm_sources() -> None:
    # Two sources at 0 dBsm = 1 m^2 each. Linear sum = 2 m^2 = 3.01 dBsm.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(1.0, 0.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    assert target.total_rcs_dbsm == pytest.approx(10.0 * math.log10(2.0), abs=1e-12)


def test_total_rcs_dbsm_single_scatterer() -> None:
    target = ExtendedTarget(
        target_id="x",
        scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=10.0),),
    )
    assert target.total_rcs_dbsm == pytest.approx(10.0, abs=1e-12)


def test_total_rcs_dbsm_mixed_levels() -> None:
    # 10 dBsm + 0 dBsm = 10 + 1 = 11 m^2 -> 10.4139 dBsm
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=10.0),
            Scatterer(offset_body_m=(1.0, 0.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    expected = 10.0 * math.log10(11.0)
    assert target.total_rcs_dbsm == pytest.approx(expected, abs=1e-12)


# ---------------------------------------------------------------------
# body_to_world_rotation
# ---------------------------------------------------------------------


def _apply(rot: np.ndarray, vec: tuple[float, float, float]) -> tuple[float, float, float]:
    out = rot @ np.asarray(vec, dtype=np.float64)
    return float(out[0]), float(out[1]), float(out[2])


def test_rotation_zero_attitude_x_to_north() -> None:
    r = body_to_world_rotation(0.0, 0.0, 0.0)
    east, north, up = _apply(r, (1.0, 0.0, 0.0))  # body forward
    assert east == pytest.approx(0.0, abs=1e-12)
    assert north == pytest.approx(1.0, abs=1e-12)
    assert up == pytest.approx(0.0, abs=1e-12)


def test_rotation_zero_attitude_y_to_east() -> None:
    r = body_to_world_rotation(0.0, 0.0, 0.0)
    east, north, up = _apply(r, (0.0, 1.0, 0.0))  # body right
    assert east == pytest.approx(1.0, abs=1e-12)
    assert north == pytest.approx(0.0, abs=1e-12)
    assert up == pytest.approx(0.0, abs=1e-12)


def test_rotation_zero_attitude_z_to_minus_up() -> None:
    r = body_to_world_rotation(0.0, 0.0, 0.0)
    east, north, up = _apply(r, (0.0, 0.0, 1.0))  # body down
    assert east == pytest.approx(0.0, abs=1e-12)
    assert north == pytest.approx(0.0, abs=1e-12)
    assert up == pytest.approx(-1.0, abs=1e-12)


def test_rotation_yaw_pi_over_2_forward_to_east() -> None:
    # yaw = +pi/2 (CW from N) -> forward points to East.
    r = body_to_world_rotation(math.pi / 2, 0.0, 0.0)
    east, north, _ = _apply(r, (1.0, 0.0, 0.0))
    assert east == pytest.approx(1.0, abs=1e-12)
    assert north == pytest.approx(0.0, abs=1e-12)


def test_rotation_pitch_pi_over_2_forward_to_up() -> None:
    # pitch = +pi/2 nose up -> forward points to Up.
    r = body_to_world_rotation(0.0, math.pi / 2, 0.0)
    _, _, up = _apply(r, (1.0, 0.0, 0.0))
    assert up == pytest.approx(1.0, abs=1e-12)


def test_rotation_roll_pi_over_2_right_wing_down() -> None:
    # Zero yaw / pitch, roll = +pi/2 (right-wing-down). At zero pitch:
    #   body y (right) = East before roll. Right wing down rotates
    #   right axis around forward (= North) toward body z direction.
    #   body z (down) at zero attitude points to -Up.
    # After roll = +pi/2 about forward, right axis goes from East
    # toward -Up direction.
    r = body_to_world_rotation(0.0, 0.0, math.pi / 2)
    east, north, up = _apply(r, (0.0, 1.0, 0.0))  # body right
    assert east == pytest.approx(0.0, abs=1e-12)
    assert north == pytest.approx(0.0, abs=1e-12)
    assert up == pytest.approx(-1.0, abs=1e-12)


def test_rotation_is_orthonormal() -> None:
    # Random-ish attitude. R^T @ R should be identity.
    r = body_to_world_rotation(yaw_rad=0.7, pitch_rad=-0.3, roll_rad=0.2)
    product = r.T @ r
    np.testing.assert_allclose(product, np.eye(3), atol=1e-12)


def test_rotation_determinant_one() -> None:
    r = body_to_world_rotation(yaw_rad=0.5, pitch_rad=0.4, roll_rad=-0.1)
    assert float(np.linalg.det(r)) == pytest.approx(1.0, abs=1e-12)


def test_rotation_yaw_only_preserves_horizontal_plane() -> None:
    # Yaw rotates about Up -> body forward stays in horizontal plane.
    r = body_to_world_rotation(yaw_rad=1.234, pitch_rad=0.0, roll_rad=0.0)
    _, _, up = _apply(r, (1.0, 0.0, 0.0))
    assert up == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------
# compute_extended_target_return — single scatterer at origin
# ---------------------------------------------------------------------


def _single_scatterer_target(rcs_dbsm: float = 0.0) -> ExtendedTarget:
    return ExtendedTarget(
        target_id="x",
        scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=rcs_dbsm),),
    )


def test_single_scatterer_apparent_equals_target_pos() -> None:
    target = _single_scatterer_target()
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(1000.0, 2000.0, 500.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    assert result.apparent_position_m == pytest.approx((1000.0, 2000.0, 500.0), abs=1e-9)
    assert result.glint_offset_m == pytest.approx((0.0, 0.0, 0.0), abs=1e-9)


def test_single_scatterer_amplitude_scales_with_inverse_r_squared() -> None:
    target = _single_scatterer_target(rcs_dbsm=0.0)  # 1 m^2

    def amp_at_range(r: float) -> float:
        result = compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(r, 0.0, 0.0),
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=9.4e9,
        )
        return abs(result.total_signal)

    a1 = amp_at_range(1000.0)
    a2 = amp_at_range(2000.0)
    # Doubling R divides amplitude by 4 (1/R^2).
    assert a1 / a2 == pytest.approx(4.0, rel=1e-12)


def test_single_scatterer_amplitude_known_value() -> None:
    # 1 m^2 RCS, R = 1000 m -> A = sqrt(1) / 1000^2 = 1e-6
    target = _single_scatterer_target(rcs_dbsm=0.0)
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(1000.0, 0.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    assert abs(result.total_signal) == pytest.approx(1e-6, rel=1e-9)


def test_offset_scatterer_drives_apparent_position() -> None:
    # Single scatterer offset 5 m forward (body x). Target at origin
    # with zero attitude -> body forward = +North. Apparent should
    # match the rotated scatterer position exactly (only one source).
    target = ExtendedTarget(
        target_id="x",
        scatterers=(Scatterer(offset_body_m=(5.0, 0.0, 0.0), rcs_dbsm=0.0),),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, -1000.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 0.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    assert result.apparent_position_m == pytest.approx((0.0, 5.0, 0.0), abs=1e-9)
    assert result.glint_offset_m == pytest.approx((0.0, 5.0, 0.0), abs=1e-9)


# ---------------------------------------------------------------------
# Multi-scatterer / glint
# ---------------------------------------------------------------------


def test_two_equal_scatterers_symmetric_about_target_apparent_at_target() -> None:
    # Two scatterers symmetric across the body x axis, equal RCS, far
    # radar. Range to each is essentially equal -> equal amplitudes,
    # phases differ by a tiny LOS-projection delta. Apparent centroid
    # should very nearly coincide with the target reference position.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 5.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(0.0, -5.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 100_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    # Far-field symmetric pair -> apparent very close to target ref.
    # body y = East, scatterers are at (+/-5, 0, 0) east of target.
    # Range to each is sqrt(100000^2 + 5^2) ~= 100000.000125 m. Phases
    # differ by 4 pi * 0.00025 / lambda but amplitudes are essentially
    # equal -> weighted centroid ~ target_pos to within numerics.
    assert result.glint_offset_m[0] == pytest.approx(0.0, abs=0.1)
    assert result.glint_offset_m[1] == pytest.approx(0.0, abs=1e-3)
    assert result.glint_offset_m[2] == pytest.approx(0.0, abs=1e-9)


def test_two_unequal_scatterers_apparent_pulled_toward_brighter() -> None:
    # +5 m east scatterer with 10 dBsm, -5 m east with 0 dBsm.
    # Brighter source dominates -> apparent shifts toward +5.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 5.0, 0.0), rcs_dbsm=10.0),
            Scatterer(offset_body_m=(0.0, -5.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 100_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    # Glint should pull east (positive E) of target reference.
    assert result.glint_offset_m[0] > 0.0


def test_destructive_interference_between_two_scatterers_along_los() -> None:
    # Two equal scatterers along the line of sight separated by
    # lambda / 4 in range -> round-trip phase difference =
    # 4 pi * (lambda/4) / lambda = pi -> coherent sum cancels.
    freq = 9.4e9
    wavelength = C_LIGHT_M_S / freq
    quarter = wavelength / 4.0

    # Place radar at origin, target north of radar at 10 km. Scatterer
    # offsets along +North (body forward at zero attitude).
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(quarter, 0.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 10_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=freq,
    )
    # |total_signal| should be essentially zero (destructive).
    # Compare against the single-source amplitude — must be much smaller.
    single = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=ExtendedTarget(
            target_id="x",
            scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),),
        ),
        target_position_enu_m=(0.0, 10_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=freq,
    )
    assert abs(result.total_signal) < 0.01 * abs(single.total_signal)


def test_constructive_interference_between_two_scatterers_along_los() -> None:
    # Two equal scatterers separated by lambda / 2 in range -> phase
    # difference = 4 pi * (lambda/2) / lambda = 2 pi -> aligned.
    freq = 9.4e9
    wavelength = C_LIGHT_M_S / freq
    half = wavelength / 2.0

    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(half, 0.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 10_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=freq,
    )
    single = compute_extended_target_return(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=ExtendedTarget(
            target_id="x",
            scatterers=(Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),),
        ),
        target_position_enu_m=(0.0, 10_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=freq,
    )
    # |sum| should be ~2 * single (within ~1 % for the small range
    # spread / 1/R^2 amplitude difference between the two scatterers).
    assert abs(result.total_signal) == pytest.approx(2.0 * abs(single.total_signal), rel=2e-3)


# ---------------------------------------------------------------------
# Attitude rotation in the return computation
# ---------------------------------------------------------------------


def test_yaw_pi_over_2_swaps_body_forward_to_east() -> None:
    # Scatterer at (5, 0, 0) body. Yaw = +pi/2 -> body forward = East.
    # Target at origin -> apparent at (5, 0, 0) ENU.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(Scatterer(offset_body_m=(5.0, 0.0, 0.0), rcs_dbsm=0.0),),
    )
    result = compute_extended_target_return(
        radar_position_enu_m=(0.0, -1000.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 0.0, 0.0),
        target_attitude_rad=(math.pi / 2, 0.0, 0.0),
        frequency_hz=9.4e9,
    )
    assert result.apparent_position_m == pytest.approx((5.0, 0.0, 0.0), abs=1e-9)


# ---------------------------------------------------------------------
# Frequency dependence
# ---------------------------------------------------------------------


def test_frequency_change_alters_phase_pattern() -> None:
    # Same target, same geometry, two frequencies -> total_signal phase
    # must differ unless distance happens to be a wavelength multiple.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 0.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(0.5, 0.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    geom = {
        "radar_position_enu_m": (0.0, 0.0, 0.0),
        "target": target,
        "target_position_enu_m": (0.0, 1234.5, 0.0),
        "target_attitude_rad": (0.0, 0.0, 0.0),
    }
    a = compute_extended_target_return(frequency_hz=9.4e9, **geom)
    b = compute_extended_target_return(frequency_hz=10.0e9, **geom)
    # Different f -> different total_signal (phase patterns differ).
    assert abs(a.total_signal - b.total_signal) > 1e-12


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_compute_rejects_non_positive_frequency() -> None:
    target = _single_scatterer_target()
    with pytest.raises(ValueError, match=r"frequency_hz"):
        compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(100.0, 0.0, 0.0),
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=0.0,
        )


def test_compute_rejects_zero_range() -> None:
    # Scatterer co-located with radar.
    target = _single_scatterer_target()
    with pytest.raises(ValueError, match=r"range"):
        compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(0.0, 0.0, 0.0),
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=9.4e9,
        )


# ---------------------------------------------------------------------
# ScatteringResult dataclass
# ---------------------------------------------------------------------


def test_scattering_result_is_frozen() -> None:
    r = ScatteringResult(
        total_signal=1 + 2j,
        apparent_position_m=(0.0, 0.0, 0.0),
        glint_offset_m=(0.0, 0.0, 0.0),
    )
    with pytest.raises(Exception):  # noqa: B017
        r.total_signal = 3 + 4j  # type: ignore[misc]


def test_c_light_constant() -> None:
    # Sanity-lock the SI exact value shared across antenna / fmcw /
    # multipath / extended_target.
    assert C_LIGHT_M_S == 299_792_458.0
