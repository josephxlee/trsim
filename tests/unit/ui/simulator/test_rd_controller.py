"""SimulatorRDController + workspace wiring tests (Phase 4 L3)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.simulator import MockRangeDopplerGenerator
from workbench.ui.simulator.panels import RangeDopplerPanel
from workbench.ui.simulator.rd_controller import SimulatorRDController
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Standalone controller (no RunController)
# ---------------------------------------------------------------------


def _panel(qtbot) -> RangeDopplerPanel:  # type: ignore[no-untyped-def]
    p = RangeDopplerPanel()
    qtbot.addWidget(p)
    return p


def test_paint_for_pushes_heatmap_into_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorRDController(rd_panel=panel)
    ctl.paint_for(0.25, 7)
    img = panel.image_item().image
    assert img is not None
    assert img.ndim == 2
    assert img.size > 0
    assert "7" in panel.frame_label().text()
    assert panel.peak_range_line().isVisible() is True
    assert panel.peak_doppler_line().isVisible() is True


def test_paint_for_is_deterministic(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorRDController(rd_panel=panel)
    ctl.paint_for(1.0, 1)
    first = panel.image_item().image.copy()
    ctl.paint_for(1.0, 999)
    second = panel.image_item().image
    np.testing.assert_array_equal(first, second)


def test_inject_custom_generator(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    custom = MockRangeDopplerGenerator(n_range_bins=16, n_doppler_bins=12)
    ctl = SimulatorRDController(rd_panel=panel, generator=custom)
    assert ctl.generator is custom
    ctl.paint_for(0.0, 0)
    img = panel.image_item().image
    assert img.shape == (16, 12)


def test_controller_without_run_controller_idempotent_disable(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    ctl = SimulatorRDController(rd_panel=panel)
    ctl.set_enabled(False)
    assert ctl.enabled is False
    ctl.set_enabled(False)
    assert ctl.enabled is False


# ---------------------------------------------------------------------
# RunController -> RD controller wiring
# ---------------------------------------------------------------------


def _run_ctl(qtbot) -> tuple[RangeDopplerPanel, SimulatorRunController]:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.panels import RunPanel

    rd = RangeDopplerPanel()
    qtbot.addWidget(rd)
    run = RunPanel()
    qtbot.addWidget(run)
    rc = SimulatorRunController(run_panel=run, autostart_timer=False)
    return rd, rc


def test_tick_completed_paints_rd_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    rd, rc = _run_ctl(qtbot)
    ctl = SimulatorRDController(rd_panel=rd, run_controller=rc)
    assert ctl.enabled is True
    rc.play()
    rc.tick(0.020)
    img = rd.image_item().image
    assert img is not None
    assert img.size > 0
    assert "1" in rd.frame_label().text()


def test_disabled_controller_does_not_paint(qtbot) -> None:  # type: ignore[no-untyped-def]
    rd, rc = _run_ctl(qtbot)
    ctl = SimulatorRDController(rd_panel=rd, run_controller=rc, enabled=False)
    assert ctl.enabled is False
    rc.play()
    rc.tick(0.020)
    assert rd.image_item().image is None  # never set
    assert rd.peak_range_line().isVisible() is False


def test_re_enable_resumes_painting(qtbot) -> None:  # type: ignore[no-untyped-def]
    rd, rc = _run_ctl(qtbot)
    ctl = SimulatorRDController(rd_panel=rd, run_controller=rc, enabled=False)
    rc.play()
    rc.tick(0.020)
    assert rd.image_item().image is None
    ctl.set_enabled(True)
    rc.tick(0.020)
    assert rd.image_item().image is not None


# ---------------------------------------------------------------------
# SimulatorWorkspace integration
# ---------------------------------------------------------------------


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None, autostart_run_timer=False, enable_3d_viewer=False
    )
    qtbot.addWidget(ws)
    return ws


def test_workspace_exposes_rd_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.rd_controller(), SimulatorRDController)
    assert ws.rd_controller().enabled is True


def test_workspace_run_tick_paints_rd_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    img = ws.range_doppler_panel().image_item().image
    assert img is not None
    assert ws.range_doppler_panel().peak_range_line().isVisible() is True
    assert "1" in ws.range_doppler_panel().frame_label().text()


def test_workspace_pause_freezes_rd_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    ws.sim_pause()
    before = ws.range_doppler_panel().image_item().image.copy()
    ws.run_controller().tick(0.020)  # paused -> sim_t_s frozen -> same arrays
    after = ws.range_doppler_panel().image_item().image
    np.testing.assert_array_equal(before, after)
