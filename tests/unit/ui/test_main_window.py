"""Unit tests for workbench.ui.main_window (Phase 4.1 + 4.2a)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QKeySequence

from workbench.ui.commands.palette import CommandPalette
from workbench.ui.editor.workspace import EditorWorkspace
from workbench.ui.main_window import MainWindow
from workbench.ui.simulator.workspace import SimulatorWorkspace
from workbench.ui.workspace_selector import Workspace

pytestmark = pytest.mark.qt


def test_main_window_default_workspace_is_editor(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.physics_lab import PhysicsLabWorkspace

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert win.selector.current == Workspace.EDITOR
    assert isinstance(win.page(Workspace.EDITOR), EditorWorkspace)
    assert isinstance(win.page(Workspace.SIMULATOR), SimulatorWorkspace)
    assert isinstance(win.page(Workspace.PHYSICS_LAB), PhysicsLabWorkspace)
    assert win.workspace_action(Workspace.EDITOR).isChecked()
    assert not win.workspace_action(Workspace.SIMULATOR).isChecked()
    assert not win.workspace_action(Workspace.PHYSICS_LAB).isChecked()


def test_main_window_switches_to_physics_lab(qtbot) -> None:  # type: ignore[no-untyped-def]
    """PL-A: Ctrl+Shift+L lands on the Physics Lab workspace page."""
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    win.selector.set_workspace(Workspace.PHYSICS_LAB)
    central = win.centralWidget()
    assert central.currentWidget() is win.page(Workspace.PHYSICS_LAB)
    assert win.workspace_action(Workspace.PHYSICS_LAB).isChecked()


def test_sim_toolbars_hidden_outside_simulator_workspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Option A: Sim + Target toolbars are Simulator-workspace-only."""
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    # Default Editor workspace -> toolbars hidden.
    assert win.simulation_toolbar().isVisibleTo(win) is False
    assert win.target_run_toolbar().isVisibleTo(win) is False
    # Switching to Simulator brings them back.
    win.selector.set_workspace(Workspace.SIMULATOR)
    assert win.simulation_toolbar().isVisibleTo(win) is True
    assert win.target_run_toolbar().isVisibleTo(win) is True
    # Physics Lab hides them again.
    win.selector.set_workspace(Workspace.PHYSICS_LAB)
    assert win.simulation_toolbar().isVisibleTo(win) is False
    assert win.target_run_toolbar().isVisibleTo(win) is False


def test_set_workspace_swaps_central_page_and_action_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    win.selector.set_workspace(Workspace.SIMULATOR)

    central = win.centralWidget()
    assert central.currentWidget() is win.page(Workspace.SIMULATOR)
    assert win.workspace_action(Workspace.SIMULATOR).isChecked()
    assert not win.workspace_action(Workspace.EDITOR).isChecked()


def test_workspace_toolbar_actions_carry_no_shortcut(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Toolbar QActions are click-only; MainMenuBar owns the shortcuts.

    Registering the same shortcut on the toolbar QAction *and* the
    MainMenuBar QAction makes Qt flag them as ambiguous and disable
    both — that bug shipped through Phase 4.2c and was reported as
    "Ctrl+Shift+E/S do not work" in MVP verification.
    """
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    editor_act = win.workspace_action(Workspace.EDITOR)
    sim_act = win.workspace_action(Workspace.SIMULATOR)
    assert editor_act.shortcut() == QKeySequence()
    assert sim_act.shortcut() == QKeySequence()


def test_main_menu_owns_workspace_and_palette_shortcuts(qtbot) -> None:  # type: ignore[no-untyped-def]
    """MainMenuBar holds the single source of truth for shortcuts."""
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    menu_bar = win.main_menu_bar()
    expected = {
        "MenuAction_workspace.switch_to_editor": QKeySequence("Ctrl+Shift+E"),
        "MenuAction_workspace.switch_to_simulator": QKeySequence("Ctrl+Shift+S"),
        "MenuAction_workspace.switch_to_physics_lab": QKeySequence("Ctrl+Shift+L"),
        "MenuAction_palette.open": QKeySequence("Ctrl+Shift+P"),
    }
    found = {
        a.objectName(): a.shortcut()
        for a in menu_bar.findChildren(type(menu_bar.actions()[0]))
        if a.objectName() in expected
    }
    for key, seq in expected.items():
        assert found.get(key) == seq, f"{key} expected {seq.toString()}, got {found.get(key)}"


def test_window_title_includes_version(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench import __version__

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert __version__ in win.windowTitle()


def test_triggering_action_updates_selector(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    with qtbot.waitSignal(win.selector.workspace_changed, timeout=500) as blocker:
        win.workspace_action(Workspace.SIMULATOR).trigger()
    assert blocker.args == [Workspace.SIMULATOR]
    assert win.selector.current == Workspace.SIMULATOR


# ---------- Phase 4.2a — Command Palette ----------


def test_main_window_seeds_command_registry_with_workspace_and_palette(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    ids = {cmd.id for cmd in win.commands.all()}
    assert {
        "workspace.switch_to_editor",
        "workspace.switch_to_simulator",
        "palette.open",
    } <= ids


def test_command_palette_dispatches_workspace_switch(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert win.selector.current == Workspace.EDITOR
    win.commands.dispatch("workspace.switch_to_simulator")
    assert win.selector.current == Workspace.SIMULATOR


def test_open_command_palette_shows_dialog(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    palette = win.command_palette()
    assert isinstance(palette, CommandPalette)
    assert palette.isVisible() is False
    win.open_command_palette()
    assert palette.isVisible() is True
    palette.close()


# ---------- Phase 4.2b — Sim / Target toolbars ----------


def test_main_window_mounts_sim_and_target_toolbars(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.toolbars.simulation_toolbar import SimulationToolbar
    from workbench.ui.toolbars.target_run_toolbar import TargetRunToolbar

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    assert isinstance(win.simulation_toolbar(), SimulationToolbar)
    assert isinstance(win.target_run_toolbar(), TargetRunToolbar)


def test_main_window_registers_full_phase_4_2_command_set(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    ids = {cmd.id for cmd in win.commands.all()}
    assert {
        "sim.start",
        "sim.pause",
        "sim.stop",
        "sim.speed.x1",
        "sim.speed.x2",
        "sim.speed.x4",
        "sim.speed.x8",
        "target.run",
        "target.pause",
        "target.stop",
    } <= ids


def test_sim_lifecycle_button_dispatches_via_registry(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    # No-op hook for sim.start at Phase 4.2b — must not raise.
    win.simulation_toolbar().lifecycle_action("sim.start").trigger()


# ---------- Phase 4.2c — MenuBar ----------


def test_main_window_mounts_menu_bar(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtWidgets import QMenuBar

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    bar = win.main_menu_bar()
    assert isinstance(bar, QMenuBar)
    assert bar is win.menuBar()


def test_menu_bar_has_seven_top_level_menus(qtbot) -> None:  # type: ignore[no-untyped-def]
    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    titles = [a.text() for a in win.main_menu_bar().actions() if a.menu() is not None]
    assert titles == ["&File", "&Edit", "&View", "&Run", "&Plugins", "&Tools", "&Help"]


# ---------- Phase 4.2d — DockManager ----------


def test_main_window_owns_dock_manager(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.dock_manager import DockManager

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    mgr = win.dock_manager()
    assert isinstance(mgr, DockManager)
    assert mgr.host is win
    # Phase 4.2d ships an empty registry; Phase 4.3+ panels populate it.
    assert len(mgr) == 0


# ---------- Phase 4.3 — Editor Activity dispatch ----------


def test_activity_command_switches_to_editor_workspace_and_activity(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activities import Activity

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    # Start in Simulator to confirm the command also flips the workspace.
    win.selector.set_workspace(Workspace.SIMULATOR)
    assert win.selector.current is Workspace.SIMULATOR
    win.commands.dispatch("editor.activity.radar")
    assert win.selector.current is Workspace.EDITOR
    editor = win.page(Workspace.EDITOR)
    assert editor.selector.current is Activity.RADAR  # type: ignore[attr-defined]


def test_every_activity_command_is_dispatchable(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activities import Activity

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    editor = win.page(Workspace.EDITOR)
    for cid, activity in (
        ("editor.activity.composer", Activity.COMPOSER),
        ("editor.activity.map", Activity.MAP),
        ("editor.activity.radar", Activity.RADAR),
        ("editor.activity.targets", Activity.TARGETS),
        ("editor.activity.browser", Activity.BROWSER),
    ):
        win.commands.dispatch(cid)
        assert editor.selector.current is activity  # type: ignore[attr-defined]
