"""Unit tests for the Scenario Composer widget (Phase 4.5)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.composer import ScenarioComposer
from workbench.ui.editor.composer.widget import (
    DEFAULT_ATMOSPHERES,
    DEFAULT_SEA_STATES,
)

pytestmark = pytest.mark.qt


def test_composer_default_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    assert cmp.name_edit().text() == "(unnamed)"
    # Each resource combo starts with a single sentinel "(none)" entry.
    for combo in (cmp.map_combo(), cmp.radar_combo(), cmp.targets_combo()):
        assert combo.count() == 1
        assert combo.itemText(0) == "(none)"


def test_default_sea_state_and_atmosphere_options_match_constants(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    sea = [cmp.sea_state_combo().itemText(i) for i in range(cmp.sea_state_combo().count())]
    atm = [cmp.atmosphere_combo().itemText(i) for i in range(cmp.atmosphere_combo().count())]
    assert sea == list(DEFAULT_SEA_STATES)
    assert atm == list(DEFAULT_ATMOSPHERES)


def test_set_resource_options_replaces_dropdown_items(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_map_options(["EastCoast_50km", "Harbor_10km"])
    items = [cmp.map_combo().itemText(i) for i in range(cmp.map_combo().count())]
    assert items == ["(none)", "EastCoast_50km", "Harbor_10km"]


def test_save_button_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    received: list[None] = []
    cmp.save_requested.connect(lambda: received.append(None))
    cmp.findChild(type(cmp.findChildren(object)[0]), "ComposerSaveBtn") if False else None
    save_btn = cmp.findChild(object, "ComposerSaveBtn")
    assert save_btn is not None
    save_btn.click()  # type: ignore[attr-defined]
    assert received == [None]


def test_open_resource_buttons_emit_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    received: list[str] = []
    cmp.open_resource_requested.connect(received.append)
    for category in ("map", "radar", "targets"):
        btn = cmp.findChild(object, f"ComposerOpen_{category}")
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert received == ["map", "radar", "targets"]


def test_set_validation_updates_status_and_messages(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_validation("OK", ["All hashes match", "Coastline coherent"])
    assert cmp.validation_status_label().text() == "Status: OK"
    msgs = cmp.validation_messages()
    assert msgs.count() == 2
    assert msgs.item(0).text() == "All hashes match"
    assert msgs.item(1).text() == "Coastline coherent"


def test_validation_message_replacement_clears_previous(qtbot) -> None:  # type: ignore[no-untyped-def]
    cmp = ScenarioComposer()
    qtbot.addWidget(cmp)
    cmp.set_validation("WARN", ["one", "two"])
    cmp.set_validation("OK", [])
    assert cmp.validation_status_label().text() == "Status: OK"
    assert cmp.validation_messages().count() == 0


def test_composer_page_hosts_scenario_composer(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activity_pages import ScenarioComposerPage

    page = ScenarioComposerPage()
    qtbot.addWidget(page)
    assert isinstance(page.composer(), ScenarioComposer)
