"""Profile-mode aware stage timing probe gate (Phase 3 Q4).

Wraps :class:`StageTimingProbe` with a :class:`ProfileMode` check so
production runs (``mode == ProfileMode.OFF``) pay zero per-stage
overhead. ``explicit`` and ``live`` both return a real probe — the
distinction between them lives in the caller (CLI vs Pipeline run).

Usage::

    from workbench.app.timing import gated_stage_probe
    from workbench.domain.timing import ProfileMode

    with gated_stage_probe(ProfileMode.LIVE, profiler, "detector"):
        detector.run(...)

When ``mode == ProfileMode.OFF`` the context body still runs; only the
``perf_counter_ns()`` pair and the ``profiler.record_sample`` call are
skipped (~200 ns/stage savings per plan/18 § 18.17.5 Q-RT4).
"""

from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext
from typing import TYPE_CHECKING, Any

from workbench.app.timing.stage_timing_probe import StageTimingProbe
from workbench.domain.timing import ProfileMode

if TYPE_CHECKING:  # pragma: no cover — runtime import not needed
    from workbench.app.timing.frame_profiler import FrameProfiler


def gated_stage_probe(
    mode: ProfileMode,
    profiler: FrameProfiler,
    stage_name: str,
) -> AbstractContextManager[Any]:
    """Return a :class:`StageTimingProbe` or a no-op context per ``mode``.

    Args:
        mode: Runtime :class:`ProfileMode` value. ``OFF`` returns
            :func:`contextlib.nullcontext`; ``EXPLICIT`` / ``LIVE``
            return a real :class:`StageTimingProbe`.
        profiler: Sink for the timing sample (unused when ``mode`` is
            ``OFF``).
        stage_name: Free-text stage identifier.
    """
    if mode is ProfileMode.OFF:
        return nullcontext()
    return StageTimingProbe(profiler=profiler, stage_name=stage_name)
