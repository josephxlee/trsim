"""Profile mode toggle (Phase 3 Q4, plan/03 § 3.5.0c).

The Profile mode controls when the
:class:`workbench.app.timing.frame_profiler.FrameProfiler` is allowed
to record a stage-timing sample:

==========  =================================================================
mode        behaviour
==========  =================================================================
``off``     No stage timings are recorded. The Profiler reports an empty
            stage list. Use when the runtime overhead of the profiler is
            unacceptable (low-latency real-time runs).
``explicit`` Recording only happens when the caller explicitly calls
            ``ProfileGate.allow_next_frame()`` before the frame starts.
            Useful for diagnostic runs where the user wants to sample
            every Nth frame from the CLI / UI.
``live``    Every frame is recorded (the canonical Phase 5.11/5.13
            behaviour the FrameProfiler was originally written for).
==========  =================================================================

The domain layer exposes the :class:`ProfileMode` StrEnum + the
``ProfileGate`` class so the App-layer profile runner + the CLI flag
share one definition.

Phase 3 originally listed this toggle as ``Q4`` — the open MVP
question whether the profiler should default-on or default-off. The
present implementation: ``ProfileGate`` defaults to ``LIVE`` (matching
the existing Phase 5 behaviour) and a CLI ``--mode`` flag lets users
opt into ``off`` / ``explicit``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ProfileMode(StrEnum):
    """Phase 3 Profile mode tri-state (plan/03 § 3.5.0c)."""

    OFF = "off"
    EXPLICIT = "explicit"
    LIVE = "live"


@dataclass(slots=True)
class ProfileGate:
    """Decide whether a frame's stage timing should be recorded.

    The gate is **mutable** by design — explicit mode toggles a
    per-frame ``_one_shot`` flag that the runtime flips on demand,
    then the gate flips it back off the moment ``should_record()``
    returns ``True``.

    Attributes:
        mode: Current :class:`ProfileMode`. The constructor's
            ``mode`` kwarg seeds this field; in-place mutation via
            :meth:`set_mode` keeps the gate live for the rest of
            the run.
    """

    mode: ProfileMode = ProfileMode.LIVE
    _one_shot: bool = field(default=False, init=False, repr=False)

    def set_mode(self, mode: ProfileMode) -> None:
        """Replace the current mode; clears any pending one-shot."""
        self.mode = mode
        self._one_shot = False

    def allow_next_frame(self) -> None:
        """Arm a single-frame recording when ``mode == EXPLICIT``.

        Calling this in any other mode is a no-op (LIVE always
        records, OFF never records).
        """
        if self.mode is ProfileMode.EXPLICIT:
            self._one_shot = True

    def should_record(self) -> bool:
        """Consume the gate's permission to record the next frame.

        Returns ``True`` exactly when the frame may be recorded:

        - ``LIVE`` — always ``True``.
        - ``OFF`` — always ``False``.
        - ``EXPLICIT`` — ``True`` only when a prior call to
          :meth:`allow_next_frame` has armed the gate; the call
          clears the armed flag so the next call returns ``False``
          again until the caller re-arms.

        The method is the only consumer of the internal one-shot
        latch; callers must invoke it exactly once per frame.
        """
        if self.mode is ProfileMode.LIVE:
            return True
        if self.mode is ProfileMode.OFF:
            return False
        # EXPLICIT: consume the latch.
        if self._one_shot:
            self._one_shot = False
            return True
        return False
