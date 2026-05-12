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


# ---------------------------------------------------------------------
# PL-9.1b — Frame slider + step-by-step controls
# ---------------------------------------------------------------------


def test_history_starts_with_seed_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    assert len(controller.history) == 1
    assert controller.current_frame_index == 0
    assert controller.history[0].time_s == 0.0


def test_step_forward_once_appends_history_and_advances_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    initial_len = len(controller.history)
    controller.step_forward_once()
    assert len(controller.history) == initial_len + 1
    assert controller.current_frame_index == initial_len
    assert controller.simulator.state.time_s > 0.0


def test_step_backward_once_rewinds_without_popping_history(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.step_forward_once()
    controller.step_forward_once()
    assert len(controller.history) == 3
    controller.step_backward_once()
    assert controller.current_frame_index == 1
    # The future frames stay in the history list.
    assert len(controller.history) == 3
    # Simulator state mirrors the cursor.
    assert controller.simulator.state == controller.history[1]


def test_step_back_at_zero_is_a_no_op(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.step_backward_once()
    assert controller.current_frame_index == 0
    assert len(controller.history) == 1


def test_step_forward_after_backward_replays_stored_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.step_forward_once()
    controller.step_forward_once()
    expected_state = controller.history[2]
    controller.step_backward_once()
    controller.step_forward_once()
    assert controller.simulator.state == expected_state
    # No duplicate frame was appended.
    assert len(controller.history) == 3


def test_seek_to_frame_clamps_and_snaps_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(4):
        controller.step_forward_once()
    controller.seek_to_frame(2)
    assert controller.current_frame_index == 2
    assert controller.simulator.state == controller.history[2]
    # Out-of-range values are clamped, not errors.
    controller.seek_to_frame(99)
    assert controller.current_frame_index == len(controller.history) - 1
    controller.seek_to_frame(-3)
    assert controller.current_frame_index == 0


def test_seek_back_then_forward_truncates_when_play_runs(qtbot) -> None:  # type: ignore[no-untyped-def]
    """When the user rewinds and then advances the simulator (step
    forward beyond the stored end, or via Play), the discarded future
    is replaced by the new trajectory.
    """
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(4):
        controller.step_forward_once()
    assert len(controller.history) == 5
    controller.seek_to_frame(2)
    # Change restitution so the next advance diverges from the stored
    # trajectory, then drive Play one tick.
    ws.parameters_panel().set_restitution(0.1)
    controller.step_once()
    # History was truncated to [0..2] + the new frame = length 4.
    assert len(controller.history) == 4
    assert controller.current_frame_index == 3


def test_stop_clears_history_to_seed(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(5):
        controller.step_forward_once()
    controller.stop()
    assert len(controller.history) == 1
    assert controller.current_frame_index == 0


def test_frame_slider_range_tracks_history_length(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    slider = ws.time_controls().frame_slider()
    assert slider.minimum() == 0
    assert slider.maximum() == 0
    controller.step_forward_once()
    controller.step_forward_once()
    assert slider.maximum() == 2
    assert slider.value() == 2


def test_frame_slider_drives_seek(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(4):
        controller.step_forward_once()
    ws.time_controls().frame_slider().setValue(1)
    assert controller.current_frame_index == 1
    assert controller.simulator.state == controller.history[1]


def test_step_back_button_disabled_at_frame_zero(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    back_btn = ws.time_controls().step_back_button()
    assert back_btn.isEnabled() is False
    controller.step_forward_once()
    assert back_btn.isEnabled() is True
    controller.step_backward_once()
    assert back_btn.isEnabled() is False


def test_frame_readout_reflects_index(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    readout = ws.time_controls().frame_readout()
    assert readout.text() == "frame 0 / 0"
    controller.step_forward_once()
    controller.step_forward_once()
    assert readout.text() == "frame 2 / 2"
    controller.step_backward_once()
    assert readout.text() == "frame 1 / 2"


def test_plot_truncates_to_cursor_on_step_back(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    for _ in range(3):
        controller.step_forward_once()
    assert ws.viz_panel().history_length() == 4  # seed + 3
    controller.step_backward_once()
    assert ws.viz_panel().history_length() == 3  # seed + 2
    controller.step_backward_once()
    assert ws.viz_panel().history_length() == 2  # seed + 1


def test_step_buttons_click_route_to_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Click the actual QPushButton instances — the connections set up
    in BouncingBallController.__init__ must forward to step_forward /
    step_backward.
    """
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    ws.time_controls().step_forward_button().click()
    ws.time_controls().step_forward_button().click()
    assert controller.current_frame_index == 2
    ws.time_controls().step_back_button().click()
    assert controller.current_frame_index == 1


# ---------------------------------------------------------------------
# PL-E — Code edit mode
# ---------------------------------------------------------------------


def test_code_preview_starts_read_only_and_default_status(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    assert cp.editor().isReadOnly() is True
    assert cp.is_editing() is False
    assert "read-only" in cp.status_label().text()
    assert cp.save_button().isEnabled() is False
    assert cp.revert_button().isEnabled() is False


def test_edit_toggle_unlocks_editor_and_swaps_default_user_step(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    cp.edit_button().setChecked(True)
    assert cp.editor().isReadOnly() is False
    assert cp.save_button().isEnabled() is True
    assert cp.revert_button().isEnabled() is True
    assert "def step(simulator, dt_s)" in cp.current_source()


def test_save_clicked_emits_save_requested_with_source(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    received: list[str] = []
    cp.save_requested.connect(received.append)
    cp.edit_button().setChecked(True)
    cp.editor().setPlainText("def step(simulator, dt_s):\n    pass\n")
    cp.save_button().click()
    assert received == ["def step(simulator, dt_s):\n    pass\n"]


def test_revert_clicked_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    seen: list[bool] = []
    cp.revert_requested.connect(lambda: seen.append(True))
    cp.edit_button().setChecked(True)
    cp.revert_button().click()
    assert seen == [True]


def test_apply_user_step_freezes_ball(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Controller installs a custom step that keeps the ball frozen."""
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    frozen_source = """
def step(simulator, dt_s):
    from workbench.app.physics_lab import BouncingBallState
    s = simulator.state
    simulator.update_state(BouncingBallState(
        time_s=s.time_s + dt_s,
        position_m=s.position_m,
        velocity_m_s=0.0,
        bounces=s.bounces,
    ))
"""
    ok = controller.apply_user_step_code(frozen_source)
    assert ok is True
    assert controller.simulator.has_step_override is True
    y0 = controller.simulator.state.position_m
    controller.step_once()
    assert controller.simulator.state.position_m == pytest.approx(y0)
    assert "applied" in ws.code_panel().status_label().text().lower()


def test_apply_user_step_with_syntax_error_reports_status(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    ok = controller.apply_user_step_code("def step(\n# missing colon")
    assert ok is False
    assert controller.simulator.has_step_override is False
    assert "syntaxerror" in ws.code_panel().status_label().text().lower()


def test_apply_user_step_without_step_symbol_reports_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    ok = controller.apply_user_step_code("x = 1\n")
    assert ok is False
    assert "no `step" in ws.code_panel().status_label().text()


def test_revert_user_step_restores_built_in(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.apply_user_step_code(
        "def step(simulator, dt_s):\n    simulator.update_state(simulator.state)\n"
    )
    assert controller.simulator.has_step_override is True
    controller.revert_user_step_code()
    assert controller.simulator.has_step_override is False
    assert "reverted" in ws.code_panel().status_label().text().lower()


def test_revert_leaves_editor_with_valid_module_level_source(qtbot) -> None:  # type: ignore[no-untyped-def]
    """User reported SyntaxError after Revert. Root cause: the editor
    was being repopulated with ``inspect.getsource(...)`` of the
    method, which is 4-space indented and carries ``self`` as the
    first argument — not valid module-level Python. A subsequent
    Save & Reload would then crash ``exec``.

    Fix: Revert refreshes the editor with the standalone-function
    scaffold (the same body the very first Edit click installs) so
    re-saving works without modification.
    """
    import ast

    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    cp = ws.code_panel()
    # Pretend the user just installed an override.
    ws.bouncing_ball_controller().apply_user_step_code(
        "def step(simulator, dt_s):\n    simulator.update_state(simulator.state)\n"
    )
    # Revert via the controller (same path the button click takes).
    ws.bouncing_ball_controller().revert_user_step_code()

    source = cp.current_source()
    # The body must compile cleanly as a module — that's the
    # regression: previously it was an indented method.
    ast.parse(source, mode="exec")
    assert "def step(simulator, dt_s)" in source
    # And the Edit toggle drops back to off so the user is not
    # staring at an editable body that the click just replaced.
    assert cp.is_editing() is False


def test_revert_then_resave_succeeds_without_syntax_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    """End-to-end of the bug the user surfaced: install a custom step,
    Revert, then click Save & Reload again. Must apply cleanly.
    """
    ws = PhysicsLabWorkspace()
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    cp = ws.code_panel()

    controller.apply_user_step_code(
        "def step(simulator, dt_s):\n    simulator.update_state(simulator.state)\n"
    )
    controller.revert_user_step_code()
    # Re-enter edit mode (the user would click Edit again).
    cp.edit_button().setChecked(True)
    # Save & Reload with the scaffold body untouched.
    ok = controller.apply_user_step_code(cp.current_source())
    assert ok is True
    assert controller.simulator.has_step_override is True
    assert "syntaxerror" not in cp.status_label().text().lower()
