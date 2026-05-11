"""NN Mode Step 1 - Dataset Builder (Phase 4.11 + task B, plan/07 § 7.4.5a).

Task B adds a "Build mode" picker so the panel can drive either:

- ``SINGLE`` — one variant (the default, behaviour from Phase 4.11) +
  the on-disk path is the literal HDF5 file the user typed.
- ``CHAIN_4VARIANT`` — :func:`workbench.app.nn.standard_pairing_build_
  plans` four-tier (A/B/C/D) chain. The on-disk path is treated as
  the output **directory** (or the directory containing the typed
  file); per-variant filenames come from the standard preset.
"""

from __future__ import annotations

from enum import StrEnum

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


class Step1BuildMode(StrEnum):
    """Step 1 build selector — single variant vs. 4-variant chain."""

    SINGLE = "single"
    CHAIN_4VARIANT = "chain_4variant"


_BUILD_MODE_LABELS: dict[Step1BuildMode, str] = {
    Step1BuildMode.SINGLE: "Single variant",
    Step1BuildMode.CHAIN_4VARIANT: "All 4 variants (A/B/C/D)",
}


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
        self._build_mode_combo = QComboBox(box)
        self._build_mode_combo.setObjectName("NNStep1BuildMode")
        for mode in (Step1BuildMode.SINGLE, Step1BuildMode.CHAIN_4VARIANT):
            self._build_mode_combo.addItem(_BUILD_MODE_LABELS[mode], mode.value)
        self._frames_edit = QLineEdit("200", box)
        self._frames_edit.setObjectName("NNStep1Frames")
        self._output_edit = QLineEdit("./datasets/dataset_v1.h5", box)
        self._output_edit.setObjectName("NNStep1OutputPath")
        form.addRow("Scenario", self._scenario_combo)
        form.addRow("Probe stage", self._probe_combo)
        form.addRow("Build mode", self._build_mode_combo)
        form.addRow("Frames (per variant)", self._frames_edit)
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

    def current_build_mode(self) -> Step1BuildMode:
        """Return the currently selected :class:`Step1BuildMode`."""
        data = self._build_mode_combo.currentData()
        if isinstance(data, str):
            return Step1BuildMode(data)
        # Fall back to enum-by-index (covers tests that set combo via
        # ``setCurrentIndex`` without populating userData).
        return list(Step1BuildMode)[self._build_mode_combo.currentIndex()]

    def set_build_mode(self, mode: Step1BuildMode) -> None:
        """Programmatic mirror of selecting a build mode in the combo."""
        idx = list(Step1BuildMode).index(mode)
        self._build_mode_combo.setCurrentIndex(idx)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def scenario_combo(self) -> QComboBox:
        return self._scenario_combo

    def probe_combo(self) -> QComboBox:
        return self._probe_combo

    def build_mode_combo(self) -> QComboBox:
        return self._build_mode_combo

    def frames_edit(self) -> QLineEdit:
        return self._frames_edit

    def output_edit(self) -> QLineEdit:
        return self._output_edit

    def status_label(self) -> QLabel:
        return self._status_label

    def log_list(self) -> QListWidget:
        return self._log
