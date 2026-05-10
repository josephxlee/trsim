"""Editor Workspace root widget — placeholder shell (Phase 4.1).

Real Editor activities (Composer / Map / Radar / Targets / Browser) wire
into this in Phase 4.3+. For now we expose a minimal QWidget so that
MainWindow has something concrete to swap into the central stack.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class EditorWorkspace(QWidget):
    """Editor Workspace placeholder — populated by Phase 4.3 ActivitySelector."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorWorkspace")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Editor Workspace")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: 600;")

        hint = QLabel("Phase 4.3 will mount the 5 Activities here.")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")

        layout.addStretch(1)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addStretch(1)
