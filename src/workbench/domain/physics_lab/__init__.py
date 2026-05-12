"""Physics Lab domain — Test Objects + session state (PL-C, plan/19 § 19.7).

PL-C ships the 9 canonical Test Objects (Sphere / Cube / Plate /
Cylinder / Cone / Trihedral / Wall / Plane / Point) that the Library
widget surfaces. Each frozen dataclass exposes an
``analytic_rcs_m2(wavelength_m)`` method backed by the analytic
formulas in :mod:`workbench.physics.reflection.rcs_single`.
"""

from __future__ import annotations

from workbench.domain.physics_lab.parameter_metadata import (
    BOUNCING_BALL_PARAM_SPECS,
    SLIDER_TICK_RESOLUTION,
    ParameterScale,
    PhysicsParam,
    get_physics_params,
    physics_param,
)
from workbench.domain.physics_lab.saved_experiments import (
    SavedExperiment,
    list_saved_experiments,
    read_saved_experiment,
    write_saved_experiment,
)
from workbench.domain.physics_lab.test_objects import (
    TEST_OBJECT_KINDS,
    Cone,
    Cube,
    Cylinder,
    Plane,
    Plate,
    Point,
    Sphere,
    TestObject,
    Trihedral,
    VisualKind,
    Wall,
    default_library,
)
from workbench.domain.physics_lab.time_modes import (
    TIME_MODES_IN_DISPLAY_ORDER,
    TimeMode,
)

__all__ = [
    "BOUNCING_BALL_PARAM_SPECS",
    "SLIDER_TICK_RESOLUTION",
    "TEST_OBJECT_KINDS",
    "TIME_MODES_IN_DISPLAY_ORDER",
    "Cone",
    "Cube",
    "Cylinder",
    "ParameterScale",
    "PhysicsParam",
    "Plane",
    "Plate",
    "Point",
    "SavedExperiment",
    "Sphere",
    "TestObject",
    "TimeMode",
    "Trihedral",
    "VisualKind",
    "Wall",
    "default_library",
    "get_physics_params",
    "list_saved_experiments",
    "physics_param",
    "read_saved_experiment",
    "write_saved_experiment",
]
