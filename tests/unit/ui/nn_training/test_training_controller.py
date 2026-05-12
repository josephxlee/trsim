"""NNTrainingController wiring tests (task 3, plan/07 § 7.5.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.ui.nn_training import NNTrainingController, TrainingPanel

pytestmark = pytest.mark.qt


def _wired(
    qtbot: object, tmp_path: Path, *, backend: str = "fake"
) -> tuple[TrainingPanel, NNTrainingController]:
    panel = TrainingPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    # Point weights at the tmp_path so the placeholder .npz lands in
    # a writable per-test dir.
    panel.weights_edit().setText(str(tmp_path / "weights" / "demo.npz"))
    panel.dataset_edit().setText(str(tmp_path / "ds.h5"))
    # Validation tests rely on the fake backend (no HDF5 read) so they
    # exercise the controller's parse/error paths in isolation. The
    # backend toggle has its own dedicated tests at the bottom of the
    # file.
    panel.set_backend(backend)
    controller = NNTrainingController(panel)
    return panel, controller


def _log_text(panel: TrainingPanel) -> list[str]:
    lst = panel.log_list()
    out: list[str] = []
    for i in range(lst.count()):
        item = lst.item(i)
        assert item is not None
        out.append(item.text())
    return out


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


def test_train_requested_runs_full_loop(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.epochs_edit().setText("3")
    panel.train_requested.emit()

    # Final status reports "done: 3/3 epochs"
    assert "done:" in panel.status_label().text()
    assert "3/3" in panel.status_label().text()
    assert "Training started" in _log_text(panel)[0]
    assert any("Training complete" in line for line in _log_text(panel))


def test_train_requested_records_per_epoch_progress(qtbot: object, tmp_path: Path) -> None:
    """After the loop the epoch label sits at the final epoch."""
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.epochs_edit().setText("5")
    panel.train_requested.emit()
    assert panel.epoch_label().text() == "Epoch: 5 / 5"


def test_train_requested_writes_placeholder_weights(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.epochs_edit().setText("2")
    panel.train_requested.emit()
    assert (tmp_path / "weights" / "demo.npz").exists()


# ---------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------


def test_empty_job_id_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.job_id_edit().setText("")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


def test_empty_dataset_path_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.dataset_edit().setText("")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


def test_empty_weights_path_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.weights_edit().setText("")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


def test_non_integer_epochs_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.epochs_edit().setText("not-an-int")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


def test_non_numeric_learning_rate_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.lr_edit().setText("not-a-float")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


def test_zero_epochs_rejected_by_training_job(qtbot: object, tmp_path: Path) -> None:
    """TrainingJob.__post_init__ rejects epochs <= 0; controller surfaces
    the message via the status label.
    """
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.epochs_edit().setText("0")
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()


# ---------------------------------------------------------------------
# Stop
# ---------------------------------------------------------------------


def test_stop_without_training_in_flight_logs(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path)
    assert controller is not None
    panel.stop_requested.emit()
    assert any("no training in flight" in line for line in _log_text(panel))


# ---------------------------------------------------------------------
# Backend toggle (A1)
# ---------------------------------------------------------------------


def test_fake_backend_logs_backend_label(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wired(qtbot, tmp_path, backend="fake")
    assert controller is not None
    panel.epochs_edit().setText("2")
    panel.train_requested.emit()
    assert any("backend=fake" in line for line in _log_text(panel))


def test_numpy_mlp_backend_runs_against_real_dataset(  # type: ignore[no-untyped-def]
    qtbot: object,
    tmp_path: Path,
) -> None:
    """Default panel backend is numpy_mlp; pair with a synthetic HDF5
    dataset so the controller dispatches the real gradient-descent path.
    """
    import numpy as np

    from workbench.app.nn import write_dataset
    from workbench.domain.nn import DatasetMeta, DatasetVariant, FieldSpec, SampleSpec

    ds = tmp_path / "ds.h5"
    spec = SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (4,), "complex64"),
            FieldSpec("down_beats", (4,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (4,), "int32"),),
    )
    rng = np.random.default_rng(0)
    n = 16
    write_dataset(
        ds,
        DatasetMeta(
            dataset_id="demo", spec=spec, variant=DatasetVariant(variant_id="A"), total_samples=n
        ),
        {
            "up_beats": (rng.standard_normal((n, 4)) + 1j * rng.standard_normal((n, 4))).astype(
                np.complex64
            ),
            "down_beats": (rng.standard_normal((n, 4)) + 1j * rng.standard_normal((n, 4))).astype(
                np.complex64
            ),
        },
        {"pair_indices": rng.integers(0, 4, (n, 4)).astype(np.int32)},
    )

    panel, controller = _wired(qtbot, tmp_path, backend="numpy_mlp")
    assert controller is not None
    panel.dataset_edit().setText(str(ds))
    panel.epochs_edit().setText("3")
    panel.lr_edit().setText("0.05")
    panel.train_requested.emit()

    assert "done:" in panel.status_label().text()
    assert any("backend=numpy_mlp" in line for line in _log_text(panel))
    saved = tmp_path / "weights" / "demo.npz"
    assert saved.is_file()
    arrays = np.load(saved)
    # numpy_mlp writes layer_i_W + layer_i_b (task C); fake writes layer_i.
    assert "layer_0_W" in arrays.files
    assert "layer_0_b" in arrays.files


def test_numpy_mlp_backend_missing_dataset_surfaces_error(  # type: ignore[no-untyped-def]
    qtbot: object,
    tmp_path: Path,
) -> None:
    """numpy_mlp raises FileNotFoundError when the HDF5 is absent;
    controller catches and writes the error to the status label.
    """
    panel, controller = _wired(qtbot, tmp_path, backend="numpy_mlp")
    assert controller is not None
    panel.dataset_edit().setText(str(tmp_path / "missing.h5"))
    panel.train_requested.emit()
    assert "error" in panel.status_label().text()
