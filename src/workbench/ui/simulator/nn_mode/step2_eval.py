"""NN Mode Step 2 - Evaluation + 4-error diagnostic (Phase 4.11)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

# plan/07 - the four diagnostic axes for NN tracker evaluation.
ERROR_CATEGORIES: tuple[str, ...] = (
    "Pairing",
    "Tracker",
    "Predictor",
    "Classifier",
)


class Step2EvalPanel(QWidget):
    """Pick dataset + NN plugin -> run inference + inspect 4-error table."""

    run_eval_requested = Signal()
    export_report_requested = Signal()
    # Manual re-scan trigger for the dataset combo. The auto-refresh
    # path is Step 1's ``build_completed`` signal; this button covers
    # the case where the user dropped a file in ``./datasets/``
    # outside the GUI.
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NNStep2EvalPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        layout.addWidget(self._build_inputs_block())
        layout.addWidget(self._build_table_block(), 1)
        layout.addWidget(self._build_action_row())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_inputs_block(self) -> QGroupBox:
        box = QGroupBox("Step 2 - Evaluation Inputs", self)
        box.setObjectName("NNStep2Inputs")
        form = QFormLayout(box)
        self._dataset_combo = QComboBox(box)
        self._dataset_combo.setObjectName("NNStep2Dataset")
        self._dataset_combo.addItem("(none)")
        self._plugin_combo = QComboBox(box)
        self._plugin_combo.setObjectName("NNStep2Plugin")
        self._plugin_combo.addItem("(none)")
        form.addRow("Dataset", self._dataset_combo)
        form.addRow("NN Plugin", self._plugin_combo)
        return box

    def _build_table_block(self) -> QGroupBox:
        box = QGroupBox("4-Error Diagnostic", self)
        box.setObjectName("NNStep2ErrorTable")
        v = QVBoxLayout(box)
        self._table = QTableWidget(len(ERROR_CATEGORIES), 3, box)
        self._table.setObjectName("NNStep2ErrorTableWidget")
        self._table.setHorizontalHeaderLabels(["Category", "RMSE", "Bias"])
        for i, cat in enumerate(ERROR_CATEGORIES):
            self._table.setItem(i, 0, QTableWidgetItem(cat))
            self._table.setItem(i, 1, QTableWidgetItem("--"))
            self._table.setItem(i, 2, QTableWidgetItem("--"))
        self._table.verticalHeader().setVisible(False)
        v.addWidget(self._table)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Refresh datasets", "refresh_requested", "NNStep2RefreshBtn"),
            ("Run Evaluation", "run_eval_requested", "NNStep2RunBtn"),
            ("Export Report...", "export_report_requested", "NNStep2ExportBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            btn.clicked.connect(getattr(self, signal_name))
            h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_datasets(self, names: list[str]) -> None:
        self._populate_combo(self._dataset_combo, names)

    def set_plugins(self, names: list[str]) -> None:
        self._populate_combo(self._plugin_combo, names)

    def set_error_metrics(self, category: str, rmse: float, bias: float) -> None:
        if category not in ERROR_CATEGORIES:
            msg = f"unknown error category {category!r}; expected one of {ERROR_CATEGORIES}"
            raise ValueError(msg)
        idx = ERROR_CATEGORIES.index(category)
        self._table.setItem(idx, 1, QTableWidgetItem(f"{rmse:.3f}"))
        self._table.setItem(idx, 2, QTableWidgetItem(f"{bias:+.3f}"))

    @staticmethod
    def _populate_combo(combo: QComboBox, names: list[str]) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(none)")
        for n in names:
            combo.addItem(n)
        combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def dataset_combo(self) -> QComboBox:
        return self._dataset_combo

    def plugin_combo(self) -> QComboBox:
        return self._plugin_combo

    def error_table(self) -> QTableWidget:
        return self._table
