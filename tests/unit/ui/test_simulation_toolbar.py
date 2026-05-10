"""Unit tests for workbench.ui.toolbars.simulation_toolbar (Phase 4.2b)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.commands.builtin import (
    SIM_SPEEDS,
    CommandHooks,
    register_builtin_commands,
)
from workbench.ui.commands.registry import WorkbenchCommandRegistry
from workbench.ui.toolbars.simulation_toolbar import SimulationToolbar

pytestmark = pytest.mark.qt


def _seeded_toolbar() -> tuple[SimulationToolbar, dict[str, list[object]]]:
    calls: dict[str, list[object]] = {"start": [], "pause": [], "stop": [], "speed": []}
    hooks = CommandHooks(
        on_sim_start=lambda: calls["start"].append(None),
        on_sim_pause=lambda: calls["pause"].append(None),
        on_sim_stop=lambda: calls["stop"].append(None),
        on_sim_speed=lambda m: calls["speed"].append(m),
    )
    reg = WorkbenchCommandRegistry()
    register_builtin_commands(reg, hooks)
    return SimulationToolbar(reg), calls


def test_lifecycle_actions_trigger_dispatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, calls = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.lifecycle_action("sim.start").trigger()
    tb.lifecycle_action("sim.pause").trigger()
    tb.lifecycle_action("sim.stop").trigger()
    assert calls["start"] == [None]
    assert calls["pause"] == [None]
    assert calls["stop"] == [None]


def test_default_speed_is_x1_and_does_not_dispatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, calls = _seeded_toolbar()
    qtbot.addWidget(tb)
    assert tb.speed_button(1).isChecked() is True
    assert calls["speed"] == []


def test_clicking_a_speed_radio_dispatches_correct_multiplier(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, calls = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.speed_button(4).setChecked(True)
    assert calls["speed"] == [4]


def test_set_selected_speed_does_not_redispatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, calls = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.set_selected_speed(8)
    assert tb.speed_button(8).isChecked() is True
    assert calls["speed"] == []


def test_set_selected_speed_rejects_unknown_multiplier(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    with pytest.raises(ValueError, match=r"unknown speed"):
        tb.set_selected_speed(3)


def test_actual_ratio_label_is_dash_initially(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    assert tb.actual_label().text() == "actual: -"


def test_set_actual_ratio_updates_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.set_actual_ratio(3.7)
    assert tb.actual_label().text() == "actual: 3.7x"
    tb.set_actual_ratio(None)
    assert tb.actual_label().text() == "actual: -"


def test_speed_radios_form_exclusive_group(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.speed_button(2).setChecked(True)
    tb.speed_button(8).setChecked(True)
    assert sum(tb.speed_button(m).isChecked() for m in SIM_SPEEDS) == 1
    assert tb.speed_button(8).isChecked() is True
