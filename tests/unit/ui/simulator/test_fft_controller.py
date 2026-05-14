"""SimulatorFFTController + workspace wiring tests (Phase 4 L2)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.simulator import MockSpectrumGenerator
from workbench.ui.simulator.fft_controller import SimulatorFFTController
from workbench.ui.simulator.panels import FFTPanel
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Standalone controller (no RunController)
# ---------------------------------------------------------------------


def _panel(qtbot) -> FFTPanel:  # type: ignore[no-untyped-def]
    p = FFTPanel()
    qtbot.addWidget(p)
    return p


def test_paint_for_pushes_arrays_into_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorFFTController(fft_panel=panel)
    ctl.paint_for(0.25, 7)
    up_x, up_y = panel.up_curve().getData()
    _down_x, down_y = panel.down_curve().getData()
    assert up_x.size > 0
    assert up_y.size == up_x.size
    assert down_y.size == up_x.size
    assert "7" in panel.frame_label().text()
    assert panel.up_peak_marker().isVisible() is True
    assert panel.down_peak_marker().isVisible() is True


def test_paint_for_is_deterministic(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorFFTController(fft_panel=panel)
    ctl.paint_for(1.0, 1)
    _, up_y_a = panel.up_curve().getData()
    # Repaint at the same sim_t_s — arrays must match bit-for-bit.
    ctl.paint_for(1.0, 999)
    _, up_y_b = panel.up_curve().getData()
    np.testing.assert_array_equal(up_y_a, up_y_b)


def test_inject_custom_generator(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    custom = MockSpectrumGenerator(
        freq_min_hz=0.0, freq_max_hz=1.0e6, n_bins=16, peak_base_hz=5.0e5
    )
    ctl = SimulatorFFTController(fft_panel=panel, generator=custom)
    assert ctl.generator is custom
    ctl.paint_for(0.0, 0)
    up_x, _ = panel.up_curve().getData()
    assert up_x.size == 16


def test_controller_without_run_controller_can_disable_idempotently(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorFFTController(fft_panel=panel)
    # No RunController attached — set_enabled() should not raise.
    ctl.set_enabled(False)
    assert ctl.enabled is False
    ctl.set_enabled(False)  # idempotent
    assert ctl.enabled is False


# ---------------------------------------------------------------------
# RunController -> FFT controller wiring
# ---------------------------------------------------------------------


def _run_ctl(qtbot) -> tuple[FFTPanel, SimulatorRunController]:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.panels import RunPanel

    fft = FFTPanel()
    qtbot.addWidget(fft)
    run = RunPanel()
    qtbot.addWidget(run)
    rc = SimulatorRunController(run_panel=run, autostart_timer=False)
    return fft, rc


def test_tick_completed_paints_fft_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    fft, rc = _run_ctl(qtbot)
    ctl = SimulatorFFTController(fft_panel=fft, run_controller=rc)
    assert ctl.enabled is True
    rc.play()
    rc.tick(0.020)
    up_x, up_y = fft.up_curve().getData()
    assert up_x.size > 0
    assert up_y.size > 0
    assert "1" in fft.frame_label().text()


def test_disabled_controller_does_not_paint(qtbot) -> None:  # type: ignore[no-untyped-def]
    fft, rc = _run_ctl(qtbot)
    ctl = SimulatorFFTController(fft_panel=fft, run_controller=rc, enabled=False)
    assert ctl.enabled is False
    rc.play()
    rc.tick(0.020)
    # No paint happened — peak markers stay hidden.
    assert fft.up_peak_marker().isVisible() is False
    assert fft.down_peak_marker().isVisible() is False


def test_re_enable_controller_resumes_painting(qtbot) -> None:  # type: ignore[no-untyped-def]
    fft, rc = _run_ctl(qtbot)
    ctl = SimulatorFFTController(fft_panel=fft, run_controller=rc, enabled=False)
    rc.play()
    rc.tick(0.020)
    assert fft.up_peak_marker().isVisible() is False
    ctl.set_enabled(True)
    rc.tick(0.020)
    assert fft.up_peak_marker().isVisible() is True


# ---------------------------------------------------------------------
# SimulatorWorkspace integration
# ---------------------------------------------------------------------


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False)
    qtbot.addWidget(ws)
    return ws


def test_workspace_exposes_fft_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.fft_controller(), SimulatorFFTController)
    assert ws.fft_controller().enabled is True


def test_workspace_run_tick_paints_fft_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    fft = ws.fft_panel()
    up_x, _ = fft.up_curve().getData()
    assert up_x.size > 0
    assert fft.up_peak_marker().isVisible() is True
    assert "1" in fft.frame_label().text()


def test_workspace_pause_freezes_fft_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Paused run -> tick is a no-op so the FFT panel stays put."""
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    ws.sim_pause()
    before = ws.fft_panel().up_curve().getData()[1].copy()
    ws.run_controller().tick(0.020)  # paused -> no advance, no signal emit-but-no-data-change
    after = ws.fft_panel().up_curve().getData()[1]
    np.testing.assert_array_equal(before, after)
