"""ScenarioComposer widget (Phase 4.5 + G4 Installation/Domain Override boost).

Phase 4.5 (May 11) shipped the skeletal Installation block (3 line
edits). The Phase 4 G4 cycle (2026-05-13) extends it to the layout
plan/13 § 13.3.3 prescribes — Position + Orientation, a DEM preview
placeholder, Coverage Stats, and a Domain Override block (plan/11
§ 11.11.8 "Scenario Composer 에도 override 옵션"). All numeric fields
emit ``position_changed`` on edit so a later cycle can wire validation
to the Map's land_mask + sample_terrain_safe.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from workbench.domain.simulation_domain import OutsideEnvironment

# Sea-state / atmosphere preset names match the plan/15 atmosphere model
# vocabulary so that Phase 5 wiring just maps strings, no rename pass.
DEFAULT_SEA_STATES: tuple[str, ...] = ("Calm", "Slight", "Moderate", "Rough")
DEFAULT_ATMOSPHERES: tuple[str, ...] = ("Clear", "Light Rain", "Heavy Rain", "Fog")

INHERIT_LABEL = "Inherit from Map"
"""Label for the outside-environment combo when override checkbox is off."""

_OUTSIDE_DISPLAY: dict[OutsideEnvironment, str] = {
    OutsideEnvironment.OPEN_SEA: "Open Sea",
    OutsideEnvironment.OPEN_LAND: "Open Land",
    OutsideEnvironment.BLOCKED: "Blocked",
    OutsideEnvironment.INFINITE_PLANE: "Infinite Plane",
}


@dataclass(frozen=True, slots=True)
class CoverageStats:
    """Read-only summary the simulator computes for the Installation block.

    The Composer accepts a :class:`CoverageStats` from a later cycle (when
    the radar resource + Map + Validator are wired) and displays it in
    the Coverage Stats group. ``blind_bearings_deg`` lists every bearing
    [degrees CW from North] that registers ≥ 50% sector obstruction.
    """

    max_range_km: float
    obstructed_sectors: int
    total_sectors: int
    blind_bearings_deg: tuple[float, ...] = ()


class ScenarioComposer(QWidget):
    """Editor Activity 1 - assembles a Scenario from referenced resources."""

    save_requested = Signal()
    save_as_requested = Signal()
    validate_requested = Signal()
    export_bundle_requested = Signal()
    open_resource_requested = Signal(str)  # category id
    position_changed = Signal(float, float, float, float)  # east, north, az_deg, el_deg
    domain_override_toggled = Signal(bool)
    outside_override_toggled = Signal(bool)
    outside_override_changed = Signal(object)  # OutsideEnvironment | None

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScenarioComposer")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_references_block())
        layout.addWidget(self._build_installation_block())
        layout.addWidget(self._build_domain_override_block())
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
        v = QVBoxLayout(box)

        # --- Position + Orientation form ----------------------------------
        form = QFormLayout()
        self._east_edit = QLineEdit("0.0")
        self._east_edit.setObjectName("ComposerInstallEast")
        self._north_edit = QLineEdit("0.0")
        self._north_edit.setObjectName("ComposerInstallNorth")
        self._azimuth_edit = QLineEdit("180.0")
        self._azimuth_edit.setObjectName("ComposerInstallAzimuth")
        self._elevation_edit = QLineEdit("0.0")
        self._elevation_edit.setObjectName("ComposerInstallElevation")
        self._altitude_label = QLabel("(DEM sample pending)")
        self._altitude_label.setObjectName("ComposerInstallAltitude")
        self._altitude_label.setStyleSheet("color: #666;")
        form.addRow("East (m)", self._east_edit)
        form.addRow("North (m)", self._north_edit)
        form.addRow("Altitude (m)", self._altitude_label)
        form.addRow("Initial Azimuth (deg)", self._azimuth_edit)
        form.addRow("Initial Elevation (deg)", self._elevation_edit)
        v.addLayout(form)

        for edit in (
            self._east_edit,
            self._north_edit,
            self._azimuth_edit,
            self._elevation_edit,
        ):
            edit.editingFinished.connect(self._emit_position_changed)

        # --- DEM Map preview placeholder -----------------------------------
        self._dem_preview = QFrame(box)
        self._dem_preview.setObjectName("ComposerInstallDEMPreview")
        self._dem_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self._dem_preview.setMinimumHeight(120)
        preview_layout = QVBoxLayout(self._dem_preview)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        self._dem_preview_hint = QLabel(
            "DEM Map (top-down) — installation pose preview", self._dem_preview
        )
        self._dem_preview_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._dem_preview_hint.setStyleSheet("color: #777;")
        self._dem_preview_hint.setObjectName("ComposerInstallDEMHint")
        preview_layout.addWidget(self._dem_preview_hint)
        v.addWidget(self._dem_preview, 1)

        # --- Coverage Stats readouts --------------------------------------
        stats_box = QGroupBox("Coverage Stats", box)
        stats_box.setObjectName("ComposerCoverageStats")
        stats_form = QFormLayout(stats_box)
        self._max_range_label = QLabel("--")
        self._max_range_label.setObjectName("ComposerCoverageMaxRange")
        self._obstructed_label = QLabel("--")
        self._obstructed_label.setObjectName("ComposerCoverageObstructed")
        self._blind_bearings_label = QLabel("--")
        self._blind_bearings_label.setObjectName("ComposerCoverageBlindBearings")
        stats_form.addRow("Max range", self._max_range_label)
        stats_form.addRow("Obstructed sectors", self._obstructed_label)
        stats_form.addRow("Blind bearings (deg)", self._blind_bearings_label)
        v.addWidget(stats_box)
        return box

    def _build_domain_override_block(self) -> QGroupBox:
        box = QGroupBox("Domain Override (optional)", self)
        box.setObjectName("ComposerDomainOverride")
        v = QVBoxLayout(box)

        self._domain_override_check = QCheckBox(
            "Override SimulationDomain (otherwise inherit from Map)", box
        )
        self._domain_override_check.setObjectName("ComposerDomainOverrideCheck")
        self._domain_override_check.toggled.connect(self.domain_override_toggled)
        v.addWidget(self._domain_override_check)

        outside_row = QHBoxLayout()
        self._outside_override_check = QCheckBox("Override Outside Environment:", box)
        self._outside_override_check.setObjectName("ComposerOutsideOverrideCheck")
        self._outside_override_check.toggled.connect(self._on_outside_override_toggled)
        self._outside_combo = QComboBox(box)
        self._outside_combo.setObjectName("ComposerOutsideOverrideCombo")
        # Store the enum's string value (PySide6 wraps user data in QVariant
        # which can lose object identity for Python Enum instances —
        # round-trip via the StrEnum value is safer).
        self._outside_combo.addItem(INHERIT_LABEL, None)
        for mode, label in _OUTSIDE_DISPLAY.items():
            self._outside_combo.addItem(label, mode.value)
        self._outside_combo.setEnabled(False)
        self._outside_combo.currentIndexChanged.connect(self._on_outside_combo_changed)
        outside_row.addWidget(self._outside_override_check)
        outside_row.addWidget(self._outside_combo, 1)
        v.addLayout(outside_row)
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
        self._atmosphere_hint = QLabel("(editor: not yet set)")
        self._atmosphere_hint.setObjectName("ComposerAtmosphereHint")
        self._atmosphere_hint.setStyleSheet("color: #777;")
        form.addRow("Sea State", self._sea_state_combo)
        form.addRow("Atmosphere", self._atmosphere_combo)
        form.addRow("", self._atmosphere_hint)
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

    def set_atmosphere_hint(self, text: str) -> None:
        """Update the editor-atmosphere hint label below the Atmosphere combo.

        Phase 9 cycle: the AtmospherePropagator subscribes to
        :attr:`AtmospherePanel.state_changed` and forwards a short
        human-readable summary here so the Composer always reflects
        whatever the user is currently editing in the Atmosphere
        Activity.
        """
        self._atmosphere_hint.setText(text)

    def atmosphere_hint_label(self) -> QLabel:
        """Test helper for the atmosphere hint widget."""
        return self._atmosphere_hint

    def set_validation(self, status: str, messages: Iterable[str]) -> None:
        """Update the validation status banner + message list."""
        self._validation_status.setText(f"Status: {status}")
        self._validation_messages.clear()
        for msg in messages:
            self._validation_messages.addItem(msg)

    # ------------------------------------------------------------------
    # Installation block API
    # ------------------------------------------------------------------
    def current_position(self) -> tuple[float, float, float, float]:
        """Return (east_m, north_m, az_deg, el_deg) as parsed from the inputs.

        Non-numeric fields fall back to 0.0 — callers should treat invalid
        text as "user is still typing" and revalidate on signal.
        """
        return (
            _try_parse_float(self._east_edit.text()),
            _try_parse_float(self._north_edit.text()),
            _try_parse_float(self._azimuth_edit.text()),
            _try_parse_float(self._elevation_edit.text()),
        )

    def set_position(self, east_m: float, north_m: float, az_deg: float, el_deg: float) -> None:
        """Programmatic mirror of editing the position fields."""
        for edit, value in (
            (self._east_edit, east_m),
            (self._north_edit, north_m),
            (self._azimuth_edit, az_deg),
            (self._elevation_edit, el_deg),
        ):
            edit.blockSignals(True)
            edit.setText(f"{value:g}")
            edit.blockSignals(False)
        self.position_changed.emit(east_m, north_m, az_deg, el_deg)

    def set_terrain_altitude(self, altitude_m: float | None) -> None:
        """Show the DEM-sampled installation altitude.

        Passing ``None`` reverts the label to the "DEM sample pending"
        placeholder (e.g. when the position falls outside Map bounds).
        """
        if altitude_m is None:
            self._altitude_label.setText("(DEM sample pending)")
            self._altitude_label.setStyleSheet("color: #666;")
            return
        self._altitude_label.setText(f"{altitude_m:.2f} m (DEM sampled)")
        self._altitude_label.setStyleSheet("")

    def set_coverage_stats(self, stats: CoverageStats | None) -> None:
        """Populate the Coverage Stats readouts.

        Passing ``None`` resets every readout to the ``--`` placeholder.
        """
        if stats is None:
            self._max_range_label.setText("--")
            self._obstructed_label.setText("--")
            self._blind_bearings_label.setText("--")
            return
        self._max_range_label.setText(f"{stats.max_range_km:.1f} km")
        total = max(stats.total_sectors, 1)
        pct = 100.0 * stats.obstructed_sectors / total
        self._obstructed_label.setText(
            f"{stats.obstructed_sectors}/{stats.total_sectors} ({pct:.0f}%)"
        )
        if stats.blind_bearings_deg:
            self._blind_bearings_label.setText(
                " / ".join(f"{b:.0f}" for b in stats.blind_bearings_deg)
            )
        else:
            self._blind_bearings_label.setText("(none)")

    # ------------------------------------------------------------------
    # Domain Override API
    # ------------------------------------------------------------------
    def is_domain_override_enabled(self) -> bool:
        return self._domain_override_check.isChecked()

    def set_domain_override_enabled(self, enabled: bool) -> None:
        self._domain_override_check.setChecked(enabled)

    def is_outside_override_enabled(self) -> bool:
        return self._outside_override_check.isChecked()

    def set_outside_override_enabled(self, enabled: bool) -> None:
        self._outside_override_check.setChecked(enabled)

    def current_outside_override(self) -> OutsideEnvironment | None:
        """Return the selected outside-environment override or None.

        ``None`` whenever the override checkbox is off or the combo is on
        the "Inherit from Map" sentinel.
        """
        if not self.is_outside_override_enabled():
            return None
        value = self._outside_combo.currentData()
        if isinstance(value, str):
            try:
                return OutsideEnvironment(value)
            except ValueError:
                return None
        return None

    def set_outside_override_mode(self, mode: OutsideEnvironment | None) -> None:
        """Programmatic mirror of choosing a value in the outside combo.

        Passing ``None`` selects the "Inherit from Map" sentinel and
        leaves the checkbox state untouched.
        """
        target_index = 0
        if mode is not None:
            target_value = mode.value
            for idx in range(self._outside_combo.count()):
                if self._outside_combo.itemData(idx) == target_value:
                    target_index = idx
                    break
        self._outside_combo.setCurrentIndex(target_index)

    # ------------------------------------------------------------------
    # Signal handlers (private)
    # ------------------------------------------------------------------
    def _emit_position_changed(self) -> None:
        e, n, az, el = self.current_position()
        self.position_changed.emit(e, n, az, el)

    def _on_outside_override_toggled(self, checked: bool) -> None:
        self._outside_combo.setEnabled(checked)
        self.outside_override_toggled.emit(checked)
        self.outside_override_changed.emit(self.current_outside_override())

    def _on_outside_combo_changed(self, _index: int) -> None:
        self.outside_override_changed.emit(self.current_outside_override())

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

    def east_edit(self) -> QLineEdit:
        return self._east_edit

    def north_edit(self) -> QLineEdit:
        return self._north_edit

    def azimuth_edit(self) -> QLineEdit:
        return self._azimuth_edit

    def elevation_edit(self) -> QLineEdit:
        return self._elevation_edit

    def altitude_label(self) -> QLabel:
        return self._altitude_label

    def dem_preview(self) -> QFrame:
        return self._dem_preview

    def max_range_label(self) -> QLabel:
        return self._max_range_label

    def obstructed_label(self) -> QLabel:
        return self._obstructed_label

    def blind_bearings_label(self) -> QLabel:
        return self._blind_bearings_label

    def domain_override_check(self) -> QCheckBox:
        return self._domain_override_check

    def outside_override_check(self) -> QCheckBox:
        return self._outside_override_check

    def outside_override_combo(self) -> QComboBox:
        return self._outside_combo


def _try_parse_float(text: str) -> float:
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0
