"""Training Panel widget (task 3, plan/07 § 7.5.3).

Qt widget that lets the user configure a :class:`TrainingJob`, hit
"Run Training", and watch the per-epoch progress. The actual
training loop lives in :class:`workbench.app.nn.TrainerService` —
this widget is glue between its inputs / progress callback and the
user.

Layout:

::

    ┌─ Training ─────────────────────────────┐
    │ Job ID     [______________]             │
    │ Dataset    [______________]             │
    │ Weights    [______________]             │
    │ Epochs     [__]  LR  [_____]            │
    │ Framework  [dropdown]                   │
    │                                         │
    │ Status: idle                            │
    │ Epoch: 0 / 0                            │
    │ Train loss: --   Val loss: --           │
    │ Best val:   --   Best epoch: --         │
    │ [Log list]                              │
    │                                         │
    │ [Run Training] [Stop]                   │
    └─────────────────────────────────────────┘

Signals:

- ``train_requested`` — fired when Run Training is clicked.
- ``stop_requested`` — fired when Stop is clicked. The TrainerService
  MVP does not yet support cancellation; the controller logs the
  click and leaves the training to finish.
"""

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

_FRAMEWORKS: tuple[str, ...] = ("numpy_only", "tensorflow", "pytorch")

# TrainerService backend identifiers (must match the Literal in
# :data:`workbench.app.nn.TrainingBackend`).
_BACKENDS: tuple[tuple[str, str], ...] = (
    ("numpy_mlp", "numpy_mlp (real SGD)"),
    ("numpy_mlp_adam", "numpy_mlp_adam (bias-corrected Adam)"),
    ("fake", "fake (deterministic decay — smoke only)"),
)


class TrainingPanel(QWidget):
    """Job config form + epoch progress readout for the Trainer."""

    train_requested = Signal()
    stop_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("NNTrainingPanel")
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
        box = QGroupBox("Training Job", self)
        box.setObjectName("NNTrainingInputs")
        form = QFormLayout(box)

        self._job_id_edit = QLineEdit("pairing_v1", box)
        self._job_id_edit.setObjectName("NNTrainingJobId")
        self._dataset_edit = QLineEdit("./datasets/pairing_variant_A.h5", box)
        self._dataset_edit.setObjectName("NNTrainingDataset")
        self._weights_edit = QLineEdit("./plugins/pairing/weights/v1.npz", box)
        self._weights_edit.setObjectName("NNTrainingWeights")
        self._epochs_edit = QLineEdit("10", box)
        self._epochs_edit.setObjectName("NNTrainingEpochs")
        self._lr_edit = QLineEdit("1e-3", box)
        self._lr_edit.setObjectName("NNTrainingLR")
        self._framework_combo = QComboBox(box)
        self._framework_combo.setObjectName("NNTrainingFramework")
        for fw in _FRAMEWORKS:
            self._framework_combo.addItem(fw)
        # numpy_mlp = real gradient descent (task C). fake = deterministic
        # decay (Phase 6.7 smoke). Default is numpy_mlp so the panel
        # produces a learning curve out of the box. Stored data is the
        # backend literal; the user-visible text is a longer human label.
        self._backend_combo = QComboBox(box)
        self._backend_combo.setObjectName("NNTrainingBackend")
        for backend_id, label in _BACKENDS:
            self._backend_combo.addItem(label, backend_id)

        form.addRow("Job ID", self._job_id_edit)
        form.addRow("Dataset", self._dataset_edit)
        form.addRow("Weights output", self._weights_edit)
        form.addRow("Epochs", self._epochs_edit)
        form.addRow("Learning rate", self._lr_edit)
        form.addRow("Framework", self._framework_combo)
        form.addRow("Backend", self._backend_combo)
        return box

    def _build_progress_block(self) -> QGroupBox:
        box = QGroupBox("Progress", self)
        box.setObjectName("NNTrainingProgress")
        v = QVBoxLayout(box)

        self._status_label = QLabel("Status: idle", box)
        self._status_label.setObjectName("NNTrainingStatus")
        self._epoch_label = QLabel("Epoch: 0 / 0", box)
        self._epoch_label.setObjectName("NNTrainingEpoch")
        self._loss_label = QLabel("Train loss: --   Val loss: --", box)
        self._loss_label.setObjectName("NNTrainingLoss")
        self._best_label = QLabel("Best val: --   Best epoch: --", box)
        self._best_label.setObjectName("NNTrainingBest")
        self._log = QListWidget(box)
        self._log.setObjectName("NNTrainingLog")

        v.addWidget(self._status_label)
        v.addWidget(self._epoch_label)
        v.addWidget(self._loss_label)
        v.addWidget(self._best_label)
        v.addWidget(self._log, 1)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Stop", "stop_requested", "NNTrainingStopBtn"),
            ("Run Training", "train_requested", "NNTrainingRunBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            btn.clicked.connect(getattr(self, signal_name))
            h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_status(self, status: str) -> None:
        self._status_label.setText(f"Status: {status}")

    def set_epoch(self, current: int, total: int) -> None:
        self._epoch_label.setText(f"Epoch: {current} / {total}")

    def set_loss(self, train_loss: float, val_loss: float) -> None:
        self._loss_label.setText(f"Train loss: {train_loss:.4f}   Val loss: {val_loss:.4f}")

    def set_best(self, best_val: float, best_epoch: int) -> None:
        self._best_label.setText(f"Best val: {best_val:.4f}   Best epoch: {best_epoch}")

    def append_log(self, line: str) -> None:
        self._log.addItem(line)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def job_id_edit(self) -> QLineEdit:
        return self._job_id_edit

    def dataset_edit(self) -> QLineEdit:
        return self._dataset_edit

    def weights_edit(self) -> QLineEdit:
        return self._weights_edit

    def epochs_edit(self) -> QLineEdit:
        return self._epochs_edit

    def lr_edit(self) -> QLineEdit:
        return self._lr_edit

    def framework_combo(self) -> QComboBox:
        return self._framework_combo

    def backend_combo(self) -> QComboBox:
        return self._backend_combo

    def current_backend(self) -> str:
        """Return the currently selected :data:`TrainingBackend` literal."""
        data = self._backend_combo.currentData()
        return str(data) if isinstance(data, str) else _BACKENDS[0][0]

    def set_backend(self, backend_id: str) -> None:
        """Programmatic mirror of selecting a backend in the combo."""
        for idx, (bid, _label) in enumerate(_BACKENDS):
            if bid == backend_id:
                self._backend_combo.setCurrentIndex(idx)
                return
        msg = f"unknown backend {backend_id!r}; expected one of {[b for b, _ in _BACKENDS]}"
        raise ValueError(msg)

    def status_label(self) -> QLabel:
        return self._status_label

    def epoch_label(self) -> QLabel:
        return self._epoch_label

    def loss_label(self) -> QLabel:
        return self._loss_label

    def best_label(self) -> QLabel:
        return self._best_label

    def log_list(self) -> QListWidget:
        return self._log
