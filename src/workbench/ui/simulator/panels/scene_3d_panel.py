"""3D Scene panel (Phase 4.10, plan/05 § 5.3.2).

Hosts the 3rd-person view of terrain + buildings + targets + radar
beams. The actual PyVista QtInteractor mounts here in Phase 4.10.x;
Phase 4.10 ships the camera preset toolbar and the SceneLayer toggle
list so the panel's surrounding affordances are reviewable end-to-end.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class SceneLayer(StrEnum):
    """Toggleable layers on the 3rd-person scene (plan/05 § 5.3.2)."""

    TERRAIN = "terrain"
    SEA = "sea"
    BUILDINGS = "buildings"
    SHIPS = "ships"
    TX_BEAM_ACTUAL = "tx_beam_actual"
    TX_BEAM_COMMAND = "tx_beam_command"
    GT_TARGETS = "gt_targets"
    DETECTIONS = "detections"
    TRACKS = "tracks"
    PRIMARY_HIGHLIGHT = "primary_highlight"
    MULTIPATH_RAYS = "multipath"


_DEFAULT_ON: frozenset[SceneLayer] = frozenset(
    {
        SceneLayer.TERRAIN,
        SceneLayer.SEA,
        SceneLayer.BUILDINGS,
        SceneLayer.SHIPS,
        SceneLayer.TX_BEAM_ACTUAL,
        SceneLayer.GT_TARGETS,
        SceneLayer.TRACKS,
        SceneLayer.PRIMARY_HIGHLIGHT,
    }
)


class CameraPreset(StrEnum):
    """Camera preset shortcuts (plan/05 § 5.5.4b)."""

    TOP = "top"
    LEFT = "left"
    FREE = "free"
    RADAR = "radar"


_CAMERA_LABEL: dict[CameraPreset, str] = {
    CameraPreset.TOP: "Top",
    CameraPreset.LEFT: "Left",
    CameraPreset.FREE: "Free",
    CameraPreset.RADAR: "Radar",
}

_CAMERA_KEY: dict[CameraPreset, str] = {
    CameraPreset.TOP: "T",
    CameraPreset.LEFT: "L",
    CameraPreset.FREE: "F",
    CameraPreset.RADAR: "R",
}


class Scene3DPanel(QWidget):
    """3rd-person 3D scene shell (PyVista canvas in Phase 4.10.x)."""

    camera_preset_chosen = Signal(CameraPreset)
    layer_visibility_changed = Signal(SceneLayer, bool)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Scene3DPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(self._build_camera_row())
        body = QHBoxLayout()
        body.setSpacing(6)
        body.addWidget(self._build_canvas(), 1)
        body.addWidget(self._build_layer_panel(), 0)
        layout.addLayout(body, 1)

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_camera_row(self) -> QWidget:
        row = QWidget(self)
        row.setObjectName("Scene3DCameraRow")
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("3D Scene (3rd-person)")
        title.setStyleSheet("font-weight: 600;")
        h.addWidget(title)
        h.addSpacing(12)
        h.addWidget(QLabel("Camera:"))
        self._camera_buttons: dict[CameraPreset, QToolButton] = {}
        self._camera_group = QButtonGroup(self)
        self._camera_group.setExclusive(True)
        for preset in CameraPreset:
            btn = QToolButton(row)
            btn.setText(f"{_CAMERA_LABEL[preset]} ({_CAMERA_KEY[preset]})")
            btn.setObjectName(f"Scene3DCamera_{preset.value}")
            btn.setCheckable(True)
            self._camera_group.addButton(btn)
            btn.toggled.connect(lambda checked, p=preset: self._on_camera_toggled(p, checked))
            h.addWidget(btn)
            self._camera_buttons[preset] = btn
        h.addStretch(1)
        return row

    def _build_canvas(self) -> QWidget:
        canvas = QFrame(self)
        canvas.setObjectName("Scene3DCanvas")
        canvas.setFrameShape(QFrame.Shape.StyledPanel)
        canvas.setMinimumSize(320, 240)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("3D canvas (Phase 4.10.x mounts the PyVista QtInteractor)")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("color: #777;")
        cl.addWidget(hint)
        return canvas

    def _build_layer_panel(self) -> QGroupBox:
        box = QGroupBox("Layers", self)
        box.setObjectName("Scene3DLayers")
        v = QVBoxLayout(box)
        self._layer_checks: dict[SceneLayer, QCheckBox] = {}
        for layer in SceneLayer:
            cb = QCheckBox(layer.value.replace("_", " "), box)
            cb.setObjectName(f"Scene3DLayer_{layer.value}")
            cb.setChecked(layer in _DEFAULT_ON)
            cb.toggled.connect(
                lambda checked, lyr=layer: self.layer_visibility_changed.emit(lyr, checked)
            )
            v.addWidget(cb)
            self._layer_checks[layer] = cb
        v.addStretch(1)
        return box

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------
    def _on_camera_toggled(self, preset: CameraPreset, checked: bool) -> None:
        if not checked:
            return
        self.camera_preset_chosen.emit(preset)

    # ------------------------------------------------------------------
    # Public API / Test helpers
    # ------------------------------------------------------------------
    def select_camera(self, preset: CameraPreset) -> None:
        btn = self._camera_buttons[preset]
        if not btn.isChecked():
            btn.setChecked(True)

    def camera_button(self, preset: CameraPreset) -> QToolButton:
        return self._camera_buttons[preset]

    def layer_check(self, layer: SceneLayer) -> QCheckBox:
        return self._layer_checks[layer]
