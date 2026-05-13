"""Phase 4 L3 — controller tick fan-out into FFT / RD / StageIO panels."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel

from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False)
    qtbot.addWidget(ws)
    return ws


def _stage_io_frame_text(ws: SimulatorWorkspace) -> str:
    label = ws.stage_io_panel().findChild(QLabel, "StageIOFrameLabel")
    assert label is not None, "StageIOFrameLabel missing"
    return label.text()


def test_frame_labels_default_to_dash(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Before any tick fires the three downstream panels read the
    placeholder ``frame: -`` text the panel constructors set."""
    ws = _ws(qtbot)
    assert ws.fft_panel().frame_label().text() == "frame: -"
    assert ws.range_doppler_panel().frame_label().text() == "frame: -"
    assert _stage_io_frame_text(ws) == "frame: -"


def test_single_tick_propagates_frame_to_all_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    """A single play+tick(20ms) bumps frame_id to 1 in all three panels."""
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    assert ws.fft_panel().frame_label().text() == "frame: 1"
    assert ws.range_doppler_panel().frame_label().text() == "frame: 1"
    assert _stage_io_frame_text(ws) == "frame: 1"


def test_paused_tick_does_not_bump_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Pause mid-flight: subsequent ticks still emit but frame_id is
    frozen, so the panel readouts stay where they were."""
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)  # frame_id -> 1
    controller.pause()
    controller.tick(0.020)  # paused -> sim_dt 0 -> frame_id stays at 1
    assert ws.fft_panel().frame_label().text() == "frame: 1"
    assert ws.range_doppler_panel().frame_label().text() == "frame: 1"
    assert _stage_io_frame_text(ws) == "frame: 1"


def test_replay_after_stop_starts_from_one(qtbot) -> None:  # type: ignore[no-untyped-def]
    """STOP resets frame_id; the next play+tick starts the panels at 1."""
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    controller.tick(0.020)
    controller.tick(0.020)
    assert ws.fft_panel().frame_label().text() == "frame: 3"
    controller.stop()
    controller.play()
    controller.tick(0.020)
    assert ws.fft_panel().frame_label().text() == "frame: 1"
    assert ws.range_doppler_panel().frame_label().text() == "frame: 1"
    assert _stage_io_frame_text(ws) == "frame: 1"


def test_multiple_ticks_increment_in_lockstep(qtbot) -> None:  # type: ignore[no-untyped-def]
    """RunPanel + downstream panels never disagree about frame_id."""
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    for expected in range(1, 6):
        controller.tick(0.020)
        assert ws.run_panel().frame_id_label().text() == str(expected)
        assert ws.fft_panel().frame_label().text() == f"frame: {expected}"
        assert ws.range_doppler_panel().frame_label().text() == f"frame: {expected}"
        assert _stage_io_frame_text(ws) == f"frame: {expected}"
