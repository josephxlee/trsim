"""Physics-model discovery from PluginLoader output (Phase 9 I2)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

from workbench.app.dlc import PackageManager, PluginLoader
from workbench.app.dlc.plugin_loader import LoadedPlugin
from workbench.app.physics_lab import (
    PHYSICS_MODEL_SLOT,
    BouncingBallModel,
    GravityOnlyModel,
    physics_models_from_loaded_plugins,
    register_discovered_physics_models,
    registered_physics_models,
    unregister_all_physics_models,
)
from workbench.domain.physics_lab import PhysicsParam


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    unregister_all_physics_models()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


class _StubModel:
    name = "stub_model_v1"
    category = "other"
    parameters: Sequence[PhysicsParam] = ()
    time_mode = "static"
    visualization = "2d"

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        return dict(state)


class _SecondStub:
    name = "stub_model_v2"
    category = "rcs"
    parameters: Sequence[PhysicsParam] = ()
    time_mode = "static"
    visualization = "2d"

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        return dict(state)


class _BrokenInit:
    def __init__(self) -> None:
        msg = "ctor blew up"
        raise RuntimeError(msg)


class _NotAModel:
    """Missing ``name`` etc. — fails the protocol check."""


_MANIFEST_TEMPLATE = """
[package]
id = "{pkg_id}"
name = "Demo"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
{entry_points}
"""


def _write_package(
    root: Path, pkg_id: str, *, entry_points: dict[str, str], files: dict[str, str]
) -> Path:
    pkg_dir = root / pkg_id
    pkg_dir.mkdir(parents=True)
    ep_text = "\n".join(f'"{slot}" = "{target}"' for slot, target in entry_points.items())
    (pkg_dir / "manifest.toml").write_text(
        _MANIFEST_TEMPLATE.format(pkg_id=pkg_id, entry_points=ep_text),
        encoding="utf-8",
    )
    for relpath, body in files.items():
        f = pkg_dir / relpath
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return pkg_dir


# ---------------------------------------------------------------------
# Pure transform — physics_models_from_loaded_plugins
# ---------------------------------------------------------------------


def test_empty_mapping_returns_empty_tuples() -> None:
    models, errors = physics_models_from_loaded_plugins({})
    assert models == ()
    assert errors == ()


def test_slot_missing_in_mapping_is_silent() -> None:
    fake_other = LoadedPlugin(
        slot="trsim.tracker",
        package_id="pkg_a",
        target="mod:T",
        attribute=type("T", (), {}),
    )
    models, errors = physics_models_from_loaded_plugins({"trsim.tracker": (fake_other,)})
    assert models == ()
    assert errors == ()


def test_well_formed_class_loads() -> None:
    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="pkg_a",
        target="mod:Stub",
        attribute=_StubModel,
    )
    models, errors = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (plugin,)})
    assert errors == ()
    assert len(models) == 1
    assert models[0].name == "stub_model_v1"


def test_two_plugins_preserve_loader_order() -> None:
    p1 = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="a", target="m:S1", attribute=_StubModel)
    p2 = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="b", target="m:S2", attribute=_SecondStub)
    models, _ = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (p1, p2)})
    assert [m.name for m in models] == ["stub_model_v1", "stub_model_v2"]


def test_none_attribute_records_error() -> None:
    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="pkg_x",
        target="mod:Missing",
        attribute=None,
    )
    models, errors = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (plugin,)})
    assert models == ()
    assert len(errors) == 1
    assert errors[0].package_id == "pkg_x"
    assert "None" in errors[0].message


def test_instantiation_failure_records_error() -> None:
    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="bad",
        target="mod:BrokenInit",
        attribute=_BrokenInit,
    )
    models, errors = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (plugin,)})
    assert models == ()
    assert len(errors) == 1
    assert "ctor blew up" in errors[0].message


def test_class_not_satisfying_protocol_records_error() -> None:
    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="bad-shape",
        target="mod:NotAModel",
        attribute=_NotAModel,
    )
    models, errors = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (plugin,)})
    assert models == ()
    assert len(errors) == 1
    assert "PhysicsModelProtocol" in errors[0].message


def test_one_bad_doesnt_block_one_good() -> None:
    good = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="g", target="m:S", attribute=_StubModel)
    bad = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="b", target="m:X", attribute=_BrokenInit)
    models, errors = physics_models_from_loaded_plugins({PHYSICS_MODEL_SLOT: (good, bad)})
    assert [m.name for m in models] == ["stub_model_v1"]
    assert len(errors) == 1
    assert errors[0].package_id == "b"


# ---------------------------------------------------------------------
# register_discovered_physics_models — registry side-effect
# ---------------------------------------------------------------------


def test_register_discovered_appends_each_unique() -> None:
    p1 = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="a", target="m:S1", attribute=_StubModel)
    p2 = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="b", target="m:S2", attribute=_SecondStub)
    result = register_discovered_physics_models({PHYSICS_MODEL_SLOT: (p1, p2)})
    assert result.registered_count == 2
    assert {m.name for m in registered_physics_models()} == {
        "stub_model_v1",
        "stub_model_v2",
    }


def test_register_discovered_skips_builtin_name_silently() -> None:
    # Stub claiming the same name as a built-in.
    class _Collide:
        name = GravityOnlyModel().name
        category = "dynamics"
        parameters: Sequence[PhysicsParam] = ()
        time_mode = "dynamic"
        visualization = "2d"

        def compute(
            self,
            state: Mapping[str, Any],
            params: Mapping[str, float],
            dt_s: float | None,
        ) -> Mapping[str, Any]:
            return dict(state)

    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="dup",
        target="m:Collide",
        attribute=_Collide,
    )
    result = register_discovered_physics_models({PHYSICS_MODEL_SLOT: (plugin,)})
    assert result.registered_count == 0
    # Still reported in models[].
    assert len(result.models) == 1


def test_register_discovered_skips_existing_registration() -> None:
    p1 = LoadedPlugin(slot=PHYSICS_MODEL_SLOT, package_id="a", target="m:S1", attribute=_StubModel)
    # First call registers stub_model_v1.
    first = register_discovered_physics_models({PHYSICS_MODEL_SLOT: (p1,)})
    assert first.registered_count == 1
    # Second call with same plugin should not double-register.
    second = register_discovered_physics_models({PHYSICS_MODEL_SLOT: (p1,)})
    assert second.registered_count == 0
    assert len(registered_physics_models()) == 1


def test_register_discovered_passes_errors_through() -> None:
    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT,
        package_id="bad",
        target="m:X",
        attribute=_BrokenInit,
    )
    result = register_discovered_physics_models({PHYSICS_MODEL_SLOT: (plugin,)})
    assert result.registered_count == 0
    assert len(result.errors) == 1


# ---------------------------------------------------------------------
# End-to-end via real PluginLoader
# ---------------------------------------------------------------------


def test_end_to_end_discovery_through_real_plugin_loader(tmp_path: Path) -> None:
    """Real DLC manifest → PluginLoader → discovery → registry."""
    _write_package(
        tmp_path,
        "physics-real",
        entry_points={"trsim.physics_model": "real_model:RealModel"},
        files={
            "real_model.py": (
                "class RealModel:\n"
                "    name = 'real_plug'\n"
                "    category = 'other'\n"
                "    parameters = ()\n"
                "    time_mode = 'static'\n"
                "    visualization = '2d'\n"
                "    def compute(self, state, params, dt_s):\n"
                "        return dict(state)\n"
            )
        },
    )
    mgr = PackageManager(tmp_path)
    mgr.scan()
    loader = PluginLoader(mgr)
    plugins = loader.load_all()
    result = register_discovered_physics_models(plugins)
    assert result.registered_count == 1
    assert any(m.name == "real_plug" for m in registered_physics_models())
    assert result.errors == ()


def test_workspace_default_pulls_in_discovered_models(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``default_physics_models()`` merges builtins + plugins, so the
    workspace's None-default loads everything the DLC registered."""
    pytest.importorskip("PySide6")
    pytest.importorskip("pyqtgraph")
    from workbench.ui.physics_lab import PhysicsLabWorkspace

    plugin = LoadedPlugin(
        slot=PHYSICS_MODEL_SLOT, package_id="a", target="m:S1", attribute=_StubModel
    )
    register_discovered_physics_models({PHYSICS_MODEL_SLOT: (plugin,)})

    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    # 3 built-ins + 1 discovered.
    assert len(ws.physics_models()) == 4
    names = {m.name for m in ws.physics_models()}
    assert "stub_model_v1" in names
    assert {m.name for m in (BouncingBallModel(), GravityOnlyModel())}.issubset(names)
