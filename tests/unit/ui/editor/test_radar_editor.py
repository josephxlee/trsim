"""Unit tests for the Radar Editor widget (Phase 4.7)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.radar_editor import (
    AntennaType,
    RadarEditor,
    RXChannelMode,
)

pytestmark = pytest.mark.qt


def test_default_antenna_type_is_parabolic(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    assert re.current_antenna_type() is AntennaType.PARABOLIC
    assert re.antenna_radio(AntennaType.PARABOLIC).isChecked() is True


def test_default_rx_mode_is_monopulse(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    assert re.current_rx_mode() is RXChannelMode.MONOPULSE_4CH
    assert re.rx_radio(RXChannelMode.MONOPULSE_4CH).isChecked() is True


def test_select_antenna_type_swaps_dynamic_form(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    received: list[AntennaType] = []
    re.antenna_type_changed.connect(received.append)
    re.select_antenna_type(AntennaType.PLANAR_ARRAY)
    assert received == [AntennaType.PLANAR_ARRAY]
    assert re.current_antenna_type() is AntennaType.PLANAR_ARRAY
    assert re.antenna_stack().currentWidget() is re.antenna_form(AntennaType.PLANAR_ARRAY)
    re.select_antenna_type(AntennaType.PARABOLIC)
    assert re.antenna_stack().currentWidget() is re.antenna_form(AntennaType.PARABOLIC)


def test_rx_radio_change_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    received: list[RXChannelMode] = []
    re.rx_mode_changed.connect(received.append)
    re.select_rx_mode(RXChannelMode.SINGLE_SUM)
    assert received == [RXChannelMode.SINGLE_SUM]
    assert re.current_rx_mode() is RXChannelMode.SINGLE_SUM


def test_antenna_radios_are_exclusive(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    re.select_antenna_type(AntennaType.PLANAR_ARRAY)
    checked = sum(re.antenna_radio(a).isChecked() for a in AntennaType)
    assert checked == 1


def test_set_computed_values_updates_labels(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    re.set_computed_values(beamwidth_az_deg=6.4, beamwidth_el_deg=6.4, peak_gain_dbi=27.1)
    az, el, gain = re.computed_labels()
    assert "6.40" in az.text()
    assert "6.40" in el.text()
    assert "27.1" in gain.text()


def test_save_and_save_as_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    saw = {"save": 0, "save_as": 0}
    re.save_requested.connect(lambda: saw.__setitem__("save", saw["save"] + 1))
    re.save_as_requested.connect(lambda: saw.__setitem__("save_as", saw["save_as"] + 1))
    save = re.findChild(object, "RadarEditorSaveBtn")
    save_as = re.findChild(object, "RadarEditorSaveAsBtn")
    assert save is not None and save_as is not None
    save.click()  # type: ignore[attr-defined]
    save_as.click()  # type: ignore[attr-defined]
    assert saw == {"save": 1, "save_as": 1}


def test_planar_form_exposes_n_az_n_el_fields(qtbot) -> None:  # type: ignore[no-untyped-def]
    re = RadarEditor()
    qtbot.addWidget(re)
    re.select_antenna_type(AntennaType.PLANAR_ARRAY)
    n_az = re.findChild(object, "AntennaPlanarNAz")
    n_el = re.findChild(object, "AntennaPlanarNEl")
    assert n_az is not None and n_el is not None


def test_radar_editor_page_hosts_real_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activity_pages import RadarEditorPage

    page = RadarEditorPage()
    qtbot.addWidget(page)
    assert isinstance(page.radar_editor(), RadarEditor)
