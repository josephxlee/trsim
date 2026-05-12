"""Bouncing Ball demo widget tests (PL-D, plan/19 § 19.12.1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.ui.physics_lab import (
    BouncingBallPlot,
    CodePreview,
    LibraryWidget,
    ParametersWidget,
    PhysicsLabWorkspace,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# LibraryWidget
# ---------------------------------------------------------------------


def test_library_widget_first_row_is_bouncing_ball(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.list_widget().item(0).text() == LibraryWidget.BOUNCING_BALL_ROW


def test_library_widget_lists_nine_test_objects_after_demo(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    # Bouncing Ball demo + 9 Test Objects = 10 rows.
    assert lib.list_widget().count() == 10


# ---------------------------------------------------------------------
# CodePreview
# ---------------------------------------------------------------------


def test_code_preview_shows_step_method_source(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    text = cp.editor().toPlainText()
    # The displayed source must contain the step signature.
    assert "def step" in text
    assert "semi-implicit Euler" in text or "dt_s" in text


# ---------------------------------------------------------------------
# BouncingBallPlot
# ---------------------------------------------------------------------


def test_plot_starts_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    assert plot.history_length() == 0


def test_plot_append_increases_history(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    plot.append(0.0, 5.0)
    plot.append(0.1, 4.95)
    assert plot.history_length() == 2


def test_plot_clear_history_resets(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    plot.set_history([0.0, 0.1, 0.2], [5.0, 4.9, 4.7])
    assert plot.history_length() == 3
    plot.clear_history()
    assert plot.history_length() == 0


# ---------------------------------------------------------------------
# ParametersWidget
# ---------------------------------------------------------------------


def test_parameters_default_restitution_is_0p70(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ParametersWidget()
    qtbot.addWidget(p)  # type: ignore[attr-defined]
    assert p.current_restitution() == pytest.approx(0.70)


def test_parameters_set_restitution_clamps(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ParametersWidget()
    qtbot.addWidget(p)  # type: ignore[attr-defined]
    p.set_restitution(0.25)
    assert p.current_restitution() == pytest.approx(0.25)
    p.set_restitution(-1.0)
    assert p.current_restitution() == 0.0
    p.set_restitution(2.0)
    assert p.current_restitution() == pytest.approx(1.0)


def test_parameters_slider_emits_restitution_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ParametersWidget()
    qtbot.addWidget(p)  # type: ignore[attr-defined]
    received: list[float] = []
    p.restitution_changed.connect(received.append)
    p.slider().setValue(45)
    assert received[-1] == pytest.approx(0.45)


# ---------------------------------------------------------------------
# BouncingBallController (integration via PhysicsLabWorkspace)
# ---------------------------------------------------------------------


def test_workspace_controller_seeds_plot_with_initial_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    plot = ws.viz_panel()
    # One initial sample at t=0 so the chart is not blank.
    assert plot.history_length() == 1


def test_step_once_advances_simulator_and_appends_to_plot(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    initial_length = ws.viz_panel().history_length()
    controller.step_once()
    assert ws.viz_panel().history_length() == initial_length + 1
    assert controller.simulator.state.time_s > 0.0


def test_play_starts_then_pause_freezes_clock(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.play()
    assert controller.clock.is_running
    controller.pause()
    assert not controller.clock.is_running


def test_stop_resets_simulator_and_plot(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(5):
        controller.step_once()
    assert ws.viz_panel().history_length() > 1
    controller.stop()
    # Plot keeps the t=0 seed point after a stop.
    assert ws.viz_panel().history_length() == 1
    assert controller.simulator.state.time_s == 0.0
    assert controller.simulator.state.bounces == 0


def test_restitution_slider_forwards_to_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    ws.parameters_panel().set_restitution(0.42)
    assert controller.simulator.restitution == pytest.approx(0.42)
