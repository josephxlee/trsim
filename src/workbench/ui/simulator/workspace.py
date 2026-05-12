"""Simulator Workspace shell (Phase 4.9 + 4.10 + task D, plan/05 § 5.2).

Phase 4.10 layout:

::

    +---------------+--------------------+--------------+--------------+
    | PluginManager | Scene3D            | Scope POV    | Properties   |
    |               +--------------------+              |              |
    |               | FFT | RangeDoppler |              |              |
    +---------------+--------------------+--------------+--------------+
    | Tabs: Run | Stage I/O | Profiler | [DLC panels...]                |
    +-----------------------------------------------------------------+

Live PyVista canvas in Scene3D + cross-hair canvas in Scope arrive
in Phase 4.10.x.

Task D adds optional DLC panel mounting via :class:`workbench.ui.
panel_registry.PanelRegistry`. Plugins registered under workspace
``"simulator"`` are instantiated lazily and appended to the bottom
tab widget. The label is ``"[DLC] <pkg>: <ClassName>"`` so the user
can tell built-in panels apart from third-party ones at a glance.
Mount errors (constructor raised, plugin returned a non-widget) are
captured in :attr:`SimulatorWorkspace.dlc_mount_errors` instead of
aborting workspace creation.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.nn_training import NNTrainingController, TrainingPanel
from workbench.ui.panel_registry import PanelRegistration, PanelRegistry
from workbench.ui.simulator.nn_mode import Step1DatasetPanel, Step2EvalPanel
from workbench.ui.simulator.nn_mode.step1_controller import NNStep1Controller
from workbench.ui.simulator.nn_mode.step2_controller import NNStep2Controller
from workbench.ui.simulator.panels import (
    FFTPanel,
    PluginManagerPanel,
    PropertiesPanel,
    RangeDopplerPanel,
    RunPanel,
    Scene3DPanel,
    ScopePOVPanel,
    StageIOPanel,
)
from workbench.ui.simulator.profiler_panel import ProfilerPanel


@dataclass(frozen=True, slots=True)
class DLCMountError:
    """One DLC panel that failed to mount on the Simulator workspace.

    Attributes:
        registration: The :class:`PanelRegistration` that triggered the
            failure (carries panel_class + source_package_id).
        message: Human-readable English failure reason.
    """

    registration: PanelRegistration
    message: str


class SimulatorWorkspace(QWidget):
    """Composite simulator view with eight runtime panels."""

    # Sentinel: tests pass ``nn_datasets_root=None`` to suppress the
    # ``<cwd>/datasets`` auto-scan and keep the Step 2 dataset combo
    # empty. Production callers (``trsim ui``) leave the kwarg out so
    # the default cwd path is used.
    _NN_DATASETS_DEFAULT: object = object()

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        panel_registry: PanelRegistry | None = None,
        nn_datasets_root: Path | None | object = _NN_DATASETS_DEFAULT,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SimulatorWorkspace")
        if nn_datasets_root is self._NN_DATASETS_DEFAULT:
            self._nn_datasets_root: Path | None = Path.cwd() / "datasets"
        elif isinstance(nn_datasets_root, Path) or nn_datasets_root is None:
            self._nn_datasets_root = nn_datasets_root
        else:
            msg = "nn_datasets_root must be a Path or None"
            raise TypeError(msg)

        # Build panels.
        self._scene_3d_panel = Scene3DPanel(self)
        self._scope_panel = ScopePOVPanel(self)
        self._fft_panel = FFTPanel(self)
        self._range_doppler_panel = RangeDopplerPanel(self)
        self._run_panel = RunPanel(self)
        self._properties_panel = PropertiesPanel(self)
        self._plugin_manager_panel = PluginManagerPanel(self)
        self._stage_io_panel = StageIOPanel(self)
        self._profiler_panel = ProfilerPanel(self)

        # Spectra row (FFT | RD).
        spectra = QSplitter(Qt.Orientation.Horizontal, self)
        spectra.setObjectName("SimulatorSpectraSplitter")
        spectra.setChildrenCollapsible(False)
        spectra.addWidget(self._fft_panel)
        spectra.addWidget(self._range_doppler_panel)
        spectra.setSizes([300, 300])

        # Center column - Scene3D on top, Spectra row below.
        center = QSplitter(Qt.Orientation.Vertical, self)
        center.setObjectName("SimulatorCenterSplitter")
        center.setChildrenCollapsible(False)
        center.addWidget(self._scene_3d_panel)
        center.addWidget(spectra)
        center.setSizes([320, 220])

        # Top row - PluginManager | center | Scope | Properties.
        top_row = QSplitter(Qt.Orientation.Horizontal, self)
        top_row.setObjectName("SimulatorTopRowSplitter")
        top_row.setChildrenCollapsible(False)
        top_row.addWidget(self._plugin_manager_panel)
        top_row.addWidget(center)
        top_row.addWidget(self._scope_panel)
        top_row.addWidget(self._properties_panel)
        top_row.setStretchFactor(0, 0)
        top_row.setStretchFactor(1, 1)
        top_row.setStretchFactor(2, 0)
        top_row.setStretchFactor(3, 0)
        top_row.setSizes([240, 640, 240, 240])

        # NN-mode panels (plan/05 § 5.1 principle 6, plan/07 § 7.4 / § 7.5).
        # Phase 4.11 shipped these widgets + controllers; this mount
        # site is where the Simulator workspace finally surfaces them.
        # A future sub-step can wrap the three NN tabs in a top-level
        # "Mode" selector (DSP vs NN Development); for the MVP they sit
        # alongside the runtime tabs.
        self._nn_step1_panel = Step1DatasetPanel(self)
        self._nn_step1_controller = NNStep1Controller(self._nn_step1_panel)
        self._nn_step2_panel = Step2EvalPanel(self)
        self._nn_step2_controller = NNStep2Controller(self._nn_step2_panel)
        # Default Step 2 setup: scan <cwd>/datasets/*.h5 (or whatever
        # path the caller injected) + register NumpyPairingNN so the
        # panel is usable without the user having to call register_*
        # by hand.
        self._nn_step2_controller.register_default_setup(datasets_root=self._nn_datasets_root)
        # Auto-refresh Step 2 when Step 1 finishes a build — the new
        # ``.h5`` files appear in the dataset combo without a restart.
        self._nn_step1_panel.build_completed.connect(self._nn_step2_controller.refresh_datasets)
        self._nn_training_panel = TrainingPanel(self)
        self._nn_training_controller = NNTrainingController(self._nn_training_panel)

        # Bottom tabs - Run / Stage I/O / Profiler / NN Step 1 / NN Step 2
        # / NN Training. DLC plugin panels (Task D) append after these.
        bottom_tabs = QTabWidget(self)
        bottom_tabs.setObjectName("SimulatorBottomTabs")
        bottom_tabs.addTab(self._run_panel, "Run")
        bottom_tabs.addTab(self._stage_io_panel, "Stage I/O")
        bottom_tabs.addTab(self._profiler_panel, "Profiler")
        bottom_tabs.addTab(self._nn_step1_panel, "NN Step 1")
        bottom_tabs.addTab(self._nn_step2_panel, "NN Step 2")
        bottom_tabs.addTab(self._nn_training_panel, "NN Training")

        outer = QSplitter(Qt.Orientation.Vertical, self)
        outer.setObjectName("SimulatorOuterSplitter")
        outer.setChildrenCollapsible(False)
        outer.addWidget(top_row)
        outer.addWidget(bottom_tabs)
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 0)
        outer.setSizes([520, 220])
        self._outer_splitter = outer
        self._top_splitter = top_row
        self._center_splitter = center
        self._spectra_splitter = spectra
        self._bottom_tabs = bottom_tabs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(outer)

        self._dlc_panels: list[QWidget] = []
        self._dlc_mount_errors: list[DLCMountError] = []
        if panel_registry is not None:
            self.mount_dlc_panels(panel_registry.get_panels_for_workspace("simulator"))

    # ------------------------------------------------------------------
    # DLC panel mounting (task D)
    # ------------------------------------------------------------------
    def mount_dlc_panels(self, registrations: Iterable[PanelRegistration]) -> int:
        """Instantiate every ``registration`` and append it as a bottom tab.

        The label format is ``"[DLC] <pkg>: <ClassName>"`` for plugin
        panels and ``"[DLC] <ClassName>"`` for built-in workspace tags
        with an empty package id.

        Mount failures (constructor raised, factory returned a non-
        :class:`QWidget`) are captured in :attr:`dlc_mount_errors`
        without aborting the loop — one broken DLC must not take down
        the whole Simulator workspace.

        Returns:
            Number of panels successfully appended.
        """
        added = 0
        for reg in registrations:
            try:
                widget = reg.panel_class(self)
            except Exception as exc:
                self._dlc_mount_errors.append(
                    DLCMountError(registration=reg, message=f"constructor failed: {exc}")
                )
                continue
            if not isinstance(widget, QWidget):
                self._dlc_mount_errors.append(
                    DLCMountError(
                        registration=reg,
                        message="panel_class did not return a QWidget instance",
                    )
                )
                continue
            label = _dlc_tab_label(reg)
            self._bottom_tabs.addTab(widget, label)
            self._dlc_panels.append(widget)
            added += 1
        return added

    @property
    def dlc_panels(self) -> tuple[QWidget, ...]:
        """Tuple of every DLC panel currently mounted (insertion order)."""
        return tuple(self._dlc_panels)

    @property
    def dlc_mount_errors(self) -> tuple[DLCMountError, ...]:
        """Tuple of DLC panels that failed to mount."""
        return tuple(self._dlc_mount_errors)

    # ------------------------------------------------------------------
    # Test helpers / Phase 5+ wiring
    # ------------------------------------------------------------------
    def fft_panel(self) -> FFTPanel:
        return self._fft_panel

    def range_doppler_panel(self) -> RangeDopplerPanel:
        return self._range_doppler_panel

    def run_panel(self) -> RunPanel:
        return self._run_panel

    def properties_panel(self) -> PropertiesPanel:
        return self._properties_panel

    def plugin_manager_panel(self) -> PluginManagerPanel:
        return self._plugin_manager_panel

    def stage_io_panel(self) -> StageIOPanel:
        return self._stage_io_panel

    def scene_3d_panel(self) -> Scene3DPanel:
        return self._scene_3d_panel

    def scope_pov_panel(self) -> ScopePOVPanel:
        return self._scope_panel

    def profiler_panel(self) -> ProfilerPanel:
        return self._profiler_panel

    def bottom_tabs(self) -> QTabWidget:
        return self._bottom_tabs

    # ------------------------------------------------------------------
    # NN-mode accessors (Phase 4.11 + MVP UI wire-up)
    # ------------------------------------------------------------------
    def nn_step1_panel(self) -> Step1DatasetPanel:
        return self._nn_step1_panel

    def nn_step1_controller(self) -> NNStep1Controller:
        return self._nn_step1_controller

    def nn_step2_panel(self) -> Step2EvalPanel:
        return self._nn_step2_panel

    def nn_step2_controller(self) -> NNStep2Controller:
        return self._nn_step2_controller

    def nn_training_panel(self) -> TrainingPanel:
        return self._nn_training_panel

    def nn_training_controller(self) -> NNTrainingController:
        return self._nn_training_controller


def _dlc_tab_label(reg: PanelRegistration) -> str:
    name = reg.panel_class.__name__
    if reg.source_package_id:
        return f"[DLC] {reg.source_package_id}: {name}"
    return f"[DLC] {name}"
