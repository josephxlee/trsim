"""Scenario — top-level configuration document (plan/03 § 3.2.1).

Phase 2.10 — minimum viable scenario container. Aggregates the Map,
atmosphere, target list, and radar platforms that a Run consumes.
The full v0.20+ ``[refs] / [composition] / [platform_install]`` split
(plan/10 § 10.9.3) is deferred to the resource-library work in Phase 3;
this MVP keeps everything in-memory.

References:

- plan/03 § 3.2.1 — Scenario schema (v0.20+ note: refs split).
- plan/10 § 10.9.3 — Scenario disk format.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from workbench.domain.map_resource import Map
from workbench.domain.platform import RadarPlatform
from workbench.domain.target import TargetEntity
from workbench.domain.timing.reference_timing import TimingConfig
from workbench.physics.atmosphere import AtmosphereState


@dataclass(frozen=True, slots=True)
class Scenario:
    """Top-level run configuration.

    Attributes:
        scenario_id: Workspace-unique identifier.
        map: Map resource (terrain, sea, buildings).
        atmosphere: Map-level atmosphere state.
        targets: Target list, length >= 0 (allow empty for radar-only
            calibration scenarios).
        platforms: Radar platform list, length >= 1.
        duration_s: Total run duration [s]. Must be > 0.
        frame_rate_hz: Frame rate [Hz]. Default 20.0 (plan/14 § 14.6.2
            main step 0.05 s). Must be > 0.
        timing: Timing-mode configuration. Default ``sim_time``.

    Raises:
        ValueError: For empty ``scenario_id``, no platforms,
            non-positive duration / frame rate.
    """

    scenario_id: str
    map: Map
    atmosphere: AtmosphereState
    targets: tuple[TargetEntity, ...]
    platforms: tuple[RadarPlatform, ...]
    duration_s: float
    frame_rate_hz: float = 20.0
    timing: TimingConfig = field(default_factory=TimingConfig)

    def __post_init__(self) -> None:
        if not self.scenario_id:
            msg = "scenario_id must be a non-empty string"
            raise ValueError(msg)
        if not self.platforms:
            msg = "scenario must include at least one radar platform"
            raise ValueError(msg)
        if self.duration_s <= 0.0:
            msg = f"duration_s must be > 0, got {self.duration_s}"
            raise ValueError(msg)
        if self.frame_rate_hz <= 0.0:
            msg = f"frame_rate_hz must be > 0, got {self.frame_rate_hz}"
            raise ValueError(msg)

    @property
    def frame_dt_s(self) -> float:
        """Per-frame time step [s] = ``1 / frame_rate_hz``."""
        return 1.0 / self.frame_rate_hz

    @property
    def n_frames(self) -> int:
        """Total integer frame count (floor(duration / dt))."""
        return int(self.duration_s * self.frame_rate_hz)
