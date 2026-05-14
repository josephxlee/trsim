"""SimulatorWorkspace ↔ run_controller integration (Phase 4 L1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.types import SimulationState
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None, autostart_run_timer=False, enable_3d_viewer=False
    )
    qtbot.addWidget(ws)
    return ws


def test_workspace_exposes_run_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.run_controller(), SimulatorRunController)


def test_sim_play_routes_to_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    assert ws.run_controller().clock.state is SimulationState.RUNNING


def test_sim_pause_routes_to_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.sim_pause()
    assert ws.run_controller().clock.state is SimulationState.PAUSED


def test_sim_stop_routes_and_resets(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    ws.sim_stop()
    assert ws.run_controller().clock.state is SimulationState.STOPPED
    assert ws.run_controller().frame_id == 0


def test_sim_set_speed_routes_int_to_multiplier(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_set_speed(4)
    assert ws.run_panel().sim_speed_label().text() == "x4"


def test_workspace_run_panel_default_readout(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    panel = ws.run_panel()
    assert panel.sim_time_label().text() == "0.000 s"
    assert panel.frame_id_label().text() == "0"
    assert panel.sim_state_label().text() == "stopped"


def test_workspace_autostart_timer_default_true(qtbot) -> None:  # type: ignore[no-untyped-def]
    # Default constructor → QTimer running. We do not let it tick (event
    # loop not driven), but verify the timer is armed for production.
    ws = SimulatorWorkspace(nn_datasets_root=None, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert ws.run_controller().timer().isActive() is True


def test_workspace_autostart_timer_false_path(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None, autostart_run_timer=False, enable_3d_viewer=False
    )
    qtbot.addWidget(ws)
    assert ws.run_controller().timer().isActive() is False
