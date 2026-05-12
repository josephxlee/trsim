"""ISA atmosphere regression vs golden dataset (Phase 5.4 + 5.4b)."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.atmosphere import (
    ISA_R_GAS_DRY_AIR_J_PER_KGK,
    AtmosphereState,
    isa_density,
    isa_pressure,
    isa_temperature,
    rain_attenuation_dbpkm,
)

_DATASET = GoldenDataset.load(Path(__file__).parent / "golden" / "atmosphere_isa.json")
_RTOL = _DATASET.meta.rtol


def _default_atm() -> AtmosphereState:
    return AtmosphereState()


@pytest.mark.parametrize(
    "case_id",
    ["temperature_sea_level", "temperature_1km", "temperature_tropopause_11km"],
)
def test_isa_temperature_matches_golden(case_id: str) -> None:
    s = _DATASET.case(case_id)
    t = isa_temperature(s.inputs["altitude_m"], _default_atm())
    assert t == pytest.approx(s.expected["temperature_k"], rel=_RTOL)


@pytest.mark.parametrize("case_id", ["pressure_sea_level", "pressure_1km", "pressure_5km"])
def test_isa_pressure_matches_golden(case_id: str) -> None:
    s = _DATASET.case(case_id)
    p = isa_pressure(s.inputs["altitude_m"], _default_atm())
    assert p == pytest.approx(s.expected["pressure_pa"], rel=_RTOL)


@pytest.mark.parametrize("case_id", ["density_sea_level", "density_1km"])
def test_isa_density_matches_golden(case_id: str) -> None:
    s = _DATASET.case(case_id)
    rho = isa_density(s.inputs["altitude_m"], _default_atm())
    assert rho == pytest.approx(s.expected["density_kg_m3"], rel=_RTOL)


def test_rain_attenuation_matches_golden() -> None:
    s = _DATASET.case("rain_10GHz_4mmh")
    a = rain_attenuation_dbpkm(
        frequency_ghz=s.inputs["frequency_ghz"],
        rain_rate_mmh=s.inputs["rain_rate_mmh"],
    )
    assert a == pytest.approx(s.expected["rain_attenuation_dbpkm"], rel=_RTOL)


def test_temperature_lapse_is_linear_in_troposphere() -> None:
    """Two altitudes below 11 km should differ by lapse_rate * dh."""
    atm = _default_atm()
    t_a = isa_temperature(2000.0, atm)
    t_b = isa_temperature(3000.0, atm)
    assert (t_a - t_b) == pytest.approx(6.5, rel=_RTOL)  # 0.0065 K/m * 1000 m


def test_pressure_above_tropopause_clamps_to_11km_value() -> None:
    atm = _default_atm()
    p_11 = isa_pressure(11000.0, atm)
    p_15 = isa_pressure(15000.0, atm)
    assert p_15 == pytest.approx(p_11, rel=_RTOL)


def test_rain_attenuation_zero_rain_returns_zero() -> None:
    assert rain_attenuation_dbpkm(frequency_ghz=10.0, rain_rate_mmh=0.0) == 0.0


def test_atmosphere_state_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match=r"temperature"):
        AtmosphereState(sea_level_temperature_k=0.0)
    with pytest.raises(ValueError, match=r"pressure"):
        AtmosphereState(sea_level_pressure_hpa=-1.0)
    with pytest.raises(ValueError, match=r"rain_rate"):
        AtmosphereState(rain_rate_mmh=-1.0)
    with pytest.raises(ValueError, match=r"visibility"):
        AtmosphereState(visibility_km=0.0)


# ---------------------------------------------------------------------
# 5.4b — stratosphere clamps + ideal-gas-law + rain monotonicity
# ---------------------------------------------------------------------


def test_temperature_above_tropopause_clamps_to_11km_value() -> None:
    """ISA in this implementation holds 216.65 K isothermally above
    the tropopause. Locks the stratosphere clamp for 15 km.
    """
    s = _DATASET.case("temperature_stratosphere_15km")
    t = isa_temperature(s.inputs["altitude_m"], _default_atm())
    assert t == pytest.approx(s.expected["temperature_k"], rel=_RTOL)
    t_11 = isa_temperature(11000.0, _default_atm())
    assert t == pytest.approx(t_11, rel=_RTOL)


def test_density_above_tropopause_clamps_to_11km_value() -> None:
    """Density clamp mirrors the temperature clamp: rho(15 km) =
    rho(11 km) in this MVP model.
    """
    s = _DATASET.case("density_stratosphere_15km")
    rho = isa_density(s.inputs["altitude_m"], _default_atm())
    assert rho == pytest.approx(s.expected["density_kg_m3"], rel=_RTOL)
    rho_11 = isa_density(11000.0, _default_atm())
    assert rho == pytest.approx(rho_11, rel=_RTOL)


def test_ideal_gas_law_holds_at_sea_level() -> None:
    """rho = P / (R T) using the module's R constant — bit-for-bit
    consistency of the three ISA helpers at sea level.
    """
    atm = _default_atm()
    rho = isa_density(0.0, atm)
    p = isa_pressure(0.0, atm)
    t = isa_temperature(0.0, atm)
    assert rho == pytest.approx(p / (ISA_R_GAS_DRY_AIR_J_PER_KGK * t), rel=_RTOL)


def test_ideal_gas_law_holds_at_1km() -> None:
    """Same consistency check at 1 km — pins the relationship inside
    the troposphere where T and P both vary.
    """
    atm = _default_atm()
    rho = isa_density(1000.0, atm)
    p = isa_pressure(1000.0, atm)
    t = isa_temperature(1000.0, atm)
    assert rho == pytest.approx(p / (ISA_R_GAS_DRY_AIR_J_PER_KGK * t), rel=_RTOL)


def test_rain_attenuation_30ghz_10mmh_matches_golden() -> None:
    """Higher-frequency / heavier-rain golden lock — 30 GHz / 10 mm/h
    sits in the realistic Ku/Ka heavy-rain regime where attenuation
    is no longer negligible (~1.9 dB/km).
    """
    s = _DATASET.case("rain_30GHz_10mmh")
    a = rain_attenuation_dbpkm(
        frequency_ghz=s.inputs["frequency_ghz"],
        rain_rate_mmh=s.inputs["rain_rate_mmh"],
    )
    assert a == pytest.approx(s.expected["rain_attenuation_dbpkm"], rel=_RTOL)


def test_rain_attenuation_monotonic_in_frequency_above_x_band() -> None:
    """At a fixed rain rate, attenuation grows strictly with frequency
    once we are above the X-band floor (the MVP model holds a tiny
    constant ~0.01 dB/km below ~10 GHz, so strict monotonicity only
    kicks in from 10 GHz upward).
    """
    rate = 10.0
    freqs_ghz = (10.0, 14.0, 20.0, 30.0)
    a_seq = [rain_attenuation_dbpkm(frequency_ghz=f, rain_rate_mmh=rate) for f in freqs_ghz]
    for a_lo, a_hi in pairwise(a_seq):
        assert a_lo < a_hi, f"non-monotonic: {a_seq}"


def test_rain_attenuation_monotonic_in_rate_at_fixed_frequency() -> None:
    """At fixed frequency, attenuation grows with rain rate. Locks the
    power-law direction of the ITU-R k * R^alpha form. Use <= for the
    0 -> 1 mm/h step because the model may clamp the very-low-rate
    floor, then strict < from 1 mm/h upward.
    """
    freq = 10.0
    rates = (0.0, 1.0, 4.0, 10.0, 50.0)
    a_seq = [rain_attenuation_dbpkm(frequency_ghz=freq, rain_rate_mmh=r) for r in rates]
    assert a_seq[0] <= a_seq[1]
    for a_lo, a_hi in pairwise(a_seq[1:]):
        assert a_lo < a_hi, f"non-monotonic above 1 mm/h: {a_seq}"
