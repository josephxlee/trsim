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
    ws = SimulatorWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert isinstance(ws.fft_panel(), FFTPanel)
    assert isinstance(ws.range_doppler_panel(), RangeDopplerPanel)
    assert isinstance(ws.run_panel(), RunPanel)
    assert isinstance(ws.properties_panel(), PropertiesPanel)
    assert isinstance(ws.plugin_manager_panel(), PluginManagerPanel)
    assert isinstance(ws.stage_io_panel(), StageIOPanel)
    assert isinstance(ws.scene_3d_panel(), Scene3DPanel)
    assert isinstance(ws.scope_pov_panel(), ScopePOVPanel)


def test_bottom_tabs_have_runtime_and_nn_mode_tabs(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Bottom tabs surface the 3 runtime panels plus the 3 NN-mode panels.

    DLC tabs (Task D) append after these six. The MVP wire-up moved
    the Phase 4.11 NN panels out of code-only existence into the
    Simulator workspace itself so users can drive Step 1 / Step 2 /
    Training from the GUI.
    """
    ws = SimulatorWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)
    tabs = ws.bottom_tabs()
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    assert titles == [
        "Run",
        "Stage I/O",
        "Profiler",
        "NN Step 1",
        "NN Step 2",
        "NN Training",
    ]
