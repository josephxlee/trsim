"""SimulatorSceneController — Phase 4 L4 Scene 3D panel live binding.

Bridges :class:`workbench.ui.simulator.run_controller.SimulatorRunController`
to :class:`workbench.ui.simulator.panels.Scene3DPanel`. On every
``tick_completed(sim_t_s, frame_id)`` signal the controller asks the
injected :class:`workbench.app.simulator.MockSceneGenerator` for the
scene frame at ``sim_t_s`` and pushes it into the panel.

Mirrors the L2/L3 controller pattern. The panel itself handles the
``enable_3d_viewer=False`` headless path; this controller stays
generic and just forwards frames.
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject

from workbench.app.simulator import MockSceneGenerator
from workbench.ui.simulator.panels import Scene3DPanel
from workbench.ui.simulator.run_controller import SimulatorRunController


class SimulatorSceneController(QObject):
    """Drives the :class:`Scene3DPanel` from a :class:`SimulatorRunController`."""

    def __init__(
        self,
        *,
        scene_panel: Scene3DPanel,
        run_controller: SimulatorRunController | None = None,
        generator: MockSceneGenerator | None = None,
        enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = scene_panel
        self._generator = generator or MockSceneGenerator()
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
    def generator(self) -> MockSceneGenerator:
        return self._generator

    def paint_for(self, sim_t_s: float, frame_id: int) -> None:
        """Manual entry — generate and paint one frame at ``sim_t_s``."""
        frame = self._generator.scene_for(sim_t_s)
        self._panel.set_scene_frame(frame)
        self._panel.set_frame(frame_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)
