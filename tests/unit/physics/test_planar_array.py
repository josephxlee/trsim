"""Unit tests for workbench.physics.planar_array (Phase 2.6b)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.antenna import AntennaType
from workbench.physics.planar_array import (
    C_LIGHT_M_S,
    PlanarArrayAntenna,
    element_power,
)


def _array(**overrides: object) -> PlanarArrayAntenna:
    base: dict[str, object] = {
        "n_elements_az": 8,
        "n_elements_el": 8,
        "frequency_hz": 9.4e9,
        "spacing_m": C_LIGHT_M_S / 9.4e9 / 2.0,  # half-wavelength
    }
    base.update(overrides)
    return PlanarArrayAntenna(**base)  # type: ignore[arg-type]


# --- dataclass / properties ------------------------------------------


def test_planar_array_type_tag() -> None:
    assert _array().antenna_type == AntennaType.PLANAR_ARRAY


def test_planar_array_default_element_pattern_cos() -> None:
    a = _array()
    assert a.element_pattern == "cos"


def test_planar_array_wavelength() -> None:
    a = _array()
    assert a.wavelength_m == pytest.approx(C_LIGHT_M_S / 9.4e9, abs=1e-12)


def test_aperture_lengths() -> None:
    spacing = 0.05
    a = _array(n_elements_az=10, n_elements_el=4, spacing_m=spacing)
    assert a.aperture_length_az_m == pytest.approx(9 * spacing, abs=1e-12)
    assert a.aperture_length_el_m == pytest.approx(3 * spacing, abs=1e-12)


def test_3db_beamwidth_known_formula() -> None:
    # 8 elements at lambda/2, lambda = c/9.4 GHz = 0.0319 m.
    # L = 7 * 0.0159464 = 0.111625 m. theta_3dB = 0.886 * lambda / L
    a = _array()
    expected_deg = math.degrees(0.886 * a.wavelength_m / a.aperture_length_az_m)
    assert a.beamwidth_3db_az_deg == pytest.approx(expected_deg, abs=1e-9)
    assert a.beamwidth_3db_el_deg == pytest.approx(expected_deg, abs=1e-9)


# --- Validation ------------------------------------------------------


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"n_elements_az": 1}, r"n_elements_az"),
        ({"n_elements_el": 0}, r"n_elements_el"),
        ({"frequency_hz": 0.0}, r"frequency_hz"),
        ({"spacing_m": -0.1}, r"spacing_m"),
        ({"element_pattern": "garbage"}, r"element_pattern"),
    ],
)
def test_planar_array_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _array(**override)


# --- Array factor ----------------------------------------------------


def test_array_factor_boresight_is_one() -> None:
    a = _array()
    assert a.array_factor_magnitude(0.0, 0.0) == pytest.approx(1.0, abs=1e-12)


def test_array_factor_first_null_az() -> None:
    # For uniform N-element array spaced d, first null occurs where
    # N * psi/2 = pi -> psi = 2 pi / N -> sin(theta) = lambda / (N d)
    a = _array(n_elements_az=8, n_elements_el=2, spacing_m=C_LIGHT_M_S / 9.4e9 / 2.0)
    null_sin_theta = 1.0 / 8.0 * 2.0  # 2 pi / N divided by k*d normalization
    # k*d = pi for half-wavelength spacing. psi = pi * sin(theta).
    # First null at psi = 2 pi / N -> sin(theta) = 2 / N.
    null_sin = 2.0 / 8.0
    null_theta_deg = math.degrees(math.asin(null_sin))
    af = a.array_factor_magnitude(null_theta_deg, 0.0)
    assert af == pytest.approx(0.0, abs=1e-9)
    _ = null_sin_theta  # unused


def test_array_factor_decays_off_axis() -> None:
    a = _array()
    af_on = a.array_factor_magnitude(0.0, 0.0)
    af_off = a.array_factor_magnitude(5.0, 0.0)
    assert af_off < af_on
    assert af_off >= 0.0


def test_beam_pattern_boresight_is_one_isotropic() -> None:
    a = _array(element_pattern="isotropic")
    assert a.beam_pattern(0.0, 0.0) == pytest.approx(1.0, abs=1e-12)


def test_beam_pattern_with_cos_element() -> None:
    # cos element multiplies the AF^2 by cos(alpha). At boresight cos=1.
    a = _array(element_pattern="cos")
    assert a.beam_pattern(0.0, 0.0) == pytest.approx(1.0, abs=1e-12)


def test_beam_pattern_decays_off_axis() -> None:
    a = _array()
    p_on = a.beam_pattern(0.0, 0.0)
    p_off = a.beam_pattern(10.0, 0.0)
    assert 0.0 <= p_off <= p_on


# --- element_power module-level helper -------------------------------


def test_element_power_isotropic_returns_one() -> None:
    assert element_power(45.0, 30.0, "isotropic") == 1.0


def test_element_power_cos_at_boresight() -> None:
    assert element_power(0.0, 0.0, "cos") == pytest.approx(1.0, abs=1e-12)


def test_element_power_cos_at_60deg() -> None:
    # cos(60 deg) = 0.5 — alpha = 60 in azimuth alone.
    assert element_power(60.0, 0.0, "cos") == pytest.approx(0.5, abs=1e-12)


def test_element_power_cos_at_90deg_is_zero() -> None:
    assert element_power(90.0, 0.0, "cos") == 0.0


def test_element_power_cos_back_hemisphere_zero() -> None:
    assert element_power(120.0, 0.0, "cos") == 0.0


def test_element_power_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match=r"element_pattern"):
        element_power(0.0, 0.0, "garbage")
