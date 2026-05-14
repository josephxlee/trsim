"""Curated built-in pipeline plug-in registry (Phase 4 L2).

The :class:`PluginManagerPanel` lists active plug-ins per pipeline
stage (plan/05 § 5.3.3). Until the Simulator workspace runs an actual
pipeline (subsequent Phase 4 cycles will wire one), this module
exposes the curated list of *available* built-in plug-ins so the
panel is no longer empty out of the box.

DLC plug-ins discovered via :class:`PluginLoader` augment this list
at runtime — that wiring is the next sub-step. For now: the panel
shows the workbench-ships baseline so users see what's available.
"""

from __future__ import annotations

# Stage names match :data:`PluginManagerPanel.PIPELINE_STAGES`.
BUILTIN_SIMULATOR_PLUGINS: dict[str, tuple[str, ...]] = {
    "Detector": (
        "CA-CFAR (1D)",
        "OS-CFAR (1D)",
    ),
    "Pairing": (
        "Numpy Pairing NN (Hungarian)",
        "FMCW Triangle Beat Matcher",
    ),
    "Tracker": (
        "EKF (Constant Velocity)",
        "UKF (Constant Velocity)",
    ),
    "Predictor": (),
    "Classifier": (),
}
