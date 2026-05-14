"""SimulatorWorkspace arrow-key manual pointing tests (Phase 4 P5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(
        nn_datasets_root=None,
        autostart_run_timer=False,
        enable_3d_viewer=False,
    )
    qtbot.addWidget(ws)
    return ws


def _press(ws: SimulatorWorkspace, key: Qt.Key) -> None:
    """Dispatch a synthetic keyPress to the workspace's handler."""
    event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    ws.keyPressEvent(event)


# ---------------------------------------------------------------------
# Step constants
# ---------------------------------------------------------------------


def test_default_step_constants() -> None:
    assert SimulatorWorkspace.MANUAL_AZ_STEP_DEG == 0.5
    assert SimulatorWorkspace.MANUAL_EL_STEP_DEG == 0.5


# ---------------------------------------------------------------------
# Arrow-key behaviour
# ---------------------------------------------------------------------


def test_initial_manual_offset_is_zero(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ptc = ws.primary_target_controller()
    assert ptc.manual_az_offset_deg == 0.0
    assert ptc.manual_el_offset_deg == 0.0


def test_right_arrow_increments_az(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Right)
    assert ws.primary_target_controller().manual_az_offset_deg == pytest.approx(0.5)
    assert ws.primary_target_controller().manual_el_offset_deg == 0.0


def test_left_arrow_decrements_az(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Left)
    assert ws.primary_target_controller().manual_az_offset_deg == pytest.approx(-0.5)


def test_up_arrow_increments_el(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Up)
    assert ws.primary_target_controller().manual_el_offset_deg == pytest.approx(0.5)


def test_down_arrow_decrements_el(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Down)
    assert ws.primary_target_controller().manual_el_offset_deg == pytest.approx(-0.5)


def test_repeated_arrows_accumulate(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    for _ in range(4):
        _press(ws, Qt.Key.Key_Right)
    assert ws.primary_target_controller().manual_az_offset_deg == pytest.approx(2.0)


def test_home_key_resets_accumulators(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Right)
    _press(ws, Qt.Key.Key_Up)
    _press(ws, Qt.Key.Key_Home)
    ptc = ws.primary_target_controller()
    assert ptc.manual_az_offset_deg == 0.0
    assert ptc.manual_el_offset_deg == 0.0


def test_zero_key_resets_accumulators(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_Right)
    _press(ws, Qt.Key.Key_0)
    ptc = ws.primary_target_controller()
    assert ptc.manual_az_offset_deg == 0.0


def test_other_key_falls_through_to_super(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Non-arrow keys must not change the manual accumulators."""
    ws = _ws(qtbot)
    _press(ws, Qt.Key.Key_A)
    ptc = ws.primary_target_controller()
    assert ptc.manual_az_offset_deg == 0.0
    assert ptc.manual_el_offset_deg == 0.0


def test_arrow_press_updates_scope_readout(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Pressing Right immediately repaints the scope (no QTimer tick needed)."""
    ws = _ws(qtbot)
    # Baseline at sim_t = 0 — paint once so the cross-hair has a starting point.
    ws.primary_target_controller().paint_for(0.0, 0)
    baseline_text = ws.scope_pov_panel().az_label().text()
    _press(ws, Qt.Key.Key_Right)
    # AZ readout text should reflect the +0.5 deg offset (paint_for ran).
    new_text = ws.scope_pov_panel().az_label().text()
    assert new_text != baseline_text


# ---------------------------------------------------------------------
# Controller-level manual-offset API
# ---------------------------------------------------------------------


def test_add_manual_offset_accepts_kwargs(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.primary_target_controller().add_manual_offset(d_az_deg=1.5, d_el_deg=-0.25)
    ptc = ws.primary_target_controller()
    assert ptc.manual_az_offset_deg == pytest.approx(1.5)
    assert ptc.manual_el_offset_deg == pytest.approx(-0.25)


def test_reset_manual_offset_clears_both_axes(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ptc = ws.primary_target_controller()
    ptc.add_manual_offset(d_az_deg=2.0, d_el_deg=1.0)
    ptc.reset_manual_offset()
    assert ptc.manual_az_offset_deg == 0.0
    assert ptc.manual_el_offset_deg == 0.0
