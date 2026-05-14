"""Scene3DPanel L4 live PyVista actors API tests (headless mode)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.app.simulator import MockSceneGenerator
from workbench.ui.simulator.panels import Scene3DPanel

pytestmark = pytest.mark.qt


def _headless_panel(qtbot) -> Scene3DPanel:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
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
