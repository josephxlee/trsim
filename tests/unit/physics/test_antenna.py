"""Unit tests for workbench.physics.antenna (Phase 2.6 — parabolic only)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.antenna import (
    AntennaType,
    ParabolicAntenna,
    parabolic_beam_pattern,
    parabolic_beamwidth_3db_deg,
    parabolic_peak_gain_dbi,
)


# ---------------------------------------------------------------------
# AntennaType enum
# ---------------------------------------------------------------------


def test_antenna_type_enum_values() -> None:
    assert AntennaType.PARABOLIC.value == "parabolic"
    assert AntennaType.PLANAR_ARRAY.value == "planar_array"


# ---------------------------------------------------------------------
# ParabolicAntenna
# ---------------------------------------------------------------------


def test_parabolic_antenna_defaults() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    assert ant.efficiency == 0.6


def test_parabolic_wavelength() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    # c/f = 299792458 / 9.4e9 = 0.0318928147... m (Python exact)
    assert ant.wavelength_m == pytest.approx(0.0318928147, abs=1e-10)


def test_parabolic_beamwidth_3db_deg_property() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    # 70 * lambda/D = 70 * 0.0318928147 / 1.0 = 2.232497 deg (Python exact)
    assert ant.beamwidth_3db_deg == pytest.approx(2.232497, abs=1e-5)


def test_parabolic_peak_gain_dbi_property() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9, efficiency=0.6)
    # ratio = pi*D/lambda = pi/0.0318928147 = 98.5132
    # G_lin = 0.6 * 98.5132^2 = 5824.59
    # 10*log10 = 37.6507 dBi (Python exact)
    assert ant.peak_gain_dbi == pytest.approx(37.6507, abs=1e-3)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"diameter_m": 0.0, "frequency_hz": 9.4e9}, r"diameter_m"),
        ({"diameter_m": -1.0, "frequency_hz": 9.4e9}, r"diameter_m"),
        ({"diameter_m": 1.0, "frequency_hz": 0.0}, r"frequency_hz"),
        ({"diameter_m": 1.0, "frequency_hz": -1.0}, r"frequency_hz"),
        ({"diameter_m": 1.0, "frequency_hz": 9.4e9, "efficiency": 0.0}, r"efficiency"),
        ({"diameter_m": 1.0, "frequency_hz": 9.4e9, "efficiency": 1.5}, r"efficiency"),
        ({"diameter_m": 1.0, "frequency_hz": 9.4e9, "efficiency": -0.1}, r"efficiency"),
    ],
)
def test_parabolic_antenna_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        ParabolicAntenna(**kwargs)


def test_parabolic_antenna_is_frozen() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    with pytest.raises(AttributeError):
        ant.diameter_m = 2.0  # type: ignore[misc]


# ---------------------------------------------------------------------
# beam_pattern
# ---------------------------------------------------------------------


def test_beam_pattern_at_boresight_is_one() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    assert ant.beam_pattern(0.0, 0.0) == 1.0


def test_beam_pattern_at_half_3db_is_half() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    bw = ant.beamwidth_3db_deg
    # one-sided 3-dB: theta = bw/2 -> 0.5
    p = ant.beam_pattern(bw / 2.0, 0.0)
    assert p == pytest.approx(0.5, abs=1e-6)


def test_beam_pattern_circular_symmetry() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    bw = ant.beamwidth_3db_deg
    p_az = ant.beam_pattern(bw / 2.0, 0.0)
    p_el = ant.beam_pattern(0.0, bw / 2.0)
    assert p_az == pytest.approx(p_el, abs=1e-9)


def test_beam_pattern_diagonal_offset() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    bw = ant.beamwidth_3db_deg
    # equal theta and phi components: total offset = sqrt(2) * x.
    # so x = (bw/2) / sqrt(2) gives total offset = bw/2 -> 0.5
    half_diag = (bw / 2.0) / math.sqrt(2.0)
    assert ant.beam_pattern(half_diag, half_diag) == pytest.approx(0.5, abs=1e-6)


def test_beam_pattern_decays_far_off_axis() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    bw = ant.beamwidth_3db_deg
    # at 5 * bw, well into side lobes — should be small.
    p = ant.beam_pattern(5.0 * bw, 0.0)
    assert 0.0 <= p < 0.05


def test_beam_pattern_symmetry_across_zero() -> None:
    ant = ParabolicAntenna(diameter_m=1.0, frequency_hz=9.4e9)
    p_pos = ant.beam_pattern(1.0, 0.0)
    p_neg = ant.beam_pattern(-1.0, 0.0)
    assert p_pos == pytest.approx(p_neg, abs=1e-12)


# ---------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------


def test_parabolic_beamwidth_function_matches_property() -> None:
    bw = parabolic_beamwidth_3db_deg(diameter_m=1.0, frequency_hz=9.4e9)
    assert bw == pytest.approx(2.232497, abs=1e-5)


def test_parabolic_peak_gain_function_matches_property() -> None:
    g = parabolic_peak_gain_dbi(diameter_m=1.0, frequency_hz=9.4e9, efficiency=0.6)
    assert g == pytest.approx(37.6507, abs=1e-3)


def test_parabolic_beam_pattern_function_at_boresight() -> None:
    assert parabolic_beam_pattern(0.0, 0.0, beamwidth_3db_deg=2.232497) == 1.0


def test_parabolic_beam_pattern_function_rejects_zero_beamwidth() -> None:
    with pytest.raises(ValueError, match=r"beamwidth_3db_deg"):
        parabolic_beam_pattern(0.0, 0.0, beamwidth_3db_deg=0.0)


def test_parabolic_peak_gain_function_rejects_bad_efficiency() -> None:
    with pytest.raises(ValueError, match=r"efficiency"):
        parabolic_peak_gain_dbi(diameter_m=1.0, frequency_hz=9.4e9, efficiency=2.0)
