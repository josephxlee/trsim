"""Reference Timing + Frame Profiler UI (Phase 4.12, plan/18 § 18.16/17).

Three widgets cover the Frame Profiler workflow:

- :class:`TimingBreakdownPanel` - per-stage bar chart of avg time.
- :class:`ScaleIndicator` - tiny strip readout ("scale: 0.57x")
  meant for the simulator toolbar.
- :class:`ProfileReport` - tabular FrameTimingReport with avg / p50 /
  p95 / p99 columns.

The composite :class:`ProfilerPanel` mounts all three plus a
"Run Profile" / "Set Reference Timing" action row. Phase 5+ wires the
real :class:`workbench.app.timing.FrameProfiler` data feed.
"""

from __future__ import annotations

from workbench.ui.simulator.profiler_panel.profile_report import (
    PROFILE_REPORT_COLUMNS,
    ProfileReport,
)
from workbench.ui.simulator.profiler_panel.scale_indicator import ScaleIndicator
from workbench.ui.simulator.profiler_panel.timing_breakdown import (
    PIPELINE_STAGES,
    TimingBreakdownPanel,
)
from workbench.ui.simulator.profiler_panel.widget import ProfilerPanel

__all__ = [
    "PIPELINE_STAGES",
    "PROFILE_REPORT_COLUMNS",
    "ProfileReport",
    "ProfilerPanel",
    "ScaleIndicator",
    "TimingBreakdownPanel",
]
