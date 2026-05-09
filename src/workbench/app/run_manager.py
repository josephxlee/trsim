"""RunManager — Target Run state machine (plan/04 § 4.3, v0.14).

Phase 3.2 — wraps :class:`workbench.domain.types.RunState` and
:class:`workbench.domain.types.RunTerminationReason` into the
inner-layer Run lifecycle (the v0.15 two-layer time model).

State transitions:

- IDLE -> RUNNING (start)
- RUNNING -> PAUSED (pause)
- PAUSED -> RUNNING (resume)
- RUNNING / PAUSED -> ENDED (stop / completion / sim_stopped / error)
- ENDED -> IDLE (reset before next start)

The RunManager doesn't itself drive trajectories — it tracks the
state and the termination reason so the App / CLI / UI know what to
report. Trajectory replay belongs to the Pipeline (Phase 2.10).
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.domain.types import RunState, RunTerminationReason


@dataclass(slots=True)
class RunManager:
    """Target Run lifecycle state machine.

    Attributes:
        state: Current run state.
        termination_reason: Set when ``state == ENDED``; ``None`` otherwise.
        run_id: Optional identifier for the run (assigned at start by
            the App layer; ``""`` when no run is active).
    """

    state: RunState = RunState.IDLE
    termination_reason: RunTerminationReason | None = None
    run_id: str = ""

    def start(self, run_id: str) -> None:
        """IDLE -> RUNNING. ``run_id`` must be non-empty.

        Raises:
            ValueError: If ``run_id`` is empty.
            RuntimeError: If state is not IDLE.
        """
        if not run_id:
            msg = "run_id must be a non-empty string"
            raise ValueError(msg)
        if self.state is not RunState.IDLE:
            msg = f"RunManager.start: invalid state {self.state.value}"
            raise RuntimeError(msg)
        self.run_id = run_id
        self.state = RunState.RUNNING
        self.termination_reason = None

    def pause(self) -> None:
        """RUNNING -> PAUSED."""
        if self.state is not RunState.RUNNING:
            msg = f"RunManager.pause: invalid state {self.state.value}"
            raise RuntimeError(msg)
        self.state = RunState.PAUSED

    def resume(self) -> None:
        """PAUSED -> RUNNING."""
        if self.state is not RunState.PAUSED:
            msg = f"RunManager.resume: invalid state {self.state.value}"
            raise RuntimeError(msg)
        self.state = RunState.RUNNING

    def end(self, reason: RunTerminationReason) -> None:
        """RUNNING / PAUSED -> ENDED with the given termination reason.

        Idempotent: calling end() while already ENDED is a no-op (the
        existing reason is preserved). Calling from IDLE raises.

        Raises:
            RuntimeError: If called from IDLE.
        """
        if self.state is RunState.IDLE:
            msg = "RunManager.end: cannot end from IDLE"
            raise RuntimeError(msg)
        if self.state is RunState.ENDED:
            return
        self.state = RunState.ENDED
        self.termination_reason = reason

    def reset(self) -> None:
        """ENDED -> IDLE. Drops ``run_id`` and ``termination_reason``."""
        if self.state is not RunState.ENDED:
            msg = f"RunManager.reset: invalid state {self.state.value}"
            raise RuntimeError(msg)
        self.state = RunState.IDLE
        self.termination_reason = None
        self.run_id = ""

    @property
    def is_active(self) -> bool:
        """True while RUNNING or PAUSED (run is in flight)."""
        return self.state in (RunState.RUNNING, RunState.PAUSED)
