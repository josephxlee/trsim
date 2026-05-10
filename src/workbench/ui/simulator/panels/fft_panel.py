"""FFT spectrum panel (Phase 4.9, plan/05 § 5.3.4)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget


class FFTPanel(QWidget):
    """Up/down sweep FFT spectra readout (canvas mounts in Phase 4.9.x)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FFTPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header strip with frame number + peak count.
        header = QHBoxLayout()
        title = QLabel("FFT Spectrum")
        title.setObjectName("FFTPanelTitle")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("FFTPanelFrameLabel")
        self._peaks_label = QLabel("peaks: 0 up / 0 down")
        self._peaks_label.setObjectName("FFTPanelPeaksLabel")
        header.addWidget(self._frame_label)
        header.addSpacing(12)
        header.addWidget(self._peaks_label)
        layout.addLayout(header)

        # Plot canvas placeholder.
        canvas = QFrame(self)
        canvas.setObjectName("FFTPanelCanvas")
        canvas.setFrameShape(QFrame.Shape.StyledPanel)
        canvas.setMinimumHeight(160)
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("FFT canvas (Phase 4.9.x mounts pyqtgraph plot)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        canvas_layout.addWidget(hint)
        layout.addWidget(canvas, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_frame(self, frame_index: int) -> None:
        self._frame_label.setText(f"frame: {frame_index}")

    def set_peak_counts(self, up: int, down: int) -> None:
        self._peaks_label.setText(f"peaks: {up} up / {down} down")

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def frame_label(self) -> QLabel:
        return self._frame_label

    def peaks_label(self) -> QLabel:
        return self._peaks_label
