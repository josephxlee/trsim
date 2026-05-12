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


def build_test_object_mesh(obj: TestObject) -> pv.PolyData:
    """Return a PyVista mesh for the given Test Object.

    The mesh is centred at the dataclass's centre (when applicable);
    Sphere / Cube / Cylinder / Cone all centre at the origin since
    their dataclasses do not carry an explicit centre.
    """
    visual = obj.visual
    if visual == "sphere":
        assert isinstance(obj, Sphere)
        return pv.Sphere(radius=obj.radius_m)
    if visual == "cube":
        assert isinstance(obj, Cube)
        a = obj.side_length_m
        return pv.Cube(x_length=a, y_length=a, z_length=a)
    if visual == "plate":
        assert isinstance(obj, Plate)
        return pv.Plane(
            center=(0.0, 0.0, 0.0),
            direction=obj.normal_direction,
            i_size=obj.width_m,
            j_size=obj.height_m,
        )
    if visual == "cylinder":
        assert isinstance(obj, Cylinder)
        return pv.Cylinder(
            center=(0.0, 0.0, 0.0),
            direction=obj.axis_direction,
            radius=obj.radius_m,
            height=obj.length_m,
        )
    if visual == "cone":
        assert isinstance(obj, Cone)
        return pv.Cone(
            center=(0.0, 0.0, 0.0),
            direction=obj.apex_direction,
            radius=obj.base_radius_m,
            height=obj.height_m,
        )
    if visual == "trihedral":
        assert isinstance(obj, Trihedral)
        return _build_trihedral_mesh(obj.side_length_m, obj.center)
    if visual == "wall":
        assert isinstance(obj, Wall)
        return pv.Plane(
            center=obj.center,
            direction=obj.normal,
            i_size=obj.width_m,
            j_size=obj.height_m,
        )
    if visual == "plane":
        assert isinstance(obj, Plane)
        # A 20 m square is enough to read as "ground / reference"
        # without dominating the camera frustum at typical zooms.
        return pv.Plane(
            center=obj.point,
            direction=obj.normal,
            i_size=20.0,
            j_size=20.0,
        )
    if visual == "point":
        assert isinstance(obj, Point)
        # Tiny sphere so the point mass is visible.
        return pv.Sphere(radius=0.05)
    msg = f"Unknown Test Object visual kind: {visual!r}"
    raise ValueError(msg)


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
