"""Unit tests for workbench.ui.main_window (Phase 4.1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QKeySequence

from workbench.ui.editor.workspace import EditorWorkspace
from workbench.ui.main_window import MainWindow
from workbench.ui.simulator.workspace import SimulatorWorkspace
from workbench.ui.workspace_selector import Workspace

pytestmark = pytest.mark.qt


def test_main_window_default_workspace_is_editor(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    assert win.selector.current == Workspace.EDITOR
    assert isinstance(win.page(Workspace.EDITOR), EditorWorkspace)
    assert isinstance(win.page(Workspace.SIMULATOR), SimulatorWorkspace)
    assert win.workspace_action(Workspace.EDITOR).isChecked()
    assert not win.workspace_action(Workspace.SIMULATOR).isChecked()


def test_set_workspace_swaps_central_page_and_action_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    win.selector.set_workspace(Workspace.SIMULATOR)

    central = win.centralWidget()
    assert central.currentWidget() is win.page(Workspace.SIMULATOR)
    assert win.workspace_action(Workspace.SIMULATOR).isChecked()
    assert not win.workspace_action(Workspace.EDITOR).isChecked()


def test_workspace_actions_have_expected_shortcuts(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    editor_act = win.workspace_action(Workspace.EDITOR)
    sim_act = win.workspace_action(Workspace.SIMULATOR)
    assert editor_act.shortcut() == QKeySequence("Ctrl+Shift+E")
    assert sim_act.shortcut() == QKeySequence("Ctrl+Shift+S")


def test_window_title_includes_version(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench import __version__

    win = MainWindow()
    qtbot.addWidget(win)
    assert __version__ in win.windowTitle()


def test_triggering_action_updates_selector(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow()
    qtbot.addWidget(win)
    with qtbot.waitSignal(win.selector.workspace_changed, timeout=500) as blocker:
        win.workspace_action(Workspace.SIMULATOR).trigger()
    assert blocker.args == [Workspace.SIMULATOR]
    assert win.selector.current == Workspace.SIMULATOR
