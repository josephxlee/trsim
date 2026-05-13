"""Parabolic antenna regression vs golden dataset (Phase 5.3)."""

from __future__ import annotations

from itertools import pairwise
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


# ---------- 5.3b — Scaling invariants beyond the golden anchors ----------


def test_beamwidth_inverse_linear_in_frequency() -> None:
    """BW ~ 70 lambda / D = 70 c / (f D). Doubling f halves the
    beamwidth (mirror of the 2x-D test, but in the frequency axis).
    """
    base = parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=9.5e9)
    doubled_f = parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=19.0e9)
    assert doubled_f == pytest.approx(base / 2.0, rel=_RTOL)


def test_peak_gain_doubling_diameter_adds_six_db() -> None:
    """G_peak ~ eff * (pi D / lambda)^2. Doubling D multiplies linear
    gain by 4 -> +6 dB in dBi. Lock the D^2 aperture scaling.
    """
    g_small = parabolic_peak_gain_dbi(diameter_m=0.6, frequency_hz=9.5e9, efficiency=0.6)
    g_big = parabolic_peak_gain_dbi(diameter_m=1.2, frequency_hz=9.5e9, efficiency=0.6)
    # 10 log10(4) = 6.020599... dB
    assert (g_big - g_small) == pytest.approx(6.020599913279624, rel=_RTOL)


def test_peak_gain_doubling_efficiency_adds_three_db() -> None:
    """Linear gain scales linearly with efficiency, so doubling eff
    adds 10 log10(2) = 3.010 dB. Used to validate the eff term in
    isolation from the aperture term.
    """
    g_half = parabolic_peak_gain_dbi(diameter_m=0.6, frequency_hz=9.5e9, efficiency=0.3)
    g_full = parabolic_peak_gain_dbi(diameter_m=0.6, frequency_hz=9.5e9, efficiency=0.6)
    # 10 log10(2) = 3.010299956... dB
    assert (g_full - g_half) == pytest.approx(3.010299956639812, rel=_RTOL)


def test_pattern_radially_symmetric_in_theta_and_phi() -> None:
    """The MVP pattern depends only on the radial off-axis angle
    sqrt(theta^2 + phi^2). pattern(1.0, 0) must equal pattern(0, 1.0)
    to numerical precision.
    """
    bw = 5.0
    p_theta_only = parabolic_beam_pattern(theta_deg=1.0, phi_deg=0.0, beamwidth_3db_deg=bw)
    p_phi_only = parabolic_beam_pattern(theta_deg=0.0, phi_deg=1.0, beamwidth_3db_deg=bw)
    assert p_theta_only == pytest.approx(p_phi_only, rel=_RTOL)


def test_pattern_decreases_monotonically_off_boresight() -> None:
    """Normalised power must decrease as the off-axis angle grows
    within the main lobe. Sweep 0 -> 0.25 BW -> 0.5 BW -> 0.75 BW
    -> 1.0 BW and verify monotone descent.
    """
    bw = 5.0
    offsets = (0.0, 0.25, 0.5, 0.75, 1.0)
    values = [
        parabolic_beam_pattern(theta_deg=k * bw, phi_deg=0.0, beamwidth_3db_deg=bw) for k in offsets
    ]
    for hi, lo in pairwise(values):
        assert hi > lo, f"non-monotonic: {values}"
