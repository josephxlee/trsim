"""Radar POV (Scope) panel (Phase 4.10 + L6 live cross-hair canvas).

Phase 4 L6 replaces the Phase 4.10 placeholder canvas with a
:class:`pyqtgraph.PlotWidget` that paints a boresight cross-hair
plus a single target marker. The marker position is supplied in
normalized scope coordinates (each component in ``[-1, 1]``,
boresight = origin) by
:class:`workbench.ui.simulator.scope_controller.SimulatorScopeController`.

The AZ readout API (``set_pointing``) is unchanged.
"""

from __future__ import annotations

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

_BORESIGHT_PEN: str = "#888"
_TARGET_PEN: str = "#ff6b6b"
_TARGET_BRUSH: str = "#ff6b6b"


class ScopePOVPanel(QWidget):
    """Boresight POV panel with a live cross-hair canvas."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScopePOVPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Radar POV (Scope)")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._az_label = QLabel("AZ actual / cmd / lag: -- / -- / --")
        self._az_label.setObjectName("ScopePOVAzLabel")
        header.addWidget(self._az_label)
        layout.addLayout(header)

        # pyqtgraph PlotWidget — boresight cross-hair + target dot.
        self._plot = pg.PlotWidget(self)
        self._plot.setObjectName("ScopePOVPlot")
        self._plot.setMinimumSize(240, 240)
        self._plot.setAspectLocked(lock=True, ratio=1.0)
        self._plot.setXRange(-1.0, 1.0, padding=0)
        self._plot.setYRange(-1.0, 1.0, padding=0)
        self._plot.hideAxis("left")
        self._plot.hideAxis("bottom")
        self._plot.setMouseEnabled(x=False, y=False)
        # Cross-hair at the boresight.
        self._v_line = pg.InfiniteLine(angle=90, pen=pg.mkPen(_BORESIGHT_PEN))
        self._h_line = pg.InfiniteLine(angle=0, pen=pg.mkPen(_BORESIGHT_PEN))
        self._v_line.setPos(0.0)
        self._h_line.setPos(0.0)
        self._plot.addItem(self._v_line)
        self._plot.addItem(self._h_line)
        # Target marker — single-point ScatterPlotItem.
        self._target_marker = pg.ScatterPlotItem(
            size=14,
            pen=pg.mkPen(_TARGET_PEN, width=2),
            brush=pg.mkBrush(_TARGET_BRUSH),
        )
        self._target_marker.setData([], [])
        self._target_visible = False
        self._plot.addItem(self._target_marker)
        layout.addWidget(self._plot, 1)

        # Background hint stays for the "no data yet" state — the label
        # is overlaid below the plot's axes when ``set_target_norm``
        # has not been called.
        self._hint_label = QLabel("(no target — start the simulator)")
        self._hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._hint_label.setStyleSheet("color: #777;")
        layout.addWidget(self._hint_label)

    # ------------------------------------------------------------------
    # Phase 4.10 AZ-readout API (unchanged)
    # ------------------------------------------------------------------
    def set_pointing(
        self,
        actual_az_deg: float,
        commanded_az_deg: float,
    ) -> None:
        lag = actual_az_deg - commanded_az_deg
        self._az_label.setText(
            f"AZ actual / cmd / lag: {actual_az_deg:.2f} / {commanded_az_deg:.2f} / {lag:+.2f}"
        )

    def az_label(self) -> QLabel:
        return self._az_label

    # ------------------------------------------------------------------
    # Phase 4 L6 live cross-hair API
    # ------------------------------------------------------------------
    def set_target_norm(self, x: float, y: float) -> None:
        """Move the target marker to ``(x, y)`` in normalized scope coords.

        Both components are clamped to ``[-1, 1]``. The first call
        also hides the "no target yet" hint label.
        """
        x_clamped = max(-1.0, min(1.0, x))
        y_clamped = max(-1.0, min(1.0, y))
        self._target_marker.setData([x_clamped], [y_clamped])
        if not self._target_visible:
            self._hint_label.hide()
            self._target_visible = True

    def clear_target(self) -> None:
        """Hide the target marker + bring back the hint label."""
        self._target_marker.setData([], [])
        if self._target_visible:
            self._hint_label.show()
            self._target_visible = False

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def plot_widget(self) -> pg.PlotWidget:
        return self._plot

    def target_marker(self) -> pg.ScatterPlotItem:
        return self._target_marker

    def hint_label(self) -> QLabel:
        return self._hint_label

    def is_target_visible(self) -> bool:
        return self._target_visible
