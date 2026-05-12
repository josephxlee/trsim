"""Physics Lab Test Objects — 9 canonical shapes (PL-C, plan/19 § 19.7).

Test Objects are the standard set of simple shapes whose RCS and
dynamics are known in closed form. plan/19 § 19.7.1 enumerates 9 of
them; each surfaces in the Physics Lab Library so the user can pick
one, watch the analytic formula and the simulation agree, and (later)
plug their own physics model in to compare.

The 9 shapes split into three groups:

- **Volumetric RCS**: Sphere, Cube, Cylinder, Cone — analytic RCS in
  the geometric-optics regime; Sphere also in Rayleigh regime.
- **Plate-class RCS**: Plate, Wall, Trihedral — broadside / corner
  reflector formulas.
- **No-RCS** (used for dynamics-only demos): Point (point mass),
  Plane (infinite ground reference).

Each Test Object exposes ``analytic_rcs_m2(wavelength_m)``. ``None``
when the shape has no closed-form RCS reference (Point / Plane —
those exist solely for dynamics + visual reference).

The analytic-RCS implementations defer to
:mod:`workbench.physics.reflection.rcs_single` where Phase 1.5 / 5.9
already shipped the canonical formulas; Cube and Cone are new
helpers added inline.

References:

- plan/19 § 19.7.1 — Test Object catalogue.
- plan/19 § 19.7.2 — analytic RCS reference table.
- Skolnik, *Radar Handbook*, Ch. 11 — Cross Section.
- Knott, *Radar Cross Section*, Ch. 6 — Cones and Cubes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import ClassVar, Final, Literal

from workbench.physics.reflection.rcs_single import (
    cylinder_rcs_broadside_m2,
    flat_plate_rcs_max_m2,
    sphere_rcs_geometric_m2,
    sphere_rcs_rayleigh_m2,
    trihedral_corner_rcs_m2,
)

# Boundary between "use Rayleigh" and "use geometric optics" for a
# sphere. ~0.5 * lambda is a conservative crossover; below it Rayleigh
# (~ λ^-4) dominates, above it the geometric formula (pi * r^2) holds.
_RAYLEIGH_KA_THRESHOLD: Final[float] = 0.5

VisualKind = Literal[
    "sphere",
    "cube",
    "plate",
    "cylinder",
    "cone",
    "point",
    "plane",
    "wall",
    "trihedral",
]


# ---------------------------------------------------------------------
# Volumetric / plate / corner classes
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Sphere:
    """Smooth conducting sphere.

    Attributes:
        name: Free-form identifier (Library label).
        radius_m: Sphere radius in metres, > 0.
        mass_kg: Mass in kilograms, >= 0 (0 = static reference target).
        drag_coefficient: Cd for translational drag. Default 0.47 =
            smooth sphere in the Newton regime (Re > 1e3).

    Raises:
        ValueError: For non-positive radius / negative mass / negative Cd.
    """

    name: str
    radius_m: float
    mass_kg: float = 1.0
    drag_coefficient: float = 0.47

    visual: ClassVar[VisualKind] = "sphere"

    def __post_init__(self) -> None:
        if self.radius_m <= 0.0:
            msg = f"Sphere.radius_m must be > 0, got {self.radius_m}"
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Sphere.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)
        if self.drag_coefficient < 0.0:
            msg = f"Sphere.drag_coefficient must be >= 0, got {self.drag_coefficient}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        """Geometric (a >> lambda) or Rayleigh (a << lambda) RCS.

        Crossover at ``2 * pi * radius / wavelength == 0.5`` (i.e. the
        sphere circumference compared to the wavelength).
        """
        if wavelength_m <= 0.0:
            msg = f"wavelength_m must be > 0, got {wavelength_m}"
            raise ValueError(msg)
        ka = 2.0 * math.pi * self.radius_m / wavelength_m
        if ka < _RAYLEIGH_KA_THRESHOLD:
            return sphere_rcs_rayleigh_m2(self.radius_m, wavelength_m)
        return sphere_rcs_geometric_m2(self.radius_m)


@dataclass(frozen=True, slots=True)
class Cube:
    """Solid cube, broadside aspect.

    Treats the cube as six identical flat plates of area ``a^2`` and
    returns the broadside RCS of a single face (plan/19 § 19.7.2). The
    Phase 9.1 visualiser can rotate the cube to test aspect dependence
    later; for the MVP we use the maximum (broadside-on-a-face) value
    so the analytic curve is a single scalar.

    Attributes:
        name: Free-form identifier.
        side_length_m: Cube side ``a`` in metres, > 0.
        mass_kg: Mass in kilograms, >= 0.
        drag_coefficient: Cd ~ 1.05 for a cube in the Newton regime.
    """

    name: str
    side_length_m: float
    mass_kg: float = 1.0
    drag_coefficient: float = 1.05

    visual: ClassVar[VisualKind] = "cube"

    def __post_init__(self) -> None:
        if self.side_length_m <= 0.0:
            msg = f"Cube.side_length_m must be > 0, got {self.side_length_m}"
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Cube.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        """Broadside RCS of a single face — ``4 * pi * a^4 / lambda^2``."""
        if wavelength_m <= 0.0:
            msg = f"wavelength_m must be > 0, got {wavelength_m}"
            raise ValueError(msg)
        return flat_plate_rcs_max_m2(self.side_length_m**2, wavelength_m)


@dataclass(frozen=True, slots=True)
class Plate:
    """Flat rectangular conducting plate, broadside aspect.

    Attributes:
        name: Free-form identifier.
        width_m: Plate width, > 0.
        height_m: Plate height, > 0.
        normal_direction: Unit normal in body frame.
        mass_kg: Mass in kilograms, >= 0.
    """

    name: str
    width_m: float
    height_m: float
    normal_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    mass_kg: float = 1.0

    visual: ClassVar[VisualKind] = "plate"

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.height_m <= 0.0:
            msg = (
                f"Plate width/height must be > 0, got width={self.width_m}, height={self.height_m}"
            )
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Plate.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        """Broadside RCS — ``4 * pi * A^2 / lambda^2`` with ``A = w * h``."""
        if wavelength_m <= 0.0:
            msg = f"wavelength_m must be > 0, got {wavelength_m}"
            raise ValueError(msg)
        area = self.width_m * self.height_m
        return flat_plate_rcs_max_m2(area, wavelength_m)


@dataclass(frozen=True, slots=True)
class Cylinder:
    """Conducting cylinder, broadside aspect.

    Attributes:
        name: Free-form identifier.
        radius_m: Cylinder radius, > 0.
        length_m: Cylinder length along its axis, > 0.
        axis_direction: Unit vector of the cylinder axis in body frame.
        mass_kg: Mass in kilograms, >= 0.
    """

    name: str
    radius_m: float
    length_m: float
    axis_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    mass_kg: float = 1.0

    visual: ClassVar[VisualKind] = "cylinder"

    def __post_init__(self) -> None:
        if self.radius_m <= 0.0 or self.length_m <= 0.0:
            msg = (
                f"Cylinder radius/length must be > 0, got "
                f"radius={self.radius_m}, length={self.length_m}"
            )
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Cylinder.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        """Broadside RCS — ``2 * pi * r * l^2 / lambda``."""
        return cylinder_rcs_broadside_m2(
            radius_m=self.radius_m,
            length_m=self.length_m,
            wavelength_m=wavelength_m,
        )


@dataclass(frozen=True, slots=True)
class Cone:
    """Right circular cone, tip-on aspect.

    Tip-on RCS (Knott Ch. 6) — ``(lambda^2 / (16 * pi)) * tan^4(alpha)``,
    where ``alpha = atan(base_radius / height)`` is the cone half-angle.
    Very small for slender cones, which is why cones are a standard
    radar-stealth shape.

    Attributes:
        name: Free-form identifier.
        base_radius_m: Base radius, > 0.
        height_m: Cone height (apex to base centre), > 0.
        apex_direction: Unit vector from base to apex in body frame.
        mass_kg: Mass in kilograms, >= 0.
    """

    name: str
    base_radius_m: float
    height_m: float
    apex_direction: tuple[float, float, float] = (0.0, 0.0, 1.0)
    mass_kg: float = 1.0

    visual: ClassVar[VisualKind] = "cone"

    def __post_init__(self) -> None:
        if self.base_radius_m <= 0.0 or self.height_m <= 0.0:
            msg = (
                f"Cone base_radius/height must be > 0, got "
                f"base_radius={self.base_radius_m}, height={self.height_m}"
            )
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Cone.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        """Tip-on RCS — ``(lambda^2 / (16 * pi)) * tan^4(alpha)``."""
        if wavelength_m <= 0.0:
            msg = f"wavelength_m must be > 0, got {wavelength_m}"
            raise ValueError(msg)
        alpha = math.atan2(self.base_radius_m, self.height_m)
        tan_alpha = math.tan(alpha)
        return (wavelength_m**2 / (16.0 * math.pi)) * tan_alpha**4


@dataclass(frozen=True, slots=True)
class Trihedral:
    """3-face corner reflector (RCS calibration standard).

    plan/19 § 19.7.2: ``sigma = (12 * pi * a^4) / lambda^2``.

    Attributes:
        name: Free-form identifier.
        center: Reflector centre position in body frame.
        side_length_m: Side length of each triangular face, > 0.
        orientation: Body orientation quaternion (w, x, y, z).
        mass_kg: Mass — reflectors are typically static, default 0.
    """

    name: str
    side_length_m: float
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    orientation: tuple[float, float, float, float] = (1.0, 0.0, 0.0, 0.0)
    mass_kg: float = 0.0

    visual: ClassVar[VisualKind] = "trihedral"

    def __post_init__(self) -> None:
        if self.side_length_m <= 0.0:
            msg = f"Trihedral.side_length_m must be > 0, got {self.side_length_m}"
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Trihedral.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        return trihedral_corner_rcs_m2(self.side_length_m, wavelength_m)


# ---------------------------------------------------------------------
# Dynamics-only classes (no analytic RCS reference)
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Point:
    """Infinitesimal point mass — pure dynamics, no RCS.

    Used for gravity / drag / trajectory demos where the shape itself
    is irrelevant.

    Attributes:
        name: Free-form identifier.
        mass_kg: Mass in kilograms, >= 0.
    """

    name: str
    mass_kg: float = 1.0

    visual: ClassVar[VisualKind] = "point"

    def __post_init__(self) -> None:
        if self.mass_kg < 0.0:
            msg = f"Point.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float | None:
        """Point mass has no shape -> no analytic RCS reference."""
        del wavelength_m
        return None


@dataclass(frozen=True, slots=True)
class Plane:
    """Infinite reference plane (ground, reflective surface).

    Used as a visual / dynamics reference (e.g. Bouncing Ball needs a
    floor). Static; no RCS — Phase 9.x multipath demos handle plane
    reflection separately.

    Attributes:
        name: Free-form identifier.
        point: A point that lies on the plane.
        normal: Plane unit normal (not necessarily axis-aligned).
    """

    name: str
    point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    mass_kg: float = 0.0

    visual: ClassVar[VisualKind] = "plane"

    def analytic_rcs_m2(self, wavelength_m: float) -> float | None:
        del wavelength_m
        return None


@dataclass(frozen=True, slots=True)
class Wall:
    """Finite rectangular reference plane (obstacle).

    Analytic RCS borrows the Plate formula since a wall is just a
    plate with mass 0 by default. Distinguished from Plate to make
    the Library catalogue read clearly.

    Attributes:
        name: Free-form identifier.
        center: Wall centre in body frame.
        width_m: Wall width, > 0.
        height_m: Wall height, > 0.
        normal: Outward unit normal.
        mass_kg: Mass — walls are typically static, default 0.
    """

    name: str
    width_m: float
    height_m: float
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    mass_kg: float = 0.0

    visual: ClassVar[VisualKind] = "wall"

    def __post_init__(self) -> None:
        if self.width_m <= 0.0 or self.height_m <= 0.0:
            msg = f"Wall width/height must be > 0, got width={self.width_m}, height={self.height_m}"
            raise ValueError(msg)
        if self.mass_kg < 0.0:
            msg = f"Wall.mass_kg must be >= 0, got {self.mass_kg}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float:
        if wavelength_m <= 0.0:
            msg = f"wavelength_m must be > 0, got {wavelength_m}"
            raise ValueError(msg)
        return flat_plate_rcs_max_m2(self.width_m * self.height_m, wavelength_m)


# ---------------------------------------------------------------------
# Catalogue helpers
# ---------------------------------------------------------------------


TEST_OBJECT_KINDS: Final[tuple[VisualKind, ...]] = (
    "sphere",
    "cube",
    "plate",
    "cylinder",
    "cone",
    "trihedral",
    "wall",
    "plane",
    "point",
)
"""All 9 kinds in Library display order — RCS-capable first, dynamics-
only at the end."""


def default_library() -> tuple[
    Sphere,
    Cube,
    Plate,
    Cylinder,
    Cone,
    Trihedral,
    Wall,
    Plane,
    Point,
]:
    """Return one Test Object per kind, sized so analytic RCS comes
    out in the 10^-3 .. 10^2 m^2 range at X-band (9.4 GHz / 0.032 m
    wavelength). The Library widget lists these as the default
    starter set; the user can clone + tweak in PL-D+.
    """
    return (
        Sphere(name="sphere_1m", radius_m=1.0, mass_kg=10.0),
        Cube(name="cube_0p5m", side_length_m=0.5, mass_kg=5.0),
        Plate(name="plate_1x1m", width_m=1.0, height_m=1.0, mass_kg=2.0),
        Cylinder(name="cylinder_0p1x2m", radius_m=0.1, length_m=2.0, mass_kg=2.0),
        Cone(name="cone_0p3x1m", base_radius_m=0.3, height_m=1.0, mass_kg=1.0),
        Trihedral(name="trihedral_0p3m", side_length_m=0.3),
        Wall(name="wall_5x3m", width_m=5.0, height_m=3.0),
        Plane(name="ground", point=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0)),
        Point(name="point_1kg", mass_kg=1.0),
    )
