"""Phase 4 L4 — Properties panel tick-driven Simulator snapshot."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False)
    qtbot.addWidget(ws)
    return ws


def test_properties_initial_context_is_nothing_selected(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert ws.properties_panel().context_label().text() == "(nothing selected)"
    assert ws.is_properties_owned_by_selection() is False


def test_tick_paints_simulator_context(qtbot) -> None:  # type: ignore[no-untyped-def]
    """A single play+tick renders the live snapshot into Properties."""
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    panel = ws.properties_panel()
    assert panel.context_label().text() == "Simulator"
    form = panel.form_layout()
    # Form should now contain 4 rows: sim_t_s / frame_id / state / speed.
    assert form.rowCount() == 4


def test_selection_pins_panel_against_tick(qtbot) -> None:  # type: ignore[no-untyped-def]
    """User picks an object - subsequent ticks must not overwrite it."""
    ws = _ws(qtbot)
    ws.show_selected_in_properties("Target #3", {"east_m": "1234.5", "north_m": "678.9"})
    assert ws.is_properties_owned_by_selection() is True
    assert ws.properties_panel().context_label().text() == "Target #3"
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    controller.tick(0.020)
    assert ws.properties_panel().context_label().text() == "Target #3"


def test_clear_selection_returns_to_simulator_snapshot(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    ws.show_selected_in_properties("Target #3", {"east_m": "1234.5"})
    ws.clear_property_selection()
    assert ws.is_properties_owned_by_selection() is False
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    assert ws.properties_panel().context_label().text() == "Simulator"


def test_tick_updates_sim_t_s_each_step(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Three consecutive ticks should rewrite the form's sim_t_s row
    each time. We sample by inspecting the QLabel text inside the form
    layout."""
    from PySide6.QtWidgets import QLabel

    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()

    def _sim_t_text() -> str:
        form = ws.properties_panel().form_layout()
        # Row 0 is sim_t_s. fieldAt returns the QLayoutItem for the
        # value column.
        item = form.itemAt(0, form.ItemRole.FieldRole)
        assert item is not None
        widget = item.widget()
        assert isinstance(widget, QLabel)
        return widget.text()

    last = ""
    for _ in range(3):
        controller.tick(0.020)
        current = _sim_t_text()
        assert current != last
        last = current
