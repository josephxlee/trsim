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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.physics_lab.bouncing_ball_demo import (
    BouncingBallController,
    BouncingBallPlot,
    CodePreview,
    LibraryWidget,
    ParametersWidget,
)


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

        # ---- Row 1: Play / Pause / Stop + status label.
        row1 = QHBoxLayout()
        row1.setSpacing(6)
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


class PhysicsLabWorkspace(QWidget):
    """3-pane Physics Lab shell mounted alongside Editor / Simulator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLabWorkspace")

        # PL-D — Library / Code / Viz / Parameters now host real
        # widgets backed by the Bouncing Ball demo. The placeholder
        # path from PL-B is gone; tests assert the live widget types
        # so the placeholders cannot silently come back.
        self._library_panel = LibraryWidget(self)
        self._code_panel = CodePreview(self)
        self._viz_panel = BouncingBallPlot(self)
        self._parameters_panel = ParametersWidget(self)

        # Middle column: Code on top, Visualization below.
        middle = QSplitter(Qt.Orientation.Vertical, self)
        middle.setObjectName("PhysicsLabMiddleSplitter")
        middle.setChildrenCollapsible(False)
        middle.addWidget(self._code_panel)
        middle.addWidget(self._viz_panel)
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
            parent=self,
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
