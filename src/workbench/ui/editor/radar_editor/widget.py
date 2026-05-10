"""RadarEditor widget (Phase 4.7, plan/05 § 5.3.9)."""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


class AntennaType(StrEnum):
    """Antenna geometry families (plan/03 § 3.2.1h)."""

    PARABOLIC = "parabolic"
    PLANAR_ARRAY = "planar_array"


class RXChannelMode(StrEnum):
    """RX channel configurations (plan/08 § 8.5a.6)."""

    SINGLE_SUM = "single_sum"
    MONOPULSE_4CH = "monopulse_4ch"


_ANTENNA_LABEL: dict[AntennaType, str] = {
    AntennaType.PARABOLIC: "Parabolic",
    AntennaType.PLANAR_ARRAY: "Planar Array",
}

_RX_LABEL: dict[RXChannelMode, str] = {
    RXChannelMode.SINGLE_SUM: "Single SUM",
    RXChannelMode.MONOPULSE_4CH: "Monopulse 4-channel",
}


class _ParabolicForm(QWidget):
    """Parabolic-dish-specific fields."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AntennaForm_Parabolic")
        form = QFormLayout(self)
        self.diameter = QLineEdit("0.6")
        self.diameter.setObjectName("AntennaParabolicDiameter")
        self.efficiency = QLineEdit("0.55")
        self.efficiency.setObjectName("AntennaParabolicEfficiency")
        form.addRow("Diameter (m)", self.diameter)
        form.addRow("Aperture efficiency", self.efficiency)


class _PlanarArrayForm(QWidget):
    """Planar-array-specific fields."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AntennaForm_PlanarArray")
        form = QFormLayout(self)
        self.n_az = QLineEdit("16")
        self.n_az.setObjectName("AntennaPlanarNAz")
        self.n_el = QLineEdit("16")
        self.n_el.setObjectName("AntennaPlanarNEl")
        self.spacing = QLineEdit("0.0158")
        self.spacing.setObjectName("AntennaPlanarSpacing")
        self.element_pattern = QComboBox(self)
        self.element_pattern.setObjectName("AntennaPlanarElementPattern")
        self.element_pattern.addItems(["cos", "isotropic"])
        self.weighting = QComboBox(self)
        self.weighting.setObjectName("AntennaPlanarWeighting")
        self.weighting.addItems(["uniform", "taylor", "hamming"])
        form.addRow("N elements (Az)", self.n_az)
        form.addRow("N elements (El)", self.n_el)
        form.addRow("Spacing (m)", self.spacing)
        form.addRow("Element pattern", self.element_pattern)
        form.addRow("Weighting", self.weighting)


class _BeamPatternPreview(QFrame):
    """Tiny placeholder for the beam-pattern plot (Phase 4.7.x)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("BeamPatternPreview")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(120)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Beam Pattern Preview (Phase 4.7.x mounts the polar plot)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        layout.addWidget(hint)


class RadarEditor(QWidget):
    """Editor Activity 3 - integrated radar form with dynamic antenna block."""

    antenna_type_changed = Signal(AntennaType)
    rx_mode_changed = Signal(RXChannelMode)
    save_requested = Signal()
    save_as_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadarEditor")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_radar_model_block())
        layout.addWidget(self._build_antenna_block(), 1)
        layout.addWidget(self._build_rx_block())
        layout.addWidget(self._build_action_row())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_header(self) -> QWidget:
        wrap = QWidget(self)
        wrap.setObjectName("RadarEditorHeader")
        form = QFormLayout(wrap)
        form.setContentsMargins(0, 0, 0, 0)
        self._name_edit = QLineEdit("(unnamed)")
        self._name_edit.setObjectName("RadarEditorName")
        form.addRow("Name", self._name_edit)
        return wrap

    def _build_radar_model_block(self) -> QGroupBox:
        box = QGroupBox("Radar Model", self)
        box.setObjectName("RadarEditorModel")
        form = QFormLayout(box)
        self._carrier = QLineEdit("9.5e9")
        self._carrier.setObjectName("RadarCarrier")
        self._bandwidth = QLineEdit("150e6")
        self._bandwidth.setObjectName("RadarBandwidth")
        self._sweep = QLineEdit("1.0e-3")
        self._sweep.setObjectName("RadarSweep")
        self._power = QLineEdit("1e3")
        self._power.setObjectName("RadarPower")
        form.addRow("Carrier (Hz)", self._carrier)
        form.addRow("Bandwidth (Hz)", self._bandwidth)
        form.addRow("Sweep (s)", self._sweep)
        form.addRow("Tx Power (W)", self._power)
        return box

    def _build_antenna_block(self) -> QGroupBox:
        box = QGroupBox("Antenna", self)
        box.setObjectName("RadarEditorAntenna")
        v = QVBoxLayout(box)

        type_row = QHBoxLayout()
        type_row.addWidget(QLabel("Type:"))
        self._antenna_group = QButtonGroup(self)
        self._antenna_group.setExclusive(True)
        self._antenna_radios: dict[AntennaType, QRadioButton] = {}
        for atype in AntennaType:
            rb = QRadioButton(_ANTENNA_LABEL[atype], box)
            rb.setObjectName(f"AntennaType_{atype.value}")
            self._antenna_group.addButton(rb)
            type_row.addWidget(rb)
            self._antenna_radios[atype] = rb
        type_row.addStretch(1)
        v.addLayout(type_row)

        self._antenna_stack = QStackedWidget(box)
        self._antenna_stack.setObjectName("AntennaFormStack")
        self._antenna_forms: dict[AntennaType, QWidget] = {
            AntennaType.PARABOLIC: _ParabolicForm(self),
            AntennaType.PLANAR_ARRAY: _PlanarArrayForm(self),
        }
        for atype in AntennaType:
            self._antenna_stack.addWidget(self._antenna_forms[atype])
        v.addWidget(self._antenna_stack)

        # Computed values strip.
        computed = QHBoxLayout()
        self._beamwidth_az = QLabel("Az BW: --")
        self._beamwidth_az.setObjectName("AntennaComputedBwAz")
        self._beamwidth_el = QLabel("El BW: --")
        self._beamwidth_el.setObjectName("AntennaComputedBwEl")
        self._peak_gain = QLabel("Peak gain: -- dBi")
        self._peak_gain.setObjectName("AntennaComputedGain")
        for w in (self._beamwidth_az, self._beamwidth_el, self._peak_gain):
            w.setStyleSheet("color: #555;")
            computed.addWidget(w)
        computed.addStretch(1)
        v.addLayout(computed)

        v.addWidget(_BeamPatternPreview(self))

        for atype, rb in self._antenna_radios.items():
            rb.toggled.connect(lambda checked, a=atype: self._on_antenna_toggled(a, checked))
        self._select_default_antenna()
        return box

    def _build_rx_block(self) -> QGroupBox:
        box = QGroupBox("RX Channels", self)
        box.setObjectName("RadarEditorRX")
        h = QHBoxLayout(box)
        h.addWidget(QLabel("Mode:"))
        self._rx_group = QButtonGroup(self)
        self._rx_group.setExclusive(True)
        self._rx_radios: dict[RXChannelMode, QRadioButton] = {}
        for mode in RXChannelMode:
            rb = QRadioButton(_RX_LABEL[mode], box)
            rb.setObjectName(f"RXMode_{mode.value}")
            self._rx_group.addButton(rb)
            h.addWidget(rb)
            self._rx_radios[mode] = rb
        h.addStretch(1)
        for mode, rb in self._rx_radios.items():
            rb.toggled.connect(lambda checked, m=mode: self._on_rx_toggled(m, checked))
        self._select_default_rx_mode()
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        row.setObjectName("RadarEditorActionRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        save_btn = QPushButton("Save", row)
        save_btn.setObjectName("RadarEditorSaveBtn")
        save_btn.clicked.connect(self.save_requested)
        save_as_btn = QPushButton("Save As New...", row)
        save_as_btn.setObjectName("RadarEditorSaveAsBtn")
        save_as_btn.clicked.connect(self.save_as_requested)
        h.addWidget(save_btn)
        h.addWidget(save_as_btn)
        return row

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _select_default_antenna(self) -> None:
        rb = self._antenna_radios[AntennaType.PARABOLIC]
        rb.blockSignals(True)
        rb.setChecked(True)
        rb.blockSignals(False)
        self._current_antenna = AntennaType.PARABOLIC
        self._antenna_stack.setCurrentWidget(self._antenna_forms[AntennaType.PARABOLIC])

    def _select_default_rx_mode(self) -> None:
        rb = self._rx_radios[RXChannelMode.MONOPULSE_4CH]
        rb.blockSignals(True)
        rb.setChecked(True)
        rb.blockSignals(False)
        self._current_rx_mode = RXChannelMode.MONOPULSE_4CH

    def _on_antenna_toggled(self, atype: AntennaType, checked: bool) -> None:
        if not checked:
            return
        self._current_antenna = atype
        self._antenna_stack.setCurrentWidget(self._antenna_forms[atype])
        self.antenna_type_changed.emit(atype)

    def _on_rx_toggled(self, mode: RXChannelMode, checked: bool) -> None:
        if not checked:
            return
        self._current_rx_mode = mode
        self.rx_mode_changed.emit(mode)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def select_antenna_type(self, atype: AntennaType) -> None:
        rb = self._antenna_radios[atype]
        if not rb.isChecked():
            rb.setChecked(True)

    def select_rx_mode(self, mode: RXChannelMode) -> None:
        rb = self._rx_radios[mode]
        if not rb.isChecked():
            rb.setChecked(True)

    def current_antenna_type(self) -> AntennaType:
        return self._current_antenna

    def current_rx_mode(self) -> RXChannelMode:
        return self._current_rx_mode

    def set_computed_values(
        self,
        beamwidth_az_deg: float,
        beamwidth_el_deg: float,
        peak_gain_dbi: float,
    ) -> None:
        """Update the read-only computed-values strip."""
        self._beamwidth_az.setText(f"Az BW: {beamwidth_az_deg:.2f} deg")
        self._beamwidth_el.setText(f"El BW: {beamwidth_el_deg:.2f} deg")
        self._peak_gain.setText(f"Peak gain: {peak_gain_dbi:.1f} dBi")

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def antenna_radio(self, atype: AntennaType) -> QRadioButton:
        return self._antenna_radios[atype]

    def rx_radio(self, mode: RXChannelMode) -> QRadioButton:
        return self._rx_radios[mode]

    def antenna_form(self, atype: AntennaType) -> QWidget:
        return self._antenna_forms[atype]

    def antenna_stack(self) -> QStackedWidget:
        return self._antenna_stack

    def computed_labels(self) -> tuple[QLabel, QLabel, QLabel]:
        return self._beamwidth_az, self._beamwidth_el, self._peak_gain
