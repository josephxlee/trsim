"""3D Scene panel (Phase 4.10 + L4 live PyVista actors, plan/05 § 5.3.2).

Hosts the 3rd-person view of terrain + radar + targets. Phase 4 L4
(2026-05-14) wires the panel to
:class:`workbench.ui.simulator.scene_controller.SimulatorSceneController`
which paints a :class:`MockSceneFrame` on every QTimer tick.

Lazy PyVista mount
------------------

Constructing a :class:`pyvistaqt.QtInteractor` requires an OpenGL
context, which headless CI sandboxes do not have. The panel accepts
an ``enable_3d_viewer: bool`` constructor kwarg (default ``True``);
``False`` skips QtInteractor creation entirely and leaves a status
QLabel in its place. Tests pass ``enable_3d_viewer=False`` to stay
on the cheap path; production callers (``trsim ui``) leave it at the
default. This mirrors the PhysicsLab :class:`TestObject3DPanel`
pattern from PL-9.1d.

State pushed by the controller
------------------------------

- :meth:`set_scene_frame(frame)` — replace the rendered radar /
  target actors at the given sim-time. The terrain placeholder is
  refreshed only when its half-span changes.
- :meth:`set_frame(idx)` — update the header frame counter.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QResizeEvent, QShortcut
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

if TYPE_CHECKING:
    from workbench.app.simulator import MockSceneFrame


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

_RADAR_MARKER_RADIUS_M: float = 80.0
_TARGET_MARKER_RADIUS_M: float = 60.0

#: Resize-settle debounce [ms]. The embedded VTK window is redrawn this
#: long after the last resize event, once Qt has reflowed the layout to
#: the final geometry — rendering inline in ``resizeEvent`` is too early
#: (the interactor is still at its old size) and leaves a stale ghost.
_RESIZE_RENDER_DEBOUNCE_MS: int = 50

#: RADAR camera preset — eye at the radar (ENU origin, slightly raised)
#: looking north toward the target orbit. ``[position, focal point, up]``.
_RADAR_CAMERA_POSITION: list[tuple[float, float, float]] = [
    (0.0, 0.0, 150.0),
    (0.0, 4000.0, 500.0),
    (0.0, 0.0, 1.0),
]


class Scene3DPanel(QWidget):
    """3rd-person 3D scene panel with lazy PyVista canvas (L4)."""

    camera_preset_chosen = Signal(CameraPreset)
    layer_visibility_changed = Signal(SceneLayer, bool)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        enable_3d_viewer: bool = True,
        interactor_factory: Callable[[QWidget], QWidget] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Scene3DPanel")
        self._enable_3d_viewer = enable_3d_viewer
        self._interactor_factory = interactor_factory
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("Scene3DFrameLabel")
        self._status_label = QLabel("3D canvas (Phase 4.10.x mounts the PyVista QtInteractor)")
        self._status_label.setObjectName("Scene3DStatusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_label.setStyleSheet("color: #777;")
        self._interactor: Any = None  # pyvistaqt.QtInteractor (or fake) when enabled
        self._terrain_actor: Any | None = None
        self._radar_actor: Any | None = None
        self._target_actor: Any | None = None
        self._terrain_halfspan_m: float | None = None

        # Resize-settle debounce — coalesces a maximise / drag burst
        # into a single VTK redraw once the layout reaches its final
        # geometry. See ``resizeEvent`` for why an inline render fails.
        self._resize_render_timer = QTimer(self)
        self._resize_render_timer.setSingleShot(True)
        self._resize_render_timer.setInterval(_RESIZE_RENDER_DEBOUNCE_MS)
        self._resize_render_timer.timeout.connect(self._render_interactor)

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
        self._camera_shortcuts: dict[CameraPreset, QShortcut] = {}
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
            # Keyboard shortcut (T/L/F/R). Scoped to this panel + its
            # children so it fires even when the embedded VTK canvas
            # holds focus, but not when focus is in another workspace.
            shortcut = QShortcut(QKeySequence(_CAMERA_KEY[preset]), self)
            shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            shortcut.activated.connect(lambda p=preset: self.select_camera(p))
            self._camera_shortcuts[preset] = shortcut
        h.addStretch(1)
        h.addWidget(self._frame_label)
        return row

    def _build_canvas(self) -> QWidget:
        canvas = QFrame(self)
        canvas.setObjectName("Scene3DCanvas")
        canvas.setFrameShape(QFrame.Shape.StyledPanel)
        canvas.setMinimumSize(320, 240)
        cl = QVBoxLayout(canvas)
        cl.setContentsMargins(0, 0, 0, 0)
        if self._enable_3d_viewer:
            if self._interactor_factory is not None:
                # Test seam — a fake QWidget interactor that records
                # add_mesh / remove_actor / render without an OpenGL
                # context. Production callers leave the factory unset.
                self._interactor = self._interactor_factory(canvas)
            else:
                # Local import so headless test runs (which set
                # ``enable_3d_viewer=False`` everywhere) never touch
                # the PyVista / pyvistaqt OpenGL stack.
                from pyvistaqt import QtInteractor

                self._interactor = QtInteractor(canvas)
            self._interactor.setObjectName("Scene3DInteractor")
            # Click + wheel trackball interaction needs StrongFocus so
            # the interactor sees mouse press / wheel events; without
            # this the inner VTK render window receives keyboard /
            # wheel input only after a click, and on some Qt setups not
            # at all. Mouse-tracking ensures hover motion reaches it
            # immediately for camera spin / pan.
            self._interactor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            self._interactor.setMouseTracking(True)
            cl.addWidget(self._interactor)
        else:
            cl.addWidget(self._status_label)
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
        self._apply_camera_preset(preset)
        self.camera_preset_chosen.emit(preset)

    def _apply_camera_preset(self, preset: CameraPreset) -> None:
        """Move the embedded VTK camera to the chosen preset.

        No-op in headless mode (no interactor). Without this the preset
        buttons / shortcuts only toggled state and emitted a signal —
        nothing consumed it, so the 3D view never actually moved.
        """
        if self._interactor is None:
            return
        if preset is CameraPreset.TOP:
            self._interactor.view_xy()
        elif preset is CameraPreset.LEFT:
            self._interactor.view_yz()
        elif preset is CameraPreset.FREE:
            self._interactor.view_isometric()
        elif preset is CameraPreset.RADAR:
            self._interactor.camera_position = _RADAR_CAMERA_POSITION
        self._interactor.render()

    # ------------------------------------------------------------------
    # Phase 4 L4 live scene API
    # ------------------------------------------------------------------
    def set_scene_frame(self, frame: MockSceneFrame) -> None:
        """Replace the radar / target actors at the given sim-time.

        When ``enable_3d_viewer=False`` the call is a no-op aside
        from updating the status label so headless tests can still
        observe that a frame was received.
        """
        if not self._enable_3d_viewer or self._interactor is None:
            self._status_label.setText(
                "3D canvas (headless) "
                f"radar=({frame.radar_position_enu_m[0]:.0f},"
                f"{frame.radar_position_enu_m[1]:.0f},"
                f"{frame.radar_position_enu_m[2]:.0f}) "
                f"target=({frame.target_position_enu_m[0]:.0f},"
                f"{frame.target_position_enu_m[1]:.0f},"
                f"{frame.target_position_enu_m[2]:.0f})"
            )
            return
        # Lazy import so the rest of the module survives without
        # PyVista on the import path.
        import pyvista as pv

        # Refresh the terrain placeholder only when its size changes.
        if frame.terrain_halfspan_m != self._terrain_halfspan_m:
            if self._terrain_actor is not None:
                self._interactor.remove_actor(self._terrain_actor)
            terrain = pv.Plane(
                center=(0.0, 0.0, 0.0),
                direction=(0.0, 0.0, 1.0),
                i_size=2.0 * frame.terrain_halfspan_m,
                j_size=2.0 * frame.terrain_halfspan_m,
            )
            self._terrain_actor = self._interactor.add_mesh(
                terrain, color="lightgray", opacity=0.4, show_edges=False
            )
            self._terrain_halfspan_m = frame.terrain_halfspan_m

        # Radar + target markers are created once and then moved via
        # the actor transform on every frame. Recreating the mesh +
        # actor per tick churns VTK needlessly and would not scale to
        # DEM terrain + many targets.
        self._radar_actor = self._ensure_marker(
            self._radar_actor, radius=_RADAR_MARKER_RADIUS_M, color="orange"
        )
        self._radar_actor.position = tuple(frame.radar_position_enu_m.tolist())
        self._target_actor = self._ensure_marker(
            self._target_actor, radius=_TARGET_MARKER_RADIUS_M, color="red"
        )
        self._target_actor.position = tuple(frame.target_position_enu_m.tolist())

        # ``.position`` updates the actor transform but, unlike
        # ``add_mesh``, does not trigger a redraw — render explicitly.
        self._interactor.render()

    def _ensure_marker(self, actor: Any | None, *, radius: float, color: str) -> Any:
        """Return ``actor``, creating a sphere marker on first use.

        The sphere is built at the origin; per-frame motion is applied
        through the actor ``position`` transform by the caller.
        """
        if actor is not None:
            return actor
        # Lazy import so the module survives without PyVista installed.
        import pyvista as pv

        mesh = pv.Sphere(radius=radius)
        return self._interactor.add_mesh(mesh, color=color)

    def set_frame(self, frame_index: int) -> None:
        """Update the header frame counter."""
        self._frame_label.setText(f"frame: {frame_index}")

    def resizeEvent(self, event: QResizeEvent) -> None:  # noqa: N802 — Qt API
        """Schedule a VTK redraw once the resize settles.

        The embedded VTK render window is a native surface outside
        Qt's compositing pipeline. Rendering inline here is too early —
        Qt has not yet reflowed the layout, so the interactor is still
        at its old geometry and the redraw lands at the wrong size,
        leaving a stale ghost after a maximise-then-shrink. Restarting a
        short single-shot timer debounces the resize burst so the redraw
        runs once, after the layout has reached its final geometry.
        """
        super().resizeEvent(event)
        if self._interactor is not None:
            self._resize_render_timer.start()

    def _render_interactor(self) -> None:
        """Redraw the embedded VTK window (resize-settle timer callback)."""
        if self._interactor is not None:
            self._interactor.render()

    # ------------------------------------------------------------------
    # Public API / Test helpers
    # ------------------------------------------------------------------
    def select_camera(self, preset: CameraPreset) -> None:
        btn = self._camera_buttons[preset]
        if not btn.isChecked():
            btn.setChecked(True)

    def camera_button(self, preset: CameraPreset) -> QToolButton:
        return self._camera_buttons[preset]

    def camera_shortcut(self, preset: CameraPreset) -> QShortcut:
        return self._camera_shortcuts[preset]

    def layer_check(self, layer: SceneLayer) -> QCheckBox:
        return self._layer_checks[layer]

    def frame_label(self) -> QLabel:
        return self._frame_label

    def status_label(self) -> QLabel:
        return self._status_label

    def is_3d_viewer_enabled(self) -> bool:
        return self._enable_3d_viewer

    def interactor(self) -> Any | None:
        """The wrapped :class:`pyvistaqt.QtInteractor` when enabled, else ``None``."""
        return self._interactor

    def radar_actor(self) -> Any | None:
        return self._radar_actor

    def target_actor(self) -> Any | None:
        return self._target_actor

    def terrain_actor(self) -> Any | None:
        return self._terrain_actor
