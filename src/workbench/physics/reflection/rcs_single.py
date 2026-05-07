"""Single-point RCS primitives — analytic radar cross-section shapes.

Phase 1.5 module covers the canonical shapes whose RCS is given in closed
form in radar reference texts. Multi-scatterer ExtendedTarget (plan/14
§ 14.10, plan/16 § 16.3.2) builds on these primitives at the Domain layer.

References:

- Skolnik, M. (2008). *Radar Handbook*, 3rd ed., Ch. 11 — Cross Section.
- Mahafza, B. (2013). *Radar Systems Analysis & Design Using MATLAB*,
  Ch. 13 — Radar Cross Section.
- Knott, E. (2004). *Radar Cross Section*, 2nd ed.

Conventions:

- All linear cross-sections in **square metres** (``m^2``).
- Logarithmic scale in **dBsm** = ``10 * log10(sigma_m2)``.
- Wavelengths and lengths in **metres**.
- "Geometric optics" regime: characteristic length ``>> lambda``.
- "Rayleigh" regime: characteristic length ``<< lambda``.
- "Resonance" regime (1 ~ 10 lambda) is not covered by primitives — it
  requires Mie series / numerical EM and lives in MVP+alpha physics models.

The default test wavelength used in the goldens is 9.4 GHz X-band
(``lambda = c/f = 299_792_458 / 9.4e9 = 0.0319 m``).
"""

from __future__ import annotations

import math
from typing import Final

PI: Final[float] = math.pi


# ---------------------------------------------------------------------------
# Sphere
# ---------------------------------------------------------------------------


def sphere_rcs_geometric_m2(radius_m: float) -> float:
    """Conducting sphere in the geometric-optics regime (``a >> lambda``).

    ``sigma = pi * a^2``.

    A 1 m-radius sphere has sigma = pi m^2 ~= 3.1416 m^2 (~4.97 dBsm).
    Note this does NOT depend on the wavelength — only on the projected
    geometric cross-section. For ``a / lambda < ~1`` use
    :func:`sphere_rcs_rayleigh_m2` instead.

    Args:
        radius_m: Sphere radius [m], > 0.

    Returns:
        RCS [m^2].
    """
    return PI * radius_m * radius_m


def sphere_rcs_rayleigh_m2(radius_m: float, wavelength_m: float) -> float:
    """Small conducting sphere in the Rayleigh regime (``a << lambda``).

    ``sigma = (4 * pi^5 / 3) * a^6 / lambda^4``.

    The strong ``a^6 / lambda^4`` dependence makes Rayleigh scattering very
    weak for sub-wavelength targets. This is the same scaling that makes
    the sky blue (atmospheric Rayleigh on visible light).

    Args:
        radius_m: Sphere radius [m], > 0, must satisfy ``a << lambda``.
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        RCS [m^2].
    """
    return (4.0 * PI**5 / 3.0) * (radius_m**6) / (wavelength_m**4)


# ---------------------------------------------------------------------------
# Flat plate
# ---------------------------------------------------------------------------


def flat_plate_rcs_max_m2(area_m2: float, wavelength_m: float) -> float:
    """Rectangular flat plate at normal incidence (peak return).

    ``sigma_max = 4 * pi * A^2 / lambda^2``.

    Off-axis the lobe falls off as ``sinc^2`` — handled by directional
    primitives (Phase 1.5+). Off-axis is dramatic: a flat plate is the
    canonical "specular" reflector with very narrow lobes.

    Args:
        area_m2: Plate physical area ``A`` [m^2], > 0.
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Peak RCS at normal incidence [m^2].
    """
    return 4.0 * PI * area_m2 * area_m2 / (wavelength_m * wavelength_m)


# ---------------------------------------------------------------------------
# Cylinder
# ---------------------------------------------------------------------------


def cylinder_rcs_broadside_m2(
    radius_m: float,
    length_m: float,
    wavelength_m: float,
) -> float:
    """Conducting circular cylinder at broadside (peak return).

    ``sigma_max = 2 * pi * a * L^2 / lambda``.

    Broadside = perpendicular incidence. End-on is much smaller (handled
    by directional primitives in higher-level modules).

    Args:
        radius_m: Cylinder radius ``a`` [m], > 0.
        length_m: Cylinder length ``L`` [m], > 0.
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Peak broadside RCS [m^2].
    """
    return 2.0 * PI * radius_m * length_m * length_m / wavelength_m


# ---------------------------------------------------------------------------
# Corner reflectors — important for calibration / radar reflectors
# ---------------------------------------------------------------------------


def trihedral_corner_rcs_m2(side_length_m: float, wavelength_m: float) -> float:
    """Square trihedral corner reflector (peak return on bisector axis).

    ``sigma_max = 12 * pi * L^4 / lambda^2``.

    A trihedral corner reflector retro-reflects over a wide solid angle
    (~40 deg cone) and returns a strong, stable signal — the
    workhorse calibration target. The peak occurs along the corner-axis
    (the long diagonal direction).

    Args:
        side_length_m: Side of each square face ``L`` [m], > 0.
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Peak RCS along the corner axis [m^2].
    """
    return 12.0 * PI * (side_length_m**4) / (wavelength_m * wavelength_m)


def dihedral_corner_rcs_m2(
    width_m: float,
    height_m: float,
    wavelength_m: float,
) -> float:
    """Dihedral corner reflector (peak return on bisector axis).

    ``sigma_max = 8 * pi * (w * h)^2 / lambda^2``.

    Dihedral = two perpendicular plates. Used for polarisation-sensitive
    calibration.

    Args:
        width_m: One plate width ``w`` [m], > 0.
        height_m: Other plate width ``h`` [m], > 0.
        wavelength_m: Radar wavelength [m], > 0.

    Returns:
        Peak RCS [m^2].
    """
    return 8.0 * PI * (width_m * height_m) ** 2 / (wavelength_m * wavelength_m)


# ---------------------------------------------------------------------------
# dB conversions
# ---------------------------------------------------------------------------


def rcs_to_dbsm(rcs_m2: float) -> float:
    """Linear RCS [m^2] -> logarithmic [dBsm].

    ``dBsm = 10 * log10(sigma)``.

    By convention, ``1 m^2 = 0 dBsm``. A ship hull tens of m^2 sits near
    +20 dBsm; a small drone near -20 dBsm.

    Args:
        rcs_m2: Linear RCS [m^2], > 0.

    Returns:
        RCS in dBsm.
    """
    return 10.0 * math.log10(rcs_m2)


def dbsm_to_rcs(rcs_dbsm: float) -> float:
    """Logarithmic [dBsm] -> linear RCS [m^2].

    ``sigma = 10 ^ (dBsm / 10)``.

    Args:
        rcs_dbsm: RCS in dBsm.

    Returns:
        Linear RCS [m^2].
    """
    return math.pow(10.0, rcs_dbsm / 10.0)
