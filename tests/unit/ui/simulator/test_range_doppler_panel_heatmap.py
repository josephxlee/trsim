"""RangeDopplerPanel pyqtgraph heatmap API tests (Phase 4 L3)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg

from workbench.ui.simulator.panels import RangeDopplerPanel

pytestmark = pytest.mark.qt


def _panel(qtbot) -> RangeDopplerPanel:  # type: ignore[no-untyped-def]
    p = RangeDopplerPanel()
    qtbot.addWidget(p)
    return p


def test_panel_mounts_plot_with_image_item(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert isinstance(p.plot_widget(), pg.PlotWidget)
    assert p.plot_widget().objectName() == "RangeDopplerPlot"
    assert isinstance(p.image_item(), pg.ImageItem)


def test_peak_lines_hidden_by_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert p.peak_range_line().isVisible() is False
    assert p.peak_doppler_line().isVisible() is False


def test_set_heatmap_populates_image(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    n_r, n_d = 16, 8
    r = np.linspace(0.0, 1_000.0, n_r, dtype=np.float64)
    d = np.linspace(-20.0, 20.0, n_d, dtype=np.float64)
    heat = np.full((n_r, n_d), -50.0, dtype=np.float64)
    heat[8, 4] = -10.0
    p.set_heatmap(heat, r, d)
    img = p.image_item().image
    assert img is not None
    np.testing.assert_array_equal(img, heat)
    cached_r = p.range_axis_m()
    cached_d = p.doppler_axis_mps()
    assert cached_r is not None
    assert cached_d is not None
    np.testing.assert_array_equal(cached_r, r)
    np.testing.assert_array_equal(cached_d, d)


def test_set_heatmap_calibrates_image_rect(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    r = np.array([100.0, 200.0, 300.0, 400.0, 500.0, 600.0, 700.0, 800.0])
    d = np.array([-10.0, -5.0, 0.0, 5.0, 10.0, 15.0, 20.0, 25.0])
    heat = np.zeros((8, 8), dtype=np.float64)
    p.set_heatmap(heat, r, d)
    # pyqtgraph's ``ImageItem.setRect`` installs a QTransform that
    # maps pixel coords -> data coords. Map the local boundingRect
    # through the item transform to recover the scene-space rect.
    item = p.image_item()
    mapped = item.mapRectToParent(item.boundingRect())
    # X axis = doppler [-10, 25], Y axis = range [100, 800].
    assert mapped.x() == pytest.approx(-10.0)
    assert mapped.y() == pytest.approx(100.0)
    assert mapped.width() == pytest.approx(35.0)
    assert mapped.height() == pytest.approx(700.0)


def test_set_heatmap_applies_levels(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    n_r, n_d = 8, 8
    r = np.linspace(0.0, 1_000.0, n_r, dtype=np.float64)
    d = np.linspace(-10.0, 10.0, n_d, dtype=np.float64)
    heat = np.zeros((n_r, n_d), dtype=np.float64)
    p.set_heatmap(heat, r, d, levels_db=(-30.0, -5.0))
    lo, hi = p.image_item().levels
    assert lo == pytest.approx(-30.0)
    assert hi == pytest.approx(-5.0)


def test_set_heatmap_rejects_1d_input(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    r = np.zeros(8, dtype=np.float64)
    d = np.zeros(8, dtype=np.float64)
    flat = np.zeros(64, dtype=np.float64)
    with pytest.raises(ValueError, match=r"heatmap_db must be 2-D"):
        p.set_heatmap(flat, r, d)


def test_set_heatmap_rejects_axis_shape_mismatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    r = np.zeros(8, dtype=np.float64)
    d = np.zeros(8, dtype=np.float64)
    heat = np.zeros((4, 8), dtype=np.float64)
    with pytest.raises(ValueError, match=r"heatmap_db shape"):
        p.set_heatmap(heat, r, d)


def test_set_heatmap_rejects_2d_range_axis(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    r2d = np.zeros((4, 2), dtype=np.float64)
    d = np.zeros(8, dtype=np.float64)
    heat = np.zeros((8, 8), dtype=np.float64)
    with pytest.raises(ValueError, match=r"range_axis_m must be 1-D"):
        p.set_heatmap(heat, r2d, d)


def test_set_heatmap_rejects_2d_doppler_axis(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    r = np.zeros(8, dtype=np.float64)
    d2d = np.zeros((4, 2), dtype=np.float64)
    heat = np.zeros((8, 8), dtype=np.float64)
    with pytest.raises(ValueError, match=r"doppler_axis_mps must be 1-D"):
        p.set_heatmap(heat, r, d2d)


def test_set_peak_shows_crosshair(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_peak(peak_range_m=300.0, peak_doppler_mps=12.5)
    assert p.peak_range_line().isVisible() is True
    assert p.peak_doppler_line().isVisible() is True
    assert p.peak_range_line().value() == pytest.approx(300.0)
    assert p.peak_doppler_line().value() == pytest.approx(12.5)


def test_clear_peak_hides_crosshair(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_peak(300.0, 0.0)
    p.clear_peak()
    assert p.peak_range_line().isVisible() is False
    assert p.peak_doppler_line().isVisible() is False


def test_header_set_frame_still_works(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_frame(123)
    assert "123" in p.frame_label().text()
