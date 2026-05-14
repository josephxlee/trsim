"""AtmospherePropagator + Composer atmosphere hint tests."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.atmosphere_panel import (
    AtmospherePanel,
    AtmospherePropagator,
    AtmosphereState,
    format_atmosphere_hint,
)
from workbench.ui.editor.composer import ScenarioComposer

pytestmark = pytest.mark.qt


def test_format_atmosphere_hint_default() -> None:
    state = AtmosphereState(
        sky_condition="Clear",
        visibility_km=20.0,
        rain_rate_mm_per_h=0.0,
        temperature_c=15.0,
        pressure_hpa=1013.25,
    )
    assert format_atmosphere_hint(state) == "editor: Clear, vis=20.0 km, rain=0.0 mm/h"


def test_format_atmosphere_hint_rain() -> None:
    state = AtmosphereState(
        sky_condition="Rain",
        visibility_km=5.5,
        rain_rate_mm_per_h=12.3,
        temperature_c=10.0,
        pressure_hpa=1000.0,
    )
    assert format_atmosphere_hint(state) == "editor: Rain, vis=5.5 km, rain=12.3 mm/h"


def test_composer_atmosphere_hint_label_default(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    composer = ScenarioComposer()
    qtbot.addWidget(composer)
    assert composer.atmosphere_hint_label().text() == "(editor: not yet set)"


def test_composer_set_atmosphere_hint_updates_label(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    composer = ScenarioComposer()
    qtbot.addWidget(composer)
    composer.set_atmosphere_hint("editor: Fog, vis=0.5 km, rain=0.0 mm/h")
    assert "Fog" in composer.atmosphere_hint_label().text()


def _build_wired(
    qtbot,  # type: ignore[no-untyped-def]
) -> tuple[AtmospherePanel, ScenarioComposer, AtmospherePropagator]:
    """Build the three connected widgets + keep refs alive.

    The propagator must outlive the QObject signal connection; assigning
    it to the test fixture (rather than letting it fall out of scope)
    is what keeps the wiring intact under pytest-qt.
    """
    panel = AtmospherePanel()
    qtbot.addWidget(panel)
    composer = ScenarioComposer()
    qtbot.addWidget(composer)
    propagator = AtmospherePropagator(panel=panel, composer=composer, parent=panel)
    return panel, composer, propagator


def test_propagator_paints_initial_state_on_construction(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    _panel, composer, _prop = _build_wired(qtbot)
    # Panel defaults: sky=Clear, vis=20.0, rain=0.0, T=15, P=1013.25.
    assert "Clear" in composer.atmosphere_hint_label().text()
    assert "20.0 km" in composer.atmosphere_hint_label().text()


def test_propagator_forwards_state_changed_signal(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    panel, composer, _prop = _build_wired(qtbot)
    panel.sky_combo().setCurrentText("Fog")
    panel.rain_rate_edit().setText("3.5")
    panel.rain_rate_edit().editingFinished.emit()
    assert "Fog" in composer.atmosphere_hint_label().text()
    assert "3.5 mm/h" in composer.atmosphere_hint_label().text()


def test_propagator_ignores_invalid_field_edits(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """AtmospherePanel.state_changed only fires for well-formed inputs;
    garbage in the visibility box leaves the hint untouched."""
    panel, composer, _prop = _build_wired(qtbot)
    before = composer.atmosphere_hint_label().text()
    panel.visibility_edit().setText("garbage")
    panel.visibility_edit().editingFinished.emit()
    assert composer.atmosphere_hint_label().text() == before
