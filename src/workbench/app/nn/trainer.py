"""TrainerService stub for the in-workbench training loop (plan/07 § 7.5).

Phase 6.7 — schema + service surface only. The MVP runs a fake epoch
loop (no real gradient descent) so the wider pipeline can exercise:

- the :class:`TrainingJob` configuration round-trip (matches the
  ``training_job.toml`` schema in plan/07 § 7.5.2);
- the progress-callback contract the UI's Training Panel will hook;
- the weights-path side effect (writes a placeholder ``.npz`` so
  downstream plugin lifecycle can find it).

Real gradient descent lives in :ref:`workbench-train` CLI (plan/07
§ 7.5.4) or layered learners (`workbench.app.nn.learners.*` in a
later sub-step). Both share the same TrainingJob schema and weights
output path so the in-workbench Trainer and the external CLI stay
interchangeable.

References:

- plan/07 § 7.5 — Training Workflow.
- plan/07 § 7.5.2 — training_job.toml schema.
- plan/07 § 7.5.3 — internal TrainerService loop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np

TrainingFramework = Literal["tensorflow", "pytorch", "numpy_only"]
"""Allowed values for ``TrainingJob.framework`` (plan/07 § 7.5.2)."""

EpochCallback = Callable[[int, float, float], None]
"""``callback(epoch, train_loss, val_loss)`` fired after every epoch."""


@dataclass(frozen=True, slots=True)
class TrainingJob:
    """In-memory mirror of ``training_job.toml`` (plan/07 § 7.5.2).

    Attributes:
        job_id: Stable identifier (``"angle_estimator_v2"``).
        task: SampleSpec task tag (``"pairing"``,
            ``"angle_estimation"``, ...).
        dataset_path: HDF5 path with the training samples.
        train_fraction: Fraction of samples used for training. The
            remainder is split between val / test according to
            ``val_fraction``.
        val_fraction: Fraction of samples used for validation. The
            rest is the held-out test split.
        architecture: Free-form arch tag (``"mlp"``,
            ``"set_transformer"``).
        layer_sizes: Tuple of layer widths (e.g. ``(4, 64, 64, 2)``).
        activation: Activation function name (``"relu"``, ``"tanh"``).
        framework: Which framework the trainer should use.
        optimizer: Optimiser name (``"adam"``, ``"sgd"``).
        learning_rate: Learning rate. Must be > 0.
        batch_size: Mini-batch size. Must be > 0.
        epochs: Total epochs. Must be > 0.
        early_stopping_patience: Stop if val_loss does not improve
            within this many epochs. ``0`` disables early stopping.
        weights_path: Where the trained weights are written.
        metrics_path: Where the per-epoch metrics JSON is written.
            Empty string means "do not persist metrics".

    Raises:
        ValueError: For empty job_id / task / framework / weights_path,
            invalid split fractions, non-positive numeric fields,
            empty layer_sizes.
    """

    job_id: str
    task: str
    dataset_path: Path
    weights_path: Path
    train_fraction: float = 0.8
    val_fraction: float = 0.1
    architecture: str = "mlp"
    layer_sizes: tuple[int, ...] = (4, 64, 64, 2)
    activation: str = "relu"
    framework: TrainingFramework = "numpy_only"
    optimizer: str = "adam"
    learning_rate: float = 1e-3
    batch_size: int = 32
    epochs: int = 10
    early_stopping_patience: int = 0
    metrics_path: Path = field(default_factory=Path)

    def __post_init__(self) -> None:
        if not self.job_id:
            msg = "TrainingJob.job_id must be a non-empty string"
            raise ValueError(msg)
        if not self.task:
            msg = "TrainingJob.task must be a non-empty string"
            raise ValueError(msg)
        if str(self.weights_path) == ".":
            msg = "TrainingJob.weights_path must be a non-empty path"
            raise ValueError(msg)
        if not 0.0 < self.train_fraction < 1.0:
            msg = f"train_fraction must be in (0, 1), got {self.train_fraction}"
            raise ValueError(msg)
        if not 0.0 <= self.val_fraction < 1.0:
            msg = f"val_fraction must be in [0, 1), got {self.val_fraction}"
            raise ValueError(msg)
        if self.train_fraction + self.val_fraction >= 1.0:
            msg = (
                f"train_fraction + val_fraction must be < 1 (test split needs "
                f"a positive remainder), got {self.train_fraction + self.val_fraction}"
            )
            raise ValueError(msg)
        if not self.layer_sizes:
            msg = "TrainingJob.layer_sizes must contain at least one entry"
            raise ValueError(msg)
        if self.learning_rate <= 0.0:
            msg = f"learning_rate must be > 0, got {self.learning_rate}"
            raise ValueError(msg)
        if self.batch_size <= 0:
            msg = f"batch_size must be > 0, got {self.batch_size}"
            raise ValueError(msg)
        if self.epochs <= 0:
            msg = f"epochs must be > 0, got {self.epochs}"
            raise ValueError(msg)
        if self.early_stopping_patience < 0:
            msg = f"early_stopping_patience must be >= 0, got {self.early_stopping_patience}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class TrainingResult:
    """Outcome of a :meth:`TrainerService.run` call.

    Attributes:
        job_id: Echo of ``TrainingJob.job_id``.
        completed_epochs: Number of epochs actually executed (may be
            < ``job.epochs`` if early stopping fired).
        final_train_loss: Loss on the last training epoch.
        final_val_loss: Loss on the last validation epoch.
        best_val_loss: Lowest val loss recorded across the run.
        best_epoch: Epoch (1-indexed) at which best_val_loss occurred.
        weights_path: Path the weights file ended up at (same as
            ``job.weights_path``).
        early_stopped: ``True`` if the run terminated early.
    """

    job_id: str
    completed_epochs: int
    final_train_loss: float
    final_val_loss: float
    best_val_loss: float
    best_epoch: int
    weights_path: Path
    early_stopped: bool


class TrainerService:
    """Synchronous training loop driver (plan/07 § 7.5.3 MVP stub).

    The MVP does not perform real gradient descent — it emits a
    deterministic exponential-decay loss schedule, writes a
    placeholder weights file, and reports the trajectory through the
    epoch callback. This is enough to let the Editor / TrainerPanel
    code path and the workbench-train CLI integration come up in
    isolation.

    A future sub-step swaps the fake loop for a real backend (numpy
    MLP / TF / PyTorch); the public surface stays the same so that
    swap is transparent to callers.
    """

    def __init__(self, *, epoch_callback: EpochCallback | None = None) -> None:
        self._epoch_callback = epoch_callback

    def run(self, job: TrainingJob) -> TrainingResult:
        """Execute the (fake) training loop and persist weights.

        Args:
            job: Configuration record.

        Returns:
            :class:`TrainingResult` with per-epoch losses + the path
            the placeholder weights file was written to.
        """
        train_losses: list[float] = []
        val_losses: list[float] = []
        best_val = float("inf")
        best_epoch = 0
        early_stopped = False
        epochs_run = 0

        for epoch in range(1, job.epochs + 1):
            train_loss = _decay_loss(epoch, base=0.5, decay=0.95)
            val_loss = _decay_loss(epoch, base=0.55, decay=0.93)
            train_losses.append(train_loss)
            val_losses.append(val_loss)
            epochs_run = epoch

            if val_loss < best_val - 1e-9:
                best_val = val_loss
                best_epoch = epoch

            if self._epoch_callback is not None:
                self._epoch_callback(epoch, train_loss, val_loss)

            if (
                job.early_stopping_patience > 0
                and epoch - best_epoch >= job.early_stopping_patience
            ):
                early_stopped = True
                break

        _write_placeholder_weights(job.weights_path, job)

        return TrainingResult(
            job_id=job.job_id,
            completed_epochs=epochs_run,
            final_train_loss=train_losses[-1],
            final_val_loss=val_losses[-1],
            best_val_loss=best_val,
            best_epoch=best_epoch,
            weights_path=job.weights_path,
            early_stopped=early_stopped,
        )


def _decay_loss(epoch: int, *, base: float, decay: float) -> float:
    """Deterministic loss schedule: ``base * decay ** (epoch - 1)``."""
    return float(base * (decay ** (epoch - 1)))


def _write_placeholder_weights(path: Path, job: TrainingJob) -> None:
    """Persist a tiny ``.npz`` with the layer-shaped placeholder weights.

    Real trainers replace this with actual learned tensors; the file
    layout is the same so :meth:`NNPluginMixin.load_weights` can read
    either.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    weights: dict[str, np.ndarray] = {
        f"layer_{i}": np.zeros((a, b), dtype=np.float32)
        for i, (a, b) in enumerate(zip(job.layer_sizes[:-1], job.layer_sizes[1:], strict=False))
    }
    np.savez(path, **weights)  # type: ignore[arg-type]
