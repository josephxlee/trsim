"""Antenna module — parabolic dish gain, beamwidth, sinc^2 beam pattern.

Phase 2.6 (plan/08 § 8.5a). Phase 2.6 covers the **parabolic** antenna
only — the v0.18 MVP path. Planar arrays + monopulse 4-channel
configurations live in Phase 2.6b (deferred).

Conventions (plan/08 § 8.5a, Skolnik / Mahafza):

- ``theta_deg`` and ``phi_deg`` are angles from boresight (the antenna
  pointing axis). At boresight the normalized pattern is 1.0.
- 3-dB beamwidth approximation: ``theta_3dB ~ 70 * lambda / D`` [deg]
  (plan/08 § 8.5a.2). For a Skolnik-style sinc^2 pattern this gives
  the symmetric pattern half-power beamwidth.
- Peak directivity (uniform aperture): ``D = (4 * pi / lambda^2) * A``
  with ``A = pi * D^2 / 4``. Peak gain ``G = efficiency * D``.

References:

- Skolnik, *Introduction to Radar Systems*, 3rd ed., chapter 9
  (parabolic antennas).
- Mahafza, *Radar Systems Analysis and Design Using MATLAB*, ch. 6.
- plan/08 § 8.5a — TRsim antenna abstraction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Final

C_LIGHT_M_S: Final[float] = 299_792_458.0
"""SI exact speed of light [m/s]. Shared with fmcw.py / multipath.py."""

# 3-dB beamwidth empirical coefficient: theta_3dB[deg] = 70 * lambda / D.
# Skolnik uses 70.5; plan/08 § 8.5a.2 standardises on 70.0.
_PARABOLIC_BEAMWIDTH_K: Final[float] = 70.0

# sinc^2 first-zero coefficient — sinc^2(u) = 0.5 at u ~= 1.391557 (rad).
# Used to convert (theta / theta_3dB) into the sinc argument so the
# pattern is exactly 0.5 at theta = theta_3dB/2 (one-sided 3-dB point).
_SINC_HALF_POWER_U: Final[float] = 1.391557377


class AntennaType(Enum):
    """Antenna form (plan/08 § 8.5a.1)."""

    PARABOLIC = "parabolic"
    PLANAR_ARRAY = "planar_array"


@dataclass(frozen=True, slots=True)
class ParabolicAntenna:
    """Parabolic dish antenna (plan/08 § 8.5a.2).

    Attributes:
        diameter_m: Reflector diameter [m]. Must be > 0.
        frequency_hz: Operating frequency [Hz]. Must be > 0.
        efficiency: Aperture efficiency in (0, 1]. Default 0.6.

    The antenna type tag is fixed to ``AntennaType.PARABOLIC``.
    """

    diameter_m: float
    frequency_hz: float
    efficiency: float = 0.6

    def __post_init__(self) -> None:
        if self.diameter_m <= 0.0:
            msg = f"diameter_m must be > 0, got {self.diameter_m}"
            raise ValueError(msg)
        if self.frequency_hz <= 0.0:
            msg = f"frequency_hz must be > 0, got {self.frequency_hz}"
            raise ValueError(msg)
        if not (0.0 < self.efficiency <= 1.0):
            msg = f"efficiency must be in (0, 1], got {self.efficiency}"
            raise ValueError(msg)

    @property
    def wavelength_m(self) -> float:
        """Operating wavelength [m]. ``c / frequency_hz``."""
        return C_LIGHT_M_S / self.frequency_hz

    @property
    def beamwidth_3db_deg(self) -> float:
        """One-sided 3-dB beamwidth [deg] (full HPBW).

        ``theta_3dB ~ 70 * lambda / D`` per plan/08 § 8.5a.2.
        """
        return _PARABOLIC_BEAMWIDTH_K * self.wavelength_m / self.diameter_m

    @property
    def peak_gain_dbi(self) -> float:
        """Peak boresight gain [dBi].

        ``G = eta * (pi * D / lambda)^2`` for a uniform circular aperture.
        """
        ratio = math.pi * self.diameter_m / self.wavelength_m
        gain_linear = self.efficiency * ratio * ratio
        return 10.0 * math.log10(gain_linear)

    def beam_pattern(self, theta_deg: float, phi_deg: float = 0.0) -> float:
        """Normalised power gain at off-boresight angle ``(theta, phi)``.

        Symmetric circular aperture — the pattern depends only on the
        total off-axis angle ``alpha = sqrt(theta^2 + phi^2)``. At
        ``alpha = 0`` the pattern is 1.0; at ``alpha = beamwidth_3db/2``
        the pattern is 0.5 (one-sided 3-dB point).

        Args:
            theta_deg: Azimuth offset from boresight [deg].
            phi_deg: Elevation offset from boresight [deg]. Default 0.

        Returns:
            Normalised power [0, 1].
        """
        return parabolic_beam_pattern(theta_deg, phi_deg, self.beamwidth_3db_deg)


# --- module-level helpers (testable without instantiating the class) ---


def parabolic_beamwidth_3db_deg(diameter_m: float, frequency_hz: float) -> float:
    """3-dB beamwidth of a parabolic dish [deg].

    ``theta_3dB ~ 70 * lambda / D`` (plan/08 § 8.5a.2).
    """
    if diameter_m <= 0.0:
        msg = f"diameter_m must be > 0, got {diameter_m}"
        raise ValueError(msg)
    if frequency_hz <= 0.0:
        msg = f"frequency_hz must be > 0, got {frequency_hz}"
        raise ValueError(msg)
    wavelength = C_LIGHT_M_S / frequency_hz
    return _PARABOLIC_BEAMWIDTH_K * wavelength / diameter_m


def parabolic_peak_gain_dbi(
    diameter_m: float, frequency_hz: float, efficiency: float = 0.6
) -> float:
    """Peak gain of a parabolic dish [dBi]."""
    if not (0.0 < efficiency <= 1.0):
        msg = f"efficiency must be in (0, 1], got {efficiency}"
        raise ValueError(msg)
    wavelength = C_LIGHT_M_S / frequency_hz  # validated below if D / f bad
    if diameter_m <= 0.0:
        msg = f"diameter_m must be > 0, got {diameter_m}"
        raise ValueError(msg)
    if frequency_hz <= 0.0:
        msg = f"frequency_hz must be > 0, got {frequency_hz}"
        raise ValueError(msg)
    ratio = math.pi * diameter_m / wavelength
    return 10.0 * math.log10(efficiency * ratio * ratio)


def parabolic_beam_pattern(theta_deg: float, phi_deg: float, beamwidth_3db_deg: float) -> float:
    """Normalised sinc^2 pattern for a circular aperture.

    Uses the off-axis angle ``alpha = sqrt(theta^2 + phi^2)`` so the
    pattern is rotationally symmetric. The argument is scaled so that
    ``alpha = beamwidth_3db/2`` returns exactly 0.5.

    Args:
        theta_deg: Azimuth offset from boresight [deg].
        phi_deg: Elevation offset from boresight [deg].
        beamwidth_3db_deg: One-sided 3-dB beamwidth [deg]. Must be > 0.

    Returns:
        Normalised power in [0, 1]. (sinc^2 has small negative-going
        regions around the side-lobes that we clamp to 0 conceptually,
        but sinc^2 is non-negative by definition so no clamp needed.)
    """
    if beamwidth_3db_deg <= 0.0:
        msg = f"beamwidth_3db_deg must be > 0, got {beamwidth_3db_deg}"
        raise ValueError(msg)
    alpha_deg = math.hypot(theta_deg, phi_deg)
    if alpha_deg == 0.0:
        return 1.0
    # Scale so that alpha = bw/2 -> sinc^2(u_half) = 0.5
    u = _SINC_HALF_POWER_U * (2.0 * alpha_deg / beamwidth_3db_deg)
    sinc_val = math.sin(u) / u
    return sinc_val * sinc_val
