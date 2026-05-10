"""Stage I/O panel (Phase 4.9, plan/05 § 5.3.6c)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PIPELINE_STAGE_BOXES: tuple[str, ...] = (
    "Transmitter",
    "Environment",
    "Receiver",
    "Detector",
    "Pairing",
    "Tracker",
)


class _StageIOBox(QGroupBox):
    """One IN/OUT inspector for a pipeline stage."""

    def __init__(self, stage: str, parent: QWidget | None = None) -> None:
        super().__init__(stage, parent)
        self.setObjectName(f"StageIOBox_{stage}")
        layout = QVBoxLayout(self)
        layout.setSpacing(2)
        self._in_label = QLabel("IN: -")
        self._in_label.setObjectName(f"StageIOBox_{stage}_In")
        self._out_label = QLabel("OUT: -")
        self._out_label.setObjectName(f"StageIOBox_{stage}_Out")
        layout.addWidget(self._in_label)
        layout.addWidget(self._out_label)

    def set_io(self, in_text: str, out_text: str) -> None:
        self._in_label.setText(f"IN: {in_text}")
        self._out_label.setText(f"OUT: {out_text}")

    def in_label(self) -> QLabel:
        return self._in_label

    def out_label(self) -> QLabel:
        return self._out_label


class StageIOPanel(QWidget):
    """Per-stage IN/OUT inspector + record toggle + export button."""

    record_toggled = Signal(bool)
    export_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("StageIOPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Stage I/O")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("StageIOFrameLabel")
        header.addWidget(self._frame_label)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setSpacing(6)
        self._boxes: dict[str, _StageIOBox] = {}
        for idx, stage in enumerate(PIPELINE_STAGE_BOXES):
            box = _StageIOBox(stage, self)
            self._boxes[stage] = box
            row, col = divmod(idx, 3)
            grid.addWidget(box, row, col)
        layout.addLayout(grid)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        self._record_btn = QPushButton("Record: OFF", self)
        self._record_btn.setObjectName("StageIORecordBtn")
        self._record_btn.setCheckable(True)
        self._record_btn.toggled.connect(self._on_record_toggled)
        export_btn = QPushButton("Export...", self)
        export_btn.setObjectName("StageIOExportBtn")
        export_btn.clicked.connect(self.export_requested)
        action_row.addWidget(self._record_btn)
        action_row.addWidget(export_btn)
        layout.addLayout(action_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_frame(self, frame_index: int) -> None:
        self._frame_label.setText(f"frame: {frame_index}")

    def set_stage_io(self, stage: str, in_text: str, out_text: str) -> None:
        if stage not in self._boxes:
            msg = f"unknown stage {stage!r}; expected one of {PIPELINE_STAGE_BOXES}"
            raise ValueError(msg)
        self._boxes[stage].set_io(in_text, out_text)

    def stage_box(self, stage: str) -> _StageIOBox:
        return self._boxes[stage]

    def record_button(self) -> QPushButton:
        return self._record_btn

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _on_record_toggled(self, checked: bool) -> None:
        self._record_btn.setText("Record: ON" if checked else "Record: OFF")
        self.record_toggled.emit(checked)
