"""Simulator Workspace shell (Phase 4.9, plan/05 § 5.2).

Phase 4.9 layout:

::

    +------------------+----------------+--------------+
    | PluginManager    | FFT            | Properties   |
    | (left col)       +----------------+              |
    |                  | RangeDoppler   |              |
    +------------------+----------------+--------------+
    | Tabs: Run | Stage I/O                            |
    +-----------------------------------------------------+

The 3D Scene View (plan/05 § 5.3.2) is intentionally absent here
until Phase 4.10 mounts the PyVista interactor in place of one of the
center plots.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.simulator.panels import (
    FFTPanel,
    PluginManagerPanel,
    PropertiesPanel,
    RangeDopplerPanel,
    RunPanel,
    StageIOPanel,
)


class SimulatorWorkspace(QWidget):
    """Composite simulator view with six runtime panels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SimulatorWorkspace")

        # Build panels.
        self._fft_panel = FFTPanel(self)
        self._range_doppler_panel = RangeDopplerPanel(self)
        self._run_panel = RunPanel(self)
        self._properties_panel = PropertiesPanel(self)
        self._plugin_manager_panel = PluginManagerPanel(self)
        self._stage_io_panel = StageIOPanel(self)

        # Center column - FFT on top, RD below.
        center = QSplitter(Qt.Orientation.Vertical, self)
        center.setObjectName("SimulatorCenterSplitter")
        center.setChildrenCollapsible(False)
        center.addWidget(self._fft_panel)
        center.addWidget(self._range_doppler_panel)
        center.setSizes([260, 260])

        # Top row - plugin manager | center column | properties.
        top_row = QSplitter(Qt.Orientation.Horizontal, self)
        top_row.setObjectName("SimulatorTopRowSplitter")
        top_row.setChildrenCollapsible(False)
        top_row.addWidget(self._plugin_manager_panel)
        top_row.addWidget(center)
        top_row.addWidget(self._properties_panel)
        top_row.setStretchFactor(0, 0)
        top_row.setStretchFactor(1, 1)
        top_row.setStretchFactor(2, 0)
        top_row.setSizes([260, 700, 280])

        # Bottom tabs - Run / Stage I/O.
        bottom_tabs = QTabWidget(self)
        bottom_tabs.setObjectName("SimulatorBottomTabs")
        bottom_tabs.addTab(self._run_panel, "Run")
        bottom_tabs.addTab(self._stage_io_panel, "Stage I/O")

        # Outer vertical splitter pairs top row + bottom tabs.
        outer = QSplitter(Qt.Orientation.Vertical, self)
        outer.setObjectName("SimulatorOuterSplitter")
        outer.setChildrenCollapsible(False)
        outer.addWidget(top_row)
        outer.addWidget(bottom_tabs)
        outer.setStretchFactor(0, 1)
        outer.setStretchFactor(1, 0)
        outer.setSizes([520, 220])
        self._outer_splitter = outer
        self._top_splitter = top_row
        self._center_splitter = center
        self._bottom_tabs = bottom_tabs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(outer)

    # ------------------------------------------------------------------
    # Test helpers / Phase 5+ wiring
    # ------------------------------------------------------------------
    def fft_panel(self) -> FFTPanel:
        return self._fft_panel

    def range_doppler_panel(self) -> RangeDopplerPanel:
        return self._range_doppler_panel

    def run_panel(self) -> RunPanel:
        return self._run_panel

    def properties_panel(self) -> PropertiesPanel:
        return self._properties_panel

    def plugin_manager_panel(self) -> PluginManagerPanel:
        return self._plugin_manager_panel

    def stage_io_panel(self) -> StageIOPanel:
        return self._stage_io_panel

    def bottom_tabs(self) -> QTabWidget:
        return self._bottom_tabs
