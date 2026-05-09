"""StageTimingProbe — measure per-stage frame latency (plan/18 § 18.17).

Phase 3.6 — context-manager that captures
``time.perf_counter_ns()`` at enter / exit, accumulates the elapsed
time per stage, and exposes the samples for the FrameProfiler.

Usage pattern::

    profiler = FrameProfiler()
    with StageTimingProbe(profiler, stage_name="detector"):
        detector.run(...)
    with StageTimingProbe(profiler, stage_name="tracker"):
        tracker.step(...)

The probe emits one sample per ``__exit__``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover — circular avoidance
    from workbench.app.timing.frame_profiler import FrameProfiler


@dataclass(slots=True)
class StageTimingProbe:
    """Context manager — records one duration sample on exit.

    Attributes:
        profiler: Sink that receives the sample on context exit.
        stage_name: Free-text identifier (``"detector"`` /
            ``"tracker"`` / ``"pipeline_total"``).
    """

    profiler: FrameProfiler
    stage_name: str
    _start_ns: int = 0

    def __enter__(self) -> StageTimingProbe:
        self._start_ns = time.perf_counter_ns()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        elapsed_ns = time.perf_counter_ns() - self._start_ns
        # Suppress no exception; record sample even if the body raised
        # so the profiler's percentiles see the worst case.
        self.profiler.record_sample(self.stage_name, elapsed_ns)
