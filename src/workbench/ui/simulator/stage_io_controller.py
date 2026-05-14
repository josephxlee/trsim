"""SimulatorStageIOController — Phase 4 L5 Stage IO panel live binding.

Bridges :class:`workbench.ui.simulator.run_controller.SimulatorRunController`
to :class:`workbench.ui.simulator.panels.StageIOPanel`. On every
``tick_completed(sim_t_s, frame_id)`` signal the controller asks the
injected :class:`workbench.app.simulator.MockStageIOGenerator` for
the per-stage IO summary at ``sim_t_s`` and pushes it into the
panel. It also owns the panel's Record toggle: while enabled,
every tick appends one :class:`MockStageIOFrame` snapshot to the
controller's in-memory log so a follow-up sub-step (Phase 6+ probe
recorder) can dump the log to disk.

Mirrors the L2/L3/L4 controller pattern.
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject

from workbench.app.simulator import MockStageIOFrame, MockStageIOGenerator
from workbench.ui.simulator.panels import StageIOPanel
from workbench.ui.simulator.run_controller import SimulatorRunController


class SimulatorStageIOController(QObject):
    """Drives the :class:`StageIOPanel` from a :class:`SimulatorRunController`."""

    def __init__(
        self,
        *,
        stage_io_panel: StageIOPanel,
        run_controller: SimulatorRunController | None = None,
        generator: MockStageIOGenerator | None = None,
        enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = stage_io_panel
        self._generator = generator or MockStageIOGenerator()
        self._run_controller = run_controller
        self._enabled = False
        self._recording: bool = False
        self._records: list[MockStageIOFrame] = []
        self._panel.record_toggled.connect(self._on_record_toggled)
        if run_controller is not None and enabled:
            self.set_enabled(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_enabled(self, value: bool) -> None:
        if value == self._enabled:
            return
        if self._run_controller is None:
            self._enabled = value
            return
        if value:
            self._run_controller.tick_completed.connect(self._on_tick)
        else:
            with contextlib.suppress(RuntimeError, TypeError):
                self._run_controller.tick_completed.disconnect(self._on_tick)
        self._enabled = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def generator(self) -> MockStageIOGenerator:
        return self._generator

    @property
    def recording(self) -> bool:
        return self._recording

    def records(self) -> tuple[MockStageIOFrame, ...]:
        """Tuple snapshot of every recorded frame so far."""
        return tuple(self._records)

    def clear_records(self) -> None:
        """Reset the recording log to empty (transport / Stop behavior)."""
        self._records.clear()

    def paint_for(self, sim_t_s: float, frame_id: int) -> None:
        """Manual entry — generate, paint, and (if recording) append."""
        frame = self._generator.io_for(sim_t_s)
        for stage, (in_text, out_text) in frame.stage_io.items():
            self._panel.set_stage_io(stage, in_text, out_text)
        self._panel.set_frame(frame_id)
        if self._recording:
            self._records.append(frame)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)

    def _on_record_toggled(self, checked: bool) -> None:
        self._recording = checked
        if not checked:
            return
        # Snapshot the current panel state -> no, we wait for the next
        # tick to land. Clearing prior records when starting a new
        # session keeps the log scoped to the active recording window.
        self._records.clear()
