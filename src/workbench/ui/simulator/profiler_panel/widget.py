"""Composite ProfilerPanel widget (Phase 4.12)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.simulator.profiler_panel.profile_report import ProfileReport
from workbench.ui.simulator.profiler_panel.scale_indicator import ScaleIndicator
from workbench.ui.simulator.profiler_panel.timing_breakdown import TimingBreakdownPanel


class ProfilerPanel(QWidget):
    """Profiler tab content - Profile/Reference actions + 3 sub-views."""

    run_profile_requested = Signal()
    set_reference_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ProfilerPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._build_action_row())

        self._timing_breakdown = TimingBreakdownPanel(self)
        self._profile_report = ProfileReport(self)
        body = QSplitter(Qt.Orientation.Horizontal, self)
        body.setObjectName("ProfilerPanelSplitter")
        body.setChildrenCollapsible(False)
        body.addWidget(self._timing_breakdown)
        body.addWidget(self._profile_report)
        body.setSizes([260, 360])
        layout.addWidget(body, 1)
        self._splitter = body

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Frame Profiler")
        title.setStyleSheet("font-weight: 600;")
        h.addWidget(title)
        h.addStretch(1)
        self._scale_indicator = ScaleIndicator(self)
        h.addWidget(self._scale_indicator)
        h.addSpacing(12)
        run_btn = QPushButton("Run Profile (100 frames)", row)
        run_btn.setObjectName("ProfilerRunBtn")
        run_btn.clicked.connect(self.run_profile_requested)
        ref_btn = QPushButton("Set Reference Timing...", row)
        ref_btn.setObjectName("ProfilerSetReferenceBtn")
        ref_btn.clicked.connect(self.set_reference_requested)
        h.addWidget(run_btn)
        h.addWidget(ref_btn)
        return row

    # ------------------------------------------------------------------
    # Public API / Test helpers
    # ------------------------------------------------------------------
    def timing_breakdown(self) -> TimingBreakdownPanel:
        return self._timing_breakdown

    def profile_report(self) -> ProfileReport:
        return self._profile_report

    def scale_indicator(self) -> ScaleIndicator:
        return self._scale_indicator

    def splitter(self) -> QSplitter:
        return self._splitter
