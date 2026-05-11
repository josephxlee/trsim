"""Training Panel controller (task 3, plan/07 § 7.5.3).

Wires :class:`TrainingPanel` signals to a :class:`TrainerService` run.
The MVP TrainerService runs a deterministic fake-loop synchronously,
so this controller blocks the Qt event loop for the duration of the
training. The fake loop is fast (microseconds per epoch) so the
freeze is invisible for the default 10-epoch run; a future real
backend will need to move the loop onto a QThread.
"""

from __future__ import annotations

from pathlib import Path

from workbench.app.nn import TrainerService, TrainingJob, TrainingResult
from workbench.ui.nn_training.training_panel import TrainingPanel


class NNTrainingController:
    """Glue between the Training panel and :class:`TrainerService`.

    Attributes:
        panel: The :class:`TrainingPanel` instance this controller
            drives.
    """

    def __init__(self, panel: TrainingPanel) -> None:
        self.panel = panel
        self._training_in_flight = False
        self.panel.train_requested.connect(self._on_train)
        self.panel.stop_requested.connect(self._on_stop)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_train(self) -> None:
        job = self._build_job_from_panel()
        if job is None:
            return

        self._training_in_flight = True
        self.panel.set_status(f"training: 0 / {job.epochs}")
        self.panel.append_log(f"Training started: {job.job_id}")
        self._best_seen_val = float("inf")
        self._best_seen_epoch = 0

        service = TrainerService(epoch_callback=self._on_epoch)
        try:
            result = service.run(job)
        except (RuntimeError, OSError) as exc:
            self.panel.set_status(f"error: {exc}")
            self.panel.append_log(f"Training failed: {exc}")
            self._training_in_flight = False
            return

        self._training_in_flight = False
        self._render_result(job, result)

    def _on_stop(self) -> None:
        # TrainerService MVP has no mid-run cancellation. Future real
        # backends will expose a stop flag the controller can flip.
        if self._training_in_flight:
            self.panel.append_log("Stop requested (not yet supported — will run to end)")
        else:
            self.panel.append_log("Stop: no training in flight")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_job_from_panel(self) -> TrainingJob | None:
        """Read panel inputs into a :class:`TrainingJob`, or set an
        error status + None on parse / validation failure.
        """
        job_id = self.panel.job_id_edit().text().strip()
        if not job_id:
            self._fail("Job ID is required")
            return None
        dataset_text = self.panel.dataset_edit().text().strip()
        if not dataset_text:
            self._fail("Dataset path is required")
            return None
        weights_text = self.panel.weights_edit().text().strip()
        if not weights_text:
            self._fail("Weights path is required")
            return None

        try:
            epochs = int(self.panel.epochs_edit().text())
        except ValueError:
            self._fail("Epochs must be an integer")
            return None
        try:
            lr = float(self.panel.lr_edit().text())
        except ValueError:
            self._fail("Learning rate must be a number")
            return None

        framework = self.panel.framework_combo().currentText()

        try:
            return TrainingJob(
                job_id=job_id,
                task="pairing",
                dataset_path=Path(dataset_text),
                weights_path=Path(weights_text),
                framework=framework,  # type: ignore[arg-type]
                learning_rate=lr,
                epochs=epochs,
            )
        except ValueError as exc:
            self._fail(str(exc))
            return None

    def _fail(self, message: str) -> None:
        self.panel.set_status(f"error: {message}")
        self.panel.append_log(f"Training aborted: {message}")

    def _on_epoch(self, epoch: int, train_loss: float, val_loss: float) -> None:
        total = self._current_total_epochs()
        self.panel.set_epoch(epoch, total)
        self.panel.set_loss(train_loss, val_loss)
        self.panel.set_status(f"training: {epoch} / {total}")
        if val_loss < self._best_seen_val:
            self._best_seen_val = val_loss
            self._best_seen_epoch = epoch
            self.panel.set_best(val_loss, epoch)

    def _current_total_epochs(self) -> int:
        """Best-effort read of the epochs LineEdit for the progress
        label. Falls back to 0 on parse error (matches the panel
        default before the first epoch).
        """
        try:
            return int(self.panel.epochs_edit().text())
        except ValueError:
            return 0

    def _render_result(self, job: TrainingJob, result: TrainingResult) -> None:
        early = " (early-stopped)" if result.early_stopped else ""
        self.panel.set_status(f"done: {result.completed_epochs}/{job.epochs} epochs{early}")
        self.panel.set_best(result.best_val_loss, result.best_epoch)
        self.panel.append_log(
            f"Training complete: {result.completed_epochs} epochs, "
            f"best val {result.best_val_loss:.4f} @ epoch {result.best_epoch}; "
            f"weights -> {result.weights_path}"
        )
