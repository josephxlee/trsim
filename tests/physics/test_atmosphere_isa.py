"""ISA atmosphere regression vs golden dataset (Phase 5.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.atmosphere import (
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
