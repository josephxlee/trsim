"""Sample user-defined Test Object plugins (PL-9.3e, plan/19 § 19.7.4).

Reference implementations the workbench ships so the Library +
:class:`TestObject3DPanel` can demonstrate the plugin path end-to-end
without an external DLC package.

- :class:`Pyramid` — square-base pyramid (no closed-form RCS in the
  built-in table; ``analytic_rcs_m2`` returns ``None``). Registered
  with the mesh-builder registry under ``visual = "pyramid"``.

Calling :func:`register_custom_test_objects` at workspace
construction time wires the sample(s) into the registry. Existing
9-built-in tests stay isolated because the call is opt-in.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

import pyvista as pv

from workbench.ui.physics_lab.test_object_view import register_visual_kind_builder


@dataclass(frozen=True, slots=True)
class Pyramid:
    """Square-base right pyramid.

    Satisfies :class:`workbench.sdk.protocols.TestObjectProtocol` —
    exposes ``name``, ``visual``, and ``analytic_rcs_m2``.

    Attributes:
        name: Library label.
        base_length_m: Side length of the square base, > 0.
        height_m: Apex height above the base centre, > 0.
    """

    name: str
    base_length_m: float
    height_m: float

    visual: ClassVar[str] = "pyramid"

    def __post_init__(self) -> None:
        if self.base_length_m <= 0.0:
            msg = f"Pyramid.base_length_m must be > 0, got {self.base_length_m}"
            raise ValueError(msg)
        if self.height_m <= 0.0:
            msg = f"Pyramid.height_m must be > 0, got {self.height_m}"
            raise ValueError(msg)

    def analytic_rcs_m2(self, wavelength_m: float) -> float | None:
        """No closed-form RCS for a generic pyramid in the built-in set."""
        del wavelength_m
        return None


def _build_pyramid_mesh(obj: Pyramid) -> pv.PolyData:
    """Apex at +z; square base on the xy-plane.

    Uses :func:`pyvista.PolyData` directly so the registry callback
    keeps a uniform signature even though no PyVista primitive matches
    a pyramid shape out of the box.
    """
    half = obj.base_length_m / 2.0
    points = [
        (-half, -half, 0.0),
        (+half, -half, 0.0),
        (+half, +half, 0.0),
        (-half, +half, 0.0),
        (0.0, 0.0, obj.height_m),
    ]
    # 4 triangular side faces + 1 quad base. PyVista PolyData faces
    # are flat int arrays prefixed by per-face vertex count.
    faces = [
        # Side faces
        3,
        0,
        1,
        4,
        3,
        1,
        2,
        4,
        3,
        2,
        3,
        4,
        3,
        3,
        0,
        4,
        # Base (quad)
        4,
        0,
        3,
        2,
        1,
    ]
    return pv.PolyData(points, faces)


def register_custom_test_objects() -> None:
    """Idempotent helper — registers every sample Test Object plugin."""
    register_visual_kind_builder("pyramid", _build_pyramid_mesh)
