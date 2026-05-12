"""PhysicsLabWorkspace shell tests (PL-A + PL-B, plan/19 § 19.5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel, QPushButton, QSplitter

from workbench.ui.physics_lab import PhysicsLabWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot: object) -> PhysicsLabWorkspace:
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    return ws


# ---------------------------------------------------------------------
# Three-pane shell (PL-B)
# ---------------------------------------------------------------------


def test_workspace_object_name_is_set(qtbot: object) -> None:
    ws = _ws(qtbot)
    assert ws.objectName() == "PhysicsLabWorkspace"


def test_workspace_exposes_four_panes(qtbot: object) -> None:
    """Library / Code / Visualization / Parameters — the 3-pane shell
    that plan/19 § 19.5 prescribes (3 columns + a stacked Code/Viz
    middle column = 4 distinct widgets).
    """
    ws = _ws(qtbot)
    assert ws.library_panel() is not None
    assert ws.code_panel() is not None
    assert ws.viz_panel() is not None
    assert ws.parameters_panel() is not None


def test_workspace_top_splitter_has_three_columns(qtbot: object) -> None:
    ws = _ws(qtbot)
    top = ws.top_splitter()
    assert isinstance(top, QSplitter)
    assert top.count() == 3
    # Left column = Library; right column = Parameters; middle is the
    # Code/Viz splitter.
    assert top.widget(0) is ws.library_panel()
    assert top.widget(2) is ws.parameters_panel()


def test_workspace_middle_splitter_has_code_above_viz(qtbot: object) -> None:
    ws = _ws(qtbot)
    middle = ws.middle_splitter()
    assert isinstance(middle, QSplitter)
    assert middle.count() == 2
    assert middle.widget(0) is ws.code_panel()
    assert middle.widget(1) is ws.viz_panel()


def test_workspace_time_controls_expose_three_buttons(qtbot: object) -> None:
    ws = _ws(qtbot)
    tc = ws.time_controls()
    for btn_name in ("play_button", "pause_button", "stop_button"):
        btn = getattr(tc, btn_name)()
        assert isinstance(btn, QPushButton)
    assert isinstance(tc.status_label(), QLabel)
