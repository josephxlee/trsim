"""Test Object plugin registry tests (PL-9.3e, plan/19 § 19.7.4)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyvista")
pytest.importorskip("pyvistaqt")

import pyvista as pv

from workbench.sdk.protocols import TestObjectProtocol
from workbench.ui.physics_lab.custom_test_objects import (
    Pyramid,
    register_custom_test_objects,
)
from workbench.ui.physics_lab.test_object_view import (
    build_test_object_mesh,
    register_visual_kind_builder,
    registered_visual_kinds,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Registry default state — built-ins pre-registered.
# ---------------------------------------------------------------------


def test_builtins_pre_registered() -> None:
    kinds = registered_visual_kinds()
    for kind in (
        "sphere",
        "cube",
        "plate",
        "cylinder",
        "cone",
        "trihedral",
        "wall",
        "plane",
        "point",
    ):
        assert kind in kinds


def test_register_visual_kind_builder_adds_to_registry() -> None:
    def trivial_builder(obj: object) -> pv.PolyData:
        del obj
        return pv.Sphere(radius=0.1)

    try:
        register_visual_kind_builder("__test_kind__", trivial_builder)
        assert "__test_kind__" in registered_visual_kinds()
    finally:
        # Tidy up so other tests do not see the kind.
        from workbench.ui.physics_lab.test_object_view import (
            _VISUAL_KIND_BUILDERS,
        )

        _VISUAL_KIND_BUILDERS.pop("__test_kind__", None)


def test_register_visual_kind_builder_overwrites_existing() -> None:
    def first_builder(obj: object) -> pv.PolyData:
        del obj
        return pv.Sphere(radius=0.1)

    def second_builder(obj: object) -> pv.PolyData:
        del obj
        return pv.Cube(x_length=0.2, y_length=0.2, z_length=0.2)

    try:
        register_visual_kind_builder("__shadow__", first_builder)
        register_visual_kind_builder("__shadow__", second_builder)
        from workbench.ui.physics_lab.test_object_view import (
            _VISUAL_KIND_BUILDERS,
        )

        assert _VISUAL_KIND_BUILDERS["__shadow__"] is second_builder
    finally:
        from workbench.ui.physics_lab.test_object_view import (
            _VISUAL_KIND_BUILDERS,
        )

        _VISUAL_KIND_BUILDERS.pop("__shadow__", None)


def test_unknown_visual_kind_raises() -> None:
    class Bogus:
        name = "bogus"
        visual = "__not-a-real-kind__"

    with pytest.raises(ValueError, match=r"Unknown Test Object visual"):
        build_test_object_mesh(Bogus())


def test_object_without_visual_attribute_raises() -> None:
    class NoVisual:
        name = "no-visual"

    with pytest.raises(ValueError, match=r"no 'visual' attribute"):
        build_test_object_mesh(NoVisual())


# ---------------------------------------------------------------------
# Pyramid sample plugin.
# ---------------------------------------------------------------------


def test_pyramid_dataclass_satisfies_test_object_protocol() -> None:
    p = Pyramid(name="pyramid_2m", base_length_m=2.0, height_m=3.0)
    assert isinstance(p, TestObjectProtocol)


def test_pyramid_analytic_rcs_returns_none() -> None:
    p = Pyramid(name="p", base_length_m=1.0, height_m=1.0)
    assert p.analytic_rcs_m2(0.032) is None


def test_pyramid_rejects_invalid_dimensions() -> None:
    with pytest.raises(ValueError, match=r"base_length_m must be > 0"):
        Pyramid(name="p", base_length_m=0.0, height_m=1.0)
    with pytest.raises(ValueError, match=r"height_m must be > 0"):
        Pyramid(name="p", base_length_m=1.0, height_m=-1.0)


def test_pyramid_mesh_not_buildable_before_registration() -> None:
    """Before ``register_custom_test_objects`` is called, the registry
    has no entry for ``"pyramid"`` (unless an earlier test registered
    it). Test isolates by snapshotting + restoring the registry.
    """
    from workbench.ui.physics_lab.test_object_view import _VISUAL_KIND_BUILDERS

    snapshot = _VISUAL_KIND_BUILDERS.pop("pyramid", None)
    try:
        p = Pyramid(name="p", base_length_m=1.0, height_m=1.0)
        with pytest.raises(ValueError, match=r"Unknown Test Object visual"):
            build_test_object_mesh(p)
    finally:
        if snapshot is not None:
            _VISUAL_KIND_BUILDERS["pyramid"] = snapshot


def test_register_custom_test_objects_adds_pyramid_kind() -> None:
    from workbench.ui.physics_lab.test_object_view import _VISUAL_KIND_BUILDERS

    _VISUAL_KIND_BUILDERS.pop("pyramid", None)
    register_custom_test_objects()
    assert "pyramid" in registered_visual_kinds()


def test_pyramid_mesh_dimensions_match_dataclass() -> None:
    register_custom_test_objects()
    p = Pyramid(name="p", base_length_m=2.0, height_m=3.0)
    mesh = build_test_object_mesh(p)
    bounds = mesh.bounds
    # Base extends [-1, 1] on x + y; apex at z=3, base at z=0.
    assert bounds[0] == pytest.approx(-1.0)
    assert bounds[1] == pytest.approx(1.0)
    assert bounds[2] == pytest.approx(-1.0)
    assert bounds[3] == pytest.approx(1.0)
    assert bounds[4] == pytest.approx(0.0)
    assert bounds[5] == pytest.approx(3.0)


def test_pyramid_mesh_returns_polydata() -> None:
    register_custom_test_objects()
    p = Pyramid(name="p", base_length_m=1.0, height_m=1.0)
    mesh = build_test_object_mesh(p)
    assert isinstance(mesh, pv.PolyData)
    assert mesh.n_points == 5  # 4 base + 1 apex
