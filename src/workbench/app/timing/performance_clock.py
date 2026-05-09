"""PerformanceClock — wall-clock pacing for real_time / reference modes.

Phase 3.6 — wraps the simulation thread's frame loop with a
wall-clock target. In ``real_time`` mode the loop sleeps to keep
each frame at ``frame_dt_s`` of wall-clock; in ``reference`` mode it
sleeps to match the user-supplied ``target_latency_ms`` from a
:class:`workbench.domain.timing.reference_timing.StageTimingProfile`.

This module deliberately does NOT spawn its own thread — the caller
(CLI / Phase 4 simulation thread) drives the loop. We just expose a
helper that computes how long to sleep given a target frame budget
and the elapsed wall-time so far.
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(slots=True)
class PerformanceClock:
    """Frame-pacing helper.

    Attributes:
        target_frame_budget_s: Wall-clock budget per frame [s]. Must
            be > 0. ``0`` would request an infinitely fast loop —
            we reject so the bug surfaces in tests.
    """

    target_frame_budget_s: float

    def __post_init__(self) -> None:
        if self.target_frame_budget_s <= 0.0:
            msg = f"target_frame_budget_s must be > 0, got {self.target_frame_budget_s}"
            raise ValueError(msg)

    def sleep_remaining(self, frame_start_ns: int) -> float:
        """Sleep for the remainder of the frame budget.

        Args:
            frame_start_ns: ``time.perf_counter_ns()`` captured at
                frame start (just before the body started running).

        Returns:
            Seconds actually slept (0 if the frame budget already
            elapsed).
        """
        elapsed_ns = time.perf_counter_ns() - frame_start_ns
        budget_ns = int(self.target_frame_budget_s * 1e9)
        remaining_ns = budget_ns - elapsed_ns
        if remaining_ns <= 0:
            return 0.0
        time.sleep(remaining_ns / 1e9)
        return remaining_ns / 1e9

    @classmethod
    def from_target_latency_ms(cls, target_latency_ms: float) -> PerformanceClock:
        """Build a clock from a per-frame target [ms]."""
        return cls(target_frame_budget_s=target_latency_ms / 1000.0)

    @classmethod
    def from_frame_rate_hz(cls, frame_rate_hz: float) -> PerformanceClock:
        """Build a clock from a target frame rate [Hz]."""
        if frame_rate_hz <= 0.0:
            msg = f"frame_rate_hz must be > 0, got {frame_rate_hz}"
            raise ValueError(msg)
        return cls(target_frame_budget_s=1.0 / frame_rate_hz)
