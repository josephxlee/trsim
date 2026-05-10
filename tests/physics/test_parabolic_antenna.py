"""Parabolic antenna regression vs golden dataset (Phase 5.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.antenna import (
    parabolic_beam_pattern,
    parabolic_beamwidth_3db_deg,
    parabolic_peak_gain_dbi,
)

_DATASET = GoldenDataset.load(Path(__file__).parent / "golden" / "parabolic_antenna.json")
_RTOL = _DATASET.meta.rtol


def test_beamwidth_06m_9_5_ghz_matches_golden() -> None:
    s = _DATASET.case("beamwidth_06m_9_5GHz")
    bw = parabolic_beamwidth_3db_deg(
        diameter_m=s.inputs["diameter_m"], frequency_hz=s.inputs["frequency_hz"]
    )
    assert bw == pytest.approx(s.expected["beamwidth_3db_deg"], rel=_RTOL)


def test_beamwidth_doubling_diameter_halves_beamwidth() -> None:
    """Confirms the 70 lambda/D scaling: 2x diameter -> 1/2 beamwidth."""
    big = parabolic_beamwidth_3db_deg(diameter_m=1.2, frequency_hz=9.5e9)
    small = parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=9.5e9)
    assert big == pytest.approx(small / 2.0, rel=_RTOL)


def test_beamwidth_matches_golden_12m_9_5_ghz() -> None:
    s = _DATASET.case("beamwidth_12m_9_5GHz")
    bw = parabolic_beamwidth_3db_deg(
        diameter_m=s.inputs["diameter_m"], frequency_hz=s.inputs["frequency_hz"]
    )
    assert bw == pytest.approx(s.expected["beamwidth_3db_deg"], rel=_RTOL)


def test_peak_gain_06m_9_5_ghz_matches_golden() -> None:
    s = _DATASET.case("peak_gain_06m_9_5GHz_eff_06")
    g = parabolic_peak_gain_dbi(
        diameter_m=s.inputs["diameter_m"],
        frequency_hz=s.inputs["frequency_hz"],
        efficiency=s.inputs["efficiency"],
    )
    assert g == pytest.approx(s.expected["peak_gain_dbi"], rel=_RTOL)


def test_pattern_at_boresight_is_unity() -> None:
    s = _DATASET.case("pattern_at_boresight")
    p = parabolic_beam_pattern(
        theta_deg=s.inputs["theta_deg"],
        phi_deg=s.inputs["phi_deg"],
        beamwidth_3db_deg=s.inputs["beamwidth_3db_deg"],
    )
    assert p == pytest.approx(s.expected["normalised_power"], abs=1e-12)


def test_pattern_at_half_bw_is_minus_3db() -> None:
    s = _DATASET.case("pattern_at_half_bw")
    p = parabolic_beam_pattern(
        theta_deg=s.inputs["theta_deg"],
        phi_deg=s.inputs["phi_deg"],
        beamwidth_3db_deg=s.inputs["beamwidth_3db_deg"],
    )
    # 3-dB definition: numerical inverse may carry ~1e-9 residual.
    assert p == pytest.approx(s.expected["normalised_power"], abs=1e-7)


@pytest.mark.parametrize("bad_diameter", [0.0, -1.0, -0.001])
def test_beamwidth_rejects_non_positive_diameter(bad_diameter: float) -> None:
    with pytest.raises(ValueError, match=r"diameter_m"):
        parabolic_beamwidth_3db_deg(diameter_m=bad_diameter, frequency_hz=9.5e9)


@pytest.mark.parametrize("bad_freq", [0.0, -1.0])
def test_beamwidth_rejects_non_positive_frequency(bad_freq: float) -> None:
    with pytest.raises(ValueError, match=r"frequency_hz"):
        parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=bad_freq)
