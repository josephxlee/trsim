"""Time-mode tests (PL-9.1e, plan/19 § 19.6).

Covers the four-way mode selector + mode-specific overlays:

- Mode enum / display tuple shape.
- Mode combo on _TimeControls (4 entries, default Run).
- Controller ``mode`` / ``set_mode`` round-trip + combo wiring.
- Static disables transport controls; non-static re-enables.
- Compare mode adds the analytic-peak overlay curve + populates it.
- Sweep mode spawns N additional simulators + plot overlays; play
  steps them in lock-step.
- Stop in Sweep mode resets the sibling simulators back to t=0.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.domain.physics_lab import (
    TIME_MODES_IN_DISPLAY_ORDER,
    TimeMode,
)
from workbench.ui.physics_lab import (
    BouncingBallController,
    BouncingBallPlot,
    PhysicsLabWorkspace,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Domain enum
# ---------------------------------------------------------------------


def test_time_mode_enum_has_four_members() -> None:
    assert {m.value for m in TimeMode} == {"static", "run", "compare", "sweep"}


def test_display_tuple_in_expected_order() -> None:
    assert TIME_MODES_IN_DISPLAY_ORDER == (
        TimeMode.STATIC,
        TimeMode.RUN,
        TimeMode.COMPARE,
        TimeMode.SWEEP,
    )


# ---------------------------------------------------------------------
# Mode combo on _TimeControls
# ---------------------------------------------------------------------


def test_time_controls_mode_combo_has_four_items(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    combo = ws.time_controls().mode_combo()
    assert combo.count() == 4
    items = {combo.itemText(i) for i in range(combo.count())}
    assert items == {"static", "run", "compare", "sweep"}


def test_time_controls_default_mode_is_run(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    combo = ws.time_controls().mode_combo()
    assert combo.currentText() == "run"


# ---------------------------------------------------------------------
# Controller mode round-trip
# ---------------------------------------------------------------------


def test_controller_starts_in_run_mode(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.bouncing_ball_controller().mode == TimeMode.RUN


def test_set_mode_to_static_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.STATIC)
    assert controller.mode == TimeMode.STATIC
    assert ws.time_controls().mode_combo().currentText() == "static"


def test_combo_drives_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    ws.time_controls().mode_combo().setCurrentText("compare")
    assert controller.mode == TimeMode.COMPARE


# ---------------------------------------------------------------------
# Static disables transport
# ---------------------------------------------------------------------


def test_static_mode_disables_transport(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.STATIC)
    tc = ws.time_controls()
    assert tc.play_button().isEnabled() is False
    assert tc.pause_button().isEnabled() is False
    assert tc.stop_button().isEnabled() is False
    assert tc.frame_slider().isEnabled() is False
    assert tc.step_forward_button().isEnabled() is False
    assert tc.step_back_button().isEnabled() is False


def test_back_to_run_mode_re_enables_transport(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.STATIC)
    controller.set_mode(TimeMode.RUN)
    tc = ws.time_controls()
    assert tc.play_button().isEnabled() is True
    assert tc.frame_slider().isEnabled() is True
    assert tc.step_forward_button().isEnabled() is True


# ---------------------------------------------------------------------
# Compare overlay
# ---------------------------------------------------------------------


def test_compare_mode_adds_analytic_overlay_curve(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.COMPARE)
    overlays = ws.viz_panel().overlay_names()
    assert BouncingBallController.COMPARE_ANALYTIC_CURVE in overlays
    # The overlay carries the geometric-decay envelope samples.
    length = ws.viz_panel().history_length_of(BouncingBallController.COMPARE_ANALYTIC_CURVE)
    assert length > 0


def test_exiting_compare_mode_removes_overlay_curve(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.COMPARE)
    controller.set_mode(TimeMode.RUN)
    overlays = ws.viz_panel().overlay_names()
    assert BouncingBallController.COMPARE_ANALYTIC_CURVE not in overlays


# ---------------------------------------------------------------------
# Sweep overlay
# ---------------------------------------------------------------------


def test_sweep_mode_spawns_one_sibling_per_restitution(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.SWEEP)
    overlays = ws.viz_panel().overlay_names()
    assert len(overlays) == len(BouncingBallController.SWEEP_RESTITUTION_VALUES)
    # Each curve is seeded with the t=0 sample.
    for name in overlays:
        assert ws.viz_panel().history_length_of(name) == 1


def test_exiting_sweep_mode_removes_all_overlay_curves(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.SWEEP)
    controller.set_mode(TimeMode.RUN)
    assert ws.viz_panel().overlay_names() == ()


def test_step_forward_in_sweep_mode_advances_every_sibling(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.SWEEP)
    overlays = ws.viz_panel().overlay_names()
    # Initial length is 1 (seed sample).
    initial_lengths = {n: ws.viz_panel().history_length_of(n) for n in overlays}
    controller.step_forward_once()
    for name in overlays:
        assert ws.viz_panel().history_length_of(name) == initial_lengths[name] + 1


def test_stop_in_sweep_mode_resets_overlay_to_seed(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    controller.set_mode(TimeMode.SWEEP)
    for _ in range(5):
        controller.step_forward_once()
    controller.stop()
    for name in ws.viz_panel().overlay_names():
        # After stop the sibling re-seeds to a single t=0 sample.
        assert ws.viz_panel().history_length_of(name) == 1


# ---------------------------------------------------------------------
# Plot multi-curve direct API
# ---------------------------------------------------------------------


def test_plot_primary_curve_implicit_at_construction(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    assert "primary" in plot.all_curve_names()
    assert plot.overlay_names() == ()


def test_plot_add_overlay_curve_appears_in_overlay_names(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    plot.add_overlay_curve("aux", color="#ff0000")
    assert "aux" in plot.overlay_names()
    assert "primary" not in plot.overlay_names()


def test_plot_add_overlay_rejects_duplicate_name(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    plot.add_overlay_curve("aux", color="#ff0000")
    with pytest.raises(ValueError, match=r"already exists"):
        plot.add_overlay_curve("aux", color="#00ff00")


def test_plot_add_overlay_rejects_primary_name(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match=r"implicit primary curve"):
        plot.add_overlay_curve("primary", color="#ff0000")


def test_plot_append_to_unknown_curve_raises(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match=r"unknown curve"):
        plot.append_to("ghost", 0.0, 0.0)


def test_plot_remove_overlay_drops_data(qtbot) -> None:  # type: ignore[no-untyped-def]
    plot = BouncingBallPlot()
    qtbot.addWidget(plot)  # type: ignore[attr-defined]
    plot.add_overlay_curve("aux", color="#ff0000")
    plot.append_to("aux", 0.0, 1.0)
    assert plot.history_length_of("aux") == 1
    plot.remove_overlay_curve("aux")
    assert "aux" not in plot.overlay_names()
    assert plot.history_length_of("aux") == 0
