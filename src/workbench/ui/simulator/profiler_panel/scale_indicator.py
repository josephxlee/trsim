"""ScaleIndicator widget (Phase 4.12, plan/18 § 18.16)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget


class ScaleIndicator(QWidget):
    """Toolbar-friendly readout showing the live simulation scale factor.

    ``scale = wall_clock_dt / sim_dt`` per plan/18 § 18.16. Numbers
    above 1.0 mean the simulator is running faster than wall-clock,
    below 1.0 mean it can't keep up. Colour cues (yellow/red) flag
    degraded performance.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScaleIndicator")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        self._prefix = QLabel("scale:")
        self._prefix.setObjectName("ScaleIndicatorPrefix")
        self._prefix.setStyleSheet("color: #777;")
        self._value = QLabel("--")
        self._value.setObjectName("ScaleIndicatorValue")
        self._value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value.setMinimumWidth(56)
        self._value.setStyleSheet("font-weight: 600;")
        layout.addWidget(self._prefix)
        layout.addWidget(self._value)

    def set_scale(self, scale: float | None) -> None:
        """Update the readout. ``None`` clears it back to ``--``.

        Colour cue:
        - >= 0.9 -> default colour.
        - 0.5..0.9 -> yellow.
        - < 0.5 -> red.
        """
        if scale is None:
            self._value.setText("--")
            self._value.setStyleSheet("font-weight: 600;")
            return
        self._value.setText(f"{scale:.2f}x")
        if scale >= 0.9:
            self._value.setStyleSheet("font-weight: 600;")
        elif scale >= 0.5:
            self._value.setStyleSheet("font-weight: 600; color: #b87000;")
        else:
            self._value.setStyleSheet("font-weight: 600; color: #b00020;")

    def value_label(self) -> QLabel:
        return self._value
