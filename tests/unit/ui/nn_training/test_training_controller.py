"""NNTrainingController wiring tests (task 3, plan/07 § 7.5.3)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.ui.nn_training import NNTrainingController, TrainingPanel

pytestmark = pytest.mark.qt


def _wired(qtbot: object, tmp_path: Path) -> tuple[TrainingPanel, NNTrainingController]:
    panel = TrainingPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    # Point weights at the tmp_path so the placeholder .npz lands in
    # a writable per-test dir.
    panel.weights_edit().setText(str(tmp_path / "weights" / "demo.npz"))
    panel.dataset_edit().setText(str(tmp_path / "ds.h5"))
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
