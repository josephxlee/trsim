"""Reference Timing data model (plan/03 § 3.2.1n, v0.39).

Phase 2.12 — minimum viable timing-mode configuration consumed by the
PerformanceClock layer (App, Phase 3+) and the HIL handshake (Phase 8+).
The dataclasses here are pure value records: no clock, no thread, no
side effects.

Three modes (plan/18 § 18.16):

- ``sim_time``: each frame is one simulation step; wall clock irrelevant.
- ``real_time``: pace simulation to wall clock 1:1.
- ``reference``: pace to a user-supplied target latency (the "Vivado
  reference run" pattern — match the latency of the real DUT board).
  Each :class:`StageTimingProfile` gives either a ``target_latency_ms``
  or a ``scale_factor`` (mutually exclusive).

References:

- plan/03 § 3.2.1n — Reference Timing dataclass.
- plan/18 § 18.16 / § 18.17 — Reference Timing Mode + Frame Profiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class StageTimingProfile:
    """Per-stage timing target (plan/03 § 3.2.1n).

    Exactly one of ``target_latency_ms`` and ``scale_factor`` must be
    supplied — the other must be ``None``.

    Attributes:
        target_name: Stage identifier (``"detector"`` / ``"tracker"``
            / ``"pairing"`` / ``"pipeline_total"`` / ...).
        target_latency_ms: Wall-clock budget per frame for this stage
            [ms]. ``None`` to use ``scale_factor`` instead.
        scale_factor: Sim:wall multiplier (e.g. 1.0 = real time,
            0.5 = half wall speed). ``None`` to use ``target_latency_ms``.
        measurement_unit: ``"stage"`` (per-stage profiling) or
            ``"pipeline"`` (whole-pipeline aggregate).

    Raises:
        ValueError: If both or neither knob is supplied, if any value
            is non-positive, or if ``measurement_unit`` is unsupported.
    """

    target_name: str
    target_latency_ms: float | None = None
    scale_factor: float | None = None
    measurement_unit: Literal["stage", "pipeline"] = "stage"

    def __post_init__(self) -> None:
        if not self.target_name:
            msg = "target_name must be a non-empty string"
            raise ValueError(msg)
        has_target = self.target_latency_ms is not None
        has_scale = self.scale_factor is not None
        if has_target == has_scale:
            msg = "exactly one of target_latency_ms / scale_factor must be set"
            raise ValueError(msg)
        if has_target and self.target_latency_ms is not None and self.target_latency_ms <= 0.0:
            msg = f"target_latency_ms must be > 0, got {self.target_latency_ms}"
            raise ValueError(msg)
        if has_scale and self.scale_factor is not None and self.scale_factor <= 0.0:
            msg = f"scale_factor must be > 0, got {self.scale_factor}"
            raise ValueError(msg)
        if self.measurement_unit not in ("stage", "pipeline"):
            msg = f"measurement_unit must be 'stage' or 'pipeline', got {self.measurement_unit!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class TimingConfig:
    """Scenario ``[timing]`` section (plan/03 § 3.2.1n).

    Attributes:
        mode: Timing mode (see module docstring).
        frame_unit: How to count frames — ``"fmcw_sweep"`` /
            ``"fft_window"`` / ``"auto"`` (frame boundary detector
            triggers off the track output, plan/18 § 18.16 Q-RT1) /
            ``"custom"``.
        profiles: Per-stage timing profiles. Used only when
            ``mode == "reference"``.

    Raises:
        ValueError: For an unknown ``mode`` / ``frame_unit``.
    """

    mode: Literal["sim_time", "real_time", "reference"] = "sim_time"
    frame_unit: Literal["fmcw_sweep", "fft_window", "auto", "custom"] = "auto"
    profiles: tuple[StageTimingProfile, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.mode not in ("sim_time", "real_time", "reference"):
            msg = f"mode must be one of sim_time / real_time / reference, got {self.mode!r}"
            raise ValueError(msg)
        if self.frame_unit not in ("fmcw_sweep", "fft_window", "auto", "custom"):
            msg = f"frame_unit must be one of fmcw_sweep / fft_window / auto / custom, got {self.frame_unit!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class FrameTimestamp:
    """Single-frame time record (plan/03 § 3.2.1n runtime).

    Attributes:
        frame_id: Monotonically increasing frame counter (>= 0).
        sim_t_s: Simulation time at frame end [s] (>= 0).
        wall_t_s: Wall-clock time at frame end [s] (>= 0). 0 in pure
            ``sim_time`` mode.

    Raises:
        ValueError: If any field is negative.
    """

    frame_id: int
    sim_t_s: float
    wall_t_s: float = 0.0

    def __post_init__(self) -> None:
        if self.frame_id < 0:
            msg = f"frame_id must be >= 0, got {self.frame_id}"
            raise ValueError(msg)
        if self.sim_t_s < 0.0:
            msg = f"sim_t_s must be >= 0, got {self.sim_t_s}"
            raise ValueError(msg)
        if self.wall_t_s < 0.0:
            msg = f"wall_t_s must be >= 0, got {self.wall_t_s}"
            raise ValueError(msg)
