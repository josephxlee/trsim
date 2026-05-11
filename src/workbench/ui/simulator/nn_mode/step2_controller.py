"""Step 2 Evaluation controller (Phase 6 후속, plan/07 § 7.6).

Mirrors :class:`workbench.ui.simulator.nn_mode.step1_controller.NNStep1Controller`
on the Step 2 panel: wires ``run_eval_requested`` to
:func:`workbench.app.nn.pairing_loss` against a registered dataset +
plugin pair, then writes the resulting loss into the panel's 4-error
table under the ``"Pairing"`` row.

The MVP is single-dataset / single-plugin. Phase 7+ (full plan/07
§ 7.6 multi-Variant evaluation) layers training / dev / test split
selection on top — but the wiring contract (controller listens to
``run_eval_requested``, populates the table, logs status) stays the
same so that swap is incremental.

The controller never touches Qt outside the panel API; unit tests
run without a real event loop.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from workbench.app.nn import pairing_loss
from workbench.app.nn.evaluator import _PairingPredictor
from workbench.ui.simulator.nn_mode.step2_eval import Step2EvalPanel

_SENTINEL_NONE = "(none)"


class NNStep2Controller:
    """Glue between the Step 2 panel and :func:`pairing_loss`.

    Attributes:
        panel: The :class:`Step2EvalPanel` this controller drives.
        datasets: Mapping from combo-box dataset name to HDF5 path.
        plugins: Mapping from combo-box plugin name to predictor.

    The constructor populates the panel combos in deterministic
    order (``sorted(...)``) and connects the run / export signals.
    Subsequent ``set_datasets`` / ``set_plugins`` calls re-populate
    the combos without clearing the table.
    """

    def __init__(
        self,
        panel: Step2EvalPanel,
        *,
        datasets: Mapping[str, Path] | None = None,
        plugins: Mapping[str, _PairingPredictor] | None = None,
    ) -> None:
        self.panel = panel
        self._datasets: dict[str, Path] = dict(datasets or {})
        self._plugins: dict[str, _PairingPredictor] = dict(plugins or {})

        self._refresh_combos()

        self.panel.run_eval_requested.connect(self._on_run_eval)
        self.panel.export_report_requested.connect(self._on_export_report)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_dataset(self, name: str, path: Path) -> None:
        if not name:
            msg = "dataset name must be non-empty"
            raise ValueError(msg)
        self._datasets[name] = path
        self._refresh_combos()

    def register_plugin(self, name: str, plugin: _PairingPredictor) -> None:
        if not name:
            msg = "plugin name must be non-empty"
            raise ValueError(msg)
        self._plugins[name] = plugin
        self._refresh_combos()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_run_eval(self) -> None:
        dataset_name = self.panel.dataset_combo().currentText()
        plugin_name = self.panel.plugin_combo().currentText()

        if dataset_name in (_SENTINEL_NONE, ""):
            self._reset_pairing_row_with_error("select a dataset")
            return
        if plugin_name in (_SENTINEL_NONE, ""):
            self._reset_pairing_row_with_error("select an NN plugin")
            return

        dataset_path = self._datasets.get(dataset_name)
        plugin = self._plugins.get(plugin_name)
        if dataset_path is None or plugin is None:
            self._reset_pairing_row_with_error("registry entry missing")
            return

        try:
            loss = pairing_loss(plugin, dataset_path)
        except (FileNotFoundError, ValueError) as exc:
            self._reset_pairing_row_with_error(f"eval failed: {exc}")
            return

        # MVP mapping: pairing_loss (1 - accuracy) lives in the RMSE
        # column; Bias is 0.0 for a classification task without a
        # natural bias scalar. Full plan/07 § 7.6 split into
        # train/dev/test rows lands in a later sub-step.
        self.panel.set_error_metrics("Pairing", rmse=loss, bias=0.0)

    def _on_export_report(self) -> None:
        # Stub for plan/07 § 7.6.5 report-export flow. The wiring is
        # in place; the actual file dialog + TOML writer lands when
        # the export schema is fixed.
        pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _refresh_combos(self) -> None:
        self.panel.set_datasets(sorted(self._datasets.keys()))
        self.panel.set_plugins(sorted(self._plugins.keys()))

    def _reset_pairing_row_with_error(self, message: str) -> None:
        from PySide6.QtWidgets import QTableWidgetItem

        table = self.panel.error_table()
        table.setItem(0, 1, QTableWidgetItem(f"err: {message}"))
        table.setItem(0, 2, QTableWidgetItem("--"))
