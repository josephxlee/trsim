"""Per-stage timing breakdown widget (Phase 4.12)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

# plan/18 § 18.17 - the canonical pipeline stages tracked by the
# Frame Profiler. Order matters: it dictates display order.
PIPELINE_STAGES: tuple[str, ...] = (
    "Transmitter",
    "Environment",
    "Receiver",
    "Detector",
    "Pairing",
    "Tracker",
)


class TimingBreakdownPanel(QWidget):
    """Visual avg-time-per-stage bar chart using QProgressBars."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TimingBreakdownPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("Stage Timing (avg us)")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        body = QGroupBox(self)
        body.setObjectName("TimingBreakdownBody")
        form = QFormLayout(body)
        self._bars: dict[str, QProgressBar] = {}
        for stage in PIPELINE_STAGES:
            bar = QProgressBar(body)
            bar.setObjectName(f"TimingBar_{stage}")
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setFormat("%v / %m us")
            bar.setMinimumWidth(180)
            form.addRow(stage, bar)
            self._bars[stage] = bar
        layout.addWidget(body, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_stage_timings(self, timings_us: dict[str, float]) -> None:
        """Update bar values. ``timings_us`` keys must be PIPELINE_STAGES."""
        if not timings_us:
            return
        max_us = max(timings_us.values())
        scale_max = max(int(max_us * 1.2), 100)
        for stage, value in timings_us.items():
            if stage not in self._bars:
                msg = f"unknown pipeline stage {stage!r}; expected one of {PIPELINE_STAGES}"
                raise ValueError(msg)
            bar = self._bars[stage]
            bar.setRange(0, scale_max)
            bar.setValue(int(value))

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def stage_bar(self, stage: str) -> QProgressBar:
        return self._bars[stage]
