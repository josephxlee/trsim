"""Composer Installation + Domain Override tests (Phase 4 G4)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.simulation_domain import OutsideEnvironment
from workbench.ui.editor.composer import ScenarioComposer
from workbench.ui.editor.composer.widget import INHERIT_LABEL, CoverageStats

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Installation block: new fields
# ---------------------------------------------------------------------


def test_installation_has_position_and_orientation_fields(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.east_edit().text() == "0.0"
    assert cmp.north_edit().text() == "0.0"
    assert cmp.azimuth_edit().text() == "180.0"
    assert cmp.elevation_edit().text() == "0.0"


def test_altitude_label_default_is_pending(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert "pending" in cmp.altitude_label().text().lower()


def test_dem_preview_exists_with_object_name(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.dem_preview().objectName() == "ComposerInstallDEMPreview"


def test_coverage_stats_labels_default_to_placeholder(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.max_range_label().text() == "--"
    assert cmp.obstructed_label().text() == "--"
    assert cmp.blind_bearings_label().text() == "--"


# ---------------------------------------------------------------------
# Position edits + signals
# ---------------------------------------------------------------------


def test_set_position_emits_position_changed(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    received: list[tuple[float, float, float, float]] = []
    cmp.position_changed.connect(lambda e, n, a, el: received.append((e, n, a, el)))
    cmp.set_position(100.0, 200.0, 90.0, -5.0)
    assert received == [(100.0, 200.0, 90.0, -5.0)]
    assert cmp.east_edit().text() == "100"
    assert cmp.north_edit().text() == "200"
    assert cmp.azimuth_edit().text() == "90"
    assert cmp.elevation_edit().text() == "-5"


def test_current_position_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_position(1.5, -2.5, 270.0, 10.0)
    assert cmp.current_position() == (1.5, -2.5, 270.0, 10.0)


def test_invalid_position_text_returns_zero_in_current(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.east_edit().setText("not_a_number")
    e, n, _az, _el = cmp.current_position()
    assert e == 0.0
    assert n == 0.0  # default values for the other fields


# ---------------------------------------------------------------------
# Terrain altitude readout
# ---------------------------------------------------------------------


def test_set_terrain_altitude_shows_sampled_value(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_terrain_altitude(87.35)
    assert "87.35" in cmp.altitude_label().text()
    assert "DEM sampled" in cmp.altitude_label().text()


def test_set_terrain_altitude_none_resets(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_terrain_altitude(50.0)
    cmp.set_terrain_altitude(None)
    assert "pending" in cmp.altitude_label().text().lower()


# ---------------------------------------------------------------------
# Coverage stats readout
# ---------------------------------------------------------------------


def test_set_coverage_stats_renders_all_three(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    stats = CoverageStats(
        max_range_km=28.4,
        obstructed_sectors=3,
        total_sectors=72,
        blind_bearings_deg=(45.0, 120.0, 280.0),
    )
    cmp.set_coverage_stats(stats)
    assert "28.4" in cmp.max_range_label().text()
    assert "3/72" in cmp.obstructed_label().text()
    # Each blind bearing should appear in the label.
    text = cmp.blind_bearings_label().text()
    assert "45" in text and "120" in text and "280" in text


def test_set_coverage_stats_handles_empty_blind_bearings(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_coverage_stats(CoverageStats(max_range_km=10.0, obstructed_sectors=0, total_sectors=72))
    assert "none" in cmp.blind_bearings_label().text().lower()


def test_set_coverage_stats_none_resets(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_coverage_stats(CoverageStats(max_range_km=10.0, obstructed_sectors=0, total_sectors=1))
    cmp.set_coverage_stats(None)
    assert cmp.max_range_label().text() == "--"
    assert cmp.obstructed_label().text() == "--"
    assert cmp.blind_bearings_label().text() == "--"


# ---------------------------------------------------------------------
# Domain Override block
# ---------------------------------------------------------------------


def test_domain_override_check_starts_unchecked(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.is_domain_override_enabled() is False
    assert cmp.is_outside_override_enabled() is False


def test_outside_combo_includes_inherit_first(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    combo = cmp.outside_override_combo()
    assert combo.count() == 5  # Inherit + 4 modes
    assert combo.itemText(0) == INHERIT_LABEL


def test_outside_combo_disabled_until_check(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.outside_override_combo().isEnabled() is False
    cmp.outside_override_check().setChecked(True)
    assert cmp.outside_override_combo().isEnabled() is True


def test_domain_override_toggle_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    received: list[bool] = []
    cmp.domain_override_toggled.connect(received.append)
    cmp.domain_override_check().setChecked(True)
    cmp.domain_override_check().setChecked(False)
    assert received == [True, False]


def test_outside_override_toggle_emits_both_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    toggled: list[bool] = []
    changed: list[OutsideEnvironment | None] = []
    cmp.outside_override_toggled.connect(toggled.append)
    cmp.outside_override_changed.connect(changed.append)
    cmp.outside_override_check().setChecked(True)
    # When the checkbox flips on but the combo is still on "Inherit"
    # (index 0), the resolved override is still None.
    assert toggled == [True]
    assert changed == [None]


def test_outside_override_combo_change_emits_value_when_enabled(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.outside_override_check().setChecked(True)
    received: list[OutsideEnvironment | None] = []
    cmp.outside_override_changed.connect(received.append)
    cmp.set_outside_override_mode(OutsideEnvironment.BLOCKED)
    assert cmp.current_outside_override() is OutsideEnvironment.BLOCKED
    assert OutsideEnvironment.BLOCKED in received


def test_outside_override_current_is_none_when_check_off(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.outside_override_check().setChecked(True)
    cmp.set_outside_override_mode(OutsideEnvironment.OPEN_LAND)
    cmp.outside_override_check().setChecked(False)
    assert cmp.current_outside_override() is None


def test_set_outside_override_mode_none_selects_inherit(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.outside_override_check().setChecked(True)
    cmp.set_outside_override_mode(OutsideEnvironment.OPEN_LAND)
    cmp.set_outside_override_mode(None)
    assert cmp.outside_override_combo().currentIndex() == 0
    assert cmp.current_outside_override() is None


# ---------------------------------------------------------------------
# CoverageStats dataclass
# ---------------------------------------------------------------------


def test_coverage_stats_is_frozen() -> None:
    stats = CoverageStats(max_range_km=1.0, obstructed_sectors=0, total_sectors=1)
    with pytest.raises(AttributeError):
        stats.max_range_km = 2.0  # type: ignore[misc]
