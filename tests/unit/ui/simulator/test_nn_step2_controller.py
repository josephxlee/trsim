"""Step 2 controller wiring tests (Phase 6 후속)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")

from workbench.app.nn import DatasetBuilder, NumpyPairingNN
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec
from workbench.ui.simulator.nn_mode.step2_controller import NNStep2Controller
from workbench.ui.simulator.nn_mode.step2_eval import Step2EvalPanel

pytestmark = pytest.mark.qt


def _pairing_spec(beat_count: int = 4) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (beat_count,), "complex64"),
            FieldSpec("down_beats", (beat_count,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (beat_count,), "int32"),),
    )


def _build_identity_dataset(tmp_path: Path, n_samples: int = 4) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "identity.h5"
    builder = DatasetBuilder(
        spec=_pairing_spec(),
        variant=DatasetVariant(variant_id="A"),
        dataset_id="identity",
        output_path=out,
    )
    rng = np.random.default_rng(seed=0)
    diagonal = np.arange(4, dtype=np.int32)
    for _ in range(n_samples):
        up = rng.standard_normal(4).astype(np.complex64)
        builder.append({"up_beats": up, "down_beats": up}, {"pair_indices": diagonal})
    builder.finalize()
    return out


def _build_wrong_dataset(tmp_path: Path, n_samples: int = 4) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    out = tmp_path / "wrong.h5"
    builder = DatasetBuilder(
        spec=_pairing_spec(),
        variant=DatasetVariant(variant_id="A"),
        dataset_id="wrong",
        output_path=out,
    )
    rng = np.random.default_rng(seed=1)
    shifted = np.roll(np.arange(4, dtype=np.int32), 1)
    for _ in range(n_samples):
        up = rng.standard_normal(4).astype(np.complex64)
        builder.append({"up_beats": up, "down_beats": up}, {"pair_indices": shifted})
    builder.finalize()
    return out


def _wire(
    qtbot: object,
    *,
    datasets: dict[str, Path] | None = None,
    plugins: dict[str, NumpyPairingNN] | None = None,
) -> tuple[Step2EvalPanel, NNStep2Controller]:
    panel = Step2EvalPanel()
    qtbot.addWidget(panel)  # type: ignore[attr-defined]
    controller = NNStep2Controller(panel, datasets=datasets, plugins=plugins)
    return panel, controller


def _rmse_cell(panel: Step2EvalPanel) -> str:
    item = panel.error_table().item(0, 1)
    assert item is not None
    return item.text()


def _select(combo_factory: object, name: str) -> None:
    combo = combo_factory()  # type: ignore[operator]
    idx = combo.findText(name)
    combo.setCurrentIndex(idx)


# ---------------------------------------------------------------------
# Combo population
# ---------------------------------------------------------------------


def test_constructor_populates_combos_from_registries(qtbot: object, tmp_path: Path) -> None:
    ds = _build_identity_dataset(tmp_path)
    plug = NumpyPairingNN()
    panel, controller = _wire(qtbot, datasets={"identity": ds}, plugins={"baseline": plug})
    assert controller is not None
    assert panel.dataset_combo().findText("identity") >= 0
    assert panel.plugin_combo().findText("baseline") >= 0


def test_register_dataset_appears_in_combo(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wire(qtbot)
    ds = _build_identity_dataset(tmp_path)
    controller.register_dataset("identity", ds)
    assert panel.dataset_combo().findText("identity") >= 0


def test_register_plugin_appears_in_combo(qtbot: object) -> None:
    panel, controller = _wire(qtbot)
    controller.register_plugin("baseline", NumpyPairingNN())
    assert panel.plugin_combo().findText("baseline") >= 0


def test_register_dataset_rejects_empty_name(qtbot: object, tmp_path: Path) -> None:
    _, controller = _wire(qtbot)
    with pytest.raises(ValueError, match=r"non-empty"):
        controller.register_dataset("", tmp_path / "x.h5")


def test_register_plugin_rejects_empty_name(qtbot: object) -> None:
    _, controller = _wire(qtbot)
    with pytest.raises(ValueError, match=r"non-empty"):
        controller.register_plugin("", NumpyPairingNN())


# ---------------------------------------------------------------------
# Default setup (A2) — out-of-the-box dataset + plugin auto-register
# ---------------------------------------------------------------------


def test_register_default_setup_adds_numpy_pairing_nn(qtbot: object) -> None:
    """Out-of-the-box plugin: NumpyPairingNN."""
    panel, controller = _wire(qtbot)
    n_ds, n_pl = controller.register_default_setup()
    assert n_ds == 0
    assert n_pl == 1
    assert panel.plugin_combo().findText("numpy_pairing_nn") >= 0


def test_register_default_setup_scans_datasets_root(qtbot: object, tmp_path: Path) -> None:
    """Scanning <root>/*.h5 registers every dataset under its stem."""
    ds_a = _build_identity_dataset(tmp_path)  # tmp_path/identity.h5
    panel, controller = _wire(qtbot)
    n_ds, n_pl = controller.register_default_setup(datasets_root=tmp_path)
    assert n_ds == 1
    assert n_pl == 1
    assert panel.dataset_combo().findText("identity") >= 0
    assert ds_a.is_file()  # sanity: scanned file still exists


def test_register_default_setup_missing_root_is_skip(qtbot: object, tmp_path: Path) -> None:
    panel, controller = _wire(qtbot)
    n_ds, _ = controller.register_default_setup(datasets_root=tmp_path / "ghost")
    assert n_ds == 0
    assert panel.dataset_combo().count() == 1  # only the (none) placeholder


def test_register_default_setup_builtin_plugins_false(qtbot: object) -> None:
    panel, controller = _wire(qtbot)
    n_ds, n_pl = controller.register_default_setup(builtin_plugins=False)
    assert n_ds == 0
    assert n_pl == 0
    assert panel.plugin_combo().findText("numpy_pairing_nn") < 0


def test_register_default_setup_does_not_double_register(qtbot: object) -> None:
    panel, controller = _wire(qtbot)
    controller.register_default_setup()
    _n_ds, n_pl = controller.register_default_setup()
    assert n_pl == 0  # second call sees the existing plugin and skips
    # combo still has exactly one numpy_pairing_nn entry
    assert (
        sum(
            1
            for i in range(panel.plugin_combo().count())
            if panel.plugin_combo().itemText(i) == "numpy_pairing_nn"
        )
        == 1
    )


# ---------------------------------------------------------------------
# Refresh (signal wire + new files picked up)
# ---------------------------------------------------------------------


def test_refresh_datasets_picks_up_new_h5_files(qtbot: object, tmp_path: Path) -> None:
    """Files dropped under datasets_root *after* register_default_setup
    appear in the combo on refresh.
    """
    panel, controller = _wire(qtbot)
    controller.register_default_setup(datasets_root=tmp_path)
    assert panel.dataset_combo().findText("identity") < 0
    # Build the dataset *after* the initial register; that's the real
    # flow surfaced by MVP_GUIDE § 5.2 + § 5.4 (Step 1 -> Step 2).
    _build_identity_dataset(tmp_path)
    controller.refresh_datasets()
    assert panel.dataset_combo().findText("identity") >= 0


def test_refresh_datasets_returns_total_count(qtbot: object, tmp_path: Path) -> None:
    _, controller = _wire(qtbot)
    controller.register_default_setup(datasets_root=tmp_path)
    _build_identity_dataset(tmp_path)
    n = controller.refresh_datasets()
    assert n == 1


def test_refresh_datasets_without_remembered_root_is_noop(qtbot: object) -> None:
    """register_default_setup was never called, so refresh has no
    root to scan and returns the current registry size.
    """
    panel, controller = _wire(qtbot)
    assert controller.refresh_datasets() == 0
    assert panel.dataset_combo().count() == 1  # placeholder only


def test_refresh_requested_signal_drives_controller(qtbot: object, tmp_path: Path) -> None:
    """Manual Refresh button (panel signal) re-scans the same root."""
    panel, controller = _wire(qtbot)
    controller.register_default_setup(datasets_root=tmp_path)
    _build_identity_dataset(tmp_path)
    panel.refresh_requested.emit()
    assert panel.dataset_combo().findText("identity") >= 0


# ---------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------


def test_run_eval_on_identity_dataset_reports_zero_loss(qtbot: object, tmp_path: Path) -> None:
    ds = _build_identity_dataset(tmp_path)
    panel, controller = _wire(
        qtbot, datasets={"identity": ds}, plugins={"baseline": NumpyPairingNN()}
    )
    assert controller is not None
    _select(panel.dataset_combo, "identity")
    _select(panel.plugin_combo, "baseline")
    panel.run_eval_requested.emit()
    assert _rmse_cell(panel) == "0.000"


def test_run_eval_on_wrong_dataset_reports_unit_loss(qtbot: object, tmp_path: Path) -> None:
    ds = _build_wrong_dataset(tmp_path)
    panel, controller = _wire(qtbot, datasets={"wrong": ds}, plugins={"baseline": NumpyPairingNN()})
    assert controller is not None
    _select(panel.dataset_combo, "wrong")
    _select(panel.plugin_combo, "baseline")
    panel.run_eval_requested.emit()
    assert _rmse_cell(panel) == "1.000"


def test_run_eval_without_dataset_emits_error(qtbot: object) -> None:
    panel, controller = _wire(qtbot, plugins={"baseline": NumpyPairingNN()})
    assert controller is not None
    _select(panel.plugin_combo, "baseline")
    panel.run_eval_requested.emit()
    assert "err" in _rmse_cell(panel)


def test_run_eval_without_plugin_emits_error(qtbot: object, tmp_path: Path) -> None:
    ds = _build_identity_dataset(tmp_path)
    panel, controller = _wire(qtbot, datasets={"identity": ds})
    assert controller is not None
    _select(panel.dataset_combo, "identity")
    panel.run_eval_requested.emit()
    assert "err" in _rmse_cell(panel)


def test_run_eval_recovers_after_initial_error(qtbot: object, tmp_path: Path) -> None:
    """Selecting a valid dataset after an error must overwrite the error
    cell with the new RMSE.
    """
    ds = _build_identity_dataset(tmp_path)
    panel, controller = _wire(
        qtbot, datasets={"identity": ds}, plugins={"baseline": NumpyPairingNN()}
    )
    assert controller is not None
    # First trigger an error (no dataset selected).
    _select(panel.plugin_combo, "baseline")
    panel.run_eval_requested.emit()
    assert "err" in _rmse_cell(panel)
    # Then select the dataset and rerun.
    _select(panel.dataset_combo, "identity")
    panel.run_eval_requested.emit()
    assert _rmse_cell(panel) == "0.000"


def test_export_report_signal_is_handled_without_crash(qtbot: object) -> None:
    """The stub controller must accept the export signal silently."""
    panel, controller = _wire(qtbot)
    assert controller is not None
    panel.export_report_requested.emit()
    # No assertion; success = no exception.
