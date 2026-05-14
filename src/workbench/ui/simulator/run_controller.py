"""SimulatorRunController — Phase 4 L1 live sim_time + frame_id wiring.

Bridges :class:`workbench.app.simulation_clock.SimulationClock` to
:class:`workbench.ui.simulator.panels.RunPanel`. A 16 ms QTimer drives
``advance(wall_dt_s)`` while RUNNING; every tick pushes the live
``sim_t_s`` / ``frame_id`` / state / speed into the RunPanel readouts
added in L1.

The controller is a thin orchestrator — the MainWindow wires its
``play()`` / ``pause()`` / ``stop()`` / ``set_speed()`` methods into the
SimulationToolbar's ``on_sim_*`` hooks. Tests construct it headless
(no QTimer fire) and drive it via the manual ``tick(wall_dt_s)``
method to avoid event-loop dependency.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from workbench.app.simulation_clock import SimulationClock
from workbench.domain.types import SimulationState, SpeedMultiplier
from workbench.ui.simulator.panels import RunPanel

# P5b — 60 Hz tick (16 ms) is more than the user can perceive on a
# panel-readout repaint and amplifies reflow cost during window resize
# / layout reflow. 30 Hz (33 ms) is the common compromise: smooth
# scope cross-hair motion, half the CPU cost, no visible step on
# numeric readouts.
_DEFAULT_TICK_MS: int = 33


class SimulatorRunController(QObject):
    """Drives a :class:`SimulationClock` + paints the RunPanel readouts.

    Attributes:
        clock: Owned :class:`SimulationClock` instance.
        frame_id: Monotonic frame counter; bumped each tick that
            actually advances ``sim_t_s`` (so paused / stopped ticks
            do not bump it).

    Signals:
        tick_completed(float, int): ``(sim_t_s, frame_id)`` after every
            tick that advanced the clock. ``sim_t_s`` may be 0.0 while
            paused / stopped (the panel still re-paints to keep the
            state label fresh).
    """

    tick_completed = Signal(float, int)

    def __init__(
        self,
        *,
        run_panel: RunPanel,
        clock: SimulationClock | None = None,
        tick_interval_ms: int = _DEFAULT_TICK_MS,
        autostart_timer: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if tick_interval_ms <= 0:
            msg = f"tick_interval_ms must be > 0, got {tick_interval_ms}"
            raise ValueError(msg)
        self._panel = run_panel
        self._clock: SimulationClock = clock or SimulationClock()
        self._tick_interval_ms = tick_interval_ms
        self._frame_id: int = 0
        # P5c — paint-suppression flag the SimulatorWorkspace flips on
        # during a resize drag to stop downstream controllers (FFT, RD,
        # Scene3D, StageIO, Properties, Scope) from re-painting their
        # pyqtgraph widgets while Qt is busy reflowing the splitter
        # tree. The Run panel readout still updates because we call
        # ``_refresh_panel`` unconditionally — only the
        # ``tick_completed`` signal is held back.
        self._paint_suppressed: bool = False
        self._timer = QTimer(self)
        self._timer.setInterval(tick_interval_ms)
        self._timer.timeout.connect(self._on_timer_tick)
        if autostart_timer:
            self._timer.start()
        self._refresh_panel()

    # ------------------------------------------------------------------
    # Transport
    # ------------------------------------------------------------------
    def play(self) -> None:
        """STOPPED / PAUSED -> RUNNING. STOPPED also resets frame_id."""
        if self._clock.state is SimulationState.STOPPED:
            self._frame_id = 0
        self._clock.start()
        self._refresh_panel()

    def pause(self) -> None:
        """RUNNING -> PAUSED. frame_id frozen; sim_t_s frozen."""
        if self._clock.state is SimulationState.RUNNING:
            self._clock.pause()
            self._refresh_panel()

    def stop(self) -> None:
        """Any -> STOPPED. Resets sim_t_s and frame_id."""
        self._clock.stop()
        self._frame_id = 0
        self._refresh_panel()

    def set_speed(self, speed: SpeedMultiplier) -> None:
        """Change clock speed multiplier (allowed in any state)."""
        self._clock.set_speed(speed)
        self._refresh_panel()

    # ------------------------------------------------------------------
    # Tick driver
    # ------------------------------------------------------------------
    def tick(self, wall_dt_s: float) -> float:
        """Manual tick (test entry). Returns ``sim_dt`` advanced."""
        if wall_dt_s < 0.0:
            msg = f"wall_dt_s must be non-negative, got {wall_dt_s}"
            raise ValueError(msg)
        sim_dt = self._clock.advance(wall_dt_s)
        if sim_dt > 0.0:
            self._frame_id += 1
        self._refresh_panel()
        # P5c — hold the downstream paint signal while a workspace
        # resize drag is in progress. ``_refresh_panel`` above still
        # runs because the Run readout is cheap (4 setText calls).
        if not self._paint_suppressed:
            self.tick_completed.emit(self._clock.sim_t_s, self._frame_id)
        return sim_dt

    # ------------------------------------------------------------------
    # P5c — paint suppression (workspace-driven debounce)
    # ------------------------------------------------------------------
    def set_paint_suppressed(self, value: bool) -> None:
        """Toggle whether ``tick_completed`` signals are emitted.

        The SimulatorWorkspace flips this on inside ``resizeEvent`` and
        clears it after a short debounce so the user's resize drag does
        not compete with 30 Hz pyqtgraph re-paints on every panel.
        Tests can drive it directly to assert downstream behaviour.
        """
        self._paint_suppressed = bool(value)

    @property
    def paint_suppressed(self) -> bool:
        return self._paint_suppressed

    def _on_timer_tick(self) -> None:
        wall_dt_s = self._tick_interval_ms / 1000.0
        self.tick(wall_dt_s)

    def _refresh_panel(self) -> None:
        self._panel.set_sim_time(self._clock.sim_t_s, self._frame_id)
        self._panel.set_sim_state(self._clock.state)
        self._panel.set_sim_speed(self._clock.speed)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    @property
    def clock(self) -> SimulationClock:
        return self._clock

    @property
    def frame_id(self) -> int:
        return self._frame_id

    @property
    def tick_interval_ms(self) -> int:
        return self._tick_interval_ms

    def timer(self) -> QTimer:
        """Owned QTimer — test helper to stop/start without re-running ``__init__``."""
        return self._timer
