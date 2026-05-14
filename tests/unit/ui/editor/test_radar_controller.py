"""RadarEditorController computed-values tests."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("PySide6")

from workbench.physics.antenna import (
    parabolic_beamwidth_3db_deg,
    parabolic_peak_gain_dbi,
)
from workbench.ui.editor.radar_editor import AntennaType, RadarEditor, RadarEditorController

pytestmark = pytest.mark.qt


def _build(qtbot) -> tuple[RadarEditor, RadarEditorController]:  # type: ignore[no-untyped-def]
    editor = RadarEditor()
    qtbot.addWidget(editor)
    controller = RadarEditorController(editor=editor)
    return editor, controller


def test_initial_paint_matches_parabolic_defaults(qtbot) -> None:  # type: ignore[no-untyped-def]
    """RadarEditor ships with Parabolic + D=0.6 m + eff=0.55 + carrier=9.5 GHz.
    The controller's construction paints the strip immediately, so the
    three labels should already reflect those defaults."""
    editor, _controller = _build(qtbot)
    expected_bw = parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=9.5e9)
    expected_gain = parabolic_peak_gain_dbi(diameter_m=0.6, frequency_hz=9.5e9, efficiency=0.55)
    assert f"{expected_bw:.2f}" in editor.beamwidth_az_label().text()
    assert f"{expected_bw:.2f}" in editor.beamwidth_el_label().text()
    assert f"{expected_gain:.1f}" in editor.peak_gain_label().text()


def test_carrier_change_triggers_refresh(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    editor.carrier_edit().setText("3.0e9")  # S-band
    assert controller.refresh_computed_values() is True
    expected_bw = parabolic_beamwidth_3db_deg(diameter_m=0.6, frequency_hz=3.0e9)
    assert f"{expected_bw:.2f}" in editor.beamwidth_az_label().text()


def test_diameter_change_triggers_refresh(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    parabolic = editor.antenna_form(AntennaType.PARABOLIC)
    parabolic.diameter.setText("1.2")  # type: ignore[attr-defined]
    assert controller.refresh_computed_values() is True
    expected_bw = parabolic_beamwidth_3db_deg(diameter_m=1.2, frequency_hz=9.5e9)
    assert f"{expected_bw:.2f}" in editor.beamwidth_az_label().text()


def test_efficiency_zero_rejects(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Aperture efficiency of 0 is invalid - controller leaves labels alone."""
    editor, controller = _build(qtbot)
    pre_az = editor.beamwidth_az_label().text()
    parabolic = editor.antenna_form(AntennaType.PARABOLIC)
    parabolic.efficiency.setText("0")  # type: ignore[attr-defined]
    assert controller.refresh_computed_values() is False
    # Labels are unchanged from the pre-edit paint.
    assert editor.beamwidth_az_label().text() == pre_az


def test_malformed_carrier_rejects(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    editor.carrier_edit().setText("not a number")
    assert controller.refresh_computed_values() is False


def test_switch_to_planar_array_recomputes(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Switching the antenna type radio triggers a recompute using the
    planar-array formula."""
    editor, _controller = _build(qtbot)
    editor.select_antenna_type(AntennaType.PLANAR_ARRAY)
    # Planar defaults: N_az=N_el=16, spacing=0.0158 m, carrier=9.5 GHz.
    wavelength = 299_792_458.0 / 9.5e9
    aperture = 16 * 0.0158
    expected_bw = 0.886 * wavelength / aperture * (180.0 / math.pi)
    assert f"{expected_bw:.2f}" in editor.beamwidth_az_label().text()


def test_planar_array_peak_gain_uses_n_az_times_n_el(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Default planar array (cos element): 10 log10(16*16) + 3 dB = 27.1 dBi."""
    editor, _controller = _build(qtbot)
    editor.select_antenna_type(AntennaType.PLANAR_ARRAY)
    expected_gain = 10.0 * math.log10(16 * 16) + 3.0  # cos bonus
    assert f"{expected_gain:.1f}" in editor.peak_gain_label().text()


def test_planar_array_isotropic_element_drops_3db(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, _controller = _build(qtbot)
    editor.select_antenna_type(AntennaType.PLANAR_ARRAY)
    form = editor.antenna_form(AntennaType.PLANAR_ARRAY)
    form.element_pattern.setCurrentText("isotropic")  # type: ignore[attr-defined]
    expected_gain = 10.0 * math.log10(16 * 16)  # no bonus
    assert f"{expected_gain:.1f}" in editor.peak_gain_label().text()


def test_planar_array_n_az_zero_rejects(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    editor.select_antenna_type(AntennaType.PLANAR_ARRAY)
    form = editor.antenna_form(AntennaType.PLANAR_ARRAY)
    form.n_az.setText("0")  # type: ignore[attr-defined]
    assert controller.refresh_computed_values() is False
