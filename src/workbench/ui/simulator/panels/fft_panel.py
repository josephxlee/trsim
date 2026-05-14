"""FFT spectrum panel (Phase 4.9, plan/05 § 5.3.4) + L2 live pyqtgraph plot.

Phase 4 L2 (2026-05-13) replaces the Phase 4.9 placeholder canvas
with a live :class:`pyqtgraph.PlotWidget`. The panel now hosts two
named curves (``"up"`` for the up-sweep beats, ``"down"`` for the
down-sweep beats) and exposes a small array-pushing API so the
:class:`workbench.ui.simulator.fft_controller.SimulatorFFTController`
can drive it on every QTimer tick:

- :meth:`set_spectrum` — replace the two curves' samples.
- :meth:`set_peak_freqs` — annotate the up/down peak markers and
  refresh the header peak count.

The header-strip API (``set_frame``, ``set_peak_counts``) from Phase
4.9 is preserved so existing tests still pass.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

_UP_CURVE_COLOR: str = "#d62728"  # red
_DOWN_CURVE_COLOR: str = "#1f77b4"  # blue
_UP_PEAK_PEN: str = "#ff6b6b"
_DOWN_PEAK_PEN: str = "#74c0fc"


class FFTPanel(QWidget):
    """Up/down sweep FFT spectra plot with live array-pushing API."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("FFTPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Header strip with frame number + peak count.
        header = QHBoxLayout()
        title = QLabel("FFT Spectrum")
        title.setObjectName("FFTPanelTitle")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._frame_label = QLabel("frame: -")
        self._frame_label.setObjectName("FFTPanelFrameLabel")
        self._peaks_label = QLabel("peaks: 0 up / 0 down")
        self._peaks_label.setObjectName("FFTPanelPeaksLabel")
        header.addWidget(self._frame_label)
        header.addSpacing(12)
        header.addWidget(self._peaks_label)
        layout.addLayout(header)

        # pyqtgraph plot canvas with two curves (up=red, down=blue).
        self._plot = pg.PlotWidget(self)
        self._plot.setObjectName("FFTPanelPlot")
        self._plot.setLabel("left", "magnitude", units="dB")
        self._plot.setLabel("bottom", "beat frequency", units="Hz")
        self._plot.showGrid(x=True, y=True, alpha=0.3)
        self._plot.addLegend(offset=(-10, 10))
        self._plot.setMinimumHeight(160)
        self._up_curve: pg.PlotDataItem = self._plot.plot(
            [], [], pen=pg.mkPen(_UP_CURVE_COLOR, width=2), name="up sweep"
        )
        self._down_curve: pg.PlotDataItem = self._plot.plot(
            [], [], pen=pg.mkPen(_DOWN_CURVE_COLOR, width=2), name="down sweep"
        )
        # Vertical peak markers (InfiniteLine instances, hidden until
        # ``set_peak_freqs`` is called). DashLine matches Qt's enum so
        # PySide6's strict-typed ``QPen.setStyle`` accepts the pen.
        self._up_peak_marker = pg.InfiniteLine(
            angle=90,
            pen=pg.mkPen(_UP_PEAK_PEN, style=Qt.PenStyle.DashLine),
            movable=False,
        )
        self._down_peak_marker = pg.InfiniteLine(
            angle=90,
            pen=pg.mkPen(_DOWN_PEAK_PEN, style=Qt.PenStyle.DashLine),
            movable=False,
        )
        self._up_peak_marker.hide()
        self._down_peak_marker.hide()
        self._plot.addItem(self._up_peak_marker)
        self._plot.addItem(self._down_peak_marker)

        layout.addWidget(self._plot, 1)

    # ------------------------------------------------------------------
    # Phase 4.9 header API (unchanged)
    # ------------------------------------------------------------------
    def set_frame(self, frame_index: int) -> None:
        self._frame_label.setText(f"frame: {frame_index}")

    def set_peak_counts(self, up: int, down: int) -> None:
        self._peaks_label.setText(f"peaks: {up} up / {down} down")

    # ------------------------------------------------------------------
    # Phase 4 L2 live spectrum API
    # ------------------------------------------------------------------
    def set_spectrum(
        self,
        freqs_hz: NDArray[np.float64],
        up_mag_db: NDArray[np.float64],
        down_mag_db: NDArray[np.float64],
    ) -> None:
        """Replace the two curves' samples in one shot.

        Args:
            freqs_hz: 1-D frequency axis, length N, non-decreasing.
            up_mag_db: Up-sweep magnitudes, length N.
            down_mag_db: Down-sweep magnitudes, length N.

        Raises:
            ValueError: If shapes do not match or arrays are not 1-D.
        """
        if freqs_hz.ndim != 1:
            msg = f"freqs_hz must be 1-D, got ndim={freqs_hz.ndim}"
            raise ValueError(msg)
        if up_mag_db.shape != freqs_hz.shape:
            msg = (
                f"up_mag_db shape {up_mag_db.shape} does not match freqs_hz shape {freqs_hz.shape}"
            )
            raise ValueError(msg)
        if down_mag_db.shape != freqs_hz.shape:
            msg = (
                f"down_mag_db shape {down_mag_db.shape} does not match "
                f"freqs_hz shape {freqs_hz.shape}"
            )
            raise ValueError(msg)
        self._up_curve.setData(freqs_hz, up_mag_db)
        self._down_curve.setData(freqs_hz, down_mag_db)

    def set_peak_freqs(self, up_peak_hz: float, down_peak_hz: float) -> None:
        """Position the two vertical peak markers + refresh the header.

        Both peak markers are made visible by this call. To hide them
        again call :meth:`clear_peak_freqs`.
        """
        self._up_peak_marker.setPos(up_peak_hz)
        self._down_peak_marker.setPos(down_peak_hz)
        self._up_peak_marker.show()
        self._down_peak_marker.show()
        self.set_peak_counts(1, 1)

    def clear_peak_freqs(self) -> None:
        """Hide both peak markers and reset the header count to 0/0."""
        self._up_peak_marker.hide()
        self._down_peak_marker.hide()
        self.set_peak_counts(0, 0)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def frame_label(self) -> QLabel:
        return self._frame_label

    def peaks_label(self) -> QLabel:
        return self._peaks_label

    def plot_widget(self) -> pg.PlotWidget:
        return self._plot

    def up_curve(self) -> pg.PlotDataItem:
        return self._up_curve

    def down_curve(self) -> pg.PlotDataItem:
        return self._down_curve

    def up_peak_marker(self) -> pg.InfiniteLine:
        return self._up_peak_marker

    def down_peak_marker(self) -> pg.InfiniteLine:
        return self._down_peak_marker
