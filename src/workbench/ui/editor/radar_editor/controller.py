"""RadarEditor live computed-values controller.

Phase 4.7 wired the Computed Values strip (Az BW / El BW / Peak gain
labels) but :meth:`RadarEditor.set_computed_values` is never called.
This controller listens to carrier / bandwidth / sweep / power /
antenna parameter edits, recomputes the three values, and pushes them
into the strip.

Parabolic dish uses the closed-form helpers in
:mod:`workbench.physics.antenna`:

- 3-dB beamwidth ``theta = 70 * lambda / D`` (deg) — same value for
  az / el (rotationally symmetric dish).
- Peak gain ``10 log10(eta * (pi * D / lambda)^2)`` (dBi).

Planar array uses the array-factor approximations in
:mod:`workbench.physics.planar_array` (3-dB beamwidth + uniform-
weighting peak gain ``10 log10(N_az * N_el * elem_gain)`` with
``elem_gain = pi`` for ``cos`` and ``1.0`` for ``isotropic``).

Field parse failures are swallowed silently — the controller leaves
the previous computed values in place so the user does not see a
jarring "ERROR" string mid-typing. Validate-style messaging is a
follow-up cycle (mirrors :class:`ScenarioComposerController` shape).
"""

from __future__ import annotations

import math

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QLineEdit

from workbench.physics.antenna import (
    parabolic_beamwidth_3db_deg,
    parabolic_peak_gain_dbi,
)
from workbench.ui.editor.radar_editor.widget import (
    AntennaType,
    RadarEditor,
    _ParabolicForm,
    _PlanarArrayForm,
)

_C_LIGHT_M_S: float = 299_792_458.0


class RadarEditorController(QObject):
    """Recomputes the Computed Values strip on every relevant edit."""

    def __init__(
        self,
        *,
        editor: RadarEditor,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._editor = editor

        # Top-level radar-model fields drive both antenna kinds.
        for line_edit in (
            editor.carrier_edit(),
            editor.bandwidth_edit(),
            editor.sweep_edit(),
            editor.power_edit(),
        ):
            line_edit.editingFinished.connect(self.refresh_computed_values)

        # Antenna-specific fields.
        parabolic = editor.antenna_form(AntennaType.PARABOLIC)
        assert isinstance(parabolic, _ParabolicForm)
        for line_edit in (parabolic.diameter, parabolic.efficiency):
            line_edit.editingFinished.connect(self.refresh_computed_values)
        planar = editor.antenna_form(AntennaType.PLANAR_ARRAY)
        assert isinstance(planar, _PlanarArrayForm)
        for line_edit in (planar.n_az, planar.n_el, planar.spacing):
            line_edit.editingFinished.connect(self.refresh_computed_values)
        planar.element_pattern.currentTextChanged.connect(lambda _: self.refresh_computed_values())

        # Antenna type / Rx mode radio toggles also recompute (different
        # algorithm path).
        editor.antenna_type_changed.connect(lambda _atype: self.refresh_computed_values())

        # Paint once on construction so the strip is not stale.
        self.refresh_computed_values()

    @property
    def editor(self) -> RadarEditor:
        return self._editor

    def refresh_computed_values(self) -> bool:
        """Recompute az BW / el BW / peak gain and push into the strip.

        Returns:
            ``True`` if all inputs parsed and the strip was refreshed,
            ``False`` if any field was malformed (strip unchanged).
        """
        carrier = _parse_positive(self._editor.carrier_edit())
        if carrier is None:
            return False
        atype = self._editor.current_antenna_type()
        if atype is AntennaType.PARABOLIC:
            return self._refresh_parabolic(carrier)
        if atype is AntennaType.PLANAR_ARRAY:
            return self._refresh_planar(carrier)
        return False

    def _refresh_parabolic(self, frequency_hz: float) -> bool:
        form = self._editor.antenna_form(AntennaType.PARABOLIC)
        assert isinstance(form, _ParabolicForm)
        diameter = _parse_positive(form.diameter)
        efficiency = _parse_in_range(form.efficiency, low=0.0, high=1.0)
        if diameter is None or efficiency is None:
            return False
        bw = parabolic_beamwidth_3db_deg(diameter, frequency_hz)
        gain = parabolic_peak_gain_dbi(diameter, frequency_hz, efficiency=efficiency)
        self._editor.set_computed_values(
            beamwidth_az_deg=bw,
            beamwidth_el_deg=bw,
            peak_gain_dbi=gain,
        )
        return True

    def _refresh_planar(self, frequency_hz: float) -> bool:
        form = self._editor.antenna_form(AntennaType.PLANAR_ARRAY)
        assert isinstance(form, _PlanarArrayForm)
        n_az = _parse_int_positive(form.n_az)
        n_el = _parse_int_positive(form.n_el)
        spacing = _parse_positive(form.spacing)
        if n_az is None or n_el is None or spacing is None:
            return False
        wavelength = _C_LIGHT_M_S / frequency_hz
        # 3-dB beamwidth (uniform array) ~ 0.886 * lambda / aperture * 180/pi
        aperture_az = n_az * spacing
        aperture_el = n_el * spacing
        bw_az = 0.886 * wavelength / aperture_az * (180.0 / math.pi)
        bw_el = 0.886 * wavelength / aperture_el * (180.0 / math.pi)
        # Element pattern adjusts peak gain. cos has pi steradian -> ~3 dBi
        # above isotropic when integrated; planar_array.element_power
        # uses cos directly so the array peak factor is N_az * N_el for
        # both kinds in boresight direction. We approximate with a tiny
        # element-pattern bonus for cos vs isotropic.
        element_pattern = form.element_pattern.currentText()
        element_bonus_db = 3.0 if element_pattern == "cos" else 0.0
        gain_lin = float(n_az * n_el)
        gain_dbi = 10.0 * math.log10(gain_lin) + element_bonus_db
        self._editor.set_computed_values(
            beamwidth_az_deg=bw_az,
            beamwidth_el_deg=bw_el,
            peak_gain_dbi=gain_dbi,
        )
        return True


def _parse_positive(edit: QLineEdit) -> float | None:
    try:
        value = float(edit.text().strip())
    except ValueError:
        return None
    if value <= 0.0:
        return None
    return value


def _parse_in_range(edit: QLineEdit, *, low: float, high: float) -> float | None:
    try:
        value = float(edit.text().strip())
    except ValueError:
        return None
    if not (low < value <= high):
        return None
    return value


def _parse_int_positive(edit: QLineEdit) -> int | None:
    try:
        value = int(edit.text().strip())
    except ValueError:
        return None
    if value < 1:
        return None
    return value
