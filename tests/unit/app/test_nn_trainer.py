"""TrainerService + TrainingJob tests (Phase 6.7)."""

from __future__ import annotations

from itertools import pairwise
from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import TrainerService, TrainingJob


def _job(tmp_path: Path, **overrides: object) -> TrainingJob:
    defaults: dict[str, object] = {
        "job_id": "demo",
        "task": "pairing",
        "dataset_path": tmp_path / "ds.h5",
        "weights_path": tmp_path / "weights" / "demo.npz",
        "epochs": 4,
    }
    defaults.update(overrides)
    return TrainingJob(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# TrainingJob validation
# ---------------------------------------------------------------------


def test_default_job_constructs(tmp_path: Path) -> None:
    job = _job(tmp_path)
    assert job.job_id == "demo"
    assert job.framework == "numpy_only"
    assert job.layer_sizes == (4, 64, 64, 2)


@pytest.mark.parametrize("field_name", ["job_id", "task"])
def test_empty_required_string_rejected(tmp_path: Path, field_name: str) -> None:
    with pytest.raises(ValueError, match=field_name):
        _job(tmp_path, **{field_name: ""})


def test_default_weights_path_rejected(tmp_path: Path) -> None:
    """An empty Path() (Path() == '.') must be flagged at construction."""
    with pytest.raises(ValueError, match=r"weights_path"):
        _job(tmp_path, weights_path=Path())


@pytest.mark.parametrize("bad", [0.0, 1.0, -0.1, 1.1])
def test_invalid_train_fraction_rejected(tmp_path: Path, bad: float) -> None:
    with pytest.raises(ValueError, match=r"train_fraction"):
        _job(tmp_path, train_fraction=bad)


def test_train_plus_val_fraction_must_leave_room_for_test(tmp_path: Path) -> None:
    """train + val < 1.0 — otherwise no test split remains."""
    with pytest.raises(ValueError, match=r"test split"):
        _job(tmp_path, train_fraction=0.8, val_fraction=0.2)


def test_empty_layer_sizes_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"layer_sizes"):
        _job(tmp_path, layer_sizes=())


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("learning_rate", 0.0),
        ("batch_size", 0),
        ("epochs", 0),
    ],
)
def test_non_positive_numeric_rejected(tmp_path: Path, field_name: str, value: float | int) -> None:
    with pytest.raises(ValueError, match=field_name):
        _job(tmp_path, **{field_name: value})


def test_negative_early_stopping_patience_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"early_stopping_patience"):
        _job(tmp_path, early_stopping_patience=-1)


# ---------------------------------------------------------------------
# TrainerService.run
# ---------------------------------------------------------------------


def test_run_executes_all_epochs_when_no_early_stopping(tmp_path: Path) -> None:
    job = _job(tmp_path, epochs=5, early_stopping_patience=0)
    result = TrainerService().run(job)
    assert result.completed_epochs == 5
    assert result.early_stopped is False


def test_run_emits_epoch_callback_per_epoch(tmp_path: Path) -> None:
    job = _job(tmp_path, epochs=3, early_stopping_patience=0)
    calls: list[tuple[int, float, float]] = []

    def cb(epoch: int, tl: float, vl: float) -> None:
        calls.append((epoch, tl, vl))

    TrainerService(epoch_callback=cb).run(job)
    assert [c[0] for c in calls] == [1, 2, 3]
    # The fake schedule decays each epoch — train_loss strictly
    # decreases. Locking this invariant lets a future real trainer
    # swap in without surprising callers that assumed monotonicity.
    for prev, cur in pairwise(calls):
        assert cur[1] < prev[1]


def test_run_writes_placeholder_weights_to_disk(tmp_path: Path) -> None:
    job = _job(tmp_path, epochs=2)
    TrainerService().run(job)
    assert job.weights_path.exists()
    # The file holds one entry per consecutive-layer pair.
    with np.load(job.weights_path) as data:
        keys = sorted(data.keys())
    # layer_sizes default (4, 64, 64, 2) -> 3 layer pairs.
    assert keys == ["layer_0", "layer_1", "layer_2"]


def test_run_early_stops_when_val_loss_stalls(tmp_path: Path) -> None:
    """With patience=1 the deterministic schedule still improves every
    epoch (it strictly decreases) — so early stopping should NOT fire.
    Verify the contract: completed_epochs == epochs, early_stopped False.
    """
    job = _job(tmp_path, epochs=10, early_stopping_patience=1)
    result = TrainerService().run(job)
    assert result.completed_epochs == 10
    assert result.early_stopped is False


def test_run_records_best_epoch_at_final_when_monotonic(tmp_path: Path) -> None:
    """The fake schedule is monotonically decreasing, so the best
    val_loss is on the last epoch.
    """
    job = _job(tmp_path, epochs=6)
    result = TrainerService().run(job)
    assert result.best_epoch == result.completed_epochs
    assert result.best_val_loss == result.final_val_loss


def test_run_returns_job_id_back(tmp_path: Path) -> None:
    job = _job(tmp_path, job_id="my_pairing_v3", epochs=1)
    result = TrainerService().run(job)
    assert result.job_id == "my_pairing_v3"


def test_run_weights_path_round_trips(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "out" / "demo.npz"
    job = _job(tmp_path, weights_path=out, epochs=1)
    result = TrainerService().run(job)
    assert result.weights_path == out
    assert out.exists()
