"""Simulator panel widgets (Phase 4.9, plan/05 § 5.3).

Six dockable panels surface the runtime data flow inside the
Simulator workspace:

- :class:`FFTPanel` - up/down sweep FFT spectra (plan/05 § 5.3.4).
- :class:`RangeDopplerPanel` - 2D range-Doppler heatmap (Phase 4.9.x).
- :class:`RunPanel` - per-frame metrics + run controls (plan/05 §
  5.3.6).
- :class:`PropertiesPanel` - context-sensitive parameter inspector
  (plan/05 § 5.3.5).
- :class:`PluginManagerPanel` - active plugin per pipeline stage
  (plan/05 § 5.3.3).
- :class:`StageIOPanel` - per-stage IN/OUT inspector with CSV/HDF5
  download (plan/05 § 5.3.6c).

Phase 4.9 ships every panel as a QWidget shell with stub data and
real-looking layout. Live plot rendering (pyqtgraph FFT, RD heatmap,
PyVista 3D scene) lands across Phase 4.9.x and Phase 4.10.
"""

from __future__ import annotations

from workbench.ui.simulator.panels.fft_panel import FFTPanel
from workbench.ui.simulator.panels.plugin_manager_panel import PluginManagerPanel
from workbench.ui.simulator.panels.properties_panel import PropertiesPanel
from workbench.ui.simulator.panels.range_doppler_panel import RangeDopplerPanel
from workbench.ui.simulator.panels.run_panel import RunPanel
from workbench.ui.simulator.panels.scene_3d_panel import (
    CameraPreset,
    Scene3DPanel,
    SceneLayer,
)
from workbench.ui.simulator.panels.scope_pov_panel import ScopePOVPanel
from workbench.ui.simulator.panels.stage_io_panel import StageIOPanel

__all__ = [
    "CameraPreset",
    "FFTPanel",
    "PluginManagerPanel",
    "PropertiesPanel",
    "RangeDopplerPanel",
    "RunPanel",
    "Scene3DPanel",
    "SceneLayer",
    "ScopePOVPanel",
    "StageIOPanel",
]
