"""Unit tests for the Atmosphere Panel widget (Phase 4.8)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.atmosphere_panel import SKY_CONDITIONS, AtmospherePanel
from workbench.ui.editor.atmosphere_panel.widget import AtmosphereState

pytestmark = pytest.mark.qt


def test_default_state_uses_isa_baseline(qtbot) -> None:  # type: ignore[no-untyped-def]
    ap = AtmospherePanel()
    qtbot.addWidget(ap)
    state = ap.current_state()
    assert state.sky_condition == "Clear"
    assert state.visibility_km == 20.0
    assert state.rain_rate_mm_per_h == 0.0
    assert state.temperature_c == 15.0
    assert state.pressure_hpa == 1013.25


def test_sky_combo_lists_every_canonical_condition(qtbot) -> None:  # type: ignore[no-untyped-def]
    ap = AtmospherePanel()
    qtbot.addWidget(ap)
    items = [ap.sky_combo().itemText(i) for i in range(ap.sky_combo().count())]
    assert items == list(SKY_CONDITIONS)


def test_set_state_round_trips_through_current_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    ap = AtmospherePanel()
    qtbot.addWidget(ap)
    target = AtmosphereState(
        sky_condition="Rain",
        visibility_km=2.5,
        rain_rate_mm_per_h=12.0,
        temperature_c=10.0,
        pressure_hpa=1005.0,
    )
    ap.set_state(target)
    assert ap.current_state() == target


def test_invalid_numeric_input_raises_value_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    ap = AtmospherePanel()
    qtbot.addWidget(ap)
    ap.visibility_edit().setText("not a number")
    with pytest.raises(ValueError, match=r"atmosphere field"):
        ap.current_state()


def test_state_changed_emits_after_user_edit(qtbot) -> None:  # type: ignore[no-untyped-def]
    ap = AtmospherePanel()
    qtbot.addWidget(ap)
    received: list[AtmosphereState] = []
    ap.state_changed.connect(received.append)
    ap.rain_rate_edit().setText("5.0")
    ap.rain_rate_edit().editingFinished.emit()
    assert received and received[-1].rain_rate_mm_per_h == 5.0
