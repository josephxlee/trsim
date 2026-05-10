"""Unit tests for workbench.ui.toolbars.target_run_toolbar (Phase 4.2b)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.commands.builtin import CommandHooks, register_builtin_commands
from workbench.ui.commands.registry import WorkbenchCommandRegistry
from workbench.ui.toolbars.target_run_toolbar import TargetRunToolbar

pytestmark = pytest.mark.qt


def _seeded_toolbar() -> tuple[TargetRunToolbar, dict[str, list[None]]]:
    calls: dict[str, list[None]] = {"run": [], "pause": [], "stop": []}
    hooks = CommandHooks(
        on_target_run=lambda: calls["run"].append(None),
        on_target_pause=lambda: calls["pause"].append(None),
        on_target_stop=lambda: calls["stop"].append(None),
    )
    reg = WorkbenchCommandRegistry()
    register_builtin_commands(reg, hooks)
    return TargetRunToolbar(reg), calls


def test_lifecycle_actions_trigger_dispatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, calls = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.lifecycle_action("target.run").trigger()
    tb.lifecycle_action("target.pause").trigger()
    tb.lifecycle_action("target.stop").trigger()
    assert calls["run"] == [None]
    assert calls["pause"] == [None]
    assert calls["stop"] == [None]


def test_state_badge_starts_idle(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    assert tb.state_label().text() == "State: IDLE"


@pytest.mark.parametrize("state", ["IDLE", "RUNNING", "PAUSED", "ENDED"])
def test_set_state_accepts_canonical_states(qtbot, state: str) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    tb.set_state(state)
    assert tb.state_label().text() == f"State: {state}"


def test_set_state_rejects_unknown_value(qtbot) -> None:  # type: ignore[no-untyped-def]
    tb, _ = _seeded_toolbar()
    qtbot.addWidget(tb)
    with pytest.raises(ValueError, match=r"unknown run state"):
        tb.set_state("WIZARDING")
