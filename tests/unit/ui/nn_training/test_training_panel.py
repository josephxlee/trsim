"""TrainingPanel widget tests (task 3, plan/07 § 7.5.3)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.nn_training import TrainingPanel

pytestmark = pytest.mark.qt


def _panel(qtbot: object) -> TrainingPanel:
    panel = TrainingPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    return panel


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------


def test_default_input_values(qtbot: object) -> None:
    panel = _panel(qtbot)
    assert panel.job_id_edit().text() == "pairing_v1"
    assert panel.dataset_edit().text() == "./datasets/pairing_variant_A.h5"
    assert panel.weights_edit().text() == "./plugins/pairing/weights/v1.npz"
    assert panel.epochs_edit().text() == "10"
    assert panel.lr_edit().text() == "1e-3"
    assert panel.framework_combo().currentText() == "numpy_only"


def test_default_progress_labels(qtbot: object) -> None:
    panel = _panel(qtbot)
    assert panel.status_label().text() == "Status: idle"
    assert panel.epoch_label().text() == "Epoch: 0 / 0"
    assert "--" in panel.loss_label().text()
    assert "--" in panel.best_label().text()


# ---------------------------------------------------------------------
# Setters
# ---------------------------------------------------------------------


def test_set_status_updates_label(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_status("training: 3 / 10")
    assert "training: 3 / 10" in panel.status_label().text()


def test_set_epoch_updates_label(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_epoch(5, 10)
    assert panel.epoch_label().text() == "Epoch: 5 / 10"


def test_set_loss_formats_to_4_decimals(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_loss(0.12345, 0.6789)
    text = panel.loss_label().text()
    assert "0.1235" in text  # 4-decimal rounding
    assert "0.6789" in text


def test_set_best_formats(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.set_best(0.01, 42)
    text = panel.best_label().text()
    assert "0.0100" in text
    assert "42" in text


def test_append_log_extends_list(qtbot: object) -> None:
    panel = _panel(qtbot)
    panel.append_log("line one")
    panel.append_log("line two")
    assert panel.log_list().count() == 2


# ---------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------


def test_train_requested_signal_fires(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    with qtbot.waitSignal(panel.train_requested, timeout=500):
        panel.train_requested.emit()


def test_stop_requested_signal_fires(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = _panel(qtbot)
    with qtbot.waitSignal(panel.stop_requested, timeout=500):
        panel.stop_requested.emit()
