"""NN Mode Step 1 - Dataset Builder (Phase 4.11, plan/07 § 7.x)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Step1DatasetPanel(QWidget):
    """Pick a Scenario + probe config + output path -> build dataset."""

    build_requested = Signal()
    cancel_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NNStep1DatasetPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._build_inputs_block())
        layout.addWidget(self._build_progress_block(), 1)
        layout.addWidget(self._build_action_row())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_inputs_block(self) -> QGroupBox:
        box = QGroupBox("Step 1 - Dataset Builder", self)
        box.setObjectName("NNStep1Inputs")
        form = QFormLayout(box)
        self._scenario_combo = QComboBox(box)
        self._scenario_combo.setObjectName("NNStep1Scenario")
        self._scenario_combo.addItem("(none)")
        self._probe_combo = QComboBox(box)
        self._probe_combo.setObjectName("NNStep1Probe")
        self._probe_combo.addItems(["Pairing", "Tracker", "Detector"])
        self._frames_edit = QLineEdit("200", box)
        self._frames_edit.setObjectName("NNStep1Frames")
        self._output_edit = QLineEdit("./datasets/dataset_v1.h5", box)
        self._output_edit.setObjectName("NNStep1OutputPath")
        form.addRow("Scenario", self._scenario_combo)
        form.addRow("Probe stage", self._probe_combo)
        form.addRow("Frames", self._frames_edit)
        form.addRow("Output path", self._output_edit)
        return box

    def _build_progress_block(self) -> QGroupBox:
        box = QGroupBox("Progress", self)
        box.setObjectName("NNStep1Progress")
        v = QVBoxLayout(box)
        self._status_label = QLabel("Status: idle")
        self._status_label.setObjectName("NNStep1Status")
        self._log = QListWidget(box)
        self._log.setObjectName("NNStep1Log")
        v.addWidget(self._status_label)
        v.addWidget(self._log, 1)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Cancel", "cancel_requested", "NNStep1CancelBtn"),
            ("Build Dataset", "build_requested", "NNStep1BuildBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            btn.clicked.connect(getattr(self, signal_name))
            h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_scenarios(self, names: list[str]) -> None:
        self._scenario_combo.blockSignals(True)
        self._scenario_combo.clear()
        self._scenario_combo.addItem("(none)")
        for n in names:
            self._scenario_combo.addItem(n)
        self._scenario_combo.blockSignals(False)

    def set_status(self, status: str) -> None:
        self._status_label.setText(f"Status: {status}")

    def append_log(self, line: str) -> None:
        self._log.addItem(line)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def scenario_combo(self) -> QComboBox:
        return self._scenario_combo

    def probe_combo(self) -> QComboBox:
        return self._probe_combo

    def frames_edit(self) -> QLineEdit:
        return self._frames_edit

    def output_edit(self) -> QLineEdit:
        return self._output_edit

    def status_label(self) -> QLabel:
        return self._status_label

    def log_list(self) -> QListWidget:
        return self._log
