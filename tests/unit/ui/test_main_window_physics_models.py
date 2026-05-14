"""MainWindow auto-register physics-model plug-ins (Phase 9 J1)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.app.dlc_runtime import DLCPaths
from workbench.app.physics_lab import unregister_all_physics_models
from workbench.ui.dlc_bootstrap import build_dlc_runtime
from workbench.ui.main_window import MainWindow
from workbench.ui.workspace_selector import Workspace

pytestmark = pytest.mark.qt


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    unregister_all_physics_models()


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _write_physics_model_package(packages_root: Path, *, pkg_id: str, model_name: str) -> None:
    pkg_dir = packages_root / pkg_id
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(
        f"""
[package]
id = "{pkg_id}"
name = "Phys"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.physics_model" = "phys_mod:Model"
""",
        encoding="utf-8",
    )
    (pkg_dir / "phys_mod.py").write_text(
        "class Model:\n"
        f"    name = '{model_name}'\n"
        "    category = 'other'\n"
        "    parameters = ()\n"
        "    time_mode = 'static'\n"
        "    visualization = '2d'\n"
        "    def compute(self, state, params, dt_s):\n"
        "        return dict(state)\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------
# No-runtime path
# ---------------------------------------------------------------------


def test_main_window_no_dlc_has_no_discovery_result(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert win.physics_discovery_result() is None
    # PhysicsLabWorkspace 가 default None → 3 built-in.
    phys = win.page(Workspace.PHYSICS_LAB)
    assert len(phys.physics_models()) == 3  # type: ignore[attr-defined]


# ---------------------------------------------------------------------
# With-runtime path
# ---------------------------------------------------------------------


def test_main_window_with_dlc_registers_physics_model_plugin(  # type: ignore[no-untyped-def]
    qtbot, tmp_path: Path
) -> None:
    packages_root = tmp_path / "packages"
    packages_root.mkdir()
    _write_physics_model_package(packages_root, pkg_id="phys-pkg-a", model_name="dlc_model_a")

    paths = DLCPaths(packages_root=packages_root, user_root=None, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    win = MainWindow(dlc_runtime=runtime, enable_3d_viewer=False)
    qtbot.addWidget(win)
    result = win.physics_discovery_result()
    assert result is not None
    assert result.registered_count == 1
    assert result.errors == ()

    phys = win.page(Workspace.PHYSICS_LAB)
    names = {m.name for m in phys.physics_models()}  # type: ignore[attr-defined]
    assert "dlc_model_a" in names
    # Built-ins still present.
    assert len(names) == 4


def test_main_window_with_two_dlc_physics_packages(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    packages_root = tmp_path / "packages"
    packages_root.mkdir()
    _write_physics_model_package(packages_root, pkg_id="phys-pkg-a", model_name="dlc_a")
    _write_physics_model_package(packages_root, pkg_id="phys-pkg-b", model_name="dlc_b")

    paths = DLCPaths(packages_root=packages_root, user_root=None, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    win = MainWindow(dlc_runtime=runtime, enable_3d_viewer=False)
    qtbot.addWidget(win)

    phys = win.page(Workspace.PHYSICS_LAB)
    names = {m.name for m in phys.physics_models()}  # type: ignore[attr-defined]
    assert {"dlc_a", "dlc_b"}.issubset(names)
    assert len(names) == 5


def test_main_window_with_dlc_but_no_physics_models(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Runtime that's mounted but ships no trsim.physics_model slot.
    discovery_result is non-None but registered_count == 0."""
    packages_root = tmp_path / "ghost"  # missing dir
    paths = DLCPaths(packages_root=packages_root, user_root=None, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)
    win = MainWindow(dlc_runtime=runtime, enable_3d_viewer=False)
    qtbot.addWidget(win)
    result = win.physics_discovery_result()
    assert result is not None
    assert result.registered_count == 0
    phys = win.page(Workspace.PHYSICS_LAB)
    assert len(phys.physics_models()) == 3  # type: ignore[attr-defined]
