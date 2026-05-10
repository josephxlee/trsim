"""Radar POV (Scope) panel (Phase 4.10, plan/05 § 5.3.2 (b))."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class ScopePOVPanel(QWidget):
    """Boresight POV (cross-hair, beam circles) shell."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScopePOVPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Radar POV (Scope)")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._az_label = QLabel("AZ actual / cmd / lag: -- / -- / --")
        self._az_label.setObjectName("ScopePOVAzLabel")
        header.addWidget(self._az_label)
        layout.addLayout(header)

        canvas = QFrame(self)
        canvas.setObjectName("ScopePOVCanvas")
        canvas.setFrameShape(QFrame.Shape.StyledPanel)
        canvas.setMinimumSize(240, 240)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Scope canvas (Phase 4.10.x mounts the cross-hair + beam circles renderer)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        cl.addWidget(hint)
        layout.addWidget(canvas, 1)

    def set_pointing(
        self,
        actual_az_deg: float,
        commanded_az_deg: float,
    ) -> None:
        lag = actual_az_deg - commanded_az_deg
        self._az_label.setText(
            f"AZ actual / cmd / lag: {actual_az_deg:.2f} / {commanded_az_deg:.2f} / {lag:+.2f}"
        )

    def az_label(self) -> QLabel:
        return self._az_label
