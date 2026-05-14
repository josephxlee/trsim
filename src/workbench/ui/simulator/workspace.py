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
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from workbench.app.simulator import DEFAULT_PLUGIN_NAMES
from workbench.domain.types import SpeedMultiplier
from workbench.ui.nn_training import NNTrainingController, TrainingPanel
from workbench.ui.panel_registry import PanelRegistration, PanelRegistry
from workbench.ui.simulator.fft_controller import SimulatorFFTController
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
from workbench.ui.simulator.primary_target_controller import (
    SimulatorPrimaryTargetController,
)
from workbench.ui.simulator.profiler_panel import ProfilerPanel
from workbench.ui.simulator.rd_controller import SimulatorRDController
from workbench.ui.simulator.run_controller import SimulatorRunController
from workbench.ui.simulator.scene_controller import SimulatorSceneController
from workbench.ui.simulator.stage_io_controller import SimulatorStageIOController
from workbench.ui.widgets import DetachableTabWidget


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
        run_tick_interval_ms: int = 33,
        autostart_run_timer: bool = True,
        enable_3d_viewer: bool = True,
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
        self._scene_3d_panel = Scene3DPanel(self, enable_3d_viewer=enable_3d_viewer)
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
        # Stretch factors preserve the column-width ratio when the
        # window is maximised. Center (FFT / RD / Scene 3D) takes the
        # largest share; the three flanking columns grow proportionally
        # at 1:3:1:1. Without non-zero stretch on the flanks, they stay
        # at the initial pixel sizes and the center column eats every
        # extra pixel — visibly wrong on 1920+ resolutions.
        top_row = QSplitter(Qt.Orientation.Horizontal, self)
        top_row.setObjectName("SimulatorTopRowSplitter")
        top_row.setChildrenCollapsible(False)
        top_row.addWidget(self._plugin_manager_panel)
        top_row.addWidget(center)
        top_row.addWidget(self._scope_panel)
        top_row.addWidget(self._properties_panel)
        top_row.setStretchFactor(0, 1)
        top_row.setStretchFactor(1, 3)
        top_row.setStretchFactor(2, 1)
        top_row.setStretchFactor(3, 1)
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
        # DetachableTabWidget lets the user right-click a tab and pop
        # it into a floating top-level window; closing the window
        # re-inserts the tab.
        bottom_tabs = DetachableTabWidget(self)
        bottom_tabs.setObjectName("SimulatorBottomTabs")
        bottom_tabs.addTab(self._run_panel, "Run")
        bottom_tabs.addTab(self._stage_io_panel, "Stage I/O")
        bottom_tabs.addTab(self._profiler_panel, "Profiler")
        bottom_tabs.addTab(self._nn_step1_panel, "NN Step 1")
        bottom_tabs.addTab(self._nn_step2_panel, "NN Step 2")
        bottom_tabs.addTab(self._nn_training_panel, "NN Training")

        # Outer split: top_row (8 panel) above, bottom_tabs below.
        # Both stretch so a maximised window grows both areas
        # proportionally (top : bottom = 3 : 1, matching the default
        # 520 : 220 pixel ratio).
        outer = QSplitter(Qt.Orientation.Vertical, self)
        outer.setObjectName("SimulatorOuterSplitter")
        outer.setChildrenCollapsible(False)
        outer.addWidget(top_row)
        outer.addWidget(bottom_tabs)
        outer.setStretchFactor(0, 3)
        outer.setStretchFactor(1, 1)
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

        # Phase 4 L1 — Run panel live sim_time / frame_id readouts. The
        # controller owns its own SimulationClock + 16 ms QTimer.
        # Tests pass ``autostart_run_timer=False`` for deterministic
        # tick control.
        self._run_controller = SimulatorRunController(
            run_panel=self._run_panel,
            tick_interval_ms=run_tick_interval_ms,
            autostart_timer=autostart_run_timer,
            parent=self,
        )

        # Phase 4 L2 — FFT panel live spectrum binding. The controller
        # listens to ``run_controller.tick_completed`` and repaints the
        # FFT curves + peak markers via a deterministic
        # ``MockSpectrumGenerator``. Real Pipeline binding lands later.
        self._fft_controller = SimulatorFFTController(
            fft_panel=self._fft_panel,
            run_controller=self._run_controller,
            parent=self,
        )

        # Phase 4 L3 — Range-Doppler panel live heatmap binding. Same
        # tick_completed wiring as L2; the deterministic
        # ``MockRangeDopplerGenerator`` paints a 2-D Gaussian blob that
        # moves along range + doppler axes over sim time.
        self._rd_controller = SimulatorRDController(
            rd_panel=self._range_doppler_panel,
            run_controller=self._run_controller,
            parent=self,
        )

        # Phase 4 L4 — Scene 3D panel live PyVista actors binding. The
        # ``MockSceneGenerator`` paints a fixed radar at the origin
        # plus a single target on a horizontal circular orbit. The
        # Scene3DPanel runs in headless mode (``enable_3d_viewer=
        # False``) skips actor creation; the controller still emits
        # frames so the status label stays in sync.
        self._scene_controller = SimulatorSceneController(
            scene_panel=self._scene_3d_panel,
            run_controller=self._run_controller,
            parent=self,
        )

        # Phase 4 L5 — Stage I/O panel live binding + Plugin Manager
        # default plugin seed. ``MockStageIOGenerator`` paints one
        # IN/OUT row per pipeline stage with counts that move with
        # sim_t_s; the panel's Record toggle drives the controller's
        # in-memory log. PluginManager rows are seeded with the
        # ``DEFAULT_PLUGIN_NAMES`` placeholders so the user sees
        # something non-empty out of the box.
        for stage, names in DEFAULT_PLUGIN_NAMES.items():
            self._plugin_manager_panel.set_stage_plugins(stage, list(names))
        self._stage_io_controller = SimulatorStageIOController(
            stage_io_panel=self._stage_io_panel,
            run_controller=self._run_controller,
            parent=self,
        )

        # Phase 4 L6 — Scope POV cross-hair + Properties primary-target
        # form. Both panels share one MockPrimaryTargetGenerator so the
        # scope and the form always agree on what the radar is looking
        # at. The Scope panel's cross-hair is now a live pyqtgraph
        # scatter point in normalized [-1, 1] x [-1, 1] coordinates.
        self._primary_target_controller = SimulatorPrimaryTargetController(
            scope_panel=self._scope_panel,
            properties_panel=self._properties_panel,
            run_controller=self._run_controller,
            parent=self,
        )

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

    def bottom_tabs(self) -> DetachableTabWidget:
        return self._bottom_tabs

    # ------------------------------------------------------------------
    # Phase 4 L1 / L2 — Run + FFT controllers (live sim_time / spectrum)
    # ------------------------------------------------------------------
    def run_controller(self) -> SimulatorRunController:
        return self._run_controller

    def fft_controller(self) -> SimulatorFFTController:
        return self._fft_controller

    def rd_controller(self) -> SimulatorRDController:
        return self._rd_controller

    def scene_controller(self) -> SimulatorSceneController:
        return self._scene_controller

    def stage_io_controller(self) -> SimulatorStageIOController:
        return self._stage_io_controller

    def primary_target_controller(self) -> SimulatorPrimaryTargetController:
        return self._primary_target_controller

    # ------------------------------------------------------------------
    # Phase 4 P5 — Manual pointing arrow-key handler
    # ------------------------------------------------------------------
    #: Per-keypress azimuth nudge [deg]. Used by the workspace's
    #: ``keyPressEvent`` to drive the manual pointing accumulator.
    MANUAL_AZ_STEP_DEG: float = 0.5
    #: Per-keypress elevation nudge [deg].
    MANUAL_EL_STEP_DEG: float = 0.5

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 — Qt API
        """Map arrow keys to the primary-target manual pointing offset.

        - Left / Right -> azimuth -/+ ``MANUAL_AZ_STEP_DEG`` deg.
        - Down / Up    -> elevation -/+ ``MANUAL_EL_STEP_DEG`` deg.
        - Home / 0     -> reset the accumulator back to zero.

        Modifier keys (Shift / Ctrl) are intentionally ignored — the
        Command palette + MainMenuBar already own every modifier-bearing
        shortcut, and the user discovers the arrow-key nudge as the
        "natural" pointing input.
        """
        key = event.key()
        if key == Qt.Key.Key_Left:
            self._primary_target_controller.add_manual_offset(
                d_az_deg=-self.MANUAL_AZ_STEP_DEG, d_el_deg=0.0
            )
            event.accept()
            return
        if key == Qt.Key.Key_Right:
            self._primary_target_controller.add_manual_offset(
                d_az_deg=self.MANUAL_AZ_STEP_DEG, d_el_deg=0.0
            )
            event.accept()
            return
        if key == Qt.Key.Key_Down:
            self._primary_target_controller.add_manual_offset(
                d_az_deg=0.0, d_el_deg=-self.MANUAL_EL_STEP_DEG
            )
            event.accept()
            return
        if key == Qt.Key.Key_Up:
            self._primary_target_controller.add_manual_offset(
                d_az_deg=0.0, d_el_deg=self.MANUAL_EL_STEP_DEG
            )
            event.accept()
            return
        if key in (Qt.Key.Key_Home, Qt.Key.Key_0):
            self._primary_target_controller.reset_manual_offset()
            event.accept()
            return
        super().keyPressEvent(event)

    def sim_play(self) -> None:
        """Toolbar / hook entry — start simulation clock."""
        self._run_controller.play()

    def sim_pause(self) -> None:
        self._run_controller.pause()

    def sim_stop(self) -> None:
        self._run_controller.stop()

    def sim_set_speed(self, multiplier: int) -> None:
        """Map toolbar speed int (1/2/4/8) to :class:`SpeedMultiplier`."""
        self._run_controller.set_speed(SpeedMultiplier(multiplier))

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
