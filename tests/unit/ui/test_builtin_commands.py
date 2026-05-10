"""Unit tests for workbench.ui.commands.builtin (Phase 4.2b)."""

from __future__ import annotations

import pytest

from workbench.ui.commands.builtin import (
    SIM_SPEEDS,
    CommandHooks,
    register_builtin_commands,
)
from workbench.ui.commands.registry import WorkbenchCommandRegistry


def _seeded_registry() -> tuple[WorkbenchCommandRegistry, dict[str, list[object]]]:
    calls: dict[str, list[object]] = {
        "editor": [],
        "sim_start": [],
        "sim_pause": [],
        "sim_stop": [],
        "sim_speed": [],
        "target_run": [],
        "target_pause": [],
        "target_stop": [],
        "palette": [],
        "simulator": [],
        "act_composer": [],
        "act_map": [],
        "act_radar": [],
        "act_targets": [],
        "act_browser": [],
    }
    hooks = CommandHooks(
        on_workspace_editor=lambda: calls["editor"].append(None),
        on_workspace_simulator=lambda: calls["simulator"].append(None),
        on_palette_open=lambda: calls["palette"].append(None),
        on_sim_start=lambda: calls["sim_start"].append(None),
        on_sim_pause=lambda: calls["sim_pause"].append(None),
        on_sim_stop=lambda: calls["sim_stop"].append(None),
        on_sim_speed=lambda m: calls["sim_speed"].append(m),
        on_target_run=lambda: calls["target_run"].append(None),
        on_target_pause=lambda: calls["target_pause"].append(None),
        on_target_stop=lambda: calls["target_stop"].append(None),
        on_activity_composer=lambda: calls["act_composer"].append(None),
        on_activity_map=lambda: calls["act_map"].append(None),
        on_activity_radar=lambda: calls["act_radar"].append(None),
        on_activity_targets=lambda: calls["act_targets"].append(None),
        on_activity_browser=lambda: calls["act_browser"].append(None),
    )
    reg = WorkbenchCommandRegistry()
    register_builtin_commands(reg, hooks)
    return reg, calls


def test_register_creates_every_phase_4_2_command() -> None:
    reg, _ = _seeded_registry()
    expected = {
        # Phase 4.2a
        "workspace.switch_to_editor",
        "workspace.switch_to_simulator",
        "palette.open",
        # Phase 4.2b
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
        # Phase 4.2c
        "file.new",
        "file.open",
        "file.save",
        "file.exit",
        "view.reset_layout",
        "view.toggle_fullscreen",
        "plugins.manage",
        "plugins.reload_all",
        "help.about",
        # Phase 4.3
        "editor.activity.composer",
        "editor.activity.map",
        "editor.activity.radar",
        "editor.activity.targets",
        "editor.activity.browser",
    }
    assert {cmd.id for cmd in reg.all()} == expected


def test_phase_4_3_activity_shortcuts_are_ctrl_one_through_five() -> None:
    reg, _ = _seeded_registry()
    assert reg.get("editor.activity.composer").shortcut == "Ctrl+1"
    assert reg.get("editor.activity.map").shortcut == "Ctrl+2"
    assert reg.get("editor.activity.radar").shortcut == "Ctrl+3"
    assert reg.get("editor.activity.targets").shortcut == "Ctrl+4"
    assert reg.get("editor.activity.browser").shortcut == "Ctrl+5"


def test_phase_4_3_activity_hooks_dispatch_in_isolation() -> None:
    reg, calls = _seeded_registry()
    reg.dispatch("editor.activity.radar")
    reg.dispatch("editor.activity.targets")
    assert calls["act_radar"] == [None]
    assert calls["act_targets"] == [None]
    assert calls["act_composer"] == []
    assert calls["act_browser"] == []


def test_phase_4_2c_shortcuts_match_plan_05() -> None:
    reg, _ = _seeded_registry()
    assert reg.get("file.new").shortcut == "Ctrl+N"
    assert reg.get("file.open").shortcut == "Ctrl+O"
    assert reg.get("file.save").shortcut == "Ctrl+S"
    assert reg.get("file.exit").shortcut == "Ctrl+Q"
    assert reg.get("view.toggle_fullscreen").shortcut == "F11"


def test_default_command_hooks_are_noops() -> None:
    reg = WorkbenchCommandRegistry()
    register_builtin_commands(reg, CommandHooks())
    # Every dispatch must succeed and return None.
    for cmd in reg.all():
        reg.dispatch(cmd.id)


def test_sim_speed_hook_receives_multiplier() -> None:
    reg, calls = _seeded_registry()
    for multiplier in SIM_SPEEDS:
        reg.dispatch(f"sim.speed.x{multiplier}")
    assert calls["sim_speed"] == list(SIM_SPEEDS)


def test_lifecycle_hooks_dispatch_in_isolation() -> None:
    reg, calls = _seeded_registry()
    reg.dispatch("sim.start")
    reg.dispatch("target.run")
    reg.dispatch("target.stop")
    assert calls["sim_start"] == [None]
    assert calls["target_run"] == [None]
    assert calls["target_stop"] == [None]
    # Untouched.
    assert calls["sim_pause"] == []
    assert calls["sim_stop"] == []


def test_shortcut_strings_match_plan_05_section_5_5_3() -> None:
    reg, _ = _seeded_registry()
    assert reg.get("sim.start").shortcut == "Shift+Space"
    assert reg.get("sim.stop").shortcut == "Ctrl+Space"
    assert reg.get("target.run").shortcut == "Space"
    assert reg.get("target.stop").shortcut == "Shift+Ctrl+Space"
    assert reg.get("palette.open").shortcut == "Ctrl+Shift+P"
    assert reg.get("sim.speed.x4").shortcut == "4"


@pytest.mark.parametrize("multiplier", SIM_SPEEDS)
def test_speed_command_carries_correct_multiplier(multiplier: int) -> None:
    reg, calls = _seeded_registry()
    reg.dispatch(f"sim.speed.x{multiplier}")
    assert calls["sim_speed"] == [multiplier]
