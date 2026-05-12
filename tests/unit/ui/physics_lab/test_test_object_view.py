"""Test Object 3D viewer tests (PL-9.1d, plan/19 § 19.7.3).

The pure-Python ``build_test_object_mesh`` function is fully tested
without Qt. The :class:`TestObject3DPanel` only ships one or two
integration tests because each ``QtInteractor`` instance plus
pytest-qt's event-processing tick risks tripping the
``vtkWin32OpenGLRenderWindow: failed to get valid pixel format``
access-violation crash on Windows-headless; the conftest sets
``pyvista.OFF_SCREEN = True`` so single-instance panels survive, but
back-to-back creation across many tests can still race.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyvista")
pytest.importorskip("pyvistaqt")

import pyvista as pv

from workbench.domain.physics_lab import (
    Cone,
    Cube,
    Cylinder,
    Plane,
    Plate,
    Point,
    Sphere,
    Trihedral,
    Wall,
    default_library,
)
from workbench.ui.physics_lab.test_object_view import (
    TestObject3DPanel,
    build_test_object_mesh,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# build_test_object_mesh (pure)
# ---------------------------------------------------------------------


def test_sphere_mesh_bounds_match_radius() -> None:
    mesh = build_test_object_mesh(Sphere(name="s", radius_m=2.0))
    bounds = mesh.bounds
    # bounds is a tuple-like (xmin, xmax, ymin, ymax, zmin, zmax)
    assert bounds[0] == pytest.approx(-2.0, abs=0.05)
    assert bounds[1] == pytest.approx(2.0, abs=0.05)
    assert bounds[5] == pytest.approx(2.0, abs=0.05)


def test_cube_mesh_bounds_match_side_length() -> None:
    mesh = build_test_object_mesh(Cube(name="c", side_length_m=4.0))
    bounds = mesh.bounds
    assert bounds[0] == pytest.approx(-2.0)
    assert bounds[1] == pytest.approx(2.0)
    assert bounds[5] == pytest.approx(2.0)


def test_plate_mesh_is_flat_polydata() -> None:
    mesh = build_test_object_mesh(
        Plate(name="p", width_m=2.0, height_m=3.0, normal_direction=(0.0, 0.0, 1.0))
    )
    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_points > 0


def test_cylinder_mesh_length_matches_axis() -> None:
    mesh = build_test_object_mesh(
        Cylinder(name="cyl", radius_m=0.5, length_m=4.0, axis_direction=(0.0, 0.0, 1.0))
    )
    bounds = mesh.bounds
    assert bounds[5] - bounds[4] == pytest.approx(4.0, abs=0.1)


def test_cone_mesh_n_points_positive() -> None:
    mesh = build_test_object_mesh(
        Cone(name="cn", base_radius_m=0.5, height_m=2.0, apex_direction=(0.0, 0.0, 1.0))
    )
    assert mesh.n_points > 0


def test_trihedral_mesh_has_three_plates_worth_of_points() -> None:
    """Three perpendicular plates merged via :meth:`pv.PolyData.merge`."""
    side = 1.0
    mesh = build_test_object_mesh(Trihedral(name="tri", side_length_m=side, center=(0.0, 0.0, 0.0)))
    # A single pv.Plane defaults to 121 points (11x11). 3 merged
    # should land somewhere near 363 (allowing pyvista version drift).
    assert mesh.n_points >= 200


def test_wall_mesh_bounds_match_dimensions() -> None:
    mesh = build_test_object_mesh(
        Wall(
            name="w",
            width_m=4.0,
            height_m=2.0,
            center=(0.0, 0.0, 0.0),
            normal=(0.0, 0.0, 1.0),
        )
    )
    bounds = mesh.bounds
    assert bounds[1] - bounds[0] == pytest.approx(4.0, abs=0.05)
    assert bounds[3] - bounds[2] == pytest.approx(2.0, abs=0.05)


def test_plane_mesh_is_large_reference_square() -> None:
    mesh = build_test_object_mesh(
        Plane(name="floor", point=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0))
    )
    bounds = mesh.bounds
    # Plane is sized as a 20m square in the implementation.
    assert bounds[1] - bounds[0] == pytest.approx(20.0, abs=0.5)


def test_point_mesh_is_small_sphere() -> None:
    mesh = build_test_object_mesh(Point(name="pt", mass_kg=1.0))
    bounds = mesh.bounds
    # Small visualisation sphere, radius 0.05.
    assert bounds[1] - bounds[0] == pytest.approx(0.1, abs=0.02)


def test_every_default_library_object_builds_a_mesh() -> None:
    for obj in default_library():
        mesh = build_test_object_mesh(obj)
        assert isinstance(mesh, pv.PolyData)
        assert mesh.n_points > 0


# ---------------------------------------------------------------------
# TestObject3DPanel — construction-only check.
#
# Anything that triggers an actual VTK render (``set_test_object``,
# ``clear``, library-driven swap) crashes on Windows-headless because
# ``vtkWin32OpenGLRenderWindow`` cannot acquire a valid pixel format
# even with ``pyvista.OFF_SCREEN = True`` set. The user's machine has
# a real display and works fine; CI / sandboxed runs do not. We cover
# the data path via the mesh-builder tests above and assert
# construction succeeds here.
# ---------------------------------------------------------------------


def test_panel_construction_succeeds(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = TestObject3DPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    assert panel.current_object() is None
    assert panel.interactor() is not None


# ---------------------------------------------------------------------
# PhysicsLabWorkspace 3D wiring
# ---------------------------------------------------------------------


def test_workspace_with_disabled_viewer_skips_panel_creation(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.physics_lab import PhysicsLabWorkspace

    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.test_object_panel() is None
    assert ws.viz_stack().count() == 1


def test_workspace_with_disabled_viewer_ignores_test_object_selection(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """Selecting a Test Object in the Library when the 3D viewer is
    disabled must not crash and must not raise (workspace just leaves
    the viz stack on the 2D plot).
    """
    from workbench.ui.physics_lab import PhysicsLabWorkspace

    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    # Click the sphere row -> handler returns early since panel is None.
    for row in range(ws.library_panel().list_widget().count()):
        text = ws.library_panel().list_widget().item(row).text()
        if "(sphere)" in text:
            ws.library_panel().list_widget().setCurrentRow(row)
            break
    # The 2D plot is the only widget in the stack.
    assert ws.current_viz_widget() is ws.viz_panel()


def test_library_round_trips_label_to_test_object(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``LibraryWidget.test_object_for`` resolves the row label back to
    the dataclass for every Test Object in the catalogue, and returns
    ``None`` for the Bouncing Ball row.
    """
    from workbench.ui.physics_lab import LibraryWidget

    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.test_object_for(LibraryWidget.BOUNCING_BALL_ROW) is None
    # Each ``default_library`` call returns fresh frozen-dataclass
    # instances, so we compare by value (the dataclasses are
    # ``frozen=True`` with the default ``__eq__``).
    for obj in default_library():
        label = f"{obj.name}  ({obj.visual})"
        assert lib.test_object_for(label) == obj
    # Unknown labels return None.
    assert lib.test_object_for("not-a-row") is None
