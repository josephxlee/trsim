"""SimulatorPrimaryTargetController — Phase 4 L6 Scope POV + Properties live binding.

Single controller that fans the
:class:`workbench.app.simulator.MockPrimaryTargetGenerator` output
into BOTH :class:`workbench.ui.simulator.panels.ScopePOVPanel`
(boresight cross-hair + AZ readout) and
:class:`workbench.ui.simulator.panels.PropertiesPanel` (Range / AZ
/ EL / RCS / Speed / Lock readout).

Both panels share one snapshot per tick so what the user sees on
the scope and what they read in the Properties form always agree.

Phase 4 P5 adds **manual pointing offsets**: the Simulator
workspace's arrow-key handler nudges ``manual_az_offset_deg`` /
``manual_el_offset_deg`` which the controller blends into every
subsequent ``paint_for`` so the commanded-azimuth readout and the
cross-hair marker move with the user's input. Real
:class:`PositionerCommand`-based Manual mode lands when Phase 3 +
Phase 4 Pipeline binding ships.
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
        # Phase 4 P5 — Manual pointing accumulator. The Simulator
        # workspace's arrow-key handler adds + / - here; paint_for()
        # blends the offset into every subsequent commanded_az_deg.
        self._manual_az_offset_deg: float = 0.0
        self._manual_el_offset_deg: float = 0.0
        # Latest sim_t_s + frame_id seen — lets ``add_manual_offset``
        # repaint immediately so the user sees the cross-hair move
        # without waiting for the next QTimer tick.
        self._last_sim_t_s: float = 0.0
        self._last_frame_id: int = 0
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

    def paint_for(self, sim_t_s: float, frame_id: int) -> None:
        """Push one tick into both panels."""
        snap = self._generator.snapshot_for(sim_t_s)
        # Blend the user's manual pointing offsets into the commanded
        # azimuth + nudge the cross-hair marker so the scope reacts to
        # arrow-key input even when the simulator is paused.
        cmd_az = snap.commanded_az_deg + self._manual_az_offset_deg
        actual_az = snap.actual_az_deg + self._manual_az_offset_deg
        scope_x = max(-1.0, min(1.0, snap.cross_hair_norm[0] + 0.1 * self._manual_az_offset_deg))
        scope_y = max(-1.0, min(1.0, snap.cross_hair_norm[1] + 0.1 * self._manual_el_offset_deg))
        # Scope: pointing readout + cross-hair marker.
        self._scope_panel.set_pointing(actual_az, cmd_az)
        self._scope_panel.set_target_norm(scope_x, scope_y)
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
        self._last_sim_t_s = sim_t_s
        self._last_frame_id = frame_id

    # ------------------------------------------------------------------
    # Phase 4 P5 — Manual pointing API
    # ------------------------------------------------------------------
    @property
    def manual_az_offset_deg(self) -> float:
        return self._manual_az_offset_deg

    @property
    def manual_el_offset_deg(self) -> float:
        return self._manual_el_offset_deg

    def add_manual_offset(self, *, d_az_deg: float, d_el_deg: float) -> None:
        """Apply an incremental manual pointing offset and repaint.

        Cumulative across calls; clears with :meth:`reset_manual_offset`.
        Triggers an immediate :meth:`paint_for` against the most-recent
        ``(sim_t_s, frame_id)`` so the user sees the cross-hair move
        even while the simulator is paused / stopped.
        """
        self._manual_az_offset_deg += d_az_deg
        self._manual_el_offset_deg += d_el_deg
        self.paint_for(self._last_sim_t_s, self._last_frame_id)

    def reset_manual_offset(self) -> None:
        """Clear both manual pointing accumulators back to zero."""
        self._manual_az_offset_deg = 0.0
        self._manual_el_offset_deg = 0.0
        self.paint_for(self._last_sim_t_s, self._last_frame_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)
