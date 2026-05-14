"""SimulatorFFTController — Phase 4 L2 FFT panel live binding.

Bridges :class:`workbench.ui.simulator.run_controller.SimulatorRunController`
to :class:`workbench.ui.simulator.panels.FFTPanel`. On every
``tick_completed(sim_t_s, frame_id)`` signal the controller asks the
injected :class:`workbench.app.simulator.MockSpectrumGenerator` for the
spectrum at ``sim_t_s`` and pushes the resulting arrays into the FFT
panel (curves + peak markers + frame label).

The controller can be enabled/disabled at runtime — disabling
disconnects the signal so a paused scenario doesn't burn CPU. Tests
construct the controller without a RunController (``run_controller=
None``) and drive it manually with :meth:`paint_for`.
"""

from __future__ import annotations

import contextlib

from PySide6.QtCore import QObject

from workbench.app.simulator import MockSpectrumGenerator
from workbench.ui.simulator.panels import FFTPanel
from workbench.ui.simulator.run_controller import SimulatorRunController


class SimulatorFFTController(QObject):
    """Drives the :class:`FFTPanel` from a :class:`SimulatorRunController`.

    Args:
        fft_panel: The FFTPanel to repaint on each tick.
        run_controller: The run controller whose ``tick_completed``
            signal triggers the repaint. May be ``None`` for headless
            tests; the controller then exposes :meth:`paint_for` as a
            manual entry point.
        generator: Spectrum generator. Defaults to a new
            :class:`MockSpectrumGenerator` so production callers do
            not have to supply one.
        enabled: Whether the ``tick_completed`` connection is live at
            construction. Defaults to ``True``.
        parent: Standard QObject parent.
    """

    def __init__(
        self,
        *,
        fft_panel: FFTPanel,
        run_controller: SimulatorRunController | None = None,
        generator: MockSpectrumGenerator | None = None,
        enabled: bool = True,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._panel = fft_panel
        self._generator = generator or MockSpectrumGenerator()
        self._run_controller = run_controller
        self._enabled = False  # set by ``set_enabled`` below
        if run_controller is not None and enabled:
            self.set_enabled(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_enabled(self, value: bool) -> None:
        """Connect / disconnect the ``tick_completed`` signal."""
        if value == self._enabled:
            return
        if self._run_controller is None:
            self._enabled = value
            return
        if value:
            self._run_controller.tick_completed.connect(self._on_tick)
        else:
            # Qt raises when the connection has been torn down by the
            # parent's destruction; treat that as already-disconnected.
            with contextlib.suppress(RuntimeError, TypeError):
                self._run_controller.tick_completed.disconnect(self._on_tick)
        self._enabled = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def generator(self) -> MockSpectrumGenerator:
        return self._generator

    def paint_for(self, sim_t_s: float, frame_id: int) -> None:
        """Manual entry — generate and paint one frame at ``sim_t_s``.

        Test helper. Production drives the panel via the QTimer-fed
        ``tick_completed`` signal instead.
        """
        frame = self._generator.spectrum_for(sim_t_s)
        self._panel.set_spectrum(frame.freqs_hz, frame.up_mag_db, frame.down_mag_db)
        self._panel.set_peak_freqs(frame.up_peak_freq_hz, frame.down_peak_freq_hz)
        self._panel.set_frame(frame_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------
    def _on_tick(self, sim_t_s: float, frame_id: int) -> None:
        self.paint_for(sim_t_s, frame_id)
