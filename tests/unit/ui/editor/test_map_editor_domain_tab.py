"""Map Editor Domain tab integration tests (Phase 4 G3)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.map_resource import MapBounds
from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain
from workbench.ui.editor.map_editor import MapEditor
from workbench.ui.editor.map_editor.domain_settings import DomainSettingsPanel

pytestmark = pytest.mark.qt


def test_right_panel_has_two_tabs(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    tabs = me.right_tabs()
    assert tabs.count() == 2
    assert tabs.tabText(0) == "Layers"
    assert tabs.tabText(1) == "Domain"


def test_domain_panel_is_domain_settings_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    assert isinstance(me.domain_panel(), DomainSettingsPanel)


def test_layers_tab_active_by_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    # Layers tab matches the pre-G3 default — don't surprise existing users.
    assert me.right_tabs().currentIndex() == 0


def test_show_domain_tab_switches(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.show_domain_tab()
    assert me.right_tabs().currentIndex() == 1


def test_current_domain_forwards_to_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    assert me.current_domain() == me.domain_panel().current_domain()


def test_current_outside_environment_forwards(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    assert me.current_outside_environment() is OutsideEnvironment.OPEN_SEA


def test_set_domain_forwards_and_emits_map_editor_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    received: list[SimulationDomain] = []
    me.domain_changed.connect(received.append)
    d = SimulationDomain(
        bounds_east=(-1000.0, 1000.0),
        bounds_north=(-2000.0, 2000.0),
        ceiling_alt_m=12000.0,
        floor_alt_m=-50.0,
    )
    me.set_domain(d)
    assert me.current_domain() == d
    assert received == [d]


def test_set_outside_environment_forwards_and_emits(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    received: list[OutsideEnvironment] = []
    me.outside_environment_changed.connect(received.append)
    me.set_outside_environment(OutsideEnvironment.BLOCKED)
    assert me.current_outside_environment() is OutsideEnvironment.BLOCKED
    assert received == [OutsideEnvironment.BLOCKED]


def test_set_map_bounds_writes_readout(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.set_map_bounds(
        MapBounds(
            east_min_m=-5000.0,
            east_max_m=5000.0,
            north_min_m=-3000.0,
            north_max_m=4000.0,
        )
    )
    text = me.domain_panel().map_bounds_label().text()
    assert "-5000" in text
    assert "5000" in text
    assert "-3000" in text
    assert "4000" in text


def test_set_map_bounds_none_resets_readout(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.set_map_bounds(
        MapBounds(east_min_m=-100.0, east_max_m=100.0, north_min_m=-100.0, north_max_m=100.0)
    )
    me.set_map_bounds(None)
    assert me.domain_panel().map_bounds_label().text() == "(no map loaded)"


def test_inner_panel_signal_propagates_through_map_editor(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Editing inside DomainSettingsPanel must surface on MapEditor.domain_changed."""
    me = MapEditor()
    qtbot.addWidget(me)
    received: list[SimulationDomain] = []
    me.domain_changed.connect(received.append)
    me.domain_panel().east_max_spin().setValue(30000.0)
    assert len(received) == 1
    assert received[0].bounds_east == (-25000.0, 30000.0)
