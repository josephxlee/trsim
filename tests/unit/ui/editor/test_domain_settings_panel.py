"""Unit tests for the Domain Settings panel (Phase 4 G2, plan/11 § 11.11.8)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain
from workbench.ui.editor.map_editor.domain_settings import DomainSettingsPanel

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------


def test_default_domain_is_25km_square(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    d = panel.current_domain()
    assert d.bounds_east == (-25000.0, 25000.0)
    assert d.bounds_north == (-25000.0, 25000.0)
    assert d.ceiling_alt_m == 30000.0
    assert d.floor_alt_m == -100.0


def test_default_outside_is_open_sea(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    assert panel.current_outside_environment() is OutsideEnvironment.OPEN_SEA
    assert panel.outside_radio(OutsideEnvironment.OPEN_SEA).isChecked() is True


def test_default_status_is_ok(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    assert panel.status_text() == "OK"


def test_all_four_outside_radios_have_object_names(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    for mode in panel.available_outside_modes():
        btn = panel.outside_radio(mode)
        assert btn.objectName() == f"DomainSettingsOutside_{mode.value}"


def test_panel_lists_four_outside_modes_in_plan_order(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    # plan/11 § 11.11.8 mockup order: OPEN_SEA -> OPEN_LAND -> BLOCKED -> INFINITE_PLANE.
    assert panel.available_outside_modes() == (
        OutsideEnvironment.OPEN_SEA,
        OutsideEnvironment.OPEN_LAND,
        OutsideEnvironment.BLOCKED,
        OutsideEnvironment.INFINITE_PLANE,
    )


# ---------------------------------------------------------------------
# Bound editing
# ---------------------------------------------------------------------


def test_changing_east_max_emits_domain_changed(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    panel.east_max_spin().setValue(30000.0)
    assert len(received) == 1
    assert received[0].bounds_east == (-25000.0, 30000.0)
    assert panel.current_domain().bounds_east == (-25000.0, 30000.0)


def test_changing_ceiling_emits_with_new_ceiling(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    panel.ceiling_spin().setValue(25000.0)
    assert len(received) == 1
    assert received[0].ceiling_alt_m == 25000.0


def test_invalid_east_max_does_not_emit_and_status_reports(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    # Default east_min = -25000. Push east_max below it.
    panel.east_max_spin().setValue(-30000.0)
    assert received == []
    assert "bounds_east" in panel.status_text()
    # Previous valid domain still in place.
    assert panel.current_domain().bounds_east == (-25000.0, 25000.0)


def test_status_recovers_to_ok_after_fixing_bounds(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    panel.east_max_spin().setValue(-30000.0)  # invalid
    assert "Invalid" in panel.status_text()
    panel.east_max_spin().setValue(40000.0)  # valid
    assert panel.status_text() == "OK"
    assert panel.current_domain().bounds_east == (-25000.0, 40000.0)


def test_invalid_ceiling_below_floor_keeps_previous(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    prev = panel.current_domain()
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    panel.ceiling_spin().setValue(-200.0)
    assert received == []
    assert panel.current_domain() is prev


# ---------------------------------------------------------------------
# Outside environment radios
# ---------------------------------------------------------------------


def test_clicking_outside_radio_emits_change(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[OutsideEnvironment] = []
    panel.outside_environment_changed.connect(received.append)
    panel.outside_radio(OutsideEnvironment.BLOCKED).setChecked(True)
    assert received == [OutsideEnvironment.BLOCKED]
    assert panel.current_outside_environment() is OutsideEnvironment.BLOCKED


def test_outside_radios_are_exclusive(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    panel.outside_radio(OutsideEnvironment.OPEN_LAND).setChecked(True)
    assert panel.outside_radio(OutsideEnvironment.OPEN_LAND).isChecked() is True
    assert panel.outside_radio(OutsideEnvironment.OPEN_SEA).isChecked() is False


# ---------------------------------------------------------------------
# Programmatic mirrors
# ---------------------------------------------------------------------


def test_set_domain_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    new_d = SimulationDomain(
        bounds_east=(-1000.0, 1000.0),
        bounds_north=(-2000.0, 2000.0),
        ceiling_alt_m=15000.0,
        floor_alt_m=-50.0,
    )
    panel.set_domain(new_d)
    assert panel.east_min_spin().value() == -1000.0
    assert panel.east_max_spin().value() == 1000.0
    assert panel.north_min_spin().value() == -2000.0
    assert panel.north_max_spin().value() == 2000.0
    assert panel.ceiling_spin().value() == 15000.0
    assert panel.floor_spin().value() == -50.0
    assert panel.current_domain() == new_d
    assert received == [new_d]


def test_set_outside_environment_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[OutsideEnvironment] = []
    panel.outside_environment_changed.connect(received.append)
    panel.set_outside_environment(OutsideEnvironment.INFINITE_PLANE)
    assert panel.current_outside_environment() is OutsideEnvironment.INFINITE_PLANE
    assert panel.outside_radio(OutsideEnvironment.INFINITE_PLANE).isChecked()
    assert received == [OutsideEnvironment.INFINITE_PLANE]


def test_setting_set_domain_does_not_double_emit_when_value_unchanged(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    received: list[SimulationDomain] = []
    panel.domain_changed.connect(received.append)
    same = panel.current_domain()
    panel.set_domain(same)
    # set_domain emits exactly once; the inner spin setValue with same
    # value is silent (Qt suppresses no-op valueChanged).
    assert received == [same]


# ---------------------------------------------------------------------
# Map bounds readout
# ---------------------------------------------------------------------


def test_map_bounds_label_default_text(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    assert "(no map loaded)" in panel.map_bounds_label().text()


def test_set_map_bounds_readout_replaces_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = DomainSettingsPanel()
    qtbot.addWidget(panel)
    panel.set_map_bounds_readout("E:[-5000, 5000] N:[-5000, 5000]")
    assert panel.map_bounds_label().text() == "E:[-5000, 5000] N:[-5000, 5000]"


# ---------------------------------------------------------------------
# Display labels
# ---------------------------------------------------------------------


def test_display_label_for_each_mode_is_non_empty() -> None:
    for mode in OutsideEnvironment:
        assert DomainSettingsPanel.display_label_for(mode)
