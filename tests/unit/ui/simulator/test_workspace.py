"""Unit tests for the SimulatorWorkspace shell (Phase 4.9)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.panels import (
    FFTPanel,
    PluginManagerPanel,
    PropertiesPanel,
    RangeDopplerPanel,
    RunPanel,
    Scene3DPanel,
    ScopePOVPanel,
    StageIOPanel,
)
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def test_workspace_mounts_every_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    assert isinstance(ws.fft_panel(), FFTPanel)
    assert isinstance(ws.range_doppler_panel(), RangeDopplerPanel)
    assert isinstance(ws.run_panel(), RunPanel)
    assert isinstance(ws.properties_panel(), PropertiesPanel)
    assert isinstance(ws.plugin_manager_panel(), PluginManagerPanel)
    assert isinstance(ws.stage_io_panel(), StageIOPanel)
    assert isinstance(ws.scene_3d_panel(), Scene3DPanel)
    assert isinstance(ws.scope_pov_panel(), ScopePOVPanel)


def test_bottom_tabs_have_run_stage_io_and_profiler(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    tabs = ws.bottom_tabs()
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    assert titles == ["Run", "Stage I/O", "Profiler"]
