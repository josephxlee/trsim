"""TargetsEditor widget (Phase 4.8, plan/13 § 13.6)."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
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


class _TrajectoryPreviewPlaceholder(QFrame):
    """Stub trajectory preview canvas - real plot lands in Phase 4.8.x."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TrajectoryPreviewPlaceholder")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumHeight(160)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Trajectory Preview (Phase 4.8.x mounts the pyqtgraph 2D path view)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        layout.addWidget(hint)


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

        v.addWidget(_TrajectoryPreviewPlaceholder(self), 1)
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

    def rcs_edit(self) -> QLineEdit:
        return self._rcs_edit

    def scatterers_edit(self) -> QLineEdit:
        return self._scatterers_edit

    def waypoint_label(self) -> QLabel:
        return self._waypoint_count

    def validation_label(self) -> QLabel:
        return self._validation_label
