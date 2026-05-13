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

from workbench.app.nn import NumpyPairingNN, pairing_loss
from workbench.app.nn.evaluator import (
    _PairingPredictor,
    classifier_loss,
    predictor_loss,
    tracker_loss,
)
from workbench.ui.simulator.nn_mode.step2_eval import ERROR_CATEGORIES, Step2EvalPanel

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
        # Last datasets_root used by ``register_default_setup`` so a
        # later :meth:`refresh_datasets` can re-scan the same path
        # without the caller having to remember it.
        self._last_datasets_root: Path | None = None

        self._refresh_combos()

        self.panel.run_eval_requested.connect(self._on_run_eval)
        self.panel.export_report_requested.connect(self._on_export_report)
        if hasattr(self.panel, "refresh_requested"):
            self.panel.refresh_requested.connect(self._on_refresh_clicked)

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

    def register_default_setup(
        self,
        *,
        datasets_root: Path | None = None,
        builtin_plugins: bool = True,
    ) -> tuple[int, int]:
        """Populate combos with sensible defaults so the panel is usable
        out of the box.

        Args:
            datasets_root: Directory scanned for ``*.h5`` datasets. Each
                file is registered under its stem (``pairing_variant_A``
                → key ``"pairing_variant_A"``). ``None`` or a missing
                directory skips the dataset scan.
            builtin_plugins: When ``True`` (default), registers the
                workbench-provided :class:`NumpyPairingNN` baseline
                under ``"numpy_pairing_nn"``. Disable in tests that
                want a strictly empty plugin registry.

        Returns:
            ``(n_datasets_registered, n_plugins_registered)`` for the
            caller to log / sanity-check.
        """
        self._last_datasets_root = datasets_root

        n_ds = 0
        if datasets_root is not None and datasets_root.is_dir():
            for entry in sorted(datasets_root.glob("*.h5")):
                self._datasets[entry.stem] = entry
                n_ds += 1

        n_pl = 0
        if builtin_plugins and "numpy_pairing_nn" not in self._plugins:
            self._plugins["numpy_pairing_nn"] = NumpyPairingNN()
            n_pl += 1

        if n_ds or n_pl:
            self._refresh_combos()
        return n_ds, n_pl

    def refresh_datasets(self) -> int:
        """Re-scan the last ``datasets_root`` from
        :meth:`register_default_setup` and pick up any new ``*.h5``
        files. Existing dataset entries with the same stem are
        overwritten (path may have moved); plugin registry is left
        alone. Returns the count of dataset entries after the refresh.
        """
        if self._last_datasets_root is None or not self._last_datasets_root.is_dir():
            return len(self._datasets)
        for entry in sorted(self._last_datasets_root.glob("*.h5")):
            self._datasets[entry.stem] = entry
        self._refresh_combos()
        return len(self._datasets)

    # ------------------------------------------------------------------
    # Signal hooks
    # ------------------------------------------------------------------

    def _on_refresh_clicked(self) -> None:
        self.refresh_datasets()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_run_eval(self) -> None:
        dataset_name = self.panel.dataset_combo().currentText()
        plugin_name = self.panel.plugin_combo().currentText()

        if dataset_name in (_SENTINEL_NONE, ""):
            for cat in ERROR_CATEGORIES:
                self._reset_row_with_error(cat, "select a dataset")
            return
        if plugin_name in (_SENTINEL_NONE, ""):
            for cat in ERROR_CATEGORIES:
                self._reset_row_with_error(cat, "select an NN plugin")
            return

        dataset_path = self._datasets.get(dataset_name)
        plugin = self._plugins.get(plugin_name)
        if dataset_path is None or plugin is None:
            for cat in ERROR_CATEGORIES:
                self._reset_row_with_error(cat, "registry entry missing")
            return

        # A1-c: per-category dispatch. Pairing is the only category with
        # a wired loss function for the MVP; Tracker / Predictor /
        # Classifier raise NotImplementedError and surface ``n/a`` so the
        # UI explicitly distinguishes "no plugin support yet" from the
        # default "--" placeholder. Once a TrackerNNPlugin etc. ships,
        # only ``app/nn/evaluator.py`` changes — the controller wiring
        # stays the same.
        for cat in ERROR_CATEGORIES:
            try:
                loss = self._eval_category(cat, plugin, dataset_path)
            except NotImplementedError:
                self._reset_row_with_error(cat, "n/a (plugin unsupported)")
                continue
            except (FileNotFoundError, ValueError) as exc:
                self._reset_row_with_error(cat, f"eval failed: {exc}")
                continue
            self.panel.set_error_metrics(cat, rmse=loss, bias=0.0)

    @staticmethod
    def _eval_category(category: str, plugin: _PairingPredictor, dataset_path: Path) -> float:
        """Dispatch the per-category loss function.

        Pairing is wired to :func:`pairing_loss`; the other three call
        the corresponding stub in ``app/nn/evaluator.py`` which raises
        NotImplementedError (the caller turns that into ``n/a``).
        """
        if category == "Pairing":
            return pairing_loss(plugin, dataset_path)
        if category == "Tracker":
            return tracker_loss(plugin, dataset_path)
        if category == "Predictor":
            return predictor_loss(plugin, dataset_path)
        if category == "Classifier":
            return classifier_loss(plugin, dataset_path)
        msg = f"unknown error category {category!r}"
        raise ValueError(msg)

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
        """Backwards-compat alias for the Pairing-only error path used
        by older tests. Preserved so the public surface doesn't break.
        """
        self._reset_row_with_error("Pairing", message)

    def _reset_row_with_error(self, category: str, message: str) -> None:
        """Write an error / status marker into ``category``'s row.

        ``n/a`` style messages stay terse (no ``err:`` prefix) so the
        table reads as data, not a debug log. Genuine failures keep
        the ``err:`` prefix from the legacy Pairing path.
        """
        from PySide6.QtWidgets import QTableWidgetItem

        table = self.panel.error_table()
        if category not in ERROR_CATEGORIES:
            msg = f"unknown error category {category!r}"
            raise ValueError(msg)
        row = ERROR_CATEGORIES.index(category)
        prefix = "" if message.startswith("n/a") else "err: "
        table.setItem(row, 1, QTableWidgetItem(f"{prefix}{message}"))
        table.setItem(row, 2, QTableWidgetItem("--"))
