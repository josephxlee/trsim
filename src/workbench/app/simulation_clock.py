"""SimulationClock — outer time-control layer (plan/03 § 3.5.0b, v0.15).

Phase 3.2 — wraps :class:`workbench.domain.types.SimulationState` and
:class:`workbench.domain.types.SpeedMultiplier` into the App-side
state machine that advances ``sim_t_s``. State transitions:

- STOPPED -> RUNNING (start; resets sim_t_s = 0)
- RUNNING -> PAUSED (pause; sim_t_s frozen)
- PAUSED -> RUNNING (resume; sim_t_s continues)
- RUNNING / PAUSED -> STOPPED (stop; sim_t_s = 0 on next start)

Time advance:

- ``advance(wall_dt_s)`` adds ``wall_dt_s * speed`` to ``sim_t_s`` while
  RUNNING; no-op while PAUSED / STOPPED.

The clock is a plain object — the simulation thread (Phase 4 / CLI)
calls ``advance`` on its tick. The thread itself is not in this
module; we keep the data model pure.
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.domain.types import SimulationState, SpeedMultiplier


@dataclass(slots=True)
class SimulationClock:
    """Outer simulation time clock (plan/03 § 3.5.0b).

    Attributes:
        state: Current simulation state.
        speed: Speed multiplier (x1 / x2 / x4 / x8).
        sim_t_s: Simulation time elapsed since the last ``start`` [s].
    """

    state: SimulationState = SimulationState.STOPPED
    speed: SpeedMultiplier = SpeedMultiplier.X1
    sim_t_s: float = 0.0

    def start(self) -> None:
        """STOPPED / PAUSED -> RUNNING. Resets ``sim_t_s`` from STOPPED.

        Raises:
            RuntimeError: If called while already RUNNING.
        """
        if self.state is SimulationState.RUNNING:
            msg = "SimulationClock.start: already RUNNING"
            raise RuntimeError(msg)
        if self.state is SimulationState.STOPPED:
            self.sim_t_s = 0.0
        self.state = SimulationState.RUNNING

    def pause(self) -> None:
        """RUNNING -> PAUSED. ``sim_t_s`` frozen.

        Raises:
            RuntimeError: If state is not RUNNING.
        """
        if self.state is not SimulationState.RUNNING:
            msg = f"SimulationClock.pause: invalid state {self.state.value}"
            raise RuntimeError(msg)
        self.state = SimulationState.PAUSED

    def stop(self) -> None:
        """Any state -> STOPPED. ``sim_t_s`` reset to 0."""
        self.state = SimulationState.STOPPED
        self.sim_t_s = 0.0

    def set_speed(self, speed: SpeedMultiplier) -> None:
        """Change speed multiplier (allowed in any state)."""
        self.speed = speed

    def advance(self, wall_dt_s: float) -> float:
        """Advance simulation time by ``wall_dt_s * speed`` if RUNNING.

        Args:
            wall_dt_s: Wall-clock elapsed since last tick [s].
                Must be >= 0.

        Returns:
            Elapsed simulation time this advance (0 while PAUSED / STOPPED).

        Raises:
            ValueError: If ``wall_dt_s < 0``.
        """
        if wall_dt_s < 0.0:
            msg = f"wall_dt_s must be >= 0, got {wall_dt_s}"
            raise ValueError(msg)
        if self.state is not SimulationState.RUNNING:
            return 0.0
        sim_dt = wall_dt_s * float(self.speed.value)
        self.sim_t_s += sim_dt
        return sim_dt

    @property
    def is_running(self) -> bool:
        return self.state is SimulationState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state is SimulationState.PAUSED

    @property
    def is_stopped(self) -> bool:
        return self.state is SimulationState.STOPPED
