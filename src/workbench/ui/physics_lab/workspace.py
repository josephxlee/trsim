"""Physics Lab Workspace shell (PL-A + PL-B, plan/19 § 19.5).

The 3rd top-level workspace. plan/19 frames it as TRsim's flagship
differentiator: a Bret-Victor-style environment where the physics
formulas backing the simulator are proven, visually verified, and
(eventually) user-extended.

Layout (PL-B, plan/19 § 19.5.1):

::

    +------------+-----------------------+--------------+
    | Library    | Code (read-only)      | Parameters   |
    | (Tests /   +-----------------------+              |
    |  Models /  | Visualization         | (auto        |
    |  Experi-   | (PyVista 3D / 2D)     |  sliders)    |
    |  ments)    |                       |              |
    +------------+-----------------------+--------------+
    | Time controls (Play / Pause / Stop / Frame slider) |
    +----------------------------------------------------+

PL-A ships:

- The :class:`PhysicsLabWorkspace` widget that the main_window mounts
  alongside Editor and Simulator.
- 3-pane QSplitter skeleton + 4 placeholder panes (Library /
  Code / Viz / Parameters) and a bottom Time controls bar.
- Public accessor methods (``library_panel`` / ``code_panel`` /
  ``viz_panel`` / ``parameters_panel`` / ``time_controls``) so PL-D
  and later sub-steps can swap real widgets in without changing the
  workspace shell.

PL-C swaps in real Test Object listings + analytic-RCS code preview.
PL-D wires the time controls to a real :class:`PhysicsClock` driving
the Bouncing Ball demo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from workbench.domain.physics_lab import (
    TIME_MODES_IN_DISPLAY_ORDER,
    MeasuredDataset,
    SavedExperiment,
    TimeMode,
    ValidationMetrics,
    list_measured_datasets,
    list_papers,
    list_saved_experiments,
    write_saved_experiment,
)
from workbench.ui.physics_lab.bouncing_ball_demo import (
    BouncingBallController,
    BouncingBallPlot,
    CodePreview,
    LibraryWidget,
    ParametersWidget,
)
from workbench.ui.physics_lab.test_object_view import TestObject3DPanel


class _Placeholder(QWidget):
    """Centred title + caption widget so each pane has a clear identity."""

    def __init__(self, title: str, caption: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(f"PhysicsLab_{title.replace(' ', '_')}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        title_label = QLabel(title, self)
        title_label.setObjectName(f"PhysicsLab_{title.replace(' ', '_')}_Title")
        title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        caption_label = QLabel(caption, self)
        caption_label.setObjectName(f"PhysicsLab_{title.replace(' ', '_')}_Caption")
        caption_label.setWordWrap(True)
        caption_label.setStyleSheet("color: #777;")
        layout.addWidget(title_label)
        layout.addWidget(caption_label)
        layout.addStretch(1)


class _TimeControls(QWidget):
    """Bottom strip with Play/Pause/Stop on row 1 and a Frame slider +
    step-by-step buttons on row 2 (PL-9.1b, plan/19 § 19.5.4).

    PL-D wires the Play row to :class:`PhysicsClock`; PL-9.1b adds the
    Frame slider, step-forward / step-back buttons and the
    ``frame N / max`` readout that the controller drives.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLabTimeControls")
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(4)

        # ---- Row 1: Mode | Play / Pause / Stop + status label.
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        self._mode_label = QLabel("Mode:", self)
        self._mode_label.setObjectName("PhysicsLabModeLabel")
        self._mode_combo = QComboBox(self)
        self._mode_combo.setObjectName("PhysicsLabModeCombo")
        for mode in TIME_MODES_IN_DISPLAY_ORDER:
            self._mode_combo.addItem(mode.value)
        self._mode_combo.setCurrentText(TimeMode.RUN.value)
        row1.addWidget(self._mode_label)
        row1.addWidget(self._mode_combo)
        row1.addSpacing(8)
        self._play_btn = QPushButton("Play", self)
        self._play_btn.setObjectName("PhysicsLabPlayBtn")
        self._pause_btn = QPushButton("Pause", self)
        self._pause_btn.setObjectName("PhysicsLabPauseBtn")
        self._stop_btn = QPushButton("Stop", self)
        self._stop_btn.setObjectName("PhysicsLabStopBtn")
        self._status = QLabel("idle", self)
        self._status.setObjectName("PhysicsLabTimeStatus")
        for btn in (self._play_btn, self._pause_btn, self._stop_btn):
            row1.addWidget(btn)
        row1.addSpacing(12)
        row1.addWidget(self._status, 1)
        root.addLayout(row1)

        # ---- Row 2: Step back | Frame slider | Step forward | readout.
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        self._step_back_btn = QPushButton("Prev", self)
        self._step_back_btn.setObjectName("PhysicsLabStepBackBtn")
        self._step_back_btn.setToolTip("Step one frame backward")
        self._step_back_btn.setFixedWidth(56)
        self._step_back_btn.setEnabled(False)
        self._frame_slider = QSlider(Qt.Orientation.Horizontal, self)
        self._frame_slider.setObjectName("PhysicsLabFrameSlider")
        self._frame_slider.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._frame_slider.setRange(0, 0)
        self._step_fwd_btn = QPushButton("Next", self)
        self._step_fwd_btn.setObjectName("PhysicsLabStepForwardBtn")
        self._step_fwd_btn.setToolTip("Step one frame forward")
        self._step_fwd_btn.setFixedWidth(56)
        self._frame_readout = QLabel("frame 0 / 0", self)
        self._frame_readout.setObjectName("PhysicsLabFrameReadout")
        self._frame_readout.setFixedWidth(110)
        row2.addWidget(self._step_back_btn)
        row2.addWidget(self._frame_slider, 1)
        row2.addWidget(self._step_fwd_btn)
        row2.addWidget(self._frame_readout)
        root.addLayout(row2)

    def play_button(self) -> QPushButton:
        return self._play_btn

    def pause_button(self) -> QPushButton:
        return self._pause_btn

    def stop_button(self) -> QPushButton:
        return self._stop_btn

    def status_label(self) -> QLabel:
        return self._status

    def step_back_button(self) -> QPushButton:
        return self._step_back_btn

    def step_forward_button(self) -> QPushButton:
        return self._step_fwd_btn

    def frame_slider(self) -> QSlider:
        return self._frame_slider

    def frame_readout(self) -> QLabel:
        return self._frame_readout

    def mode_combo(self) -> QComboBox:
        return self._mode_combo


class PhysicsLabWorkspace(QWidget):
    """3-pane Physics Lab shell mounted alongside Editor / Simulator.

    The ``enable_3d_viewer`` kwarg (default ``True``) decides whether
    a :class:`TestObject3DPanel` is added to the viz QStackedWidget.
    Production code paths leave it on; pytest passes ``False`` because
    each new ``QtInteractor`` instance plus pytest-qt's event-processing
    interaction triggers a ``vtkWin32OpenGLRenderWindow: failed to get
    valid pixel format`` access violation on Windows-headless. Panel +
    mesh-builder tests live in ``test_test_object_view.py`` and create
    a single panel under careful isolation.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        enable_3d_viewer: bool = True,
        experiment_root: Path | None = None,
        measured_root: Path | None = None,
        papers_root: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLabWorkspace")
        self._experiment_root = experiment_root
        self._measured_root = measured_root
        self._papers_root = papers_root

        # PL-D — Library / Code / Viz / Parameters now host real
        # widgets backed by the Bouncing Ball demo. The placeholder
        # path from PL-B is gone; tests assert the live widget types
        # so the placeholders cannot silently come back.
        self._library_panel = LibraryWidget(self)
        self._code_panel = CodePreview(self)
        self._viz_panel = BouncingBallPlot(self)
        self._parameters_panel = ParametersWidget(self)

        # PL-9.1d — viz area is a QStackedWidget so the Library
        # selection can swap between the 2D y(t) plot (Bouncing Ball)
        # and the 3D mesh viewer (any of the 9 Test Objects).
        # The 3D panel is created lazily on the first Test Object
        # selection so workspaces that only ever show the Bouncing
        # Ball never pay for an OpenGL render context, and so headless
        # CI runs that never click a Test Object never crash.
        self._viz_stack = QStackedWidget(self)
        self._viz_stack.setObjectName("PhysicsLabVizStack")
        self._viz_stack.addWidget(self._viz_panel)
        self._viz_stack.setCurrentWidget(self._viz_panel)
        self._enable_3d_viewer = enable_3d_viewer
        self._test_object_panel: TestObject3DPanel | None = None

        # Middle column: Code on top, Visualization below.
        middle = QSplitter(Qt.Orientation.Vertical, self)
        middle.setObjectName("PhysicsLabMiddleSplitter")
        middle.setChildrenCollapsible(False)
        middle.addWidget(self._code_panel)
        middle.addWidget(self._viz_stack)
        middle.setStretchFactor(0, 0)
        middle.setStretchFactor(1, 1)
        middle.setSizes([220, 420])

        # Top row: Library | (Code/Viz) | Parameters
        top_row = QSplitter(Qt.Orientation.Horizontal, self)
        top_row.setObjectName("PhysicsLabTopRowSplitter")
        top_row.setChildrenCollapsible(False)
        top_row.addWidget(self._library_panel)
        top_row.addWidget(middle)
        top_row.addWidget(self._parameters_panel)
        top_row.setStretchFactor(0, 0)
        top_row.setStretchFactor(1, 1)
        top_row.setStretchFactor(2, 0)
        top_row.setSizes([240, 700, 240])

        self._time_controls = _TimeControls(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(top_row, 1)
        layout.addWidget(self._time_controls)

        self._top_splitter = top_row
        self._middle_splitter = middle

        # PL-D — wire the time controls + parameter slider + plot to a
        # live BouncingBallSimulator. The controller owns its QTimer
        # so the workspace stays a thin shell. PL-9.1b extends the
        # constructor with the frame-control widgets.
        self._bouncing_controller = BouncingBallController(
            plot=self._viz_panel,
            parameters=self._parameters_panel,
            play_button=self._time_controls.play_button(),
            pause_button=self._time_controls.pause_button(),
            stop_button=self._time_controls.stop_button(),
            status_label=self._time_controls.status_label(),
            code_preview=self._code_panel,
            frame_slider=self._time_controls.frame_slider(),
            step_back_button=self._time_controls.step_back_button(),
            step_forward_button=self._time_controls.step_forward_button(),
            frame_readout=self._time_controls.frame_readout(),
            mode_combo=self._time_controls.mode_combo(),
            parent=self,
        )

        # PL-9.1d — Library selection drives the viz swap.
        self._library_panel.demo_selected.connect(self._on_library_selection)

        # PL-9.1f — Save current experiment + restore on Saved row click.
        self._library_panel.save_requested.connect(self._on_save_requested)
        self._library_panel.experiment_selected.connect(self.load_experiment)
        if self._experiment_root is not None:
            self.refresh_saved_experiments()
        # PL-9.2a/b — populate Library Measured Data + Papers categories.
        if self._measured_root is not None:
            self.refresh_measured_datasets()
        if self._papers_root is not None:
            self.refresh_papers()

        # PL-9.2c — Validation Bench. Selecting a Measured row in the
        # Library runs the live simulator against it and overlays
        # measurement + simulation curves on the y(t) plot.
        self._last_validation_metrics: ValidationMetrics | None = None
        self._library_panel.measured_dataset_selected.connect(self._on_measured_dataset_selected)
        self._bouncing_controller.validation_metrics_ready.connect(
            self._on_validation_metrics_ready
        )

    # ------------------------------------------------------------------
    # Accessors (PL-D ships the live widgets; PL-9.1+ keeps the same API)
    # ------------------------------------------------------------------
    def library_panel(self) -> LibraryWidget:
        return self._library_panel

    def code_panel(self) -> CodePreview:
        return self._code_panel

    def viz_panel(self) -> BouncingBallPlot:
        return self._viz_panel

    def parameters_panel(self) -> ParametersWidget:
        return self._parameters_panel

    def time_controls(self) -> _TimeControls:
        return self._time_controls

    def top_splitter(self) -> QSplitter:
        return self._top_splitter

    def middle_splitter(self) -> QSplitter:
        return self._middle_splitter

    def bouncing_ball_controller(self) -> BouncingBallController:
        return self._bouncing_controller

    # ------------------------------------------------------------------
    # PL-9.1d — viz stack
    # ------------------------------------------------------------------
    def viz_stack(self) -> QStackedWidget:
        return self._viz_stack

    def test_object_panel(self) -> TestObject3DPanel | None:
        return self._test_object_panel

    def current_viz_widget(self) -> QWidget:
        widget = self._viz_stack.currentWidget()
        if widget is None:
            return self._viz_panel
        return widget

    def _ensure_test_object_panel(self) -> TestObject3DPanel | None:
        """Lazy-instantiate the 3D viewer on first Test Object click.

        Returns ``None`` when the workspace was constructed with
        ``enable_3d_viewer=False`` (tests + CLI smoke runs).
        """
        if not self._enable_3d_viewer:
            return None
        if self._test_object_panel is None:
            self._test_object_panel = TestObject3DPanel(self)
            self._viz_stack.addWidget(self._test_object_panel)
        return self._test_object_panel

    # ------------------------------------------------------------------
    # PL-9.1f — Saved experiments
    # ------------------------------------------------------------------

    def experiment_root(self) -> Path | None:
        return self._experiment_root

    def refresh_saved_experiments(self) -> None:
        """Re-scan ``experiment_root`` and rebuild the Saved Experiments
        sub-tree. No-op when no root was configured.
        """
        if self._experiment_root is None:
            return
        experiments = list_saved_experiments(self._experiment_root)
        self._library_panel.set_saved_experiments(experiments)

    def measured_root(self) -> Path | None:
        return self._measured_root

    def papers_root(self) -> Path | None:
        return self._papers_root

    def refresh_measured_datasets(self) -> None:
        """Re-scan ``measured_root`` and rebuild the Measured Data
        sub-tree. No-op when no root was configured.
        """
        if self._measured_root is None:
            return
        datasets = list_measured_datasets(self._measured_root)
        self._library_panel.set_measured_datasets(datasets)

    def refresh_papers(self) -> None:
        """Re-scan ``papers_root`` and rebuild the Papers sub-tree."""
        if self._papers_root is None:
            return
        papers = list_papers(self._papers_root)
        self._library_panel.set_papers(papers)

    # ------------------------------------------------------------------
    # PL-9.2c — Validation Bench
    # ------------------------------------------------------------------

    def last_validation_metrics(self) -> ValidationMetrics | None:
        return self._last_validation_metrics

    def _on_measured_dataset_selected(self, dataset: MeasuredDataset) -> None:
        """Run validation against ``dataset`` when the Library row is
        selected. Errors are swallowed silently (UI feedback comes via
        the status label / future banner).
        """
        try:
            self._bouncing_controller.run_validation_from_dataset(dataset)
        except (ValueError, OSError):
            self._last_validation_metrics = None

    def _on_validation_metrics_ready(self, metrics: ValidationMetrics) -> None:
        self._last_validation_metrics = metrics
        # Surface the metrics in the bottom status label.
        text = (
            f"validation: RMSE={metrics.rmse:.3g} m  "
            f"max|err|={metrics.max_abs_error:.3g} m  "
            f"corr={metrics.pearson_correlation:.3f}  "
            f"(n={metrics.n_samples})"
        )
        self._time_controls.status_label().setText(text)

    def save_current_experiment(self, experiment_id: str) -> SavedExperiment:
        """Snapshot current simulator + mode and persist to TOML.

        Raises:
            RuntimeError: When ``experiment_root`` was not configured.
            ValueError: For an invalid experiment_id (caller can catch
                + reprompt).
        """
        if self._experiment_root is None:
            msg = "PhysicsLabWorkspace: experiment_root not configured"
            raise RuntimeError(msg)
        sim = self._bouncing_controller.simulator
        exp = SavedExperiment(
            experiment_id=experiment_id,
            gravity_m_s2=sim.gravity_m_s2,
            restitution=sim.restitution,
            initial_height_m=sim.initial_height_m,
            initial_velocity_m_s=sim.initial_velocity_m_s,
            drag_coefficient_k=sim.drag_coefficient_k,
            mode=self._bouncing_controller.mode,
        )
        path = self._experiment_root / f"{experiment_id}.toml"
        write_saved_experiment(path, exp)
        self.refresh_saved_experiments()
        return exp

    def load_experiment(self, experiment: SavedExperiment) -> None:
        """Restore a :class:`SavedExperiment` onto the live controller."""
        params = self._parameters_panel.auto_parameters()
        params.set_value("gravity_m_s2", experiment.gravity_m_s2)
        params.set_value("restitution", experiment.restitution)
        params.set_value("initial_height_m", experiment.initial_height_m)
        params.set_value("initial_velocity_m_s", experiment.initial_velocity_m_s)
        params.set_value("drag_coefficient_k", experiment.drag_coefficient_k)
        self._bouncing_controller.reset_with(
            gravity_m_s2=experiment.gravity_m_s2,
            restitution=experiment.restitution,
            initial_height_m=experiment.initial_height_m,
            initial_velocity_m_s=experiment.initial_velocity_m_s,
            drag_coefficient_k=experiment.drag_coefficient_k,
        )
        self._bouncing_controller.set_mode(experiment.mode)

    def _on_save_requested(self) -> None:
        """User clicked the Library "Save current experiment..." button."""
        if self._experiment_root is None:
            QMessageBox.information(
                self,
                "Save unavailable",
                "Workspace was constructed without an experiment_root.",
            )
            return
        name, accepted = QInputDialog.getText(
            self,
            "Save experiment",
            "Experiment id (kebab-case):",
        )
        if not accepted:
            return
        name = name.strip()
        if not name:
            return
        try:
            self.save_current_experiment(name)
        except ValueError as exc:
            QMessageBox.warning(self, "Save failed", str(exc))

    def _on_library_selection(self, label: str) -> None:
        """Swap the viz panel based on the Library selection.

        - ``BOUNCING_BALL_ROW`` -> 2D y(t) plot.
        - Any Test Object row -> ensure the 3D mesh panel exists +
          push the corresponding dataclass into
          :meth:`TestObject3DPanel.set_test_object`. No-op when the
          3D viewer was disabled at construction time
          (``enable_3d_viewer=False``).
        - Anything else (currently impossible) -> leave the stack alone.
        """
        if label == LibraryWidget.BOUNCING_BALL_ROW:
            self._viz_stack.setCurrentWidget(self._viz_panel)
            return
        obj = self._library_panel.test_object_for(label)
        if obj is None:
            return
        panel = self._ensure_test_object_panel()
        if panel is None:
            return
        panel.set_test_object(obj)
        self._viz_stack.setCurrentWidget(panel)
