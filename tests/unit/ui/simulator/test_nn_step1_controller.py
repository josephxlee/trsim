"""Step 1 controller wiring tests (Phase 6.4c)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.app.nn import read_dataset
from workbench.ui.simulator.nn_mode.step1_controller import NNStep1Controller
from workbench.ui.simulator.nn_mode.step1_dataset import Step1DatasetPanel

pytestmark = pytest.mark.qt


def _wired_panel(
    tmp_path: Path, qtbot: object, *, target: int = 8
) -> tuple[Step1DatasetPanel, NNStep1Controller, Path]:
    panel = Step1DatasetPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    panel.frames_edit().setText(str(target))
    out = tmp_path / "demo.h5"
    panel.output_edit().setText(str(out))
    controller = NNStep1Controller(panel, seed=42)
    # controller must stay alive — Qt signal connection holds no strong
    # reference, so returning it keeps the wiring intact for the test.
    return panel, controller, out


def test_build_requested_writes_dataset_with_target_samples(qtbot: object, tmp_path: Path) -> None:
    panel, controller, out = _wired_panel(tmp_path, qtbot, target=6)
    assert controller is not None
    panel.build_requested.emit()

    assert out.exists()
    meta, inputs, labels = read_dataset(out)
    assert meta.total_samples == 6
    assert meta.spec.spec_id == "pairing"
    assert inputs["up_beats"].shape == (6, 16)
    assert labels["pair_indices"].shape == (6, 16)
    # Scenario-driven build emits diagonal GT for active targets
    # (default 3) and -1 padding for slots 3..15.
    gt0 = labels["pair_indices"][0]
    assert int(gt0[0]) == 0
    assert int(gt0[1]) == 1
    assert int(gt0[2]) == 2
    assert int(gt0[3]) == -1
    assert int(gt0[15]) == -1


def test_build_requested_updates_status_and_log(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wired_panel(tmp_path, qtbot, target=4)
    assert controller is not None
    panel.build_requested.emit()

    assert "done:" in panel.status_label().text()
    _log = panel.log_list()
    log_items = [_log.item(i).text() for i in range(_log.count())]
    assert any("Build started" in line for line in log_items)
    assert any("Build complete" in line for line in log_items)


def test_build_invalid_frames_value_aborts_with_error(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wired_panel(tmp_path, qtbot, target=4)
    assert controller is not None
    panel.frames_edit().setText("not-an-int")
    panel.build_requested.emit()
    assert "error" in panel.status_label().text()


def test_build_negative_frames_aborts_with_error(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wired_panel(tmp_path, qtbot, target=4)
    assert controller is not None
    panel.frames_edit().setText("-1")
    panel.build_requested.emit()
    assert "error" in panel.status_label().text()


def test_build_empty_output_path_aborts_with_error(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wired_panel(tmp_path, qtbot, target=4)
    assert controller is not None
    panel.output_edit().setText("")
    panel.build_requested.emit()
    assert "error" in panel.status_label().text()


def test_cancel_with_no_build_in_flight_logs_message(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wired_panel(tmp_path, qtbot, target=4)
    assert controller is not None
    panel.cancel_requested.emit()
    _log = panel.log_list()
    log_items = [_log.item(i).text() for i in range(_log.count())]
    assert any("no build in flight" in line for line in log_items)


def test_zero_target_writes_empty_dataset(qtbot: object, tmp_path: Path) -> None:
    panel, controller, out = _wired_panel(tmp_path, qtbot, target=0)
    assert controller is not None
    panel.build_requested.emit()
    meta, inputs, _ = read_dataset(out)
    assert meta.total_samples == 0
    assert inputs["up_beats"].shape == (0, 16)


def test_two_consecutive_builds_overwrite_same_path(qtbot: object, tmp_path: Path) -> None:
    panel, controller, out = _wired_panel(tmp_path, qtbot, target=3)
    assert controller is not None
    panel.build_requested.emit()
    panel.frames_edit().setText("5")
    panel.build_requested.emit()
    meta, _, _ = read_dataset(out)
    assert meta.total_samples == 5
