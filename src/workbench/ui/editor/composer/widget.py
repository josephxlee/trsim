"""ScenarioComposer widget (Phase 4.5, plan/13 section 13.3.1)."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Sea-state / atmosphere preset names match the plan/15 atmosphere model
# vocabulary so that Phase 5 wiring just maps strings, no rename pass.
DEFAULT_SEA_STATES: tuple[str, ...] = ("Calm", "Slight", "Moderate", "Rough")
DEFAULT_ATMOSPHERES: tuple[str, ...] = ("Clear", "Light Rain", "Heavy Rain", "Fog")


class ScenarioComposer(QWidget):
    """Editor Activity 1 - assembles a Scenario from referenced resources."""

    save_requested = Signal()
    save_as_requested = Signal()
    validate_requested = Signal()
    export_bundle_requested = Signal()
    open_resource_requested = Signal(str)  # category id

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScenarioComposer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_references_block())
        layout.addWidget(self._build_installation_block())
        layout.addWidget(self._build_composition_block())
        layout.addWidget(self._build_validation_block(), 1)
        layout.addWidget(self._build_action_row())

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_header(self) -> QWidget:
        wrap = QWidget(self)
        wrap.setObjectName("ComposerHeader")
        form = QFormLayout(wrap)
        form.setContentsMargins(0, 0, 0, 0)
        self._name_edit = QLineEdit("(unnamed)")
        self._name_edit.setObjectName("ComposerName")
        self._description_edit = QLineEdit()
        self._description_edit.setObjectName("ComposerDescription")
        self._description_edit.setPlaceholderText("One-line description")
        self._hash_label = QLabel("hash: (not saved)")
        self._hash_label.setObjectName("ComposerHash")
        form.addRow("Name", self._name_edit)
        form.addRow("Description", self._description_edit)
        form.addRow("Identifier", self._hash_label)
        return wrap

    def _build_references_block(self) -> QGroupBox:
        box = QGroupBox("References", self)
        box.setObjectName("ComposerReferences")
        form = QFormLayout(box)
        self._map_combo = self._make_resource_combo("ComposerMapCombo")
        self._radar_combo = self._make_resource_combo("ComposerRadarCombo")
        self._targets_combo = self._make_resource_combo("ComposerTargetsCombo")
        for label, combo, category in (
            ("Map", self._map_combo, "map"),
            ("Radar", self._radar_combo, "radar"),
            ("Targets", self._targets_combo, "targets"),
        ):
            row = QWidget(box)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(combo, 1)
            open_btn = QPushButton(f"Open in {label} Editor", row)
            open_btn.setObjectName(f"ComposerOpen_{category}")
            open_btn.clicked.connect(
                lambda _checked=False, c=category: self.open_resource_requested.emit(c)
            )
            row_layout.addWidget(open_btn)
            form.addRow(label, row)
        return box

    def _build_installation_block(self) -> QGroupBox:
        box = QGroupBox("Installation", self)
        box.setObjectName("ComposerInstallation")
        form = QFormLayout(box)
        self._east_edit = QLineEdit("0.0")
        self._east_edit.setObjectName("ComposerInstallEast")
        self._north_edit = QLineEdit("0.0")
        self._north_edit.setObjectName("ComposerInstallNorth")
        self._azimuth_edit = QLineEdit("180.0")
        self._azimuth_edit.setObjectName("ComposerInstallAzimuth")
        form.addRow("East (m)", self._east_edit)
        form.addRow("North (m)", self._north_edit)
        form.addRow("Initial Azimuth (deg)", self._azimuth_edit)
        return box

    def _build_composition_block(self) -> QGroupBox:
        box = QGroupBox("Composition", self)
        box.setObjectName("ComposerComposition")
        form = QFormLayout(box)
        self._sea_state_combo = QComboBox(box)
        self._sea_state_combo.setObjectName("ComposerSeaState")
        self._sea_state_combo.addItems(DEFAULT_SEA_STATES)
        self._atmosphere_combo = QComboBox(box)
        self._atmosphere_combo.setObjectName("ComposerAtmosphere")
        self._atmosphere_combo.addItems(DEFAULT_ATMOSPHERES)
        form.addRow("Sea State", self._sea_state_combo)
        form.addRow("Atmosphere", self._atmosphere_combo)
        return box

    def _build_validation_block(self) -> QGroupBox:
        box = QGroupBox("Validation", self)
        box.setObjectName("ComposerValidation")
        layout = QVBoxLayout(box)
        self._validation_status = QLabel("Status: not yet validated")
        self._validation_status.setObjectName("ComposerValidationStatus")
        self._validation_status.setFont(QFont(self.font().family(), weight=QFont.Weight.DemiBold))
        self._validation_messages = QListWidget(box)
        self._validation_messages.setObjectName("ComposerValidationMessages")
        layout.addWidget(self._validation_status)
        layout.addWidget(self._validation_messages, 1)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        row.setObjectName("ComposerActionRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Save", "save_requested", "ComposerSaveBtn"),
            ("Save As...", "save_as_requested", "ComposerSaveAsBtn"),
            ("Validate", "validate_requested", "ComposerValidateBtn"),
            ("Export Bundle...", "export_bundle_requested", "ComposerExportBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            signal = getattr(self, signal_name)
            btn.clicked.connect(signal)
            h.addWidget(btn)
        return row

    @staticmethod
    def _make_resource_combo(object_name: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(object_name)
        combo.addItem("(none)")
        return combo

    # ------------------------------------------------------------------
    # Public API (Phase 5+ wires data sources)
    # ------------------------------------------------------------------
    def set_map_options(self, names: Iterable[str]) -> None:
        """Replace the Map dropdown options."""
        self._populate_combo(self._map_combo, names)

    def set_radar_options(self, names: Iterable[str]) -> None:
        self._populate_combo(self._radar_combo, names)

    def set_targets_options(self, names: Iterable[str]) -> None:
        self._populate_combo(self._targets_combo, names)

    def set_validation(self, status: str, messages: Iterable[str]) -> None:
        """Update the validation status banner + message list."""
        self._validation_status.setText(f"Status: {status}")
        self._validation_messages.clear()
        for msg in messages:
            self._validation_messages.addItem(msg)

    @staticmethod
    def _populate_combo(combo: QComboBox, names: Iterable[str]) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("(none)")
        for name in names:
            combo.addItem(name)
        combo.blockSignals(False)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def name_edit(self) -> QLineEdit:
        return self._name_edit

    def map_combo(self) -> QComboBox:
        return self._map_combo

    def radar_combo(self) -> QComboBox:
        return self._radar_combo

    def targets_combo(self) -> QComboBox:
        return self._targets_combo

    def sea_state_combo(self) -> QComboBox:
        return self._sea_state_combo

    def atmosphere_combo(self) -> QComboBox:
        return self._atmosphere_combo

    def validation_messages(self) -> QListWidget:
        return self._validation_messages

    def validation_status_label(self) -> QLabel:
        return self._validation_status
