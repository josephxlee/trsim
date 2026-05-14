"""SimulatorSceneController + workspace wiring tests (Phase 4 L4)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.app.simulator import MockSceneGenerator
from workbench.ui.simulator.panels import Scene3DPanel
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.scene_controller import SimulatorSceneController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Standalone controller
# ---------------------------------------------------------------------


def _headless_panel(qtbot) -> Scene3DPanel:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    return p


def test_paint_for_pushes_status_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _headless_panel(qtbot)
    ctl = SimulatorSceneController(scene_panel=panel)
    ctl.paint_for(1.0, 5)
    assert "5" in panel.frame_label().text()
    assert "headless" in panel.status_label().text()


def test_inject_custom_generator(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _headless_panel(qtbot)
    gen = MockSceneGenerator(target_orbit_radius_m=1234.0)
    ctl = SimulatorSceneController(scene_panel=panel, generator=gen)
    assert ctl.generator is gen
    ctl.paint_for(0.0, 0)
    assert "1234" in panel.status_label().text()


def test_controller_without_run_controller_idempotent_disable(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _headless_panel(qtbot)
    ctl = SimulatorSceneController(scene_panel=panel)
    ctl.set_enabled(False)
    assert ctl.enabled is False
    ctl.set_enabled(False)
    assert ctl.enabled is False


# ---------------------------------------------------------------------
# RunController -> SceneController wiring
# ---------------------------------------------------------------------


def _run_ctl(qtbot) -> tuple[Scene3DPanel, SimulatorRunController]:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.panels import RunPanel

    panel = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(panel)
    run = RunPanel()
    qtbot.addWidget(run)
    rc = SimulatorRunController(run_panel=run, autostart_timer=False)
    return panel, rc


def test_tick_completed_paints_scene_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel, rc = _run_ctl(qtbot)
    ctl = SimulatorSceneController(scene_panel=panel, run_controller=rc)
    assert ctl.enabled is True
    rc.play()
    rc.tick(0.020)
    assert "1" in panel.frame_label().text()


def test_disabled_controller_does_not_paint(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel, rc = _run_ctl(qtbot)
    ctl = SimulatorSceneController(scene_panel=panel, run_controller=rc, enabled=False)
    assert ctl.enabled is False
    rc.play()
    rc.tick(0.020)
    # Still the default placeholder hint — no tick was forwarded.
    assert "mounts the PyVista QtInteractor" in panel.status_label().text()


def test_re_enable_resumes_painting(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel, rc = _run_ctl(qtbot)
    ctl = SimulatorSceneController(scene_panel=panel, run_controller=rc, enabled=False)
    rc.play()
    rc.tick(0.020)
    assert "mounts" in panel.status_label().text()
    ctl.set_enabled(True)
    rc.tick(0.020)
    assert "headless" in panel.status_label().text()


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


def test_workspace_exposes_scene_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.scene_controller(), SimulatorSceneController)
    assert ws.scene_controller().enabled is True


def test_workspace_run_tick_paints_scene_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    panel = ws.scene_3d_panel()
    assert "1" in panel.frame_label().text()
    assert "headless" in panel.status_label().text()


def test_workspace_scene_panel_disabled_3d_viewer(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Workspace's enable_3d_viewer kwarg propagates to the Scene3DPanel."""
    ws = _ws(qtbot)
    assert ws.scene_3d_panel().is_3d_viewer_enabled() is False
    assert ws.scene_3d_panel().interactor() is None
