"""Domain Settings panel — SimulationDomain + Outside Environment.

Phase 4 G2. UI for plan/11 § 11.11.8 (Map Editor) — surfaces the
:class:`workbench.domain.simulation_domain.SimulationDomain` dataclass
and the :class:`workbench.domain.simulation_domain.OutsideEnvironment`
policy as a self-contained panel that the Map Editor can mount and a
later sub-step can wire to actual Map data.

The widget is I/O free — every field is a Qt input plus a Signal. Tests
construct it, drive the controls, and assert on the SimulationDomain
returned by :meth:`current_domain`. No filesystem / clipboard / network.

References:
- plan/11 § 11.11.3 — ``SimulationDomain`` / ``OutsideEnvironment`` data
  model.
- plan/11 § 11.11.8 — Editor UI mockup.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain

_MAX_BOUND_M: Final[float] = 1_000_000.0
_MIN_BOUND_M: Final[float] = -1_000_000.0
_MAX_CEILING_M: Final[float] = 100_000.0
_MIN_FLOOR_M: Final[float] = -10_000.0

_OUTSIDE_LABELS: Final[dict[OutsideEnvironment, str]] = {
    OutsideEnvironment.OPEN_SEA: "Open Sea",
    OutsideEnvironment.OPEN_LAND: "Open Land",
    OutsideEnvironment.BLOCKED: "Blocked (Map 밖 진입 시 오류)",
    OutsideEnvironment.INFINITE_PLANE: "Infinite Plane (디버그용)",
}
"""Display order is also the radio-button visual order (plan/11 § 11.11.8)."""

_DEFAULT_DOMAIN: Final[SimulationDomain] = SimulationDomain(
    bounds_east=(-25000.0, 25000.0),
    bounds_north=(-25000.0, 25000.0),
)


class DomainSettingsPanel(QWidget):
    """Editor sub-panel for ``SimulationDomain`` + ``OutsideEnvironment``.

    The panel emits :pyattr:`domain_changed` whenever the bounds /
    ceiling / floor produce a valid :class:`SimulationDomain`, and
    :pyattr:`outside_environment_changed` whenever the radio selection
    moves. Invalid bound combinations (e.g. ``east_max <= east_min``)
    leave the domain unchanged and surface a status string at
    :meth:`status_text` — callers can mirror that into the Validation
    block.
    """

    domain_changed = Signal(SimulationDomain)
    outside_environment_changed = Signal(OutsideEnvironment)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DomainSettingsPanel")

        self._suppress_signals = True
        self._current_domain: SimulationDomain = _DEFAULT_DOMAIN
        self._current_outside: OutsideEnvironment = OutsideEnvironment.OPEN_SEA
        self._status_text = "OK"

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addWidget(self._build_map_bounds_readout())
        layout.addWidget(self._build_bounds_group())
        layout.addWidget(self._build_outside_group())
        layout.addWidget(self._build_coverage_preview(), 1)
        layout.addWidget(self._build_status_label())

        self._wire_signals()
        self._apply_domain_to_inputs(_DEFAULT_DOMAIN)
        self._apply_outside_to_radios(OutsideEnvironment.OPEN_SEA)
        self._suppress_signals = False

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_map_bounds_readout(self) -> QWidget:
        wrap = QFrame(self)
        wrap.setObjectName("DomainSettingsMapBoundsRow")
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Map bounds (precise):", wrap)
        title.setObjectName("DomainSettingsMapBoundsTitle")
        self._map_bounds_label = QLabel("(no map loaded)", wrap)
        self._map_bounds_label.setObjectName("DomainSettingsMapBoundsValue")
        self._map_bounds_label.setStyleSheet("color: #666;")
        h.addWidget(title)
        h.addWidget(self._map_bounds_label, 1)
        return wrap

    def _build_bounds_group(self) -> QGroupBox:
        box = QGroupBox("Simulation Domain (full simulator extent)", self)
        box.setObjectName("DomainSettingsBounds")
        form = QFormLayout(box)
        self._east_min = self._make_spin("DomainSettingsEastMin", _MIN_BOUND_M, _MAX_BOUND_M)
        self._east_max = self._make_spin("DomainSettingsEastMax", _MIN_BOUND_M, _MAX_BOUND_M)
        self._north_min = self._make_spin("DomainSettingsNorthMin", _MIN_BOUND_M, _MAX_BOUND_M)
        self._north_max = self._make_spin("DomainSettingsNorthMax", _MIN_BOUND_M, _MAX_BOUND_M)
        self._ceiling = self._make_spin("DomainSettingsCeiling", _MIN_FLOOR_M, _MAX_CEILING_M)
        self._floor = self._make_spin("DomainSettingsFloor", _MIN_FLOOR_M, _MAX_CEILING_M)
        form.addRow("East min (m)", self._east_min)
        form.addRow("East max (m)", self._east_max)
        form.addRow("North min (m)", self._north_min)
        form.addRow("North max (m)", self._north_max)
        form.addRow("Ceiling (m)", self._ceiling)
        form.addRow("Floor (m)", self._floor)
        return box

    def _build_outside_group(self) -> QGroupBox:
        box = QGroupBox("Outside Map Environment", self)
        box.setObjectName("DomainSettingsOutside")
        v = QVBoxLayout(box)
        self._outside_group = QButtonGroup(self)
        self._outside_group.setExclusive(True)
        self._outside_radios: dict[OutsideEnvironment, QRadioButton] = {}
        for idx, mode in enumerate(_OUTSIDE_LABELS):
            btn = QRadioButton(_OUTSIDE_LABELS[mode], box)
            btn.setObjectName(f"DomainSettingsOutside_{mode.value}")
            self._outside_group.addButton(btn, idx)
            self._outside_radios[mode] = btn
            v.addWidget(btn)
        return box

    def _build_coverage_preview(self) -> QGroupBox:
        box = QGroupBox("Coverage Preview", self)
        box.setObjectName("DomainSettingsCoveragePreview")
        v = QVBoxLayout(box)
        hint = QLabel(
            "Map + Simulation Domain footprint + radar beam arc."
            "\nWires to actual data in a later cycle.",
            box,
        )
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        hint.setObjectName("DomainSettingsCoverageHint")
        hint.setMinimumHeight(120)
        v.addWidget(hint)
        return box

    def _build_status_label(self) -> QLabel:
        label = QLabel("Status: OK", self)
        label.setObjectName("DomainSettingsStatus")
        return label

    @staticmethod
    def _make_spin(object_name: str, lo: float, hi: float) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setObjectName(object_name)
        spin.setRange(lo, hi)
        spin.setDecimals(2)
        spin.setSingleStep(100.0)
        return spin

    # ------------------------------------------------------------------
    # Signal wiring + handlers
    # ------------------------------------------------------------------
    def _wire_signals(self) -> None:
        for spin in (
            self._east_min,
            self._east_max,
            self._north_min,
            self._north_max,
            self._ceiling,
            self._floor,
        ):
            spin.valueChanged.connect(self._on_bound_changed)
        self._outside_group.idToggled.connect(self._on_outside_toggled)

    def _on_bound_changed(self, _value: float) -> None:
        if self._suppress_signals:
            return
        try:
            candidate = SimulationDomain(
                bounds_east=(self._east_min.value(), self._east_max.value()),
                bounds_north=(self._north_min.value(), self._north_max.value()),
                ceiling_alt_m=self._ceiling.value(),
                floor_alt_m=self._floor.value(),
            )
        except ValueError as exc:
            self._set_status(f"Invalid: {exc}")
            return
        self._current_domain = candidate
        self._set_status("OK")
        self.domain_changed.emit(candidate)

    def _on_outside_toggled(self, button_id: int, checked: bool) -> None:
        if not checked or self._suppress_signals:
            return
        for mode, btn in self._outside_radios.items():
            if self._outside_group.id(btn) == button_id:
                self._current_outside = mode
                self.outside_environment_changed.emit(mode)
                return

    def _set_status(self, text: str) -> None:
        self._status_text = text
        self._status_label().setText(f"Status: {text}")

    def _status_label(self) -> QLabel:
        return self.findChild(QLabel, "DomainSettingsStatus")  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def current_domain(self) -> SimulationDomain:
        """Return the last valid :class:`SimulationDomain`."""
        return self._current_domain

    def current_outside_environment(self) -> OutsideEnvironment:
        """Return the currently selected :class:`OutsideEnvironment`."""
        return self._current_outside

    def set_domain(self, domain: SimulationDomain) -> None:
        """Programmatic mirror of editing the bound spins."""
        self._suppress_signals = True
        self._apply_domain_to_inputs(domain)
        self._suppress_signals = False
        self._current_domain = domain
        self._set_status("OK")
        self.domain_changed.emit(domain)

    def set_outside_environment(self, mode: OutsideEnvironment) -> None:
        """Programmatic mirror of clicking a radio button (no double-emit)."""
        self._suppress_signals = True
        self._apply_outside_to_radios(mode)
        self._suppress_signals = False
        self._current_outside = mode
        self.outside_environment_changed.emit(mode)

    def set_map_bounds_readout(self, text: str) -> None:
        """Replace the read-only Map bounds line (G3 wires Map → readout)."""
        self._map_bounds_label.setText(text)

    def status_text(self) -> str:
        """Latest validation status (``OK`` or ``Invalid: <reason>``)."""
        return self._status_text

    def available_outside_modes(self) -> tuple[OutsideEnvironment, ...]:
        """Display order — also the radio button order."""
        return tuple(_OUTSIDE_LABELS)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def east_min_spin(self) -> QDoubleSpinBox:
        return self._east_min

    def east_max_spin(self) -> QDoubleSpinBox:
        return self._east_max

    def north_min_spin(self) -> QDoubleSpinBox:
        return self._north_min

    def north_max_spin(self) -> QDoubleSpinBox:
        return self._north_max

    def ceiling_spin(self) -> QDoubleSpinBox:
        return self._ceiling

    def floor_spin(self) -> QDoubleSpinBox:
        return self._floor

    def outside_radio(self, mode: OutsideEnvironment) -> QRadioButton:
        return self._outside_radios[mode]

    def map_bounds_label(self) -> QLabel:
        return self._map_bounds_label

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _apply_domain_to_inputs(self, domain: SimulationDomain) -> None:
        self._east_min.setValue(domain.bounds_east[0])
        self._east_max.setValue(domain.bounds_east[1])
        self._north_min.setValue(domain.bounds_north[0])
        self._north_max.setValue(domain.bounds_north[1])
        self._ceiling.setValue(domain.ceiling_alt_m)
        self._floor.setValue(domain.floor_alt_m)

    def _apply_outside_to_radios(self, mode: OutsideEnvironment) -> None:
        btn = self._outside_radios[mode]
        btn.setChecked(True)

    # ------------------------------------------------------------------
    # Class-level convenience
    # ------------------------------------------------------------------
    @staticmethod
    def display_label_for(mode: OutsideEnvironment) -> str:
        return _OUTSIDE_LABELS[mode]

    @staticmethod
    def display_modes() -> Iterable[OutsideEnvironment]:
        return _OUTSIDE_LABELS.keys()
