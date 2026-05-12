"""3D Test Object viewer (PL-9.1d, plan/19 § 19.7.3).

Two layers:

- :func:`build_test_object_mesh` — pure-Python mapping from any of the
  nine :mod:`workbench.domain.physics_lab.test_objects` dataclasses to
  a PyVista ``PolyData`` mesh. The mesh primitives follow plan/19
  § 19.7.3:

  =========== =====================
  visual kind PyVista primitive
  =========== =====================
  sphere      ``pv.Sphere``
  cube        ``pv.Cube``
  plate       ``pv.Plane`` with the dataclass normal direction
  cylinder    ``pv.Cylinder`` with the dataclass axis direction
  cone        ``pv.Cone`` with the dataclass apex direction
  trihedral   three perpendicular ``pv.Plane`` instances merged
  wall        ``pv.Plane`` (rectangular)
  plane       ``pv.Plane`` enlarged to a 20 m square for reference
  point       small ``pv.Sphere`` placeholder so it's visible
  =========== =====================

- :class:`TestObject3DPanel` — a ``QWidget`` that wraps a
  ``pyvistaqt.QtInteractor`` and exposes :meth:`set_test_object`,
  :meth:`clear`, :meth:`current_object`. The Physics Lab workspace
  swaps it into the central viz slot whenever the Library selection
  is a Test Object.

Constructing the QtInteractor requires an OpenGL context. Tests that
target the Qt panel use ``pytest.importorskip('pyvistaqt')`` and guard
against environments without a usable GL context.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pyvista as pv
from PySide6.QtWidgets import QVBoxLayout, QWidget
from pyvistaqt import QtInteractor

from workbench.domain.physics_lab import (
    Cone,
    Cube,
    Cylinder,
    Plane,
    Plate,
    Point,
    Sphere,
    TestObject,
    Trihedral,
    Wall,
)

# Mesh-builder registry (PL-9.3e). User plugins call
# :func:`register_visual_kind_builder` at load time to teach the panel
# how to render their custom visual kinds. Built-in 9 kinds are
# pre-registered below the function definitions.
MeshBuilder = Callable[[Any], pv.PolyData]
_VISUAL_KIND_BUILDERS: dict[str, MeshBuilder] = {}


def register_visual_kind_builder(visual: str, builder: MeshBuilder) -> None:
    """Register a callable that builds a PyVista mesh for ``visual``.

    Plugins call this once at import / load time. Re-registering the
    same kind overwrites the previous builder so the user can shadow a
    built-in if they want a custom rendering (sphere with bumpy
    normals, etc.).
    """
    _VISUAL_KIND_BUILDERS[visual] = builder


def registered_visual_kinds() -> tuple[str, ...]:
    """Sorted tuple of every kind known to the registry."""
    return tuple(sorted(_VISUAL_KIND_BUILDERS))


def build_test_object_mesh(obj: TestObject | Any) -> pv.PolyData:
    """Return a PyVista mesh for the given Test Object.

    Dispatches by ``obj.visual`` against the
    :data:`_VISUAL_KIND_BUILDERS` registry. Built-ins are
    pre-registered at module load; user plugins can extend the
    registry via :func:`register_visual_kind_builder`.

    The function accepts the :data:`TestObject` Union *or* any
    duck-typed object satisfying
    :class:`workbench.sdk.protocols.TestObjectProtocol` (must expose a
    ``visual`` attribute).
    """
    visual = getattr(obj, "visual", None)
    if visual is None:
        msg = f"build_test_object_mesh: object has no 'visual' attribute: {obj!r}"
        raise ValueError(msg)
    builder = _VISUAL_KIND_BUILDERS.get(visual)
    if builder is None:
        msg = f"Unknown Test Object visual kind: {visual!r}"
        raise ValueError(msg)
    return builder(obj)


def _sphere_mesh(obj: Sphere) -> pv.PolyData:
    return pv.Sphere(radius=obj.radius_m)


def _cube_mesh(obj: Cube) -> pv.PolyData:
    a = obj.side_length_m
    return pv.Cube(x_length=a, y_length=a, z_length=a)


def _plate_mesh(obj: Plate) -> pv.PolyData:
    return pv.Plane(
        center=(0.0, 0.0, 0.0),
        direction=obj.normal_direction,
        i_size=obj.width_m,
        j_size=obj.height_m,
    )


def _cylinder_mesh(obj: Cylinder) -> pv.PolyData:
    return pv.Cylinder(
        center=(0.0, 0.0, 0.0),
        direction=obj.axis_direction,
        radius=obj.radius_m,
        height=obj.length_m,
    )


def _cone_mesh(obj: Cone) -> pv.PolyData:
    return pv.Cone(
        center=(0.0, 0.0, 0.0),
        direction=obj.apex_direction,
        radius=obj.base_radius_m,
        height=obj.height_m,
    )


def _trihedral_dispatch(obj: Trihedral) -> pv.PolyData:
    return _build_trihedral_mesh(obj.side_length_m, obj.center)


def _wall_mesh(obj: Wall) -> pv.PolyData:
    return pv.Plane(
        center=obj.center,
        direction=obj.normal,
        i_size=obj.width_m,
        j_size=obj.height_m,
    )


def _plane_mesh(obj: Plane) -> pv.PolyData:
    # A 20 m square is enough to read as "ground / reference"
    # without dominating the camera frustum at typical zooms.
    return pv.Plane(
        center=obj.point,
        direction=obj.normal,
        i_size=20.0,
        j_size=20.0,
    )


def _point_mesh(obj: Point) -> pv.PolyData:
    # Tiny sphere so the point mass is visible.
    del obj
    return pv.Sphere(radius=0.05)


# ---------------------------------------------------------------------
# Pre-register the 9 built-in visual kinds.
# ---------------------------------------------------------------------


register_visual_kind_builder("sphere", _sphere_mesh)
register_visual_kind_builder("cube", _cube_mesh)
register_visual_kind_builder("plate", _plate_mesh)
register_visual_kind_builder("cylinder", _cylinder_mesh)
register_visual_kind_builder("cone", _cone_mesh)
register_visual_kind_builder("trihedral", _trihedral_dispatch)
register_visual_kind_builder("wall", _wall_mesh)
register_visual_kind_builder("plane", _plane_mesh)
register_visual_kind_builder("point", _point_mesh)


def _build_trihedral_mesh(
    side: float,
    center: tuple[float, float, float],
) -> pv.PolyData:
    """3-face corner reflector: three squares meeting at the inner corner.

    Each face lies in one of the three coordinate planes and shares
    one edge with the other two faces. ``side`` is the length of each
    face's edge.
    """
    cx, cy, cz = center
    half = side / 2.0
    xy = pv.Plane(
        center=(cx + half, cy + half, cz),
        direction=(0.0, 0.0, 1.0),
        i_size=side,
        j_size=side,
    )
    yz = pv.Plane(
        center=(cx, cy + half, cz + half),
        direction=(1.0, 0.0, 0.0),
        i_size=side,
        j_size=side,
    )
    xz = pv.Plane(
        center=(cx + half, cy, cz + half),
        direction=(0.0, 1.0, 0.0),
        i_size=side,
        j_size=side,
    )
    # ``PolyData.merge`` returns ``Any`` in pyvista 0.48 stubs; the
    # runtime value is a fresh PolyData, so we narrow here.
    merged: pv.PolyData = xy.merge(yz).merge(xz)
    return merged


class TestObject3DPanel(QWidget):
    # Block pytest from treating this Qt widget as a test class.
    __test__ = False

    """PyVista QtInteractor wrapped as a Qt widget.

    Public API:
        :meth:`set_test_object(obj)` — clear, add the mesh, reset
            the camera so the object fills the frame.
        :meth:`clear()` — remove the current mesh.
        :meth:`current_object()` — most-recently-set :class:`TestObject`
            or ``None`` after a :meth:`clear`.
        :meth:`interactor()` — the underlying
            :class:`pyvistaqt.QtInteractor` (tests only).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_TestObject3DPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._interactor = QtInteractor(self)
        self._interactor.setObjectName("PhysicsLab_TestObjectInteractor")
        layout.addWidget(self._interactor)
        self._current: TestObject | None = None

    def interactor(self) -> QtInteractor:
        return self._interactor

    def current_object(self) -> TestObject | None:
        return self._current

    def set_test_object(self, obj: TestObject) -> None:
        self._interactor.clear()
        mesh = build_test_object_mesh(obj)
        self._interactor.add_mesh(mesh, show_edges=True, color="lightblue")
        self._interactor.reset_camera()
        self._current = obj

    def clear(self) -> None:
        self._interactor.clear()
        self._current = None
