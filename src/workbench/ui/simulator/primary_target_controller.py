"""SimulatorPrimaryTargetController — Phase 4 L6 Scope POV + Properties live binding.

Single controller that fans the
:class:`workbench.app.simulator.MockPrimaryTargetGenerator` output
into BOTH :class:`workbench.ui.simulator.panels.ScopePOVPanel`
(boresight cross-hair + AZ readout) and
:class:`workbench.ui.simulator.panels.PropertiesPanel` (Range / AZ
/ EL / RCS / Speed / Lock readout).

Both panels share one snapshot per tick so what the user sees on
the scope and what they read in the Properties form always agree.
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject

from workbench.app.simulator import MockPrimaryTargetGenerator
from workbench.ui.simulator.panels import PropertiesPanel, ScopePOVPanel
from workbench.ui.simulator.run_controller import SimulatorRunController


class SimulatorPrimaryTargetController(QObject):
    """Drives Scope + Properties from a :class:`SimulatorRunController`."""

    def __init__(
        self,
        *,
        scope_panel: ScopePOVPanel,
        properties_panel: PropertiesPanel,
        run_controller: SimulatorRunController | None = None,
        generator: MockPrimaryTargetGenerator | None = None,
        enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._scope_panel = scope_panel
        self._properties_panel = properties_panel
        self._generator = generator or MockPrimaryTargetGenerator()
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
    def generator(self) -> MockPrimaryTargetGenerator:
        return self._generator

    def paint_for(self, sim_t_s: float, _frame_id: int) -> None:
        """Push one tick into both panels."""
        snap = self._generator.snapshot_for(sim_t_s)
        # Scope: pointing readout + cross-hair marker.
        self._scope_panel.set_pointing(snap.actual_az_deg, snap.commanded_az_deg)
        self._scope_panel.set_target_norm(*snap.cross_hair_norm)
        # Properties: human-readable summary form.
        lock_text = "LOCKED" if snap.is_locked else "searching"
        self._properties_panel.show_object(
            "Primary Target",
            {
                "Range": f"{snap.range_m:.1f} m",
                "Azimuth": f"{snap.azimuth_deg:.2f} deg",
                "Elevation": f"{snap.elevation_deg:.2f} deg",
                "RCS": f"{snap.rcs_dbsm:.2f} dBsm",
                "Speed": f"{snap.speed_mps:.1f} m/s",
                "Lock": lock_text,
            },
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)
