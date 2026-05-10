"""Unit tests for workbench.ui.workspace_selector (Phase 4.1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.workspace_selector import Workspace, WorkspaceSelector

pytestmark = pytest.mark.qt


def test_default_initial_workspace_is_editor(qtbot: object) -> None:
    sel = WorkspaceSelector()
    assert sel.current == Workspace.EDITOR


def test_explicit_initial_workspace_is_honoured(qtbot: object) -> None:
    sel = WorkspaceSelector(initial=Workspace.SIMULATOR)
    assert sel.current == Workspace.SIMULATOR


def test_set_workspace_emits_signal_on_change(qtbot) -> None:  # type: ignore[no-untyped-def]
    sel = WorkspaceSelector()
    with qtbot.waitSignal(sel.workspace_changed, timeout=500) as blocker:
        changed = sel.set_workspace(Workspace.SIMULATOR)
    assert changed is True
    assert blocker.args == [Workspace.SIMULATOR]
    assert sel.current == Workspace.SIMULATOR


def test_set_same_workspace_is_idempotent(qtbot) -> None:  # type: ignore[no-untyped-def]
    sel = WorkspaceSelector(initial=Workspace.EDITOR)
    received: list[Workspace] = []
    sel.workspace_changed.connect(received.append)
    changed = sel.set_workspace(Workspace.EDITOR)
    assert changed is False
    assert received == []


def test_toggle_cycles_editor_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    sel = WorkspaceSelector(initial=Workspace.EDITOR)
    assert sel.toggle() == Workspace.SIMULATOR
    assert sel.toggle() == Workspace.EDITOR


def test_workspace_enum_values_are_stable_strings() -> None:
    # Persisted in layout state — must not change without a migration.
    assert Workspace.EDITOR.value == "editor"
    assert Workspace.SIMULATOR.value == "simulator"
