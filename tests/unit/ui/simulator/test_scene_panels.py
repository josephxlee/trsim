"""Unit tests for Scene3DPanel + ScopePOVPanel (Phase 4.10)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.panels import (
    CameraPreset,
    Scene3DPanel,
    SceneLayer,
    ScopePOVPanel,
)

pytestmark = pytest.mark.qt


# ---------- Scene3DPanel ----------


def test_scene3d_has_one_button_per_camera_preset(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    for preset in CameraPreset:
        btn = p.camera_button(preset)
        assert btn.objectName() == f"Scene3DCamera_{preset.value}"
        assert btn.isCheckable() is True


def test_scene3d_select_camera_emits_preset(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    received: list[CameraPreset] = []
    p.camera_preset_chosen.connect(received.append)
    p.select_camera(CameraPreset.TOP)
    assert received == [CameraPreset.TOP]
    p.select_camera(CameraPreset.RADAR)
    assert received[-1] is CameraPreset.RADAR


def test_scene3d_camera_buttons_are_exclusive(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    p.select_camera(CameraPreset.LEFT)
    p.select_camera(CameraPreset.FREE)
    checked = [pre for pre in CameraPreset if p.camera_button(pre).isChecked()]
    assert checked == [CameraPreset.FREE]


def test_scene3d_layer_toggle_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    received: list[tuple[SceneLayer, bool]] = []
    p.layer_visibility_changed.connect(lambda lyr, v: received.append((lyr, v)))
    p.layer_check(SceneLayer.MULTIPATH_RAYS).setChecked(True)
    p.layer_check(SceneLayer.TERRAIN).setChecked(False)
    assert received == [(SceneLayer.MULTIPATH_RAYS, True), (SceneLayer.TERRAIN, False)]


def test_scene3d_default_layers_match_plan_05(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Scene3DPanel(enable_3d_viewer=False)
    qtbot.addWidget(p)
    expected_on = {
        SceneLayer.TERRAIN,
        SceneLayer.SEA,
        SceneLayer.BUILDINGS,
        SceneLayer.SHIPS,
        SceneLayer.TX_BEAM_ACTUAL,
        SceneLayer.GT_TARGETS,
        SceneLayer.TRACKS,
        SceneLayer.PRIMARY_HIGHLIGHT,
    }
    for layer in SceneLayer:
        expected = layer in expected_on
        assert p.layer_check(layer).isChecked() is expected


# ---------- ScopePOVPanel ----------


def test_scope_pov_default_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ScopePOVPanel()
    qtbot.addWidget(p)
    assert "AZ actual / cmd / lag" in p.az_label().text()
    assert "--" in p.az_label().text()


def test_scope_pov_set_pointing_formats_lag(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ScopePOVPanel()
    qtbot.addWidget(p)
    p.set_pointing(actual_az_deg=183.4, commanded_az_deg=182.0)
    txt = p.az_label().text()
    assert "183.40" in txt
    assert "182.00" in txt
    assert "+1.40" in txt
