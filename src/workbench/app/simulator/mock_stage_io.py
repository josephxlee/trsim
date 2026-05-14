"""Mock pipeline-stage IN/OUT generator for the Simulator StageIO panel.

Phase 4 L5 wires :class:`workbench.ui.simulator.panels.StageIOPanel`
to a deterministic, sim-time-driven mock generator that paints
per-stage IN / OUT summary strings. Real Pipeline binding lands
later via :class:`workbench.app.probe_recorder.ProbeRecorder`.

Behaviour:

- The generator owns a fixed pipeline stage ordering
  (:data:`PIPELINE_STAGE_BOXES`).
- For each stage it returns a ``(in_text, out_text)`` pair whose
  numeric counts move deterministically with sim_t_s so the user
  can see the IO update on every tick.

The default plugin names exposed by :data:`DEFAULT_PLUGIN_NAMES`
seed the PluginManager panel with one stub plugin per pipeline
stage; the user can replace them via the Plugin Manager UI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

PIPELINE_STAGE_BOXES: tuple[str, ...] = (
    "Transmitter",
    "Environment",
    "Receiver",
    "Detector",
    "Pairing",
    "Tracker",
)

DEFAULT_PLUGIN_NAMES: dict[str, tuple[str, ...]] = {
    "Detector": ("default_cfar",),
    "Pairing": ("default_pairing",),
    "Tracker": ("default_ekf",),
    "Predictor": ("default_cv",),
    "Classifier": ("default_threshold",),
}


@dataclass(frozen=True, slots=True)
class MockStageIOFrame:
    """One generated Stage IO frame.

    Attributes:
        stage_io: Ordered mapping of stage name to ``(in_text, out_text)``.
            Mapping insertion order matches :data:`PIPELINE_STAGE_BOXES`.
        sim_t_s: Simulation time the frame was generated at [s].
    """

    stage_io: dict[str, tuple[str, str]]
    sim_t_s: float


class MockStageIOGenerator:
    """Deterministic mock pipeline-stage IO generator.

    Args:
        base_pulses: Baseline pulse count handed to the Transmitter
            row [-], > 0.
        peak_reflections: Maximum number of reflections the
            Environment stage reports [-], > 0. Modulated by a
            unit-sin so the value moves over sim_t_s.
        peak_detections: Maximum CFAR-detection count [-], > 0.
        peak_pairs: Maximum number of Pairing output rows [-], > 0.
        peak_tracks: Maximum Tracker output rows [-], > 0.
        sweep_period_s: Period of the synthetic IO modulation [s], > 0.

    Raises:
        ValueError: On any out-of-range constructor argument.
    """

    def __init__(
        self,
        *,
        base_pulses: int = 256,
        peak_reflections: int = 32,
        peak_detections: int = 12,
        peak_pairs: int = 8,
        peak_tracks: int = 4,
        sweep_period_s: float = 5.0,
    ) -> None:
        if base_pulses <= 0:
            msg = f"base_pulses must be > 0, got {base_pulses}"
            raise ValueError(msg)
        if peak_reflections <= 0:
            msg = f"peak_reflections must be > 0, got {peak_reflections}"
            raise ValueError(msg)
        if peak_detections <= 0:
            msg = f"peak_detections must be > 0, got {peak_detections}"
            raise ValueError(msg)
        if peak_pairs <= 0:
            msg = f"peak_pairs must be > 0, got {peak_pairs}"
            raise ValueError(msg)
        if peak_tracks <= 0:
            msg = f"peak_tracks must be > 0, got {peak_tracks}"
            raise ValueError(msg)
        if sweep_period_s <= 0.0:
            msg = f"sweep_period_s must be > 0, got {sweep_period_s}"
            raise ValueError(msg)
        self._base_pulses = base_pulses
        self._peak_reflections = peak_reflections
        self._peak_detections = peak_detections
        self._peak_pairs = peak_pairs
        self._peak_tracks = peak_tracks
        self._sweep_period_s = sweep_period_s

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def io_for(self, sim_t_s: float) -> MockStageIOFrame:
        """Return the per-stage IO summary at ``sim_t_s``."""
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        phase = 2.0 * math.pi * sim_t_s / self._sweep_period_s
        modulation = (math.sin(phase) + 1.0) / 2.0  # 0..1
        reflections = max(1, round(modulation * self._peak_reflections))
        detections = max(1, round(modulation * self._peak_detections))
        pairs = max(0, round(modulation * self._peak_pairs))
        tracks = max(0, round(modulation * self._peak_tracks))

        # Use an ordered dict (insertion order is the canonical pipeline
        # order). Each entry mirrors the structure consumed by
        # ``StageIOPanel.set_stage_io(stage, in_text, out_text)``.
        stage_io: dict[str, tuple[str, str]] = {
            "Transmitter": (
                f"sim_t={sim_t_s:.3f}s",
                f"{self._base_pulses} pulses",
            ),
            "Environment": (
                f"{self._base_pulses} pulses",
                f"{reflections} reflections",
            ),
            "Receiver": (
                f"{reflections} reflections",
                "FFTSpectrum",
            ),
            "Detector": (
                "FFTSpectrum",
                f"{detections} detections",
            ),
            "Pairing": (
                f"{detections} detections",
                f"{pairs} pairs",
            ),
            "Tracker": (
                f"{pairs} pairs",
                f"{tracks} tracks",
            ),
        }
        return MockStageIOFrame(stage_io=stage_io, sim_t_s=sim_t_s)
