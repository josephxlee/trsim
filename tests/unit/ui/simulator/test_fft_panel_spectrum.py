"""FFTPanel pyqtgraph spectrum API tests (Phase 4 L2)."""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg

from workbench.ui.simulator.panels import FFTPanel

pytestmark = pytest.mark.qt


def _panel(qtbot) -> FFTPanel:  # type: ignore[no-untyped-def]
    p = FFTPanel()
    qtbot.addWidget(p)
    return p


def test_panel_mounts_pyqtgraph_plot_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert isinstance(p.plot_widget(), pg.PlotWidget)
    assert p.plot_widget().objectName() == "FFTPanelPlot"


def test_panel_has_two_named_curves(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert isinstance(p.up_curve(), pg.PlotDataItem)
    assert isinstance(p.down_curve(), pg.PlotDataItem)
    assert p.up_curve() is not p.down_curve()


def test_peak_markers_hidden_by_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert p.up_peak_marker().isVisible() is False
    assert p.down_peak_marker().isVisible() is False
    assert "0 up / 0 down" in p.peaks_label().text()


def test_set_spectrum_populates_both_curves(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    freqs = np.linspace(0.0, 1.0e6, 64, dtype=np.float64)
    up = np.full_like(freqs, -50.0)
    down = np.full_like(freqs, -45.0)
    p.set_spectrum(freqs, up, down)
    # PlotDataItem.getData() returns (x, y) tuple.
    up_x, up_y = p.up_curve().getData()
    down_x, down_y = p.down_curve().getData()
    np.testing.assert_array_equal(up_x, freqs)
    np.testing.assert_array_equal(up_y, up)
    np.testing.assert_array_equal(down_x, freqs)
    np.testing.assert_array_equal(down_y, down)


def test_set_spectrum_rejects_ndim_mismatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    freqs2d = np.zeros((4, 4), dtype=np.float64)
    with pytest.raises(ValueError, match=r"freqs_hz must be 1-D"):
        p.set_spectrum(freqs2d, freqs2d, freqs2d)


def test_set_spectrum_rejects_up_shape_mismatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    freqs = np.zeros(8, dtype=np.float64)
    bad = np.zeros(7, dtype=np.float64)
    good = np.zeros(8, dtype=np.float64)
    with pytest.raises(ValueError, match=r"up_mag_db shape"):
        p.set_spectrum(freqs, bad, good)


def test_set_spectrum_rejects_down_shape_mismatch(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    freqs = np.zeros(8, dtype=np.float64)
    good = np.zeros(8, dtype=np.float64)
    bad = np.zeros(7, dtype=np.float64)
    with pytest.raises(ValueError, match=r"down_mag_db shape"):
        p.set_spectrum(freqs, good, bad)


def test_set_peak_freqs_shows_markers_and_updates_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_peak_freqs(8.0e5, 7.0e5)
    assert p.up_peak_marker().isVisible() is True
    assert p.down_peak_marker().isVisible() is True
    assert p.up_peak_marker().value() == pytest.approx(8.0e5)
    assert p.down_peak_marker().value() == pytest.approx(7.0e5)
    assert "1 up / 1 down" in p.peaks_label().text()


def test_clear_peak_freqs_hides_markers(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_peak_freqs(8.0e5, 7.0e5)
    p.clear_peak_freqs()
    assert p.up_peak_marker().isVisible() is False
    assert p.down_peak_marker().isVisible() is False
    assert "0 up / 0 down" in p.peaks_label().text()


def test_header_set_frame_and_peak_counts_still_work(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The Phase 4.9 header API survives the L2 pyqtgraph integration."""
    p = _panel(qtbot)
    p.set_frame(99)
    p.set_peak_counts(2, 3)
    assert "99" in p.frame_label().text()
    assert "2 up / 3 down" in p.peaks_label().text()
