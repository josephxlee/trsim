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
    QSplitter,
    QVBoxLayout,
    QWidget,
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
    """Bottom strip — Play / Pause / Stop placeholder buttons + status label.

    PL-D will wire these to :class:`PhysicsClock`. PL-A keeps them
    visible so the workspace shape is recognisable from the start.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLabTimeControls")
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(6)

        self._play_btn = QPushButton("Play", self)
        self._play_btn.setObjectName("PhysicsLabPlayBtn")
        self._pause_btn = QPushButton("Pause", self)
        self._pause_btn.setObjectName("PhysicsLabPauseBtn")
        self._stop_btn = QPushButton("Stop", self)
        self._stop_btn.setObjectName("PhysicsLabStopBtn")
        self._status = QLabel("idle  (PL-D will wire PhysicsClock)", self)
        self._status.setObjectName("PhysicsLabTimeStatus")

        for btn in (self._play_btn, self._pause_btn, self._stop_btn):
            row.addWidget(btn)
        row.addSpacing(12)
        row.addWidget(self._status, 1)

    def play_button(self) -> QPushButton:
        return self._play_btn

    def pause_button(self) -> QPushButton:
        return self._pause_btn

    def stop_button(self) -> QPushButton:
        return self._stop_btn

    def status_label(self) -> QLabel:
        return self._status


class PhysicsLabWorkspace(QWidget):
    """3-pane Physics Lab shell mounted alongside Editor / Simulator."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLabWorkspace")

        self._library_panel = _Placeholder(
            "Library",
            "Tests / Models / Saved Experiments. PL-C lists the 9 Test "
            "Objects (Sphere / Cube / Plate / ...) with their analytic-"
            "RCS formulas. Saved Experiments + Measured Data arrive in "
            "Phase 9.2.",
            self,
        )
        self._code_panel = _Placeholder(
            "Code",
            "Currently-active physics formula (read-only). PL-D shows "
            "the gravity / drag function powering the Bouncing Ball "
            "demo; Phase 9.3 layers an Edit mode + PhysicsModelProtocol "
            "plugin authoring.",
            self,
        )
        self._viz_panel = _Placeholder(
            "Visualization",
            "PyVista 3D scene + pyqtgraph 2D charts. PL-D draws the "
            "Bouncing Ball trajectory; Phase 9.1 finalises the 4 time "
            "modes (Static / Run / Compare / Sweep) on top of this "
            "canvas.",
            self,
        )
        self._parameters_panel = _Placeholder(
            "Parameters",
            "Auto-generated sliders from @physics_param decorators on "
            "the active formula. PL-D ships the Restitution slider; "
            "Phase 9.1 generates the full set per Test Object.",
            self,
        )

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

    # ------------------------------------------------------------------
    # Accessors (PL-C / PL-D / Phase 9.1 will swap real widgets in)
    # ------------------------------------------------------------------
    def library_panel(self) -> QWidget:
        return self._library_panel

    def code_panel(self) -> QWidget:
        return self._code_panel

    def viz_panel(self) -> QWidget:
        return self._viz_panel

    def parameters_panel(self) -> QWidget:
        return self._parameters_panel

    def time_controls(self) -> _TimeControls:
        return self._time_controls

    def top_splitter(self) -> QSplitter:
        return self._top_splitter

    def middle_splitter(self) -> QSplitter:
        return self._middle_splitter
