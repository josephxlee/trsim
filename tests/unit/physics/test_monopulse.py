"""Unit tests for workbench.physics.monopulse (Phase 2.6b)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.monopulse import (
    MonopulseError,
    monopulse_error_extended,
    monopulse_error_from_channels,
)
from workbench.physics.reflection.extended_target import ExtendedTarget, Scatterer

# ---------------------------------------------------------------------
# monopulse_error_from_channels — core formula
# ---------------------------------------------------------------------


def test_zero_delta_zero_error() -> None:
    err = monopulse_error_from_channels(
        sigma=1.0 + 0j,
        delta_az=0.0 + 0j,
        delta_el=0.0 + 0j,
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == 0.0
    assert err.error_el_rad == 0.0
    assert err.sum_amplitude == pytest.approx(1.0, abs=1e-12)


def test_in_phase_delta_az_gives_positive_error() -> None:
    # delta_az / sigma = 0.1 (real) -> error_az = slope * 0.1
    err = monopulse_error_from_channels(
        sigma=1.0 + 0j,
        delta_az=0.1 + 0j,
        delta_el=0.0 + 0j,
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == pytest.approx(1.4 * 0.1, abs=1e-12)
    assert err.error_el_rad == 0.0


def test_imaginary_delta_az_gives_zero_error() -> None:
    # Re(j / 1) = 0 -> error = 0 (phase-comparison rejected at MVP).
    err = monopulse_error_from_channels(
        sigma=1.0 + 0j,
        delta_az=0.0 + 1j,
        delta_el=0.0 + 0j,
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == 0.0


def test_negative_delta_gives_negative_error() -> None:
    err = monopulse_error_from_channels(
        sigma=1.0 + 0j,
        delta_az=-0.05 + 0j,
        delta_el=0.0 + 0j,
        slope_az=2.0,
        slope_el=2.0,
    )
    assert err.error_az_rad == pytest.approx(-0.1, abs=1e-12)


def test_sigma_phase_does_not_change_error() -> None:
    # A common phase factor on Sigma and Delta cancels via Delta * conj(Sigma).
    sigma = math.cos(0.3) + 1j * math.sin(0.3)  # |sigma| = 1, phase 0.3 rad
    delta = 0.1 * sigma  # in-phase with sigma
    err = monopulse_error_from_channels(
        sigma=sigma,
        delta_az=delta,
        delta_el=0.0 + 0j,
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == pytest.approx(1.4 * 0.1, abs=1e-12)


def test_sum_amplitude_is_sigma_magnitude() -> None:
    err = monopulse_error_from_channels(
        sigma=3.0 + 4.0j,  # |sigma| = 5
        delta_az=0.0 + 0j,
        delta_el=0.0 + 0j,
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.sum_amplitude == pytest.approx(5.0, abs=1e-12)


# Validation


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"slope_az": 0.0}, r"slope_az"),
        ({"slope_az": -1.0}, r"slope_az"),
        ({"slope_el": 0.0}, r"slope_el"),
    ],
)
def test_monopulse_validation_slopes(kwargs: dict, match: str) -> None:
    base = {
        "sigma": 1.0 + 0j,
        "delta_az": 0.0 + 0j,
        "delta_el": 0.0 + 0j,
        "slope_az": 1.4,
        "slope_el": 1.4,
    }
    base.update(kwargs)
    with pytest.raises(ValueError, match=match):
        monopulse_error_from_channels(**base)  # type: ignore[arg-type]


def test_monopulse_rejects_zero_sigma() -> None:
    with pytest.raises(ValueError, match=r"sigma"):
        monopulse_error_from_channels(
            sigma=0.0 + 0j,
            delta_az=0.1 + 0j,
            delta_el=0.0 + 0j,
            slope_az=1.4,
            slope_el=1.4,
        )


def test_monopulse_error_is_frozen() -> None:
    e = MonopulseError(error_az_rad=0.0, error_el_rad=0.0, sum_amplitude=1.0)
    with pytest.raises(Exception):  # noqa: B017
        e.error_az_rad = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------
# monopulse_error_extended — glint coupling
# ---------------------------------------------------------------------


def _single_at(offset: tuple[float, float, float]) -> ExtendedTarget:
    return ExtendedTarget(
        target_id="x",
        scatterers=(Scatterer(offset_body_m=offset, rcs_dbsm=0.0),),
    )


def test_extended_single_scatterer_on_boresight_zero_error() -> None:
    # Scatterer at body origin, target on radar boresight (north, level).
    err = monopulse_error_extended(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=_single_at((0.0, 0.0, 0.0)),
        target_position_enu_m=(0.0, 1000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
        slope_az=1.4,
        slope_el=1.4,
        boresight_az_rad=0.0,  # radar pointing North
        boresight_el_rad=0.0,
    )
    assert err.error_az_rad == pytest.approx(0.0, abs=1e-9)
    assert err.error_el_rad == pytest.approx(0.0, abs=1e-9)


def test_extended_off_boresight_target_yields_error() -> None:
    # Single scatterer 5 deg east of boresight (target north of radar
    # but offset east by ~ 1000*tan(5deg) m).
    east_offset = 1000.0 * math.tan(math.radians(5.0))
    err = monopulse_error_extended(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=_single_at((0.0, 0.0, 0.0)),
        target_position_enu_m=(east_offset, 1000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
        slope_az=1.4,
        slope_el=1.4,
        boresight_az_rad=0.0,
        boresight_el_rad=0.0,
    )
    # Target is east of boresight -> positive azimuth error.
    assert err.error_az_rad > 0.0
    # Magnitude should be near slope * 5_deg_in_rad for this geometry.
    expected_rough = 1.4 * math.radians(5.0)
    assert err.error_az_rad == pytest.approx(expected_rough, rel=0.05)


def test_extended_above_horizon_target_positive_el_error() -> None:
    # Target 100 m up at 1000 m north -> elevation angle ~5.7 deg above horizon.
    err = monopulse_error_extended(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=_single_at((0.0, 0.0, 0.0)),
        target_position_enu_m=(0.0, 1000.0, 100.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
        slope_az=1.4,
        slope_el=1.4,
        boresight_az_rad=0.0,
        boresight_el_rad=0.0,
    )
    assert err.error_el_rad > 0.0


def test_extended_glint_emerges_from_two_scatterers() -> None:
    # Two scatterers symmetric about target East/West, far field.
    # On boresight -> error ideally zero; with glint it's a tiny
    # non-zero number that depends on phase coincidence. We don't
    # constrain magnitude, just that the function runs and the result
    # has finite (small) error consistent with glint.
    target = ExtendedTarget(
        target_id="x",
        scatterers=(
            Scatterer(offset_body_m=(0.0, 5.0, 0.0), rcs_dbsm=0.0),
            Scatterer(offset_body_m=(0.0, -5.0, 0.0), rcs_dbsm=0.0),
        ),
    )
    err = monopulse_error_extended(
        radar_position_enu_m=(0.0, 0.0, 0.0),
        target=target,
        target_position_enu_m=(0.0, 100_000.0, 0.0),
        target_attitude_rad=(0.0, 0.0, 0.0),
        frequency_hz=9.4e9,
        slope_az=1.4,
        slope_el=1.4,
        boresight_az_rad=0.0,
        boresight_el_rad=0.0,
    )
    # Symmetric pair on boresight -> error tiny but finite (glint).
    assert abs(err.error_az_rad) < 1e-3
    assert abs(err.error_el_rad) < 1e-3


def test_extended_rejects_zero_frequency() -> None:
    with pytest.raises(ValueError, match=r"frequency_hz"):
        monopulse_error_extended(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=_single_at((0.0, 0.0, 0.0)),
            target_position_enu_m=(0.0, 100.0, 0.0),
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=0.0,
            slope_az=1.4,
            slope_el=1.4,
            boresight_az_rad=0.0,
            boresight_el_rad=0.0,
        )


def test_extended_rejects_scatterer_at_radar() -> None:
    with pytest.raises(ValueError, match=r"range"):
        monopulse_error_extended(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=_single_at((0.0, 0.0, 0.0)),
            target_position_enu_m=(0.0, 0.0, 0.0),  # target at radar
            target_attitude_rad=(0.0, 0.0, 0.0),
            frequency_hz=9.4e9,
            slope_az=1.4,
            slope_el=1.4,
            boresight_az_rad=0.0,
            boresight_el_rad=0.0,
        )
