"""PhysicsLabWorkspace shell tests (PL-A + PL-B + PL-D, plan/19 § 19.5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtWidgets import QLabel, QPushButton, QSplitter

from workbench.ui.physics_lab import (
    BouncingBallController,
    BouncingBallPlot,
    CodePreview,
    LibraryWidget,
    ParametersWidget,
    PhysicsLabWorkspace,
)

pytestmark = pytest.mark.qt


def _ws(qtbot: object) -> PhysicsLabWorkspace:
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    return ws


# ---------------------------------------------------------------------
# Three-pane shell (PL-B + PL-D — panes now host real widgets)
# ---------------------------------------------------------------------


def test_workspace_object_name_is_set(qtbot: object) -> None:
    ws = _ws(qtbot)
    assert ws.objectName() == "PhysicsLabWorkspace"


def test_workspace_panes_are_live_widgets(qtbot: object) -> None:
    """PL-D replaces the PL-B placeholders with the Bouncing Ball
    Library / Code / Plot / Parameters widgets.
    """
    ws = _ws(qtbot)
    assert isinstance(ws.library_panel(), LibraryWidget)
    assert isinstance(ws.code_panel(), CodePreview)
    assert isinstance(ws.viz_panel(), BouncingBallPlot)
    assert isinstance(ws.parameters_panel(), ParametersWidget)
    assert isinstance(ws.bouncing_ball_controller(), BouncingBallController)


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
    """PL-9.1d: middle splitter's bottom widget is the viz QStackedWidget
    holding the BouncingBallPlot at index 0 (and optionally the 3D
    panel at index 1 when ``enable_3d_viewer=True``).
    """
    ws = _ws(qtbot)
    middle = ws.middle_splitter()
    assert isinstance(middle, QSplitter)
    assert middle.count() == 2
    assert middle.widget(0) is ws.code_panel()
    assert middle.widget(1) is ws.viz_stack()
    assert ws.viz_stack().widget(0) is ws.viz_panel()


def test_workspace_time_controls_expose_three_buttons(qtbot: object) -> None:
    ws = _ws(qtbot)
    tc = ws.time_controls()
    for btn_name in ("play_button", "pause_button", "stop_button"):
        btn = getattr(tc, btn_name)()
        assert isinstance(btn, QPushButton)
    assert isinstance(tc.status_label(), QLabel)
