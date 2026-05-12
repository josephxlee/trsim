"""Auto-generated parameter sliders (PL-9.1c, plan/19 § 19.5.5).

Given an iterable of :class:`PhysicsParam` metadata, build one slider
+ readout row per parameter and emit a single
``parameter_changed(name, value)`` signal whenever any slider moves.

Tick mapping (linear vs. log) follows plan/19 § 19.5.5: the slider is
always integer-valued in ``[0, SLIDER_TICK_RESOLUTION]``; the
controller maps ticks back to the parameter's real-world units.
"""

from __future__ import annotations

import math
from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from workbench.domain.physics_lab import (
    SLIDER_TICK_RESOLUTION,
    PhysicsParam,
)


def _default_for(param: PhysicsParam) -> float:
    if param.default is not None:
        return param.default
    if param.scale == "log":
        # Geometric mid-point keeps the slider knob roughly centred.
        return math.sqrt(param.min_value * param.max_value)
    return 0.5 * (param.min_value + param.max_value)


def _tick_to_value(param: PhysicsParam, tick: int) -> float:
    ratio = max(0, min(SLIDER_TICK_RESOLUTION, tick)) / SLIDER_TICK_RESOLUTION
    if param.scale == "log":
        lo = math.log10(param.min_value)
        hi = math.log10(param.max_value)
        return float(10.0 ** (lo + ratio * (hi - lo)))
    return float(param.min_value + ratio * (param.max_value - param.min_value))


def _value_to_tick(param: PhysicsParam, value: float) -> int:
    clamped = max(param.min_value, min(param.max_value, value))
    if param.scale == "log":
        lo = math.log10(param.min_value)
        hi = math.log10(param.max_value)
        ratio = (math.log10(clamped) - lo) / (hi - lo)
    else:
        span = param.max_value - param.min_value
        ratio = 0.0 if span == 0.0 else (clamped - param.min_value) / span
    return round(ratio * SLIDER_TICK_RESOLUTION)


def _format_value(param: PhysicsParam, value: float) -> str:
    av = abs(value)
    if param.scale == "log" or av >= 1000.0 or (value != 0.0 and av < 0.01):
        text = f"{value:.3g}"
    else:
        text = f"{value:.3f}"
    if param.unit and param.unit != "-":
        return f"{text} {param.unit}"
    return text


class AutoParametersWidget(QWidget):
    """Build one slider + readout row per :class:`PhysicsParam`.

    Signals:
        parameter_changed(str, float): emitted on every slider move.
            First arg is the parameter ``name``; second is the
            real-world value after the linear / log mapping.

    Public API:
        :meth:`current_value(name)` — read the live parameter value.
        :meth:`set_value(name, value)` — programmatic slider move.
        :meth:`slider_for(name)` — fetch the raw :class:`QSlider`.
        :meth:`parameter_names()` — ordered tuple of names.
        :meth:`parameter_spec(name)` — the underlying
            :class:`PhysicsParam` (for tooltips, etc.).
    """

    parameter_changed = Signal(str, float)

    def __init__(
        self,
        params: Iterable[PhysicsParam],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_AutoParametersWidget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Parameters", self)
        title.setStyleSheet("font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        self._params: dict[str, PhysicsParam] = {}
        self._sliders: dict[str, QSlider] = {}
        self._readouts: dict[str, QLabel] = {}

        form = QFormLayout()
        for param in params:
            if param.name in self._params:
                msg = f"AutoParametersWidget: duplicate parameter name {param.name!r}"
                raise ValueError(msg)
            self._params[param.name] = param

            slider = QSlider(Qt.Orientation.Horizontal, self)
            slider.setObjectName(f"PhysicsLab_AutoSlider_{param.name}")
            slider.setRange(0, SLIDER_TICK_RESOLUTION)
            slider.setToolTip(param.description or param.name)

            readout = QLabel("", self)
            readout.setObjectName(f"PhysicsLab_AutoReadout_{param.name}")
            readout.setMinimumWidth(80)

            self._sliders[param.name] = slider
            self._readouts[param.name] = readout

            initial = _default_for(param)
            slider.setValue(_value_to_tick(param, initial))
            readout.setText(_format_value(param, initial))

            # Closure capture the param name so the slot knows which
            # row fired.
            slider.valueChanged.connect(
                lambda tick, name=param.name: self._on_slider_changed(name, tick)
            )

            label_text = param.name
            if param.unit and param.unit != "-":
                label_text = f"{param.name}  ({param.unit})"
            row = QHBoxLayout()
            row.addWidget(slider, 1)
            row.addWidget(readout)
            form.addRow(label_text, row)

        layout.addLayout(form)
        layout.addStretch(1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parameter_names(self) -> tuple[str, ...]:
        return tuple(self._params.keys())

    def parameter_spec(self, name: str) -> PhysicsParam:
        return self._params[name]

    def slider_for(self, name: str) -> QSlider:
        return self._sliders[name]

    def readout_for(self, name: str) -> QLabel:
        return self._readouts[name]

    def current_value(self, name: str) -> float:
        param = self._params[name]
        slider = self._sliders[name]
        return _tick_to_value(param, slider.value())

    def set_value(self, name: str, value: float) -> None:
        param = self._params[name]
        slider = self._sliders[name]
        clamped = max(param.min_value, min(param.max_value, value))
        slider.setValue(_value_to_tick(param, clamped))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_slider_changed(self, name: str, tick: int) -> None:
        param = self._params[name]
        value = _tick_to_value(param, tick)
        self._readouts[name].setText(_format_value(param, value))
        self.parameter_changed.emit(name, value)
