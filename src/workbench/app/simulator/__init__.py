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

from workbench.app.simulator.mock_primary_target import (
    MockPrimaryTargetGenerator,
    MockPrimaryTargetSnapshot,
)
from workbench.app.simulator.mock_range_doppler import (
    DEFAULT_DOPPLER_MAX_MPS,
    DEFAULT_DOPPLER_MIN_MPS,
    DEFAULT_N_DOPPLER_BINS,
    DEFAULT_N_RANGE_BINS,
    DEFAULT_RANGE_MAX_M,
    DEFAULT_RANGE_MIN_M,
    MockRangeDopplerFrame,
    MockRangeDopplerGenerator,
)
from workbench.app.simulator.mock_scene import (
    MockSceneFrame,
    MockSceneGenerator,
)
from workbench.app.simulator.mock_spectrum import (
    DEFAULT_FREQ_MAX_HZ,
    DEFAULT_FREQ_MIN_HZ,
    DEFAULT_N_BINS,
    MockSpectrumFrame,
    MockSpectrumGenerator,
)
from workbench.app.simulator.mock_stage_io import (
    DEFAULT_PLUGIN_NAMES,
    PIPELINE_STAGE_BOXES,
    MockStageIOFrame,
    MockStageIOGenerator,
)

__all__ = [
    "DEFAULT_DOPPLER_MAX_MPS",
    "DEFAULT_DOPPLER_MIN_MPS",
    "DEFAULT_FREQ_MAX_HZ",
    "DEFAULT_FREQ_MIN_HZ",
    "DEFAULT_N_BINS",
    "DEFAULT_N_DOPPLER_BINS",
    "DEFAULT_N_RANGE_BINS",
    "DEFAULT_PLUGIN_NAMES",
    "DEFAULT_RANGE_MAX_M",
    "DEFAULT_RANGE_MIN_M",
    "PIPELINE_STAGE_BOXES",
    "MockPrimaryTargetGenerator",
    "MockPrimaryTargetSnapshot",
    "MockRangeDopplerFrame",
    "MockRangeDopplerGenerator",
    "MockSceneFrame",
    "MockSceneGenerator",
    "MockSpectrumFrame",
    "MockSpectrumGenerator",
    "MockStageIOFrame",
    "MockStageIOGenerator",
]
