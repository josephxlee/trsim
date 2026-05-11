"""MainWindow DLC integration tests (Phase 7.6, plan/17 § 17.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.app.dlc_runtime import DLCPaths
from workbench.ui.dlc_bootstrap import build_dlc_runtime
from workbench.ui.editor.resource_browser import ResourceCategory as UICategory
from workbench.ui.main_window import MainWindow
from workbench.ui.workspace_selector import Workspace

pytestmark = pytest.mark.qt


def test_main_window_default_has_no_dlc_runtime(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.dlc_runtime() is None


def test_main_window_with_dlc_runtime_exposes_it(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=None, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)
    win = MainWindow(dlc_runtime=runtime)
    qtbot.addWidget(win)
    assert win.dlc_runtime() is runtime


def test_main_window_populates_editor_sidebar_from_user_resources(  # type: ignore[no-untyped-def]
    qtbot,
    tmp_path: Path,
) -> None:
    user_root = tmp_path / "user"
    radars = user_root / "resources" / "radars"
    radars.mkdir(parents=True)
    (radars / "kuband_naval.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    win = MainWindow(dlc_runtime=runtime)
    qtbot.addWidget(win)

    editor = win.page(Workspace.EDITOR)
    sidebar = editor.resource_browser()  # type: ignore[attr-defined]
    radar_node = sidebar.category_node(UICategory.RADAR)
    assert radar_node.childCount() == 1
    assert "kuband_naval" in radar_node.child(0).text(0)


def test_main_window_without_runtime_leaves_sidebar_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    editor = win.page(Workspace.EDITOR)
    sidebar = editor.resource_browser()  # type: ignore[attr-defined]
    for cat in UICategory:
        assert sidebar.category_node(cat).childCount() == 0
