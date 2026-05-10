"""Map Editor widget (Phase 4.6, plan/13 section 13.4)."""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class MapTool(StrEnum):
    """The five MVP tools enumerated in plan/13 § 13.4.2."""

    PAN = "pan"
    LAND_SEA_BRUSH = "land_sea_brush"
    SPOT_EDIT = "spot_edit"
    FLATTEN = "flatten"
    ADD_BUILDING = "add_building"


_TOOL_LABEL: dict[MapTool, str] = {
    MapTool.PAN: "Pan",
    MapTool.LAND_SEA_BRUSH: "Land/Sea Brush",
    MapTool.SPOT_EDIT: "Spot Edit",
    MapTool.FLATTEN: "Flatten Area",
    MapTool.ADD_BUILDING: "Add Building",
}

_LAYER_NAMES: tuple[str, ...] = (
    "Terrain heightmap",
    "Land/Sea mask",
    "Buildings",
    "Coastline polygon",
    "Source DEM (reference)",
)


class _MapCanvasPlaceholder(QFrame):
    """Stub map canvas - real renderer arrives with pyqtgraph (Phase 4.6.x)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapCanvasPlaceholder")
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setMinimumSize(320, 240)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, pal.color(QPalette.ColorRole.AlternateBase))
        self.setAutoFillBackground(True)
        self.setPalette(pal)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Map canvas (Phase 4.6.x mounts the pyqtgraph view here)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        hint.setObjectName("MapCanvasHint")
        layout.addWidget(hint)


class MapEditor(QWidget):
    """Editor Activity 2 - DEM + terrain + building edit shell."""

    tool_changed = Signal(MapTool)
    layer_visibility_changed = Signal(str, bool)
    save_requested = Signal()
    import_dem_requested = Signal()
    validate_requested = Signal()
    reset_to_source_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapEditor")

        self._tool_buttons: dict[MapTool, QToolButton] = {}
        self._tool_group = QButtonGroup(self)
        self._tool_group.setExclusive(True)
        self._layer_checks: dict[str, QCheckBox] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setSpacing(12)
        body.addWidget(self._build_tool_palette(), 0)
        body.addWidget(self._build_canvas(), 1)
        body.addWidget(self._build_layers_panel(), 0)
        layout.addLayout(body, 1)

        layout.addWidget(self._build_history_block(), 0)
        layout.addWidget(self._build_action_row(), 0)

        self._tool_group.idToggled.connect(self._on_tool_toggled)
        self._select_default_tool()

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_header(self) -> QWidget:
        wrap = QWidget(self)
        wrap.setObjectName("MapEditorHeader")
        h = QHBoxLayout(wrap)
        h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Map Editor")
        title.setObjectName("MapEditorTitle")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        h.addWidget(title)
        h.addStretch(1)
        self._origin_label = QLabel("Origin: (unset)  Vertical: (unset)")
        self._origin_label.setObjectName("MapEditorOrigin")
        h.addWidget(self._origin_label)
        return wrap

    def _build_tool_palette(self) -> QGroupBox:
        box = QGroupBox("Tools", self)
        box.setObjectName("MapEditorTools")
        v = QVBoxLayout(box)
        for idx, tool in enumerate(MapTool):
            btn = QToolButton(box)
            btn.setText(_TOOL_LABEL[tool])
            btn.setObjectName(f"MapTool_{tool.value}")
            btn.setCheckable(True)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
            self._tool_group.addButton(btn, idx)
            self._tool_buttons[tool] = btn
            v.addWidget(btn)
        v.addStretch(1)
        return box

    def _build_canvas(self) -> QWidget:
        return _MapCanvasPlaceholder(self)

    def _build_layers_panel(self) -> QGroupBox:
        box = QGroupBox("Layers", self)
        box.setObjectName("MapEditorLayers")
        v = QVBoxLayout(box)
        for layer in _LAYER_NAMES:
            cb = QCheckBox(layer, box)
            cb.setObjectName(f"MapLayer_{layer.replace(' ', '_')}")
            cb.setChecked(layer in {"Terrain heightmap", "Land/Sea mask", "Buildings"})
            cb.toggled.connect(
                lambda checked, name=layer: self.layer_visibility_changed.emit(name, checked)
            )
            self._layer_checks[layer] = cb
            v.addWidget(cb)
        v.addStretch(1)
        return box

    def _build_history_block(self) -> QGroupBox:
        box = QGroupBox("Edit History", self)
        box.setObjectName("MapEditorHistory")
        v = QVBoxLayout(box)
        self._history_list = QListWidget(box)
        self._history_list.setObjectName("MapEditorHistoryList")
        v.addWidget(self._history_list, 1)
        reset_row = QHBoxLayout()
        reset_btn = QPushButton("Reset to source DEM", box)
        reset_btn.setObjectName("MapEditorResetBtn")
        reset_btn.clicked.connect(self.reset_to_source_requested)
        reset_row.addStretch(1)
        reset_row.addWidget(reset_btn)
        v.addLayout(reset_row)
        return box

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        row.setObjectName("MapEditorActionRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        h.addStretch(1)
        for label, signal_name, object_name in (
            ("Save", "save_requested", "MapEditorSaveBtn"),
            ("Import DEM...", "import_dem_requested", "MapEditorImportBtn"),
            ("Validate", "validate_requested", "MapEditorValidateBtn"),
        ):
            btn = QPushButton(label, row)
            btn.setObjectName(object_name)
            btn.clicked.connect(getattr(self, signal_name))
            h.addWidget(btn)
        return row

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _select_default_tool(self) -> None:
        btn = self._tool_buttons[MapTool.PAN]
        btn.blockSignals(True)
        btn.setChecked(True)
        btn.blockSignals(False)
        self._current_tool = MapTool.PAN

    def _on_tool_toggled(self, button_id: int, checked: bool) -> None:
        if not checked:
            return
        for tool, btn in self._tool_buttons.items():
            if self._tool_group.id(btn) == button_id:
                self._current_tool = tool
                self.tool_changed.emit(tool)
                return

    # ------------------------------------------------------------------
    # Public API (Phase 5+ wires data sources)
    # ------------------------------------------------------------------
    def set_origin(self, lat_lon_text: str, vertical_ref: str) -> None:
        """Update the origin readout in the header strip."""
        self._origin_label.setText(f"Origin: {lat_lon_text}  Vertical: {vertical_ref}")

    def set_history(self, entries: list[str]) -> None:
        """Replace the edit-history list contents."""
        self._history_list.clear()
        for entry in entries:
            self._history_list.addItem(entry)

    def select_tool(self, tool: MapTool) -> None:
        """Programmatic mirror of clicking a tool button (no double-emit)."""
        btn = self._tool_buttons[tool]
        if not btn.isChecked():
            btn.setChecked(True)

    def current_tool(self) -> MapTool:
        return self._current_tool

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def tool_button(self, tool: MapTool) -> QToolButton:
        return self._tool_buttons[tool]

    def layer_check(self, name: str) -> QCheckBox:
        return self._layer_checks[name]

    def history_list(self) -> QListWidget:
        return self._history_list
