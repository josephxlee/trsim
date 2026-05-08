"""Atmosphere model — ISA standard atmosphere + ITU-R P.838 rain attenuation.

Phase 2.5 (plan/15 § 15.3 + § 15.5). Three influences on the simulation
(per plan/15 § 15.1):

- **Visual**: 3D Scene fog / sky color (Phase 4 UI; Map Editor only).
- **Dynamics**: air density drives lift / drag (Phase 2.4 dynamics).
- **Propagation**: rain attenuation drives radar two-way path loss.

Scope (MVP, plan/15 § 15.2.2):

- ISA troposphere (0-11 km), with clamp above 11 km.
- ITU-R P.838 specific rain attenuation (simplified — X-band 8-12 GHz
  is the validated band; below/above use coarser linear fits).
- Two-way path loss = 2 x (range_km * specific_attenuation).

Out of MVP (Phase 6+): ducting, wind, time-varying atmosphere.

References:

- ICAO 1976 ISA / NOAA reference atmosphere — troposphere model.
- ITU-R P.838-3 — Specific attenuation model for rain in radio
  propagation prediction.
- plan/15 §§ 15.3, 15.5.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

# --- ISA standard-atmosphere constants -------------------------------

ISA_LAPSE_RATE_K_PER_M: Final[float] = 0.0065
"""Standard temperature lapse rate in the troposphere [K/m]."""

ISA_R_GAS_DRY_AIR_J_PER_KGK: Final[float] = 287.058
"""Specific gas constant of dry air [J / (kg.K)]."""

ISA_G_M_PER_S2: Final[float] = 9.80665
"""Standard gravitational acceleration [m/s^2]."""

ISA_TROPOPAUSE_M: Final[float] = 11_000.0
"""Troposphere upper boundary [m]. Above this, the MVP clamps to 11 km."""

ISA_SEA_LEVEL_TEMPERATURE_K: Final[float] = 288.15
"""Default sea-level temperature [K] (15 deg C)."""

ISA_SEA_LEVEL_PRESSURE_HPA: Final[float] = 1013.25
"""Default sea-level pressure [hPa]."""


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Map-level atmosphere parameters (plan/15 § 15.2.1).

    Held by a Scenario; one per simulation run (time-varying is Phase 6+).

    Attributes:
        visibility_km: Horizontal visibility [km]. Drives fog density in
            the 3D Scene view (Phase 4); not used by physics.
        sky_condition: One of ``"clear"``, ``"overcast"``, ``"fog"``,
            ``"rain"``, ``"storm"``. Visual only.
        sea_level_pressure_hpa: ISA reference pressure [hPa]. Default
            1013.25.
        sea_level_temperature_k: ISA reference temperature [K]. Default
            288.15 (15 deg C).
        rain_rate_mmh: Rain rate [mm/h]. ``0`` disables rain attenuation.
        refractivity_n: Surface refractivity [N-units]. Default 313.0.
            Used by ducting models (Phase 6+); MVP ignores.
        ducting_enabled: Phase 6+ ducting toggle.
    """

    visibility_km: float = 30.0
    sky_condition: str = "clear"
    sea_level_pressure_hpa: float = ISA_SEA_LEVEL_PRESSURE_HPA
    sea_level_temperature_k: float = ISA_SEA_LEVEL_TEMPERATURE_K
    rain_rate_mmh: float = 0.0
    refractivity_n: float = 313.0
    ducting_enabled: bool = False

    def __post_init__(self) -> None:
        if self.sea_level_temperature_k <= 0.0:
            msg = f"sea_level_temperature_k must be > 0 K, got {self.sea_level_temperature_k}"
            raise ValueError(msg)
        if self.sea_level_pressure_hpa <= 0.0:
            msg = f"sea_level_pressure_hpa must be > 0, got {self.sea_level_pressure_hpa}"
            raise ValueError(msg)
        if self.rain_rate_mmh < 0.0:
            msg = f"rain_rate_mmh must be >= 0, got {self.rain_rate_mmh}"
            raise ValueError(msg)
        if self.visibility_km <= 0.0:
            msg = f"visibility_km must be > 0, got {self.visibility_km}"
            raise ValueError(msg)


# --- ISA temperature / pressure / density ----------------------------


def isa_temperature(altitude_m: float, atm: AtmosphereState) -> float:
    """ISA temperature at altitude [K] (plan/15 § 15.3.1).

    Troposphere: ``T = T0 - L * h``. Above 11 km, clamps to the
    11-km value (MVP simplification).

    Args:
        altitude_m: Altitude above the Map's sea-level reference [m].
        atm: Atmosphere state providing ``sea_level_temperature_k``.

    Returns:
        Static temperature [K].
    """
    h = min(altitude_m, ISA_TROPOPAUSE_M) if altitude_m > 0.0 else altitude_m
    return atm.sea_level_temperature_k - ISA_LAPSE_RATE_K_PER_M * h


def isa_pressure(altitude_m: float, atm: AtmosphereState) -> float:
    """ISA pressure at altitude [Pa] (plan/15 § 15.3.1).

    Args:
        altitude_m: Altitude above the Map's sea-level reference [m].
        atm: Atmosphere state providing ``sea_level_pressure_hpa`` /
            ``sea_level_temperature_k``.

    Returns:
        Static pressure [Pa].
    """
    p0_pa = atm.sea_level_pressure_hpa * 100.0
    t0 = atm.sea_level_temperature_k
    if altitude_m <= ISA_TROPOPAUSE_M:
        h = max(altitude_m, 0.0)
        t = t0 - ISA_LAPSE_RATE_K_PER_M * h
        # P = P0 * (T/T0) ** (g / (R*L))
        exponent = ISA_G_M_PER_S2 / (ISA_R_GAS_DRY_AIR_J_PER_KGK * ISA_LAPSE_RATE_K_PER_M)
        return p0_pa * math.pow(t / t0, exponent)
    # MVP: clamp at tropopause value.
    return isa_pressure(ISA_TROPOPAUSE_M, atm)


def isa_density(altitude_m: float, atm: AtmosphereState) -> float:
    """ISA density at altitude [kg/m^3] (plan/15 § 15.3.1).

    Computed via the ideal gas law from :func:`isa_pressure` and
    :func:`isa_temperature`. At sea level with default ``atm``,
    returns approximately 1.225 kg/m^3.

    Args:
        altitude_m: Altitude above the Map's sea-level reference [m].
        atm: Atmosphere state.

    Returns:
        Air density [kg/m^3].
    """
    p = isa_pressure(altitude_m, atm)
    t = isa_temperature(altitude_m, atm)
    return p / (ISA_R_GAS_DRY_AIR_J_PER_KGK * t)


# --- Rain attenuation (ITU-R P.838 simplified) -----------------------


def rain_attenuation_dbpkm(frequency_ghz: float, rain_rate_mmh: float) -> float:
    """Specific rain attenuation [dB/km] (plan/15 § 15.5.1, ITU-R P.838).

    Simplified piecewise model. The X-band region (8-12 GHz) is the
    validated band; outside it uses coarser linear fits — adequate for
    MVP gross-effect testing but not absolute accuracy.

    Formula: ``L = k * (R ** alpha)`` [dB/km], where ``R`` is the rain
    rate in mm/h.

    Args:
        frequency_ghz: Radar carrier frequency [GHz].
        rain_rate_mmh: Rain rate [mm/h]. ``0`` returns 0 dB/km.

    Returns:
        Specific attenuation [dB/km].

    Raises:
        ValueError: If ``frequency_ghz <= 0`` or ``rain_rate_mmh < 0``.
    """
    if frequency_ghz <= 0.0:
        msg = f"frequency_ghz must be > 0, got {frequency_ghz}"
        raise ValueError(msg)
    if rain_rate_mmh < 0.0:
        msg = f"rain_rate_mmh must be >= 0, got {rain_rate_mmh}"
        raise ValueError(msg)
    if rain_rate_mmh == 0.0:
        return 0.0

    if 8.0 <= frequency_ghz <= 12.0:
        # X-band linear fit (plan/15 § 15.5.1)
        k = 0.0117 * frequency_ghz - 0.0734
        alpha = 1.097
    elif frequency_ghz < 8.0:
        k = 0.001
        alpha = 1.0
    else:
        k = 0.05 * (frequency_ghz / 10.0)
        alpha = 1.1

    return k * math.pow(rain_rate_mmh, alpha)


def two_way_loss_db(target_range_m: float, atm: AtmosphereState, frequency_hz: float) -> float:
    """Two-way rain-attenuation path loss [dB] (plan/15 § 15.5.2).

    Two-way = 2 * (range_km * specific_attenuation). Other propagation
    losses (free-space spreading, antenna gain) are NOT included — this
    function returns only the rain contribution to L_atmo in the radar
    range equation.

    Args:
        target_range_m: One-way slant range to target [m].
        atm: Atmosphere state. ``rain_rate_mmh = 0`` returns 0 dB.
        frequency_hz: Radar carrier frequency [Hz].

    Returns:
        Two-way attenuation [dB].

    Raises:
        ValueError: If ``target_range_m < 0`` or ``frequency_hz <= 0``.
    """
    if target_range_m < 0.0:
        msg = f"target_range_m must be >= 0, got {target_range_m}"
        raise ValueError(msg)
    if frequency_hz <= 0.0:
        msg = f"frequency_hz must be > 0, got {frequency_hz}"
        raise ValueError(msg)
    range_km = target_range_m / 1000.0
    freq_ghz = frequency_hz / 1e9
    specific_db_per_km = rain_attenuation_dbpkm(freq_ghz, atm.rain_rate_mmh)
    return 2.0 * range_km * specific_db_per_km
