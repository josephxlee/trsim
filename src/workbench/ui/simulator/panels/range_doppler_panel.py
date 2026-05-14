"""Range-Doppler heatmap panel (Phase 4.9, plan/05 § 5.3) + L3 live pyqtgraph plot.

Phase 4 L3 (2026-05-14) replaces the Phase 4.9 placeholder canvas
with a :class:`pyqtgraph.PlotWidget` hosting a single
:class:`pyqtgraph.ImageItem`. The image is calibrated to the
range-axis (m) and doppler-axis (m/s) supplied by
:class:`workbench.ui.simulator.rd_controller.SimulatorRDController`
on every QTimer tick. The Phase 4.9 header-strip API
(:meth:`set_frame`) is preserved.

Axes:

- The image's X axis is doppler (m/s) and the Y axis is range (m),
  matching standard radar Range-Doppler conventions (target Doppler
  on the horizontal, range on the vertical).
- The cell at row ``r`` / column ``d`` corresponds to the range
  bin at ``range_axis_m[r]`` and the doppler bin at
  ``doppler_axis_mps[d]``.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

_DEFAULT_LEVELS_DB: tuple[float, float] = (-70.0, -10.0)
_PEAK_PEN: str = "#ffd43b"


class RangeDopplerPanel(QWidget):
    """2-D Range-Doppler heatmap with a live array-pushing API."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RangeDopplerPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Range-Doppler")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("RangeDopplerFrameLabel")
        header.addWidget(self._frame_label)
        layout.addLayout(header)

        # pyqtgraph PlotWidget hosts the ImageItem; ImageItem stays
        # row-major so heatmap[r, d] indexes (range bin, doppler bin).
        self._plot = pg.PlotWidget(self)
        self._plot.setObjectName("RangeDopplerPlot")
        self._plot.setLabel("left", "range", units="m")
        self._plot.setLabel("bottom", "doppler", units="m/s")
        self._plot.setMinimumHeight(160)
        self._image = pg.ImageItem(axisOrder="row-major")
        self._plot.addItem(self._image)
        # Default to a perceptually uniform colour map (viridis).
        # pyqtgraph >=0.13 exposes ``colormap.get`` for the matplotlib
        # palettes; fall back to the built-in cyclic map if the call
        # is unavailable at runtime.
        try:
            cmap = pg.colormap.get("viridis")
        except (KeyError, AttributeError):
            cmap = pg.colormap.get("CET-L9")
        if cmap is not None:
            self._image.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
        self._image.setLevels(_DEFAULT_LEVELS_DB)

        # Peak cross-hair (vertical doppler line + horizontal range
        # line). Hidden until ``set_peak`` is called.
        self._peak_range_line = pg.InfiniteLine(
            angle=0, pen=pg.mkPen(_PEAK_PEN, style=Qt.PenStyle.DashLine), movable=False
        )
        self._peak_doppler_line = pg.InfiniteLine(
            angle=90, pen=pg.mkPen(_PEAK_PEN, style=Qt.PenStyle.DashLine), movable=False
        )
        self._peak_range_line.hide()
        self._peak_doppler_line.hide()
        self._plot.addItem(self._peak_range_line)
        self._plot.addItem(self._peak_doppler_line)

        layout.addWidget(self._plot, 1)

        # Cache of the most recent axes so a re-paint that only
        # supplies the heatmap can still compute the ImageItem rect.
        self._range_axis_m: NDArray[np.float64] | None = None
        self._doppler_axis_mps: NDArray[np.float64] | None = None

    # ------------------------------------------------------------------
    # Phase 4.9 header API (unchanged)
    # ------------------------------------------------------------------
    def set_frame(self, frame_index: int) -> None:
        self._frame_label.setText(f"frame: {frame_index}")

    def frame_label(self) -> QLabel:
        return self._frame_label

    # ------------------------------------------------------------------
    # Phase 4 L3 live heatmap API
    # ------------------------------------------------------------------
    def set_heatmap(
        self,
        heatmap_db: NDArray[np.float64],
        range_axis_m: NDArray[np.float64],
        doppler_axis_mps: NDArray[np.float64],
        *,
        levels_db: tuple[float, float] | None = None,
    ) -> None:
        """Replace the heatmap data + axis calibration in one shot.

        Args:
            heatmap_db: 2-D array of shape ``(n_range, n_doppler)`` in dB.
            range_axis_m: 1-D range axis [m], non-decreasing, length
                ``n_range``.
            doppler_axis_mps: 1-D doppler axis [m/s], non-decreasing,
                length ``n_doppler``.
            levels_db: ``(low, high)`` dB clamp for the colour map; if
                omitted the previously set levels remain unchanged.

        Raises:
            ValueError: If shapes do not match or arrays are not the
                expected dimensionality.
        """
        if heatmap_db.ndim != 2:
            msg = f"heatmap_db must be 2-D, got ndim={heatmap_db.ndim}"
            raise ValueError(msg)
        if range_axis_m.ndim != 1:
            msg = f"range_axis_m must be 1-D, got ndim={range_axis_m.ndim}"
            raise ValueError(msg)
        if doppler_axis_mps.ndim != 1:
            msg = f"doppler_axis_mps must be 1-D, got ndim={doppler_axis_mps.ndim}"
            raise ValueError(msg)
        if heatmap_db.shape != (range_axis_m.size, doppler_axis_mps.size):
            msg = (
                f"heatmap_db shape {heatmap_db.shape} does not match "
                f"(range_axis_m.size, doppler_axis_mps.size) = "
                f"({range_axis_m.size}, {doppler_axis_mps.size})"
            )
            raise ValueError(msg)
        self._image.setImage(heatmap_db, autoLevels=False)
        if levels_db is not None:
            self._image.setLevels(levels_db)
        # Calibrate the ImageItem rect to the supplied axes so the
        # pyqtgraph axis ticks land in [m] and [m/s] rather than bin
        # indices. doppler -> X, range -> Y.
        x0 = float(doppler_axis_mps[0])
        x1 = float(doppler_axis_mps[-1])
        y0 = float(range_axis_m[0])
        y1 = float(range_axis_m[-1])
        self._image.setRect(x0, y0, x1 - x0, y1 - y0)
        self._range_axis_m = range_axis_m
        self._doppler_axis_mps = doppler_axis_mps

    def set_peak(self, peak_range_m: float, peak_doppler_mps: float) -> None:
        """Show the peak cross-hair at ``(range, doppler)``."""
        self._peak_range_line.setPos(peak_range_m)
        self._peak_doppler_line.setPos(peak_doppler_mps)
        self._peak_range_line.show()
        self._peak_doppler_line.show()

    def clear_peak(self) -> None:
        """Hide the peak cross-hair."""
        self._peak_range_line.hide()
        self._peak_doppler_line.hide()

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def plot_widget(self) -> pg.PlotWidget:
        return self._plot

    def image_item(self) -> pg.ImageItem:
        return self._image

    def peak_range_line(self) -> pg.InfiniteLine:
        return self._peak_range_line

    def peak_doppler_line(self) -> pg.InfiniteLine:
        return self._peak_doppler_line

    def range_axis_m(self) -> NDArray[np.float64] | None:
        return self._range_axis_m

    def doppler_axis_mps(self) -> NDArray[np.float64] | None:
        return self._doppler_axis_mps
