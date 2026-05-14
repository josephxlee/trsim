"""P5c resize-drag paint suppression tests (workspace + run controller)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent

from workbench.ui.simulator.panels import RunPanel
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# RunController suppression flag
# ---------------------------------------------------------------------


def test_run_controller_paint_suppressed_default_false(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    rc = SimulatorRunController(run_panel=panel, autostart_timer=False)
    assert rc.paint_suppressed is False


def test_set_paint_suppressed_toggles_flag(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    rc = SimulatorRunController(run_panel=panel, autostart_timer=False)
    rc.set_paint_suppressed(True)
    assert rc.paint_suppressed is True
    rc.set_paint_suppressed(False)
    assert rc.paint_suppressed is False


def test_tick_completed_suppressed_when_flag_set(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``tick_completed`` must not fire when ``paint_suppressed`` is True."""
    panel = RunPanel()
    qtbot.addWidget(panel)
    rc = SimulatorRunController(run_panel=panel, autostart_timer=False)
    received: list[tuple[float, int]] = []
    rc.tick_completed.connect(lambda t, f: received.append((t, f)))
    rc.play()
    rc.set_paint_suppressed(True)
    rc.tick(0.033)
    rc.tick(0.033)
    assert received == []  # Both ticks held back.
    rc.set_paint_suppressed(False)
    rc.tick(0.033)
    assert len(received) == 1  # Resumed.


def test_run_panel_readout_still_updates_when_suppressed(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The Run panel itself still gets refreshed — only downstream signals are held."""
    panel = RunPanel()
    qtbot.addWidget(panel)
    rc = SimulatorRunController(run_panel=panel, autostart_timer=False)
    rc.set_paint_suppressed(True)
    rc.play()
    rc.tick(0.033)
    # frame_id still bumps + sim_t_label still updates because
    # _refresh_panel runs regardless of suppression.
    assert rc.frame_id == 1
    assert "0.033" in panel.sim_time_label().text()


# ---------------------------------------------------------------------
# SimulatorWorkspace.resizeEvent wiring
# ---------------------------------------------------------------------


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None,
        autostart_run_timer=False,
        enable_3d_viewer=False,
    )
    qtbot.addWidget(ws)
    return ws


def test_resize_event_sets_paint_suppressed(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.resizeEvent(QResizeEvent(QSize(900, 700), QSize(800, 600)))
    assert ws.run_controller().paint_suppressed is True


def test_paint_suppressed_clears_after_debounce_timer(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Manually firing the debounce timer's timeout clears the flag."""
    ws = _ws(qtbot)
    ws.resizeEvent(QResizeEvent(QSize(900, 700), QSize(800, 600)))
    assert ws.run_controller().paint_suppressed is True
    # Trigger the debounce timeout directly (avoids real-time wait).
    ws._on_resize_settled()  # type: ignore[attr-defined]
    assert ws.run_controller().paint_suppressed is False


def test_resize_release_timer_is_single_shot(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert ws._resize_release_timer.isSingleShot() is True  # type: ignore[attr-defined]
    assert ws._resize_release_timer.interval() == ws.RESIZE_PAINT_RELEASE_MS  # type: ignore[attr-defined]


def test_resize_event_during_drag_keeps_timer_pending(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Multiple resizeEvents (drag) keep restarting the debounce timer."""
    ws = _ws(qtbot)
    ws.resizeEvent(QResizeEvent(QSize(900, 700), QSize(800, 600)))
    assert ws._resize_release_timer.isActive() is True  # type: ignore[attr-defined]
    # Another resize while timer is still pending — it restarts, not stops.
    ws.resizeEvent(QResizeEvent(QSize(1000, 800), QSize(900, 700)))
    assert ws._resize_release_timer.isActive() is True  # type: ignore[attr-defined]
    assert ws.run_controller().paint_suppressed is True


def test_paint_suppressed_blocks_downstream_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    """While suppressed, FFT / RD / Scope / Properties panels don't repaint."""
    ws = _ws(qtbot)
    ws.sim_play()
    # First tick before suppression -- everything paints.
    ws.run_controller().tick(0.033)
    assert ws.scope_pov_panel().target_marker().getData()[0] is not None

    initial_az_text = ws.scope_pov_panel().az_label().text()
    initial_fft_x, _ = ws.fft_panel().up_curve().getData()
    initial_fft_x_copy = initial_fft_x.copy()

    # Engage suppression -> tick should not propagate.
    ws.run_controller().set_paint_suppressed(True)
    ws.run_controller().tick(0.033)
    ws.run_controller().tick(0.033)

    # AZ readout stayed put because PrimaryTargetController got no signal.
    assert ws.scope_pov_panel().az_label().text() == initial_az_text
    # FFT curve unchanged.
    after_fft_x, _ = ws.fft_panel().up_curve().getData()
    assert (after_fft_x == initial_fft_x_copy).all()

    # Release -> next tick paints again.
    ws.run_controller().set_paint_suppressed(False)
    ws.run_controller().tick(0.033)
    assert ws.scope_pov_panel().az_label().text() != initial_az_text


def test_resize_settled_creates_event_loop_safety(qtbot) -> None:  # type: ignore[no-untyped-def]
    """`_on_resize_settled` is safe to call when not previously suppressed."""
    ws = _ws(qtbot)
    # Fresh workspace — suppression never engaged.
    assert ws.run_controller().paint_suppressed is False
    ws._on_resize_settled()  # type: ignore[attr-defined]
    assert ws.run_controller().paint_suppressed is False
