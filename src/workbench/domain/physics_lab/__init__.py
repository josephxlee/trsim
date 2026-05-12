"""Physics Lab domain — Test Objects + session state (PL-C, plan/19 § 19.7).

PL-C ships the 9 canonical Test Objects (Sphere / Cube / Plate /
Cylinder / Cone / Trihedral / Wall / Plane / Point) that the Library
widget surfaces. Each frozen dataclass exposes an
``analytic_rcs_m2(wavelength_m)`` method backed by the analytic
formulas in :mod:`workbench.physics.reflection.rcs_single`.
"""

from __future__ import annotations

from workbench.domain.physics_lab.test_objects import (
    TEST_OBJECT_KINDS,
    Cone,
    Cube,
    Cylinder,
    Plane,
    Plate,
    Point,
    Sphere,
    Trihedral,
    VisualKind,
    Wall,
    default_library,
)

__all__ = [
    "TEST_OBJECT_KINDS",
    "Cone",
    "Cube",
    "Cylinder",
    "Plane",
    "Plate",
    "Point",
    "Sphere",
    "Trihedral",
    "VisualKind",
    "Wall",
    "default_library",
]
