"""Unit tests for workbench.ui.commands.palette (Phase 4.2a)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from workbench.ui.commands.palette import CommandPalette
from workbench.ui.commands.registry import (
    WorkbenchCommand,
    WorkbenchCommandRegistry,
)

pytestmark = pytest.mark.qt


def _seed(reg: WorkbenchCommandRegistry, calls: list[str]) -> None:
    for cid, title, cat in (
        ("scenario.open", "Open Scenario", "Scenario"),
        ("scenario.close", "Close Scenario", "Scenario"),
        ("view.toggle_panel", "Toggle Panel", "View"),
        ("sim.start", "Start Simulation", "Simulation"),
    ):
        reg.register(
            WorkbenchCommand(
                id=cid,
                title=title,
                category=cat,
                execute=lambda c=cid: calls.append(c),
            )
        )


def test_palette_lists_all_commands_when_search_is_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    _seed(reg, [])
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    assert pal.result_list().count() == 4
    assert pal.result_list().currentRow() == 0


def test_palette_filters_by_substring_and_updates_live(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    _seed(reg, [])
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    pal.search_box().setText("scenario")
    assert pal.result_list().count() == 2
    pal.search_box().setText("sim")
    assert pal.result_list().count() == 1


def test_palette_enter_dispatches_current_command(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    calls: list[str] = []
    _seed(reg, calls)
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    pal.search_box().setText("start sim")  # title-only hit: "Start Simulation"
    assert pal.result_list().count() == 1
    QTest.keyClick(pal.search_box(), Qt.Key.Key_Return)
    assert calls == ["sim.start"]


def test_palette_double_click_dispatches(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    calls: list[str] = []
    _seed(reg, calls)
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    pal.search_box().setText("toggle")
    item = pal.result_list().item(0)
    pal.result_list().itemActivated.emit(item)
    assert calls == ["view.toggle_panel"]


def test_palette_arrow_keys_walk_results_from_search_box(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    _seed(reg, [])
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    assert pal.result_list().currentRow() == 0
    QTest.keyClick(pal.search_box(), Qt.Key.Key_Down)
    assert pal.result_list().currentRow() == 1
    QTest.keyClick(pal.search_box(), Qt.Key.Key_Up)
    assert pal.result_list().currentRow() == 0
    # Wrap-around going up from row 0.
    QTest.keyClick(pal.search_box(), Qt.Key.Key_Up)
    assert pal.result_list().currentRow() == pal.result_list().count() - 1


def test_palette_disabled_command_is_skipped_and_greyed(qtbot) -> None:  # type: ignore[no-untyped-def]
    reg = WorkbenchCommandRegistry()
    calls: list[str] = []
    reg.register(
        WorkbenchCommand(
            id="x.disabled",
            title="Disabled Action",
            category="X",
            execute=lambda: calls.append("ran"),
            enabled_when=lambda: False,
        )
    )
    pal = CommandPalette(reg)
    qtbot.addWidget(pal)
    item = pal.result_list().item(0)
    assert not (item.flags() & Qt.ItemFlag.ItemIsEnabled)
    QTest.keyClick(pal.search_box(), Qt.Key.Key_Return)
    assert calls == []
