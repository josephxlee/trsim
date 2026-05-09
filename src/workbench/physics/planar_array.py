"""Planar (rectangular) phased-array antenna (plan/08 § 8.5a.3).

Phase 2.6b — companion to :mod:`workbench.physics.antenna` (parabolic
dish, Phase 2.6). Adds the ``N x M`` rectangular array form whose
beam pattern is the product of an array factor (interference among
elements) and a per-element pattern.

MVP (plan/08 § 8.5a.3):

- Rectangular grid with uniform spacing.
- Uniform amplitude weighting (no Taylor / Chebyshev taper — that
  belongs to ``weighting != "uniform"`` MVP+alpha).
- Element pattern: ``"cos"`` (cos-power lobed element) or
  ``"isotropic"`` (constant 1).
- 3-dB beamwidth approximation: ``theta_3dB = degrees(0.886 * lambda / L)``
  where ``L = (N - 1) * spacing`` for a uniform line-source aperture.
- Closed-form magnitude of the array factor:
  ``|AF| = |sin(N * psi/2) / sin(psi/2)|`` with
  ``psi = k * d * sin(theta)``. Normalised by ``N`` so the boresight
  value is 1. The 2D pattern is the product of the two 1D factors.

References:

- Skolnik, *Introduction to Radar Systems* 3e, ch.9 (arrays).
- Mahafza, *Radar Systems Analysis and Design Using MATLAB*, ch.7.
- Balanis, *Antenna Theory*, ch.6 (uniform linear array).
- plan/08 § 8.5a.3 — TRsim planar-array abstraction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

from workbench.physics.antenna import AntennaType

C_LIGHT_M_S: Final[float] = 299_792_458.0
"""SI exact speed of light [m/s]. Shared with antenna / fmcw / multipath."""

# 3-dB beamwidth coefficient for a uniform line-source aperture (Balanis
# table 6.4). plan/08 § 8.5a.3 standardises on 0.886.
_LINE_SOURCE_BEAMWIDTH_K: Final[float] = 0.886


@dataclass(frozen=True, slots=True)
class PlanarArrayAntenna:
    """Rectangular ``N x M`` planar array (plan/08 § 8.5a.3).

    Attributes:
        n_elements_az: Element count along azimuth (>= 2).
        n_elements_el: Element count along elevation (>= 2).
        frequency_hz: Operating frequency [Hz]. Must be > 0.
        spacing_m: Inter-element spacing [m]. Must be > 0. Default
            0.5 m (lambda/2 at f = c/(2*0.5) = 3e8 Hz, but typically
            the user supplies a value matched to their carrier).
        element_pattern: ``"cos"`` (cosine-power element) or
            ``"isotropic"`` (constant). Default ``"cos"``.

    Raises:
        ValueError: For non-positive sizes / spacing / frequency, or
            an unsupported ``element_pattern``.
    """

    n_elements_az: int
    n_elements_el: int
    frequency_hz: float
    spacing_m: float = 0.5
    element_pattern: str = "cos"

    def __post_init__(self) -> None:
        if self.n_elements_az < 2:
            msg = f"n_elements_az must be >= 2, got {self.n_elements_az}"
            raise ValueError(msg)
        if self.n_elements_el < 2:
            msg = f"n_elements_el must be >= 2, got {self.n_elements_el}"
            raise ValueError(msg)
        if self.frequency_hz <= 0.0:
            msg = f"frequency_hz must be > 0, got {self.frequency_hz}"
            raise ValueError(msg)
        if self.spacing_m <= 0.0:
            msg = f"spacing_m must be > 0, got {self.spacing_m}"
            raise ValueError(msg)
        if self.element_pattern not in ("cos", "isotropic"):
            msg = f"element_pattern must be 'cos' or 'isotropic', got {self.element_pattern!r}"
            raise ValueError(msg)

    @property
    def antenna_type(self) -> AntennaType:
        """Always :data:`AntennaType.PLANAR_ARRAY`."""
        return AntennaType.PLANAR_ARRAY

    @property
    def wavelength_m(self) -> float:
        """``c / frequency_hz`` [m]."""
        return C_LIGHT_M_S / self.frequency_hz

    @property
    def aperture_length_az_m(self) -> float:
        """``L_az = (N_az - 1) * spacing_m`` [m]."""
        return (self.n_elements_az - 1) * self.spacing_m

    @property
    def aperture_length_el_m(self) -> float:
        """``L_el = (N_el - 1) * spacing_m`` [m]."""
        return (self.n_elements_el - 1) * self.spacing_m

    @property
    def beamwidth_3db_az_deg(self) -> float:
        """Azimuth 3-dB beamwidth [deg] — ``0.886 * lambda / L_az``."""
        return math.degrees(
            _LINE_SOURCE_BEAMWIDTH_K * self.wavelength_m / self.aperture_length_az_m
        )

    @property
    def beamwidth_3db_el_deg(self) -> float:
        """Elevation 3-dB beamwidth [deg] — ``0.886 * lambda / L_el``."""
        return math.degrees(
            _LINE_SOURCE_BEAMWIDTH_K * self.wavelength_m / self.aperture_length_el_m
        )

    def array_factor_magnitude(self, theta_az_deg: float, phi_el_deg: float) -> float:
        """Normalised array-factor magnitude in [0, 1] (boresight = 1).

        Closed form for a uniform rectangular array:

        ``|AF_norm| = |sin(N * psi / 2) / (N * sin(psi / 2))| *
                       |sin(M * xi / 2) / (M * sin(xi / 2))|``

        with ``psi = k * d * sin(theta_az)`` and ``xi = k * d * sin(phi_el)``.
        At ``theta = phi = 0`` both arguments vanish and the limit is 1
        (we evaluate the limit explicitly).
        """
        k = 2.0 * math.pi / self.wavelength_m
        psi = k * self.spacing_m * math.sin(math.radians(theta_az_deg))
        xi = k * self.spacing_m * math.sin(math.radians(phi_el_deg))
        return _uniform_factor(self.n_elements_az, psi) * _uniform_factor(self.n_elements_el, xi)

    def beam_pattern(self, theta_az_deg: float, phi_el_deg: float) -> float:
        """Normalised power gain in [0, 1] (boresight = 1).

        Combines the array factor (squared) with the element pattern.
        Element ``"cos"`` uses ``cos(off-axis-angle)`` capped at zero
        (no back-lobe); ``"isotropic"`` returns 1.0.

        Args:
            theta_az_deg: Azimuth offset from boresight [deg].
            phi_el_deg: Elevation offset from boresight [deg].
        """
        af_mag = self.array_factor_magnitude(theta_az_deg, phi_el_deg)
        # Power = |AF|^2 * element power.
        af_pow = af_mag * af_mag
        ep_pow = element_power(theta_az_deg, phi_el_deg, self.element_pattern)
        return af_pow * ep_pow


# ---------------------------------------------------------------------
# module-level helpers
# ---------------------------------------------------------------------


def _uniform_factor(n: int, psi: float) -> float:
    """``|sin(N * psi / 2) / (N * sin(psi / 2))|`` with the psi=0 limit.

    Returns 1 when ``psi == 0``; otherwise the closed-form expression.
    Always non-negative (we take the absolute value).
    """
    if psi == 0.0:
        return 1.0
    half = psi * 0.5
    denom = math.sin(half)
    if denom == 0.0:
        # psi is a non-zero multiple of 2*pi — grating lobe peak,
        # array factor magnitude is also N (returns 1 normalised).
        return 1.0
    return abs(math.sin(n * half) / (n * denom))


def element_power(theta_az_deg: float, phi_el_deg: float, kind: str) -> float:
    """Element-level power pattern in [0, 1].

    - ``"isotropic"``: returns 1.0 always.
    - ``"cos"``: ``max(0, cos(alpha))`` where
      ``alpha = sqrt(theta^2 + phi^2)`` is the off-axis angle. Below
      90 deg this is the standard cos-power element used in
      planar-array textbooks; above 90 deg the element is in the
      back-hemisphere and we return 0 (no back-lobe at MVP).

    Args:
        theta_az_deg: Azimuth offset from boresight [deg].
        phi_el_deg: Elevation offset from boresight [deg].
        kind: ``"cos"`` or ``"isotropic"``.

    Raises:
        ValueError: For unsupported ``kind``.
    """
    if kind == "isotropic":
        return 1.0
    if kind == "cos":
        alpha_deg = math.hypot(theta_az_deg, phi_el_deg)
        if alpha_deg >= 90.0:
            return 0.0
        return max(0.0, math.cos(math.radians(alpha_deg)))
    msg = f"element_pattern kind must be 'cos' or 'isotropic', got {kind!r}"
    raise ValueError(msg)
