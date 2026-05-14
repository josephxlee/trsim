"""Phase 4 P7 Editor preview tests (RadarEditor / TargetsEditor / AtmospherePanel)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg

from workbench.ui.editor.atmosphere_panel.widget import AtmospherePanel
from workbench.ui.editor.radar_editor.widget import RadarEditor
from workbench.ui.editor.targets_editor.widget import MOTION_KINDS, TargetsEditor

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Radar beam pattern preview
# ---------------------------------------------------------------------


def test_radar_editor_beam_pattern_mounts_pyqtgraph(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = RadarEditor()
    qtbot.addWidget(ed)
    preview = ed.findChild(pg.PlotWidget, "BeamPatternPlot")
    assert preview is not None


def test_radar_beam_preview_default_curve_is_populated(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = RadarEditor()
    qtbot.addWidget(ed)
    # The plot widget hosts the beam curve as the first PlotDataItem
    # on its main ViewBox.
    plot = ed.findChild(pg.PlotWidget, "BeamPatternPlot")
    assert plot is not None
    items = plot.listDataItems()
    assert len(items) >= 1
    xs, ys = items[0].getData()
    assert xs is not None and xs.size > 0
    # Peak gain at boresight is ~0 dB.
    assert max(ys) >= -0.01


# ---------------------------------------------------------------------
# Targets trajectory preview
# ---------------------------------------------------------------------


def test_targets_editor_mounts_trajectory_plot(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    plot = ed.trajectory_preview().plot_widget()
    assert isinstance(plot, pg.PlotWidget)
    assert plot.objectName() == "TrajectoryPlot"


def test_targets_trajectory_swaps_with_motion_kind(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    # Default trajectory has data (AIRCRAFT init).
    curve = ed.trajectory_preview().curve()
    east_before, _ = curve.getData()
    assert east_before is not None
    # Pick a different kind via the combo — the preview must change.
    ed.motion_combo().setCurrentText("BALLISTIC")
    east_after, _ = curve.getData()
    # The two arrays should differ (different synthetic paths).
    assert east_after[10] != pytest.approx(east_before[10])


def test_targets_trajectory_all_motion_kinds_renderable(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    preview = ed.trajectory_preview()
    for kind in MOTION_KINDS:
        preview.set_motion_kind(kind)
        east, north = preview.curve().getData()
        assert east is not None
        assert north is not None
        assert east.size == north.size


def test_targets_set_trajectory_explicit_path(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    preview = ed.trajectory_preview()
    preview.set_trajectory([0.0, 100.0, 200.0], [0.0, 50.0, -50.0])
    east, north = preview.curve().getData()
    assert list(east) == pytest.approx([0.0, 100.0, 200.0])
    assert list(north) == pytest.approx([0.0, 50.0, -50.0])


def test_targets_set_trajectory_rejects_length_mismatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    with pytest.raises(ValueError, match=r"length mismatch"):
        ed.trajectory_preview().set_trajectory([0.0, 1.0], [0.0])


def test_targets_set_trajectory_empty_clears_curve(qtbot) -> None:  # type: ignore[no-untyped-def]
    ed = TargetsEditor()
    qtbot.addWidget(ed)
    ed.trajectory_preview().set_trajectory([], [])
    east, _ = ed.trajectory_preview().curve().getData()
    assert east is None or len(east) == 0


# ---------------------------------------------------------------------
# Atmosphere preview
# ---------------------------------------------------------------------


def test_atmosphere_preview_mounts_pyqtgraph(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = AtmospherePanel()
    qtbot.addWidget(panel)
    assert isinstance(panel.preview_plot(), pg.PlotWidget)
    assert panel.preview_plot().objectName() == "AtmospherePreviewPlot"


def test_atmosphere_preview_curve_populated_at_construction(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = AtmospherePanel()
    qtbot.addWidget(panel)
    xs, ys = panel.preview_curve().getData()
    assert xs is not None
    assert xs.size > 0
    # Rain rate 0 -> attenuation may be small but the array is populated.
    assert ys.size == xs.size


def test_atmosphere_preview_curve_responds_to_rain_rate(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = AtmospherePanel()
    qtbot.addWidget(panel)
    # Set rain rate to a heavy value -> attenuation should rise.
    _, ys_dry = panel.preview_curve().getData()
    panel.rain_rate_edit().setText("25.0")
    panel.rain_rate_edit().editingFinished.emit()
    _, ys_heavy = panel.preview_curve().getData()
    # Peak attenuation must increase (or at minimum: differ).
    assert max(ys_heavy) > max(ys_dry)
