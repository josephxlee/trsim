"""SimulatorRDController — Phase 4 L3 Range-Doppler panel live binding.

Bridges :class:`workbench.ui.simulator.run_controller.SimulatorRunController`
to :class:`workbench.ui.simulator.panels.RangeDopplerPanel`. On every
``tick_completed(sim_t_s, frame_id)`` signal the controller asks the
injected :class:`workbench.app.simulator.MockRangeDopplerGenerator`
for the heatmap at ``sim_t_s`` and pushes the resulting arrays into
the RD panel (image + peak cross-hair + frame label).

Mirrors the L2 :class:`SimulatorFFTController` design.
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject

from workbench.app.simulator import MockRangeDopplerGenerator
from workbench.ui.simulator.panels import RangeDopplerPanel
from workbench.ui.simulator.run_controller import SimulatorRunController


class SimulatorRDController(QObject):
    """Drives the :class:`RangeDopplerPanel` from a :class:`SimulatorRunController`."""

    def __init__(
        self,
        *,
        rd_panel: RangeDopplerPanel,
        run_controller: SimulatorRunController | None = None,
        generator: MockRangeDopplerGenerator | None = None,
        enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = rd_panel
        self._generator = generator or MockRangeDopplerGenerator()
        self._run_controller = run_controller
        self._enabled = False
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
    def generator(self) -> MockRangeDopplerGenerator:
        return self._generator

    def paint_for(self, sim_t_s: float, frame_id: int) -> None:
        """Manual entry — generate and paint one frame at ``sim_t_s``."""
        frame = self._generator.heatmap_for(sim_t_s)
        self._panel.set_heatmap(frame.heatmap_db, frame.range_axis_m, frame.doppler_axis_mps)
        self._panel.set_peak(frame.peak_range_m, frame.peak_doppler_mps)
        self._panel.set_frame(frame_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)
