"""Unit tests for workbench.ui.main_menu (Phase 4.2c)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QMainWindow

from workbench.ui.commands.builtin import (
    SIM_SPEEDS,
    CommandHooks,
    register_builtin_commands,
)
from workbench.ui.commands.registry import WorkbenchCommandRegistry
from workbench.ui.main_menu import MainMenuBar

pytestmark = pytest.mark.qt


@pytest.fixture
def menu_fixture(qtbot):  # type: ignore[no-untyped-def]
    """Build a host QMainWindow + MainMenuBar wired to a calls dict.

    QMainWindow takes ownership of the bar via :meth:`setMenuBar` and
    the bar holds strong refs to every QMenu so sub-menus survive the
    test (no libshiboken "C++ object already deleted" failures).
    """
    win = QMainWindow()
    qtbot.addWidget(win)
    calls: dict[str, list[object]] = {
        "file_new": [],
        "file_open": [],
        "file_save": [],
        "file_exit": [],
        "view_reset": [],
        "view_fs": [],
        "plugins_manage": [],
        "plugins_reload": [],
        "help_about": [],
        "sim_start": [],
        "target_run": [],
    }
    hooks = CommandHooks(
        on_file_new=lambda: calls["file_new"].append(None),
        on_file_open=lambda: calls["file_open"].append(None),
        on_file_save=lambda: calls["file_save"].append(None),
        on_file_exit=lambda: calls["file_exit"].append(None),
        on_view_reset_layout=lambda: calls["view_reset"].append(None),
        on_view_toggle_fullscreen=lambda: calls["view_fs"].append(None),
        on_plugins_manage=lambda: calls["plugins_manage"].append(None),
        on_plugins_reload_all=lambda: calls["plugins_reload"].append(None),
        on_help_about=lambda: calls["help_about"].append(None),
        on_sim_start=lambda: calls["sim_start"].append(None),
        on_target_run=lambda: calls["target_run"].append(None),
    )
    reg = WorkbenchCommandRegistry()
    register_builtin_commands(reg, hooks)
    bar = MainMenuBar(win, reg)
    win.setMenuBar(bar)
    return win, bar, calls


def test_top_level_menu_titles_match_plan_05_section_5_2(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    titles = [a.text() for a in bar.actions() if a.menu() is not None]
    assert titles == ["&File", "&Edit", "&View", "&Run", "&Plugins", "&Tools", "&Help"]


def test_file_menu_dispatches_each_command(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, calls = menu_fixture
    for command_id, key in (
        ("file.new", "file_new"),
        ("file.open", "file_open"),
        ("file.save", "file_save"),
        ("file.exit", "file_exit"),
    ):
        bar.action_for(command_id).trigger()
        assert calls[key] == [None]


def test_run_menu_includes_sim_target_and_speed_submenu(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    for cid in ("sim.start", "sim.pause", "sim.stop", "target.run", "target.pause", "target.stop"):
        bar.action_for(cid)
    speed = bar.speed_submenu()
    assert speed.objectName() == "MenuRunSpeed"
    speed_ids = {a.objectName() for a in speed.actions()}
    assert speed_ids == {f"MenuAction_sim.speed.x{m}" for m in SIM_SPEEDS}


def test_view_menu_exposes_workspace_switch_and_palette(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    for cid in (
        "workspace.switch_to_editor",
        "workspace.switch_to_simulator",
        "palette.open",
        "view.reset_layout",
        "view.toggle_fullscreen",
    ):
        bar.action_for(cid)


def test_help_menu_has_about(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, calls = menu_fixture
    bar.action_for("help.about").trigger()
    assert calls["help_about"] == [None]


def test_action_shortcut_inherits_from_command(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    assert bar.action_for("file.open").shortcut() == QKeySequence("Ctrl+O")
    assert bar.action_for("view.toggle_fullscreen").shortcut() == QKeySequence("F11")


def test_edit_and_tools_menus_are_empty_placeholders(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    assert bar.menu_for("edit").actions() == []
    assert bar.menu_for("tools").actions() == []


def test_menu_for_rejects_unknown_key(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    with pytest.raises(ValueError, match=r"unknown menu key"):
        bar.menu_for("nope")


def test_action_for_rejects_unregistered_command(menu_fixture) -> None:  # type: ignore[no-untyped-def]
    _, bar, _ = menu_fixture
    with pytest.raises(KeyError):
        bar.action_for("does.not.exist")
