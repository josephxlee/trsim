"""Unit tests for workbench.physics.atmosphere (Phase 2.5)."""

from __future__ import annotations

import pytest

from workbench.physics.atmosphere import (
    ISA_SEA_LEVEL_PRESSURE_HPA,
    ISA_SEA_LEVEL_TEMPERATURE_K,
    AtmosphereState,
    isa_density,
    isa_pressure,
    isa_temperature,
    rain_attenuation_dbpkm,
    two_way_loss_db,
)

# ---------------------------------------------------------------------
# AtmosphereState
# ---------------------------------------------------------------------


def test_atmosphere_state_defaults() -> None:
    atm = AtmosphereState()
    assert atm.visibility_km == 30.0
    assert atm.sky_condition == "clear"
    assert atm.sea_level_pressure_hpa == ISA_SEA_LEVEL_PRESSURE_HPA
    assert atm.sea_level_temperature_k == ISA_SEA_LEVEL_TEMPERATURE_K
    assert atm.rain_rate_mmh == 0.0
    assert atm.refractivity_n == 313.0
    assert atm.ducting_enabled is False


def test_atmosphere_state_is_frozen() -> None:
    atm = AtmosphereState()
    with pytest.raises(AttributeError):
        atm.rain_rate_mmh = 5.0  # type: ignore[misc]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"sea_level_temperature_k": 0.0}, r"temperature"),
        ({"sea_level_temperature_k": -1.0}, r"temperature"),
        ({"sea_level_pressure_hpa": 0.0}, r"pressure"),
        ({"sea_level_pressure_hpa": -100.0}, r"pressure"),
        ({"rain_rate_mmh": -1.0}, r"rain_rate_mmh"),
        ({"visibility_km": 0.0}, r"visibility_km"),
    ],
)
def test_atmosphere_state_validation(kwargs: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        AtmosphereState(**kwargs)


# ---------------------------------------------------------------------
# ISA — temperature / pressure / density
# ---------------------------------------------------------------------


def test_isa_temperature_at_sea_level() -> None:
    atm = AtmosphereState()
    assert isa_temperature(0.0, atm) == pytest.approx(288.15, abs=1e-9)


def test_isa_temperature_at_1000m() -> None:
    atm = AtmosphereState()
    # T = 288.15 - 0.0065 * 1000 = 281.65
    assert isa_temperature(1000.0, atm) == pytest.approx(281.65, abs=1e-9)


def test_isa_temperature_clamps_above_tropopause() -> None:
    atm = AtmosphereState()
    # at 11 km
    t_11km = isa_temperature(11_000.0, atm)
    # at 15 km should equal 11 km (clamp)
    t_15km = isa_temperature(15_000.0, atm)
    assert t_11km == pytest.approx(t_15km, abs=1e-9)


def test_isa_pressure_at_sea_level() -> None:
    atm = AtmosphereState()
    # 1013.25 hPa = 101325 Pa
    assert isa_pressure(0.0, atm) == pytest.approx(101325.0, rel=1e-9)


def test_isa_pressure_at_1000m_python_exact() -> None:
    atm = AtmosphereState()
    # Python-exact reference (computed via the same formula):
    # exponent = 9.80665 / (287.058 * 0.0065) = 5.25578588...
    # T1 = 288.15 - 0.0065*1000 = 281.65
    # P1 = 101325 * (281.65/288.15)^5.25578588 = 89874.7555 Pa
    p = isa_pressure(1000.0, atm)
    assert p == pytest.approx(89874.7555, abs=1e-3)


def test_isa_density_at_sea_level() -> None:
    atm = AtmosphereState()
    # 101325 / (287.058 * 288.15) = 1.22500088... kg/m^3
    rho = isa_density(0.0, atm)
    assert rho == pytest.approx(1.225, abs=1e-3)


def test_isa_density_decreases_with_altitude() -> None:
    atm = AtmosphereState()
    rho_0 = isa_density(0.0, atm)
    rho_1km = isa_density(1000.0, atm)
    rho_5km = isa_density(5000.0, atm)
    rho_10km = isa_density(10_000.0, atm)
    assert rho_0 > rho_1km > rho_5km > rho_10km > 0.0


def test_isa_clamps_above_tropopause() -> None:
    atm = AtmosphereState()
    rho_11km = isa_density(11_000.0, atm)
    rho_15km = isa_density(15_000.0, atm)
    assert rho_11km == pytest.approx(rho_15km, rel=1e-9)


# ---------------------------------------------------------------------
# Rain attenuation (ITU-R P.838 simplified)
# ---------------------------------------------------------------------


def test_rain_attenuation_zero_rain() -> None:
    assert rain_attenuation_dbpkm(9.4, 0.0) == 0.0


def test_rain_attenuation_xband_9p4_ghz_10_mmh() -> None:
    # k = 0.0117 * 9.4 - 0.0734 = 0.036580
    # alpha = 1.097
    # L = 0.036580 * 10^1.097 = 0.457345 dB/km (Python exact)
    actual = rain_attenuation_dbpkm(9.4, 10.0)
    assert actual == pytest.approx(0.457345, abs=1e-5)


def test_rain_attenuation_below_xband_uses_simplified() -> None:
    # frequency < 8 GHz: k=0.001, alpha=1.0 -> 0.001 * R
    assert rain_attenuation_dbpkm(5.0, 10.0) == pytest.approx(0.01, abs=1e-9)


def test_rain_attenuation_above_xband_uses_simplified() -> None:
    # frequency > 12 GHz: k = 0.05 * (f/10), alpha=1.1
    # at f=20: k = 0.10, L = 0.10 * 10^1.1 = 0.10 * 12.589 = 1.2589
    actual = rain_attenuation_dbpkm(20.0, 10.0)
    assert actual == pytest.approx(0.10 * 10.0**1.1, rel=1e-9)


@pytest.mark.parametrize(
    ("freq_ghz", "rain_mmh"),
    [(0.0, 5.0), (-1.0, 5.0)],
)
def test_rain_attenuation_rejects_bad_frequency(freq_ghz: float, rain_mmh: float) -> None:
    with pytest.raises(ValueError, match=r"frequency_ghz"):
        rain_attenuation_dbpkm(freq_ghz, rain_mmh)


def test_rain_attenuation_rejects_negative_rain() -> None:
    with pytest.raises(ValueError, match=r"rain_rate_mmh"):
        rain_attenuation_dbpkm(9.4, -1.0)


# ---------------------------------------------------------------------
# Two-way loss
# ---------------------------------------------------------------------


def test_two_way_loss_no_rain() -> None:
    atm = AtmosphereState(rain_rate_mmh=0.0)
    assert two_way_loss_db(100_000.0, atm, 9.4e9) == 0.0


def test_two_way_loss_xband_100km_10_mmh() -> None:
    atm = AtmosphereState(rain_rate_mmh=10.0)
    # specific = 0.457345 dB/km, range_km=100, two-way = 2 * 100 * 0.457345 = 91.468951
    actual = two_way_loss_db(100_000.0, atm, 9.4e9)
    assert actual == pytest.approx(91.468951, abs=1e-4)


def test_two_way_loss_zero_range() -> None:
    atm = AtmosphereState(rain_rate_mmh=10.0)
    assert two_way_loss_db(0.0, atm, 9.4e9) == 0.0


def test_two_way_loss_rejects_negative_range() -> None:
    atm = AtmosphereState()
    with pytest.raises(ValueError, match=r"target_range_m"):
        two_way_loss_db(-1.0, atm, 9.4e9)


def test_two_way_loss_rejects_zero_frequency() -> None:
    atm = AtmosphereState()
    with pytest.raises(ValueError, match=r"frequency_hz"):
        two_way_loss_db(1000.0, atm, 0.0)
