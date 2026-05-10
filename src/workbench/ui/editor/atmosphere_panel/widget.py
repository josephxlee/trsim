"""AtmospherePanel widget (Phase 4.8, plan/15 § 15.4.3)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

# plan/15 § 15.4.3 sky-condition vocabulary.
SKY_CONDITIONS: tuple[str, ...] = ("Clear", "Cloudy", "Fog", "Rain")


@dataclass(frozen=True, slots=True)
class AtmosphereState:
    """Snapshot of the panel's current values.

    Phase 5+ ScenarioService will accept this dataclass directly when
    saving / loading. Floats are kept as raw text-parsed values; the
    panel does not enforce ranges - validation is the App layer's job.
    """

    sky_condition: str
    visibility_km: float
    rain_rate_mm_per_h: float
    temperature_c: float
    pressure_hpa: float


class AtmospherePanel(QWidget):
    """Sky condition + visibility + rain rate + ISA inputs."""

    state_changed = Signal(AtmosphereState)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("AtmospherePanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._build_form_block())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_form_block(self) -> QGroupBox:
        box = QGroupBox("Atmosphere", self)
        box.setObjectName("AtmospherePanelForm")
        form = QFormLayout(box)
        self._sky = QComboBox(box)
        self._sky.setObjectName("AtmosphereSky")
        self._sky.addItems(SKY_CONDITIONS)
        self._visibility = QLineEdit("20.0", box)
        self._visibility.setObjectName("AtmosphereVisibility")
        self._rain_rate = QLineEdit("0.0", box)
        self._rain_rate.setObjectName("AtmosphereRainRate")
        self._temperature = QLineEdit("15.0", box)
        self._temperature.setObjectName("AtmosphereTemperature")
        self._pressure = QLineEdit("1013.25", box)
        self._pressure.setObjectName("AtmospherePressure")

        form.addRow("Sky condition", self._sky)
        form.addRow("Visibility (km)", self._visibility)
        form.addRow("Rain rate (mm/h)", self._rain_rate)
        form.addRow("Temperature (C)", self._temperature)
        form.addRow("Pressure (hPa)", self._pressure)

        for w in (self._visibility, self._rain_rate, self._temperature, self._pressure):
            w.editingFinished.connect(self._emit_state)
        self._sky.currentTextChanged.connect(lambda _: self._emit_state())
        return box

    # ------------------------------------------------------------------
    # State serialization
    # ------------------------------------------------------------------
    def _emit_state(self) -> None:
        try:
            state = self.current_state()
        except ValueError:
            # User typed garbage; quietly skip until they fix it.
            return
        self.state_changed.emit(state)

    def current_state(self) -> AtmosphereState:
        """Parse the current widget values into an :class:`AtmosphereState`.

        Raises:
            ValueError: If any numeric field is not a valid float.
        """
        try:
            return AtmosphereState(
                sky_condition=self._sky.currentText(),
                visibility_km=float(self._visibility.text()),
                rain_rate_mm_per_h=float(self._rain_rate.text()),
                temperature_c=float(self._temperature.text()),
                pressure_hpa=float(self._pressure.text()),
            )
        except ValueError as exc:
            msg = f"atmosphere field parse error: {exc}"
            raise ValueError(msg) from exc

    def set_state(self, state: AtmosphereState) -> None:
        """Programmatic setter; does not re-emit state_changed."""
        for w in (
            self._sky,
            self._visibility,
            self._rain_rate,
            self._temperature,
            self._pressure,
        ):
            w.blockSignals(True)
        self._sky.setCurrentText(state.sky_condition)
        self._visibility.setText(f"{state.visibility_km}")
        self._rain_rate.setText(f"{state.rain_rate_mm_per_h}")
        self._temperature.setText(f"{state.temperature_c}")
        self._pressure.setText(f"{state.pressure_hpa}")
        for w in (
            self._sky,
            self._visibility,
            self._rain_rate,
            self._temperature,
            self._pressure,
        ):
            w.blockSignals(False)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def sky_combo(self) -> QComboBox:
        return self._sky

    def visibility_edit(self) -> QLineEdit:
        return self._visibility

    def rain_rate_edit(self) -> QLineEdit:
        return self._rain_rate

    def temperature_edit(self) -> QLineEdit:
        return self._temperature

    def pressure_edit(self) -> QLineEdit:
        return self._pressure
