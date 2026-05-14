"""Simulator-workspace application helpers (Phase 4 L-series live binding).

This sub-package hosts the App-layer drivers that feed the Simulator
workspace panels (FFT / Range-Doppler / Scene 3D / ...) with synthetic
or pipeline-sourced data while the full Phase 3 ``Pipeline`` is being
wired in. Each driver is pure-Python + numpy and has no Qt / pyqtgraph
import — the corresponding UI controller in
``workbench.ui.simulator`` consumes the generated arrays and pushes
them into the panels.
"""

from __future__ import annotations

from workbench.app.simulator.mock_spectrum import (
    DEFAULT_FREQ_MAX_HZ,
    DEFAULT_FREQ_MIN_HZ,
    DEFAULT_N_BINS,
    MockSpectrumFrame,
    MockSpectrumGenerator,
)

__all__ = [
    "DEFAULT_FREQ_MAX_HZ",
    "DEFAULT_FREQ_MIN_HZ",
    "DEFAULT_N_BINS",
    "MockSpectrumFrame",
    "MockSpectrumGenerator",
]
