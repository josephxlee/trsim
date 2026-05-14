"""MainWindow ↔ PackageManagerController wiring (Phase 7 remainder F3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.package_manager_dialog import PackageManagerController
from workbench.ui.main_menu import MainMenuBar
from workbench.ui.main_window import MainWindow

pytestmark = pytest.mark.qt


def test_main_window_creates_dlc_manager_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    ctrl = win.dlc_manager_controller()
    assert isinstance(ctrl, PackageManagerController)


def test_dlc_manager_uses_default_packages_root_without_runtime(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    root = win.dlc_manager_controller().packages_root()
    # Resolves under ~/.trsim/packages (don't pin the literal home).
    assert root.parts[-2:] == (".trsim", "packages")


def test_plugins_manage_menu_action_opens_dialog(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    menu_bar = win.main_menu_bar()
    assert isinstance(menu_bar, MainMenuBar)
    action = menu_bar.action_for("plugins.manage")
    assert action.text() == "Manage Plugins..."

    ctrl = win.dlc_manager_controller()
    assert ctrl.active_dialog() is None
    action.trigger()
    dlg = ctrl.active_dialog()
    assert dlg is not None
    qtbot.addWidget(dlg)


def test_plugins_install_package_menu_entry_exists(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    menu_bar = win.main_menu_bar()
    action = menu_bar.action_for("plugins.install_package")
    assert action.text() == "Install Package..."


def test_plugins_install_package_action_invokes_file_picker(qtbot, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Clicking Install Package... triggers the controller's
    ``install_via_file_picker``. We monkey-patch the file picker on the
    controller after construction so we don't have to spawn a real
    QFileDialog."""
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    ctrl = win.dlc_manager_controller()

    chosen: list[Path] = []

    def fake_picker(_parent: object) -> Path | None:
        chosen.append(tmp_path / "fake.trsim-pkg")
        return None  # Cancel — we only care that the controller hit the picker.

    monkeypatch.setattr(ctrl, "_file_picker", fake_picker)

    menu_bar = win.main_menu_bar()
    menu_bar.action_for("plugins.install_package").trigger()
    assert len(chosen) == 1


def test_dlc_runtime_overrides_packages_root(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    from workbench.app.dlc_runtime import DLCPaths
    from workbench.ui.dlc_bootstrap import build_dlc_runtime

    paths = DLCPaths(
        packages_root=tmp_path / "alt_packages",
        user_root=tmp_path / "user",
        builtin_root=None,
    )
    runtime = build_dlc_runtime(paths=paths)
    win = MainWindow(dlc_runtime=runtime, enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert win.dlc_manager_controller().packages_root() == tmp_path / "alt_packages"
