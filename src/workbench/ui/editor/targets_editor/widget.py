"""TargetsEditor widget (Phase 4.8 + P7 live trajectory preview, plan/13 § 13.6)."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# plan/12 § 12.4 + plan/14 § 14.x - 7 motion kinds (Level 1 MVP).
MOTION_KINDS: tuple[str, ...] = (
    "FIXED_GROUND",
    "GROUND_VEHICLE",
    "SURFACE_VESSEL",
    "FLOATING_STATIC",
    "AIRCRAFT",
    "POWERED_FLIGHT",
    "BALLISTIC",
)


class _TrajectoryPreview(QFrame):
    """Live trajectory preview canvas (Phase 4 P7).

    pyqtgraph PlotWidget with an aspect-locked top-down (East/North)
    2D scatter + line path. ``set_motion_kind(kind)`` swaps in a
    synthetic trajectory representative of each motion kind so the
    user sees something non-trivial as they click through the combo.

    Real scenario-driven trajectory plots land in a post-MVP cycle
    once the scenario loader populates the editor.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TrajectoryPreview")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self._plot = pg.PlotWidget(self)
        self._plot.setObjectName("TrajectoryPlot")
        self._plot.setLabel("left", "north", units="m")
        self._plot.setLabel("bottom", "east", units="m")
        self._plot.setAspectLocked(lock=True, ratio=1.0)
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._curve: pg.PlotDataItem = self._plot.plot([], [], pen=pg.mkPen("#1f77b4", width=2))
        # Start marker (East/North origin sample) — small filled circle.
        self._start_marker: pg.ScatterPlotItem = pg.ScatterPlotItem(
            size=10, pen=pg.mkPen("#2ca02c", width=2), brush=pg.mkBrush("#2ca02c")
        )
        self._plot.addItem(self._start_marker)
        layout.addWidget(self._plot)

        self.set_motion_kind("AIRCRAFT")

    def set_motion_kind(self, kind: str) -> None:
        """Replace the curve with a deterministic synthetic trajectory."""
        east, north = _synthetic_trajectory(kind)
        self._curve.setData(east, north)
        self._start_marker.setData([east[0]], [north[0]])

    def set_trajectory(
        self,
        east_m: Sequence[float],
        north_m: Sequence[float],
    ) -> None:
        """Push an explicit (east, north) path (post-MVP scenario hook)."""
        if len(east_m) != len(north_m):
            msg = f"trajectory east ({len(east_m)}) / north ({len(north_m)}) length mismatch"
            raise ValueError(msg)
        if len(east_m) == 0:
            self._curve.setData([], [])
            self._start_marker.setData([], [])
            return
        self._curve.setData(list(east_m), list(north_m))
        self._start_marker.setData([east_m[0]], [north_m[0]])

    def plot_widget(self) -> pg.PlotWidget:
        return self._plot

    def curve(self) -> pg.PlotDataItem:
        return self._curve

    def start_marker(self) -> pg.ScatterPlotItem:
        return self._start_marker


def _synthetic_trajectory(kind: str) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic mock path for each motion kind.

    The shapes are illustrative only — the user sees them flip as
    they click the motion-kind combo so the preview pane feels alive.
    """
    t = np.linspace(0.0, 1.0, 200, dtype=np.float64)
    if kind == "FIXED_GROUND" or kind == "FLOATING_STATIC":
        east = np.zeros_like(t)
        north = np.zeros_like(t)
    elif kind == "GROUND_VEHICLE":
        east = 1_000.0 * t
        north = 200.0 * np.sin(2.0 * math.pi * t)
    elif kind == "SURFACE_VESSEL":
        east = 800.0 * t
        north = 800.0 * np.sin(math.pi * t)
    elif kind == "AIRCRAFT":
        east = 2_000.0 * np.cos(2.0 * math.pi * t) - 2_000.0
        north = 1_500.0 * np.sin(2.0 * math.pi * t)
    elif kind == "POWERED_FLIGHT":
        east = 1_500.0 * t
        north = 1_000.0 * t**2
    elif kind == "BALLISTIC":
        east = 3_000.0 * t
        north = 3_000.0 * t - 4_500.0 * t**2  # parabolic arc
    else:
        east = np.zeros_like(t)
        north = np.zeros_like(t)
    return east, north


class TargetsEditor(QWidget):
    """Editor Activity 4 - target metadata + trajectory preview shell."""

    motion_kind_changed = Signal(str)
    csv_import_requested = Signal()
    csv_export_requested = Signal()
    save_requested = Signal()
    validate_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TargetsEditor")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_metadata_block())
        layout.addWidget(self._build_trajectory_block(), 1)
        layout.addWidget(self._build_validation_block())
        layout.addWidget(self._build_action_row())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_metadata_block(self) -> QGroupBox:
        box = QGroupBox("Target Metadata", self)
        box.setObjectName("TargetsEditorMetadata")
        form = QFormLayout(box)
        self._name_edit = QLineEdit("(unnamed)")
        self._name_edit.setObjectName("TargetsName")
        self._motion_combo = QComboBox(box)
        self._motion_combo.setObjectName("TargetsMotionKind")
        self._motion_combo.addItems(MOTION_KINDS)
        self._motion_combo.currentTextChanged.connect(self.motion_kind_changed)
        self._rcs_edit = QLineEdit("1.0")
        self._rcs_edit.setObjectName("TargetsRCS")
        self._scatterers_edit = QLineEdit("3")
        self._scatterers_edit.setObjectName("TargetsScatterers")
        form.addRow("Name", self._name_edit)
        form.addRow("Motion kind", self._motion_combo)
        form.addRow("RCS (m^2)", self._rcs_edit)
        form.addRow("Scatterer count", self._scatterers_edit)
        return box

    def _build_trajectory_block(self) -> QGroupBox:
        box = QGroupBox("Trajectory", self)
        box.setObjectName("TargetsEditorTrajectory")
        v = QVBoxLayout(box)

        toolbar = QHBoxLayout()
        import_btn = QPushButton("Import CSV...", box)
        import_btn.setObjectName("TargetsImportBtn")
        import_btn.clicked.connect(self.csv_import_requested)
        export_btn = QPushButton("Export CSV...", box)
        export_btn.setObjectName("TargetsExportBtn")
        export_btn.clicked.connect(self.csv_export_requested)
        self._waypoint_count = QLabel("0 waypoints")
        self._waypoint_count.setObjectName("TargetsWaypointCount")
        toolbar.addWidget(import_btn)
        toolbar.addWidget(export_btn)
        toolbar.addStretch(1)
        toolbar.addWidget(self._waypoint_count)
        v.addLayout(toolbar)

        self._trajectory_preview = _TrajectoryPreview(self)
        v.addWidget(self._trajectory_preview, 1)
        # Wire the motion-kind combo so the preview swaps to a matching
        # synthetic path the moment the user picks a row.
        self._motion_combo.currentTextChanged.connect(self._trajectory_preview.set_motion_kind)
        return box

    def _build_validation_block(self) -> QGroupBox:
        box = QGroupBox("Validation", self)
        box.setObjectName("TargetsEditorValidation")
        v = QVBoxLayout(box)
        self._validation_label = QLabel("Status: not yet validated")
        self._validation_label.setObjectName("TargetsValidationStatus")
        v.addWidget(self._validation_label)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        row.setObjectName("TargetsEditorActionRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Save", "save_requested", "TargetsSaveBtn"),
            ("Validate", "validate_requested", "TargetsValidateBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            btn.clicked.connect(getattr(self, signal_name))
            h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_motion_kind(self, kind: str) -> None:
        if kind not in MOTION_KINDS:
            msg = f"unknown motion kind {kind!r}; expected one of {MOTION_KINDS}"
            raise ValueError(msg)
        self._motion_combo.setCurrentText(kind)

    def current_motion_kind(self) -> str:
        return self._motion_combo.currentText()

    def set_waypoint_count(self, count: int) -> None:
        self._waypoint_count.setText(f"{count} waypoint{'' if count == 1 else 's'}")

    def set_validation_status(self, status: str) -> None:
        self._validation_label.setText(f"Status: {status}")

    def set_motion_options(self, kinds: Iterable[str]) -> None:
        """Override the default motion-kind list (test / future use)."""
        kinds_tuple = tuple(kinds)
        self._motion_combo.blockSignals(True)
        self._motion_combo.clear()
        self._motion_combo.addItems(kinds_tuple)
        self._motion_combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def name_edit(self) -> QLineEdit:
        return self._name_edit

    def motion_combo(self) -> QComboBox:
        return self._motion_combo

    def waypoint_label(self) -> QLabel:
        return self._waypoint_count

    def validation_label(self) -> QLabel:
        return self._validation_label

    def trajectory_preview(self) -> _TrajectoryPreview:
        return self._trajectory_preview
