"""FrameBoundaryDetector — auto-frame inference (plan/18 § 18.16, Q-RT1).

Phase 3.6 — when ``TimingConfig.frame_unit == "auto"``, the App
infers a frame boundary off the *track output* signal: every time
the test code emits a final track decision, that's one frame.

This implementation is a thin counter — call :meth:`on_track_output`
each time the tracker stage emits a track. Returns ``True`` on every
call (each output is a frame boundary at MVP — the multi-target /
batched-output cases are MVP+alpha).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class FrameBoundaryDetector:
    """Track-output trigger frame counter.

    Attributes:
        frame_id: Current frame counter (starts at 0; first
            ``on_track_output`` call returns ``True`` and increments to 1).
    """

    frame_id: int = 0

    def on_track_output(self) -> bool:
        """Mark a frame boundary; bump the counter.

        Returns:
            ``True`` — every track output starts a new frame at MVP.
            (Plan/18 reserves a more nuanced detector for multi-target
            / batched-output runs in MVP+alpha.)
        """
        self.frame_id += 1
        return True

    def reset(self) -> None:
        """Reset the counter to 0 (use when starting a new Run)."""
        self.frame_id = 0
