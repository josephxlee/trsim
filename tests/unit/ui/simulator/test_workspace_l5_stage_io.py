"""Phase 4 L5 — StageIO 6-box per-tick placeholder IN/OUT text."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False)
    qtbot.addWidget(ws)
    return ws


def test_stage_io_boxes_default_to_dash(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    panel = ws.stage_io_panel()
    for stage in ("Transmitter", "Environment", "Receiver", "Detector", "Pairing", "Tracker"):
        box = panel.stage_box(stage)
        assert box.in_label().text() == "IN: -"
        assert box.out_label().text() == "OUT: -"


def test_first_tick_populates_all_six_boxes(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    panel = ws.stage_io_panel()
    # Transmitter encodes frame_id in IN + OUT.
    assert "frame=1" in panel.stage_box("Transmitter").in_label().text()
    assert "#1" in panel.stage_box("Transmitter").out_label().text()
    # Environment OUT encodes sim_t_s.
    assert "0.020" in panel.stage_box("Environment").out_label().text()
    # Receiver IN+OUT chain reuses frame_id.
    assert "#1" in panel.stage_box("Receiver").out_label().text()
    # Detector / Pairing / Tracker are placeholders awaiting real pipeline.
    assert "pipeline pending" in panel.stage_box("Pairing").in_label().text()
    assert "pipeline pending" in panel.stage_box("Tracker").out_label().text()


def test_consecutive_ticks_advance_frame_in_transmitter(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    for expected in range(1, 4):
        controller.tick(0.020)
        tx_in = ws.stage_io_panel().stage_box("Transmitter").in_label().text()
        assert tx_in == f"IN: scenario @ frame={expected}"


def test_paused_tick_freezes_stage_io(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    first_text = ws.stage_io_panel().stage_box("Transmitter").in_label().text()
    controller.pause()
    controller.tick(0.020)
    assert ws.stage_io_panel().stage_box("Transmitter").in_label().text() == first_text
