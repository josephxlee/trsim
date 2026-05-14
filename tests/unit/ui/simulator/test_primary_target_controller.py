"""SimulatorPrimaryTargetController + workspace wiring tests (Phase 4 L6)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.simulator import MockPrimaryTargetGenerator
from workbench.ui.simulator.panels import PropertiesPanel, ScopePOVPanel
from workbench.ui.simulator.primary_target_controller import (
    SimulatorPrimaryTargetController,
)
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Standalone controller
# ---------------------------------------------------------------------


def _panels(qtbot) -> tuple[ScopePOVPanel, PropertiesPanel]:  # type: ignore[no-untyped-def]
    s = ScopePOVPanel()
    qtbot.addWidget(s)
    p = PropertiesPanel()
    qtbot.addWidget(p)
    return s, p


def test_paint_for_fills_both_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props = _panels(qtbot)
    ctl = SimulatorPrimaryTargetController(scope_panel=scope, properties_panel=props)
    ctl.paint_for(0.0, 0)
    # Scope cross-hair shows the target marker.
    xs, _ys = scope.target_marker().getData()
    assert len(xs) == 1
    # Properties form lists Range / Azimuth / Lock at minimum.
    assert props.context_label().text() == "Primary Target"
    # 6 rows: Range, Azimuth, Elevation, RCS, Speed, Lock.
    assert props.form_layout().rowCount() == 6


def test_paint_for_az_readout_matches_snapshot(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props = _panels(qtbot)
    ctl = SimulatorPrimaryTargetController(scope_panel=scope, properties_panel=props)
    ctl.paint_for(0.0, 0)
    snap = ctl.generator.snapshot_for(0.0)
    txt = scope.az_label().text()
    assert f"{snap.actual_az_deg:.2f}" in txt
    assert f"{snap.commanded_az_deg:.2f}" in txt


def test_paint_for_lock_text_changes_after_lock_time(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props = _panels(qtbot)
    gen = MockPrimaryTargetGenerator(lock_after_s=0.5)
    ctl = SimulatorPrimaryTargetController(scope_panel=scope, properties_panel=props, generator=gen)
    ctl.paint_for(0.0, 0)
    # Read the Lock row label content (it's the second column of the
    # last form row).
    rows = props.form_layout().rowCount()
    last_field = props.form_layout().itemAt(rows - 1, props.form_layout().ItemRole.FieldRole)
    assert last_field is not None
    label = last_field.widget()
    assert label.text() == "searching"  # type: ignore[attr-defined]
    ctl.paint_for(1.0, 60)
    last_field = props.form_layout().itemAt(rows - 1, props.form_layout().ItemRole.FieldRole)
    assert last_field is not None
    label = last_field.widget()
    assert label.text() == "LOCKED"  # type: ignore[attr-defined]


def test_inject_custom_generator(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props = _panels(qtbot)
    gen = MockPrimaryTargetGenerator(orbit_radius_m=1234.0)
    ctl = SimulatorPrimaryTargetController(scope_panel=scope, properties_panel=props, generator=gen)
    assert ctl.generator is gen


def test_controller_idempotent_disable_without_run_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props = _panels(qtbot)
    ctl = SimulatorPrimaryTargetController(scope_panel=scope, properties_panel=props)
    ctl.set_enabled(False)
    assert ctl.enabled is False
    ctl.set_enabled(False)
    assert ctl.enabled is False


# ---------------------------------------------------------------------
# RunController -> primary-target controller wiring
# ---------------------------------------------------------------------


def _run_ctl(qtbot) -> tuple[ScopePOVPanel, PropertiesPanel, SimulatorRunController]:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.panels import RunPanel

    scope = ScopePOVPanel()
    qtbot.addWidget(scope)
    props = PropertiesPanel()
    qtbot.addWidget(props)
    run = RunPanel()
    qtbot.addWidget(run)
    rc = SimulatorRunController(run_panel=run, autostart_timer=False)
    return scope, props, rc


def test_tick_completed_paints_both_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props, rc = _run_ctl(qtbot)
    ctl = SimulatorPrimaryTargetController(
        scope_panel=scope, properties_panel=props, run_controller=rc, parent=scope
    )
    assert ctl.enabled is True
    rc.play()
    rc.tick(0.020)
    xs, _ = scope.target_marker().getData()
    assert len(xs) == 1
    assert props.context_label().text() == "Primary Target"


def test_disabled_controller_does_not_paint(qtbot) -> None:  # type: ignore[no-untyped-def]
    scope, props, rc = _run_ctl(qtbot)
    SimulatorPrimaryTargetController(
        scope_panel=scope,
        properties_panel=props,
        run_controller=rc,
        enabled=False,
        parent=scope,
    )
    rc.play()
    rc.tick(0.020)
    # Properties form stays at the default "(nothing selected)" label.
    assert props.context_label().text() == "(nothing selected)"


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


def test_workspace_exposes_primary_target_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert isinstance(ws.primary_target_controller(), SimulatorPrimaryTargetController)
    assert ws.primary_target_controller().enabled is True


def test_workspace_run_tick_paints_scope_and_properties(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.sim_play()
    ws.run_controller().tick(0.020)
    xs, _ = ws.scope_pov_panel().target_marker().getData()
    assert len(xs) == 1
    assert ws.properties_panel().context_label().text() == "Primary Target"
