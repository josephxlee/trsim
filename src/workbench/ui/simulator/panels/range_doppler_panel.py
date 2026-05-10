"""Range-Doppler heatmap panel (Phase 4.9, plan/05 § 5.3)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class RangeDopplerPanel(QWidget):
    """2D Range-Doppler heatmap shell (canvas in Phase 4.9.x)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RangeDopplerPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Range-Doppler")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("RangeDopplerFrameLabel")
        header.addWidget(self._frame_label)
        layout.addLayout(header)

        canvas = QFrame(self)
        canvas.setObjectName("RangeDopplerCanvas")
        canvas.setFrameShape(QFrame.Shape.StyledPanel)
        canvas.setMinimumHeight(160)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("RD canvas (Phase 4.9.x mounts pyqtgraph ImageView)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        cl.addWidget(hint)
        layout.addWidget(canvas, 1)

    def set_frame(self, frame_index: int) -> None:
        self._frame_label.setText(f"frame: {frame_index}")

    def frame_label(self) -> QLabel:
        return self._frame_label
