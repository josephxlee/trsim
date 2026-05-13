"""TrainerService for the in-workbench training loop (plan/07 § 7.5).

Phase 6.7 stubbed the schema + service surface with a fake decay-
schedule loop. Task C adds a real numpy MLP backend (still pure
numpy — no Torch / TF / sklearn) selectable via the ``backend``
constructor argument:

- ``"fake"`` (default, Phase 6.7 behaviour) — emits a deterministic
  exponential-decay loss schedule and writes a placeholder ``.npz``.
  Useful for UI smoke tests that should not require an HDF5 dataset.
- ``"numpy_mlp"`` (task C) — reads the HDF5 dataset pointed at by
  :attr:`TrainingJob.dataset_path`, flattens its inputs / labels,
  splits into train / val / test, trains a fully-connected MLP via
  mini-batch SGD, and writes ``layer_i_W`` / ``layer_i_b`` arrays
  to the weights ``.npz``. ``best_val_loss`` and ``early_stopped``
  reflect the actual training curve.
- ``"numpy_mlp_adam"`` (Phase 6 NN augmentation A1-a) — identical
  data path to ``"numpy_mlp"`` but uses bias-corrected Adam
  (Kingma & Ba 2014, default beta1=0.9 / beta2=0.999 / eps=1e-8)
  instead of plain SGD. Adam state persists across epochs to keep
  the momentum accumulators warm.

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
from numpy.typing import NDArray

from workbench.app.nn.data_exporter import read_dataset
from workbench.app.nn.numpy_mlp import (
    AdamState,
    NumpyMLPParams,
    flatten_inputs,
    flatten_labels,
    forward,
    init_adam_state,
    init_params,
    mse_loss,
    train_one_epoch,
    train_one_epoch_adam,
)

TrainingFramework = Literal["tensorflow", "pytorch", "numpy_only"]
"""Allowed values for ``TrainingJob.framework`` (plan/07 § 7.5.2)."""

TrainingBackend = Literal["fake", "numpy_mlp", "numpy_mlp_adam"]
"""TrainerService backends. ``"fake"`` keeps the Phase 6.7 behaviour
(no dataset I/O); ``"numpy_mlp"`` runs the real gradient-descent
loop introduced in task C; ``"numpy_mlp_adam"`` reuses the same data
path but swaps SGD for bias-corrected Adam (Phase 6 NN augmentation
A1-a)."""

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
    """Synchronous training loop driver (plan/07 § 7.5.3).

    Two backends:

    - ``"fake"`` — Phase 6.7 deterministic decay loop. No HDF5 read.
    - ``"numpy_mlp"`` — task C real numpy gradient descent.

    The public surface (``run(job) -> TrainingResult``) is identical
    across backends; the choice lives on the constructor so callers
    can swap implementations without rewriting their plumbing.
    """

    def __init__(
        self,
        *,
        epoch_callback: EpochCallback | None = None,
        backend: TrainingBackend = "fake",
        rng_seed: int = 0,
    ) -> None:
        self._epoch_callback = epoch_callback
        self._backend = backend
        self._rng_seed = rng_seed

    def run(self, job: TrainingJob) -> TrainingResult:
        """Execute the configured backend and persist the weights file.

        Args:
            job: Configuration record.

        Returns:
            :class:`TrainingResult` with per-epoch losses + the path
            the weights file was written to.
        """
        if self._backend == "numpy_mlp":
            return self._run_numpy_mlp(job, optimizer="sgd")
        if self._backend == "numpy_mlp_adam":
            return self._run_numpy_mlp(job, optimizer="adam")
        return self._run_fake(job)

    # ------------------------------------------------------------------
    # Fake backend (Phase 6.7)
    # ------------------------------------------------------------------

    def _run_fake(self, job: TrainingJob) -> TrainingResult:
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

    # ------------------------------------------------------------------
    # numpy_mlp backend (task C)
    # ------------------------------------------------------------------

    def _run_numpy_mlp(
        self, job: TrainingJob, *, optimizer: Literal["sgd", "adam"] = "sgd"
    ) -> TrainingResult:
        meta, inputs, labels = read_dataset(job.dataset_path)
        n_samples = meta.total_samples
        if n_samples <= 0:
            backend_name = "numpy_mlp_adam" if optimizer == "adam" else "numpy_mlp"
            msg = f"{backend_name} backend requires >= 1 sample; dataset has {n_samples}"
            raise ValueError(msg)

        x = flatten_inputs(meta.spec, inputs, n_samples)
        y = flatten_labels(meta.spec, labels, n_samples)

        x_train, y_train, x_val, y_val = _split_train_val(
            x, y, job.train_fraction, job.val_fraction, seed=self._rng_seed
        )

        layer_dims = _resolve_layer_dims(job, x.shape[1], y.shape[1])
        activation: Literal["relu", "tanh"] = "tanh" if job.activation == "tanh" else "relu"
        params = init_params(layer_dims, activation=activation, rng_seed=self._rng_seed)
        adam_state: AdamState | None = init_adam_state(params) if optimizer == "adam" else None

        rng = np.random.default_rng(self._rng_seed + 1)
        train_losses: list[float] = []
        val_losses: list[float] = []
        best_val = float("inf")
        best_epoch = 0
        early_stopped = False
        epochs_run = 0

        for epoch in range(1, job.epochs + 1):
            if adam_state is not None:
                train_loss = train_one_epoch_adam(
                    params,
                    adam_state,
                    x_train,
                    y_train,
                    learning_rate=job.learning_rate,
                    batch_size=job.batch_size,
                    rng=rng,
                )
            else:
                train_loss = train_one_epoch(
                    params,
                    x_train,
                    y_train,
                    learning_rate=job.learning_rate,
                    batch_size=job.batch_size,
                    rng=rng,
                )
            val_loss = mse_loss(forward(params, x_val), y_val) if x_val.shape[0] > 0 else train_loss
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

        _write_learned_weights(job.weights_path, params)

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


def _write_learned_weights(path: Path, params: NumpyMLPParams) -> None:
    """Persist the trained ``NumpyMLPParams`` as ``layer_i_W`` / ``layer_i_b``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    for i, (w, b) in enumerate(zip(params.weights, params.biases, strict=True)):
        arrays[f"layer_{i}_W"] = w
        arrays[f"layer_{i}_b"] = b
    np.savez(path, **arrays)  # type: ignore[arg-type]


def _split_train_val(
    x: NDArray[np.float32],
    y: NDArray[np.float32],
    train_fraction: float,
    val_fraction: float,
    *,
    seed: int,
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.float32], NDArray[np.float32]]:
    """Shuffle ``(x, y)`` and slice the train / val portions.

    The remaining tail (test split) is not returned — the TrainerService
    MVP only tracks train + val losses. The Step 2 evaluator computes
    the test loss separately via :func:`workbench.app.nn.evaluate`.
    """
    n = x.shape[0]
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    n_train = max(1, int(n * train_fraction))
    n_val = max(0, int(n * val_fraction))
    if n_train >= n:
        n_train = max(1, n - 1)
        n_val = 0
    elif n_train + n_val >= n:
        n_val = max(0, n - n_train - 1)

    train_idx = perm[:n_train]
    val_idx = perm[n_train : n_train + n_val]
    return x[train_idx], y[train_idx], x[val_idx], y[val_idx]


def _resolve_layer_dims(job: TrainingJob, d_in: int, d_out: int) -> tuple[int, ...]:
    """Anchor :attr:`TrainingJob.layer_sizes` to the data dimensions.

    ``job.layer_sizes[0]`` and ``[-1]`` are treated as suggestions —
    the actual first / last entries come from the dataset to keep the
    forward shape sound. Hidden widths pass through.
    """
    if len(job.layer_sizes) < 2:
        return (d_in, d_out)
    hidden = job.layer_sizes[1:-1]
    return (d_in, *hidden, d_out)
