"""TrainerService numpy_mlp backend tests (Task C, plan/07 § 7.5.3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import TrainerService, TrainingJob, write_dataset
from workbench.domain.nn import DatasetMeta, DatasetVariant, FieldSpec, SampleSpec


def _spec(buffer: int = 4) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (buffer,), "complex64"),
            FieldSpec("down_beats", (buffer,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (buffer,), "int32"),),
    )


def _write_synthetic_dataset(
    path: Path,
    *,
    n: int = 32,
    buffer: int = 4,
    seed: int = 0,
) -> SampleSpec:
    """Write a tiny synthetic HDF5 dataset to ``path``.

    The "labels" are derived deterministically from the beat magnitudes
    so the MLP has a learnable target — the regression task is well
    defined even though the underlying scenario is synthetic.
    """
    rng = np.random.default_rng(seed)
    spec = _spec(buffer)
    up = (rng.standard_normal((n, buffer)) + 1j * rng.standard_normal((n, buffer))).astype(
        np.complex64
    )
    down = (rng.standard_normal((n, buffer)) + 1j * rng.standard_normal((n, buffer))).astype(
        np.complex64
    )
    # Label = floor(|up| + |down|) clipped to [0, buffer-1] — a real
    # function of the inputs so the MLP can decrease loss.
    label = np.clip(
        np.floor(np.abs(up) + np.abs(down)),
        0,
        buffer - 1,
    ).astype(np.int32)
    meta = DatasetMeta(
        dataset_id="synthetic",
        spec=spec,
        variant=DatasetVariant(variant_id="A"),
        total_samples=n,
    )
    write_dataset(path, meta, {"up_beats": up, "down_beats": down}, {"pair_indices": label})
    return spec


def _job(
    tmp_path: Path,
    *,
    dataset_path: Path,
    weights_path: Path | None = None,
    **overrides: object,
) -> TrainingJob:
    base: dict[str, object] = {
        "job_id": "numpy_mlp_demo",
        "task": "pairing",
        "dataset_path": dataset_path,
        "weights_path": weights_path or (tmp_path / "weights" / "out.npz"),
        "layer_sizes": (4, 16, 4),
        "epochs": 5,
        "learning_rate": 0.05,
        "batch_size": 8,
        "train_fraction": 0.6,
        "val_fraction": 0.2,
    }
    base.update(overrides)
    return TrainingJob(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# Backend dispatch
# ---------------------------------------------------------------------


def test_default_backend_is_fake(tmp_path: Path) -> None:
    job = _job(tmp_path, dataset_path=tmp_path / "ds.h5")  # dataset never read for fake
    trainer = TrainerService()
    result = trainer.run(job)
    # Fake loop never writes the dataset path; success here means we did
    # not accidentally route to numpy_mlp.
    assert result.weights_path.is_file()
    assert result.completed_epochs == job.epochs


def test_numpy_mlp_backend_requires_dataset(tmp_path: Path) -> None:
    job = _job(tmp_path, dataset_path=tmp_path / "missing.h5")
    trainer = TrainerService(backend="numpy_mlp")
    with pytest.raises(FileNotFoundError):
        trainer.run(job)


# ---------------------------------------------------------------------
# numpy_mlp happy path
# ---------------------------------------------------------------------


def test_numpy_mlp_runs_and_writes_weights(tmp_path: Path) -> None:
    ds = tmp_path / "dataset.h5"
    _write_synthetic_dataset(ds, n=32, buffer=4)
    weights_path = tmp_path / "weights" / "out.npz"
    job = _job(tmp_path, dataset_path=ds, weights_path=weights_path, epochs=3)
    trainer = TrainerService(backend="numpy_mlp")
    result = trainer.run(job)

    assert result.weights_path == weights_path
    assert weights_path.is_file()
    assert result.completed_epochs == 3

    loaded = np.load(weights_path)
    # numpy_mlp writes layer_i_W + layer_i_b per layer.
    assert "layer_0_W" in loaded.files
    assert "layer_0_b" in loaded.files


def test_numpy_mlp_decreases_val_loss(tmp_path: Path) -> None:
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=64, buffer=4, seed=1)
    job = _job(
        tmp_path,
        dataset_path=ds,
        epochs=30,
        learning_rate=0.05,
        batch_size=8,
    )
    losses: list[float] = []

    def _on_epoch(_epoch: int, _train_loss: float, val_loss: float) -> None:
        losses.append(val_loss)

    trainer = TrainerService(backend="numpy_mlp", epoch_callback=_on_epoch)
    result = trainer.run(job)
    assert len(losses) == 30
    # Validation loss after 30 epochs must be lower than the very first
    # epoch (loose smoke test — the actual training is synthetic).
    assert result.best_val_loss < losses[0]


def test_numpy_mlp_epoch_callback_signature(tmp_path: Path) -> None:
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=16, buffer=4, seed=2)
    job = _job(tmp_path, dataset_path=ds, epochs=2, batch_size=4)
    seen: list[tuple[int, float, float]] = []

    def _cb(epoch: int, train: float, val: float) -> None:
        seen.append((epoch, train, val))

    TrainerService(backend="numpy_mlp", epoch_callback=_cb).run(job)
    assert [e for e, _, _ in seen] == [1, 2]
    for _, train_loss, val_loss in seen:
        assert train_loss >= 0.0
        assert val_loss >= 0.0


@pytest.mark.filterwarnings("ignore:overflow")
@pytest.mark.filterwarnings("ignore:invalid value")
def test_numpy_mlp_early_stopping(tmp_path: Path) -> None:
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=16, buffer=4, seed=3)
    # Pathological lr that pushes loss up — best_val never improves so
    # the patience window triggers early stop. The diverging update
    # cascade trips numpy overflow warnings; the test asserts behaviour,
    # not numerics, so the warnings are suppressed.
    job = _job(
        tmp_path,
        dataset_path=ds,
        epochs=20,
        learning_rate=10.0,
        early_stopping_patience=2,
        batch_size=4,
    )
    trainer = TrainerService(backend="numpy_mlp")
    result = trainer.run(job)
    assert result.early_stopped
    assert result.completed_epochs < job.epochs


def test_numpy_mlp_zero_sample_dataset_rejected(tmp_path: Path) -> None:
    ds = tmp_path / "empty.h5"
    spec = _spec(4)
    write_dataset(
        ds,
        DatasetMeta(
            dataset_id="empty",
            spec=spec,
            variant=DatasetVariant(variant_id="A"),
            total_samples=0,
        ),
        {
            "up_beats": np.empty((0, 4), dtype=np.complex64),
            "down_beats": np.empty((0, 4), dtype=np.complex64),
        },
        {"pair_indices": np.empty((0, 4), dtype=np.int32)},
    )
    job = _job(tmp_path, dataset_path=ds, epochs=2)
    trainer = TrainerService(backend="numpy_mlp")
    with pytest.raises(ValueError, match=r">= 1 sample"):
        trainer.run(job)


def test_numpy_mlp_seed_is_reproducible(tmp_path: Path) -> None:
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=24, buffer=4, seed=42)
    job_a = _job(tmp_path, dataset_path=ds, weights_path=tmp_path / "a.npz", epochs=4)
    job_b = _job(tmp_path, dataset_path=ds, weights_path=tmp_path / "b.npz", epochs=4)
    ra = TrainerService(backend="numpy_mlp", rng_seed=7).run(job_a)
    rb = TrainerService(backend="numpy_mlp", rng_seed=7).run(job_b)
    assert ra.final_train_loss == pytest.approx(rb.final_train_loss, rel=1e-12)
    assert ra.final_val_loss == pytest.approx(rb.final_val_loss, rel=1e-12)


# ---------------------------------------------------------------------
# numpy_mlp_adam backend (A1-a)
# ---------------------------------------------------------------------


def test_numpy_mlp_adam_backend_routes_and_writes_weights(tmp_path: Path) -> None:
    """`backend="numpy_mlp_adam"` runs the Adam optimizer and persists
    the layer_i_W / layer_i_b weight file.
    """
    ds = tmp_path / "dataset.h5"
    _write_synthetic_dataset(ds, n=32, buffer=4)
    weights_path = tmp_path / "weights" / "out.npz"
    job = _job(
        tmp_path,
        dataset_path=ds,
        weights_path=weights_path,
        epochs=3,
        learning_rate=1e-2,
    )
    trainer = TrainerService(backend="numpy_mlp_adam")
    result = trainer.run(job)

    assert result.weights_path == weights_path
    assert weights_path.is_file()
    assert result.completed_epochs == 3
    loaded = np.load(weights_path)
    assert "layer_0_W" in loaded.files
    assert "layer_0_b" in loaded.files


def test_numpy_mlp_adam_backend_decreases_val_loss(tmp_path: Path) -> None:
    """Adam drives val loss down across 30 epochs on the synthetic
    pairing task. Looser smoke check than the SGD test because Adam's
    early curve is noisier — we compare best vs first.
    """
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=64, buffer=4, seed=1)
    job = _job(
        tmp_path,
        dataset_path=ds,
        epochs=30,
        learning_rate=5e-3,
        batch_size=8,
    )
    losses: list[float] = []

    def _on_epoch(_epoch: int, _train_loss: float, val_loss: float) -> None:
        losses.append(val_loss)

    trainer = TrainerService(backend="numpy_mlp_adam", epoch_callback=_on_epoch)
    result = trainer.run(job)
    assert len(losses) == 30
    assert result.best_val_loss < losses[0]


def test_numpy_mlp_adam_backend_is_reproducible_under_fixed_seed(tmp_path: Path) -> None:
    """Same dataset + same rng_seed -> identical losses across two
    runs. Pins Adam state determinism through the trainer surface.
    """
    ds = tmp_path / "ds.h5"
    _write_synthetic_dataset(ds, n=24, buffer=4, seed=42)
    job_a = _job(tmp_path, dataset_path=ds, weights_path=tmp_path / "a.npz", epochs=4)
    job_b = _job(tmp_path, dataset_path=ds, weights_path=tmp_path / "b.npz", epochs=4)
    ra = TrainerService(backend="numpy_mlp_adam", rng_seed=7).run(job_a)
    rb = TrainerService(backend="numpy_mlp_adam", rng_seed=7).run(job_b)
    assert ra.final_train_loss == pytest.approx(rb.final_train_loss, rel=1e-12)
    assert ra.final_val_loss == pytest.approx(rb.final_val_loss, rel=1e-12)


def test_numpy_mlp_adam_backend_zero_sample_rejected(tmp_path: Path) -> None:
    """Empty dataset -> error message mentions the Adam backend name."""
    ds = tmp_path / "empty.h5"
    spec = _spec(4)
    write_dataset(
        ds,
        DatasetMeta(
            dataset_id="empty",
            spec=spec,
            variant=DatasetVariant(variant_id="A"),
            total_samples=0,
        ),
        {
            "up_beats": np.empty((0, 4), dtype=np.complex64),
            "down_beats": np.empty((0, 4), dtype=np.complex64),
        },
        {"pair_indices": np.empty((0, 4), dtype=np.int32)},
    )
    job = _job(tmp_path, dataset_path=ds, epochs=2)
    trainer = TrainerService(backend="numpy_mlp_adam")
    with pytest.raises(ValueError, match=r"numpy_mlp_adam.*>= 1 sample"):
        trainer.run(job)
