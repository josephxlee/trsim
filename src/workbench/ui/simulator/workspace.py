"""Simulator Workspace root widget — placeholder shell (Phase 4.1).

Real Simulator panels (FFT / Range-Doppler / Run / Properties / 3D Scene
/ Profiler) wire into this in Phase 4.8+. For now we expose a minimal
QWidget so that MainWindow has something concrete to swap into the
central stack.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class SimulatorWorkspace(QWidget):
    """Simulator Workspace placeholder — populated by Phase 4.8 panels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SimulatorWorkspace")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Simulator Workspace")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        hint = QLabel("Phase 4.8 will mount Run / FFT / Range-Doppler / 3D Scene panels.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)
