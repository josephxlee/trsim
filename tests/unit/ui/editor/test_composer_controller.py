"""ScenarioComposerController validation tests."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.composer import ScenarioComposer, ScenarioComposerController

pytestmark = pytest.mark.qt


def _build(qtbot) -> tuple[ScenarioComposer, ScenarioComposerController]:  # type: ignore[no-untyped-def]
    composer = ScenarioComposer()
    qtbot.addWidget(composer)
    controller = ScenarioComposerController(composer=composer)
    return composer, controller


def _select_combo_text(combo, text: str) -> None:  # type: ignore[no-untyped-def]
    """Add ``text`` as a combo entry and select it."""
    combo.addItem(text)
    combo.setCurrentText(text)


def test_validation_ok_when_all_three_combos_have_values(qtbot) -> None:  # type: ignore[no-untyped-def]
    composer, controller = _build(qtbot)
    _select_combo_text(composer.map_combo(), "east_coast")
    _select_combo_text(composer.radar_combo(), "kuband")
    _select_combo_text(composer.targets_combo(), "fighter_a")
    status, messages = controller.run_validation()
    assert status == "OK"
    assert any("east_coast" in m for m in messages)
    assert any("kuband" in m for m in messages)
    assert any("fighter_a" in m for m in messages)


def test_validation_error_when_map_missing(qtbot) -> None:  # type: ignore[no-untyped-def]
    composer, controller = _build(qtbot)
    _select_combo_text(composer.radar_combo(), "kuband")
    _select_combo_text(composer.targets_combo(), "fighter_a")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("Map" in m for m in messages)


def test_validation_error_when_radar_missing(qtbot) -> None:  # type: ignore[no-untyped-def]
    composer, controller = _build(qtbot)
    _select_combo_text(composer.map_combo(), "east_coast")
    _select_combo_text(composer.targets_combo(), "fighter_a")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("Radar" in m for m in messages)


def test_validation_warn_when_only_targets_missing(qtbot) -> None:  # type: ignore[no-untyped-def]
    composer, controller = _build(qtbot)
    _select_combo_text(composer.map_combo(), "east_coast")
    _select_combo_text(composer.radar_combo(), "kuband")
    status, messages = controller.run_validation()
    assert status == "WARN"
    assert any("target" in m.lower() for m in messages)


def test_validate_signal_triggers_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Clicking Validate (signal emission) routes through the controller
    and updates the validation panel."""
    composer, _controller = _build(qtbot)
    _select_combo_text(composer.map_combo(), "east_coast")
    _select_combo_text(composer.radar_combo(), "kuband")
    _select_combo_text(composer.targets_combo(), "fighter_a")
    composer.validate_requested.emit()
    # The set_validation call should have written into the panel's
    # status label. Use the public accessor to confirm.
    assert "OK" in composer.validation_status_label().text()  # type: ignore[attr-defined]
