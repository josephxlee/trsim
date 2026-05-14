"""SimulatorStageIOController + plugin manager seed tests (Phase 4 L5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.app.simulator import DEFAULT_PLUGIN_NAMES, MockStageIOGenerator
from workbench.ui.simulator.panels import StageIOPanel
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.stage_io_controller import SimulatorStageIOController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Standalone controller
# ---------------------------------------------------------------------


def _panel(qtbot) -> StageIOPanel:  # type: ignore[no-untyped-def]
    p = StageIOPanel()
    qtbot.addWidget(p)
    return p


def test_paint_for_updates_every_stage_box(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    ctl.paint_for(0.5, 3)
    # Every default-stage box now reports the mock IN/OUT text.
    assert "0.500" in panel.stage_box("Transmitter").in_label().text()
    assert "pulses" in panel.stage_box("Transmitter").out_label().text()
    assert "3" in panel.frame_label().text()


def test_paint_for_is_deterministic(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    ctl.paint_for(1.0, 1)
    first_in = panel.stage_box("Environment").in_label().text()
    ctl.paint_for(1.0, 99)
    assert panel.stage_box("Environment").in_label().text() == first_in


def test_inject_custom_generator(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    gen = MockStageIOGenerator(base_pulses=7)
    ctl = SimulatorStageIOController(stage_io_panel=panel, generator=gen)
    assert ctl.generator is gen
    ctl.paint_for(0.0, 0)
    assert "7 pulses" in panel.stage_box("Transmitter").out_label().text()


def test_recording_toggle_starts_disabled(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    assert ctl.recording is False
    assert ctl.records() == ()


def test_recording_captures_frames(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    panel.record_button().setChecked(True)
    assert ctl.recording is True
    ctl.paint_for(0.0, 0)
    ctl.paint_for(0.5, 1)
    assert len(ctl.records()) == 2
    assert ctl.records()[0].sim_t_s == pytest.approx(0.0)
    assert ctl.records()[1].sim_t_s == pytest.approx(0.5)


def test_recording_disabled_drops_frames(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    # Recording off -> tick should not append.
    ctl.paint_for(0.0, 0)
    assert ctl.records() == ()


def test_starting_new_recording_clears_log(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    panel.record_button().setChecked(True)
    ctl.paint_for(0.0, 0)
    panel.record_button().setChecked(False)
    assert len(ctl.records()) == 1
    # Re-enabling clears the previous session.
    panel.record_button().setChecked(True)
    assert ctl.records() == ()


def test_clear_records_resets_log(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorStageIOController(stage_io_panel=panel)
    panel.record_button().setChecked(True)
    ctl.paint_for(0.0, 0)
    ctl.clear_records()
    assert ctl.records() == ()


# ---------------------------------------------------------------------
# RunController -> StageIOController wiring
# ---------------------------------------------------------------------


def _run_ctl(qtbot) -> tuple[StageIOPanel, SimulatorRunController]:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.panels import RunPanel

    panel = StageIOPanel()
    qtbot.addWidget(panel)
    run = RunPanel()
    qtbot.addWidget(run)
    rc = SimulatorRunController(run_panel=run, autostart_timer=False)
    return panel, rc


def test_tick_completed_paints_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel, rc = _run_ctl(qtbot)
    # Parent the controller to the panel so it survives the test until
    # ``qtbot.addWidget`` cleanup, otherwise a refcount=0 QObject can
    # disconnect mid-tick.
    ctl = SimulatorStageIOController(
        stage_io_panel=panel, run_controller=rc, parent=panel
    )
    assert ctl.enabled is True
    rc.play()
    rc.tick(0.020)
    assert "1" in panel.frame_label().text()
    assert "0.020" in panel.stage_box("Transmitter").in_label().text()


def test_disabled_controller_does_not_paint(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel, rc = _run_ctl(qtbot)
    ctl = SimulatorStageIOController(
        stage_io_panel=panel, run_controller=rc, enabled=False, parent=panel
    )
    assert ctl.enabled is False
    rc.play()
    rc.tick(0.020)
    # No paint happened — the Transmitter IN label still shows the default '-'.
    assert "IN: -" in panel.stage_box("Transmitter").in_label().text()


# ---------------------------------------------------------------------
# SimulatorWorkspace integration
# ---------------------------------------------------------------------


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None,
        autostart_run_timer=False,
        enable_3d_viewer=False,
    )
    qtbot.addWidget(ws)
    return ws


def test_workspace_exposes_stage_io_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.stage_io_controller(), SimulatorStageIOController)
    assert ws.stage_io_controller().enabled is True


def test_workspace_seeds_default_plugins(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The PluginManager rows arrive pre-populated with default plugin names."""
    ws = _ws(qtbot)
    plugin_panel = ws.plugin_manager_panel()
    for stage, expected in DEFAULT_PLUGIN_NAMES.items():
        section = plugin_panel.stage_section(stage)
        lw = section.list_widget()
        items = [lw.item(i).text() for i in range(lw.count())]
        for name in expected:
            assert name in items


def test_workspace_run_tick_paints_stage_io_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    panel = ws.stage_io_panel()
    assert "1" in panel.frame_label().text()
    assert "0.020" in panel.stage_box("Transmitter").in_label().text()
