"""Scene3DPanel L4 live PyVista actors API tests (headless mode)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QSize
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QApplication, QWidget

from workbench.app.simulator import MockSceneGenerator
from workbench.ui.simulator.panels import CameraPreset, Scene3DPanel

pytestmark = pytest.mark.qt


class _FakeActor:
    """Stand-in for a pyvista.Actor — exposes a settable transform position."""

    def __init__(self) -> None:
        self.position: tuple[float, float, float] = (0.0, 0.0, 0.0)


class _FakeInteractor(QWidget):
    """Headless QtInteractor stand-in recording add_mesh / remove_actor / render.

    Lets the live Scene3DPanel actor path run without an OpenGL context
    so the per-frame actor lifecycle is unit-testable in headless CI.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.add_mesh_calls = 0
        self.remove_actor_calls = 0
        self.render_calls = 0
        self.last_mesh: object = None
        self.last_kwargs: dict[str, object] = {}
        self.last_removed: object = None
        self.view_calls: list[str] = []
        self.camera_position: object = None

    def add_mesh(self, mesh: object, **kwargs: object) -> _FakeActor:
        self.add_mesh_calls += 1
        self.last_mesh = mesh
        self.last_kwargs = kwargs
        return _FakeActor()

    def remove_actor(self, actor: object) -> None:
        self.remove_actor_calls += 1
        self.last_removed = actor

    def render(self) -> None:
        self.render_calls += 1

    def view_xy(self) -> None:
        self.view_calls.append("xy")

    def view_yz(self) -> None:
        self.view_calls.append("yz")

    def view_isometric(self) -> None:
        self.view_calls.append("isometric")


def _headless_panel(qtbot) -> Scene3DPanel:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    return p


def _live_fake_panel(qtbot) -> Scene3DPanel:  # type: ignore[no-untyped-def]
    """A Scene3DPanel with the OpenGL interactor replaced by a fake."""
    p = Scene3DPanel(enable_3d_viewer=True, interactor_factory=_FakeInteractor)
    qtbot.addWidget(p)
    return p


def test_enable_3d_viewer_false_leaves_interactor_none(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _headless_panel(qtbot)
    assert p.is_3d_viewer_enabled() is False
    assert p.interactor() is None
    assert p.radar_actor() is None
    assert p.target_actor() is None
    assert p.terrain_actor() is None


def test_set_scene_frame_updates_status_label_in_headless_mode(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _headless_panel(qtbot)
    frame = MockSceneGenerator().scene_for(0.0)
    p.set_scene_frame(frame)
    # Headless path -> no actor; the status label now describes the
    # most recent radar+target ENU positions instead of the default
    # 'mounts the PyVista QtInteractor' hint.
    txt = p.status_label().text()
    assert "headless" in txt
    assert "radar=" in txt
    assert "target=" in txt
    # Actors stay None — set_scene_frame must not have touched VTK.
    assert p.radar_actor() is None
    assert p.target_actor() is None


def test_headless_set_scene_frame_idempotent(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Calling set_scene_frame twice without enabling the viewer is safe."""
    p = _headless_panel(qtbot)
    gen = MockSceneGenerator()
    p.set_scene_frame(gen.scene_for(0.0))
    first = p.status_label().text()
    p.set_scene_frame(gen.scene_for(0.0))
    assert p.status_label().text() == first


def test_set_frame_updates_header_counter(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _headless_panel(qtbot)
    p.set_frame(42)
    assert "42" in p.frame_label().text()


def test_headless_panel_status_label_contains_default_hint(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Before any set_scene_frame call, the placeholder hint is shown."""
    p = _headless_panel(qtbot)
    assert "mounts the PyVista QtInteractor" in p.status_label().text()


# ---------------------------------------------------------------------
# Live actor lifecycle (fake interactor — no OpenGL)
# ---------------------------------------------------------------------


def test_markers_created_once_not_per_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Radar + target markers are made once, not recreated every frame."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    gen = MockSceneGenerator()
    for sim_t in (0.0, 1.0, 2.0, 3.0, 4.0):
        p.set_scene_frame(gen.scene_for(sim_t))
    # terrain + radar + target = exactly 3 add_mesh calls across 5
    # frames — the refactor must not recreate markers per tick.
    assert fake.add_mesh_calls == 3
    assert fake.remove_actor_calls == 0


def test_marker_position_tracks_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Each frame moves the same actor instances via the transform."""
    p = _live_fake_panel(qtbot)
    gen = MockSceneGenerator()
    frame = gen.scene_for(3.0)
    p.set_scene_frame(frame)
    assert p.radar_actor().position == tuple(frame.radar_position_enu_m.tolist())
    assert p.target_actor().position == tuple(frame.target_position_enu_m.tolist())
    radar_before = p.radar_actor()
    target_before = p.target_actor()
    frame2 = gen.scene_for(7.5)
    p.set_scene_frame(frame2)
    # Same actor objects — only the transform changed.
    assert p.radar_actor() is radar_before
    assert p.target_actor() is target_before
    assert p.target_actor().position == tuple(frame2.target_position_enu_m.tolist())


def test_set_scene_frame_renders_each_call(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``.position`` updates need an explicit render — one per frame."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    fake.render_calls = 0
    gen = MockSceneGenerator()
    p.set_scene_frame(gen.scene_for(0.0))
    p.set_scene_frame(gen.scene_for(1.0))
    assert fake.render_calls == 2


def test_resize_triggers_interactor_render(qtbot) -> None:  # type: ignore[no-untyped-def]
    """resizeEvent schedules a debounced VTK redraw so resize leaves no ghost."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    before = fake.render_calls
    QApplication.sendEvent(p, QResizeEvent(QSize(642, 391), QSize(517, 343)))
    # The redraw fires on the resize-settle timer, not inline.
    qtbot.waitUntil(lambda: fake.render_calls > before, timeout=1000)


def test_resize_render_is_debounced(qtbot) -> None:  # type: ignore[no-untyped-def]
    """A resize burst coalesces into a single settle render."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    fake.render_calls = 0
    for width in (400, 500, 600, 700):
        QApplication.sendEvent(p, QResizeEvent(QSize(width, 300), QSize(300, 300)))
    qtbot.wait(150)  # > _RESIZE_RENDER_DEBOUNCE_MS
    assert fake.render_calls == 1


def test_headless_resize_is_safe(qtbot) -> None:  # type: ignore[no-untyped-def]
    """resizeEvent is a no-op with no interactor — must not raise."""
    p = _headless_panel(qtbot)
    QApplication.sendEvent(p, QResizeEvent(QSize(800, 600), QSize(640, 480)))
    qtbot.wait(150)
    assert p.interactor() is None


def test_camera_preset_moves_interactor(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Selecting a preset actually moves the embedded VTK camera."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    p.select_camera(CameraPreset.TOP)
    assert fake.view_calls[-1] == "xy"
    p.select_camera(CameraPreset.LEFT)
    assert fake.view_calls[-1] == "yz"
    p.select_camera(CameraPreset.FREE)
    assert fake.view_calls[-1] == "isometric"
    p.select_camera(CameraPreset.RADAR)
    assert fake.camera_position is not None


def test_camera_shortcut_moves_interactor(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The keyboard shortcut path drives the camera, not just the button."""
    p = _live_fake_panel(qtbot)
    fake = p.interactor()
    p.camera_shortcut(CameraPreset.TOP).activated.emit()
    assert fake.view_calls[-1] == "xy"
