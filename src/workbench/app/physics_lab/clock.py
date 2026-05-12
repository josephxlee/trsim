"""PhysicsClock — drives the Physics Lab time axis (PL-D, plan/19 § 19.6.5).

Single source of truth for ``current_time_s`` + ``frame_id`` in the
Physics Lab workspace. The clock owns only the time state; the
caller (controller / UI) is responsible for stepping individual
simulators with the ``dt_s`` returned by :meth:`tick`.

plan/19 § 19.6 prescribes four modes (Static / Run / Compare /
Sweep). PL-D wires the Run mode — fixed-rate playback with a
per-tick callback. Compare / Sweep arrive in Phase 9.1.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClockTick:
    """One time-step descriptor emitted by :meth:`PhysicsClock.tick`.

    Attributes:
        dt_s: Elapsed seconds since the previous tick.
        time_s: Total elapsed simulation seconds since reset.
        frame_id: Monotonic 0-indexed counter.
    """

    dt_s: float
    time_s: float
    frame_id: int


class PhysicsClock:
    """Discrete time stepper for the Physics Lab.

    Attributes:
        dt_s: Default step size each :meth:`tick` advances by.

    Raises:
        ValueError: For non-positive ``dt_s``.
    """

    def __init__(self, *, dt_s: float = 0.02) -> None:
        if dt_s <= 0.0:
            msg = f"PhysicsClock.dt_s must be > 0, got {dt_s}"
            raise ValueError(msg)
        self.dt_s = dt_s
        self._time_s: float = 0.0
        self._frame_id: int = 0
        self._running: bool = False

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def time_s(self) -> float:
        return self._time_s

    @property
    def frame_id(self) -> int:
        return self._frame_id

    @property
    def is_running(self) -> bool:
        return self._running

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Begin emitting ticks; idempotent."""
        self._running = True

    def pause(self) -> None:
        """Stop emitting ticks; preserves ``time_s`` and ``frame_id``."""
        self._running = False

    def stop(self) -> None:
        """Pause + reset both time and frame counter to zero."""
        self._running = False
        self._time_s = 0.0
        self._frame_id = 0

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def tick(self) -> ClockTick | None:
        """Advance one step. Returns ``None`` when paused / stopped.

        The ``ClockTick`` carries the dt the caller should hand to the
        simulator; this clock does not call into the simulator itself
        so the caller stays free to fan-out to multiple simulations.
        """
        if not self._running:
            return None
        self._frame_id += 1
        self._time_s += self.dt_s
        return ClockTick(dt_s=self.dt_s, time_s=self._time_s, frame_id=self._frame_id)

    def run_for(self, n_frames: int, callback: Callable[[ClockTick], None]) -> int:
        """Convenience helper: synchronously emit ``n_frames`` ticks.

        Used by tests (and by the headless "drive simulator for N
        frames" mode). Sets ``running`` to True before iterating so
        callers don't have to call :meth:`start` first.

        Returns the number of ticks actually emitted (always equal to
        ``n_frames`` for a well-formed call; the early exit on
        pause-mid-callback is for safety).
        """
        if n_frames < 0:
            msg = f"n_frames must be >= 0, got {n_frames}"
            raise ValueError(msg)
        self._running = True
        emitted = 0
        for _ in range(n_frames):
            ev = self.tick()
            if ev is None:
                break
            callback(ev)
            emitted += 1
        return emitted
