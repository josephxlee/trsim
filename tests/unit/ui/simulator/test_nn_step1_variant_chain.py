"""Step 1 controller variant-chain build tests (task B, plan/07 § 7.4.5a)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.app.nn import read_dataset
from workbench.domain.nn.variant_manifest import load_variants_manifest
from workbench.ui.simulator.nn_mode.step1_controller import NNStep1Controller
from workbench.ui.simulator.nn_mode.step1_dataset import (
    Step1BuildMode,
    Step1DatasetPanel,
)

pytestmark = pytest.mark.qt


def _wire(
    tmp_path: Path, qtbot: object, *, frames: int
) -> tuple[Step1DatasetPanel, NNStep1Controller, Path]:
    panel = Step1DatasetPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    panel.frames_edit().setText(str(frames))
    # In CHAIN mode the controller treats the output path's parent
    # directory as output_root. Pass tmp_path directly (no suffix) so
    # tmp_path itself becomes output_root.
    panel.output_edit().setText(str(tmp_path))
    panel.set_build_mode(Step1BuildMode.CHAIN_4VARIANT)
    controller = NNStep1Controller(panel)
    return panel, controller, tmp_path


# ---------------------------------------------------------------------
# Panel default
# ---------------------------------------------------------------------


def test_panel_default_build_mode_is_single(qtbot: object) -> None:
    panel = Step1DatasetPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    assert panel.current_build_mode() is Step1BuildMode.SINGLE
    assert panel.build_mode_combo().count() == 2


def test_panel_set_build_mode_chain(qtbot: object) -> None:
    panel = Step1DatasetPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    panel.set_build_mode(Step1BuildMode.CHAIN_4VARIANT)
    assert panel.current_build_mode() is Step1BuildMode.CHAIN_4VARIANT


# ---------------------------------------------------------------------
# Controller — chain build happy path
# ---------------------------------------------------------------------


def test_chain_build_writes_4_h5_plus_manifest(qtbot: object, tmp_path: Path) -> None:
    panel, controller, output_root = _wire(tmp_path, qtbot, frames=2)
    assert controller is not None
    panel.build_requested.emit()

    for variant_id in ("A", "B", "C", "D"):
        assert (output_root / f"pairing_variant_{variant_id}.h5").is_file()
    manifest_path = output_root / "pairing_variants_manifest.toml"
    assert manifest_path.is_file()

    manifest = load_variants_manifest(manifest_path)
    assert tuple(e.variant.variant_id for e in manifest.entries) == ("A", "B", "C", "D")


def test_chain_build_each_h5_has_correct_variant_id(qtbot: object, tmp_path: Path) -> None:
    panel, controller, output_root = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.build_requested.emit()

    for variant_id in ("A", "B", "C", "D"):
        meta, _, _ = read_dataset(output_root / f"pairing_variant_{variant_id}.h5")
        assert meta.variant.variant_id == variant_id
        assert meta.total_samples == 1


def test_chain_build_logs_per_variant_summary(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.build_requested.emit()

    log = panel.log_list()
    lines = [log.item(i).text() for i in range(log.count())]
    assert any("Chain build started" in line for line in lines)
    assert any("variant A:" in line for line in lines)
    assert any("variant D:" in line for line in lines)
    assert any("Manifest written" in line for line in lines)


def test_chain_build_status_lands_on_done(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.build_requested.emit()
    assert "done" in panel.status_label().text().lower()
    assert "4/4 variants" in panel.status_label().text()
    assert "(100%)" in panel.status_label().text()
    assert panel.progress_bar().value() == 100


# ---------------------------------------------------------------------
# Validation — chain build shares the SINGLE-mode error paths
# ---------------------------------------------------------------------


def test_chain_build_invalid_frames_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.frames_edit().setText("oops")
    panel.build_requested.emit()
    assert "error" in panel.status_label().text()


def test_chain_build_empty_output_aborts(qtbot: object, tmp_path: Path) -> None:
    panel, controller, _ = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.output_edit().setText("")
    panel.build_requested.emit()
    assert "error" in panel.status_label().text()


# ---------------------------------------------------------------------
# Round-trip: switch back to SINGLE mode after a chain build
# ---------------------------------------------------------------------


def test_switch_back_to_single_after_chain(qtbot: object, tmp_path: Path) -> None:
    panel, controller, output_root = _wire(tmp_path, qtbot, frames=1)
    assert controller is not None
    panel.build_requested.emit()
    assert (output_root / "pairing_variant_A.h5").is_file()

    # Now switch back to SINGLE mode and point at a fresh path.
    single_out = tmp_path / "single.h5"
    panel.set_build_mode(Step1BuildMode.SINGLE)
    panel.output_edit().setText(str(single_out))
    panel.frames_edit().setText("3")
    panel.build_requested.emit()

    assert single_out.is_file()
    meta, _, _ = read_dataset(single_out)
    assert meta.total_samples == 3
    assert meta.variant.variant_id == "A"
