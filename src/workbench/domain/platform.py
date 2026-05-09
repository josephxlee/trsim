"""Radar platform — antenna + tracker + placement aggregate (Phase 2.11).

Wraps the per-radar configuration that a :class:`Scenario` puts on a
Map. The radar's mount, antenna form, and tracker choice are bound
together so the Pipeline (Phase 2.10) has one handle to dereference.

References:

- plan/03 § 3.2.1m — RadarPlatform abstraction.
- plan/09 — radar_platforms.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workbench.domain.placement import PlacedEntity


class TrackerKind(Enum):
    """Filter selection for a radar platform (plan/03 § 3.2.1k, v0.34)."""

    EKF = "ekf"
    UKF = "ukf"


@dataclass(frozen=True, slots=True)
class RadarPlatform:
    """Single radar instance placed on a Map (plan/03 § 3.2.1m).

    Carries the static configuration; runtime state (live tracks,
    receive buffers, ...) lives in the Pipeline.

    Attributes:
        platform_id: Workspace-unique identifier (``"radar_host_01"``).
        placement: Where the antenna is mounted on the Map.
        antenna_id: Free-string handle for the antenna resource. Phase
            3 ResourceLibrary resolves it; we keep the field as a
            string so the Domain layer doesn't import physics-side
            antenna types directly.
        carrier_frequency_hz: Operating frequency [Hz]. Must be > 0.
        tracker_kind: EKF or UKF (the filter the Pipeline runs).
        boresight_az_rad: Antenna pointing azimuth (CW from N) [rad].
        boresight_el_rad: Antenna pointing elevation [rad].

    Raises:
        ValueError: For empty ``platform_id`` / ``antenna_id`` or
            non-positive ``carrier_frequency_hz``.
    """

    platform_id: str
    placement: PlacedEntity
    antenna_id: str
    carrier_frequency_hz: float
    tracker_kind: TrackerKind = TrackerKind.EKF
    boresight_az_rad: float = 0.0
    boresight_el_rad: float = 0.0

    def __post_init__(self) -> None:
        if not self.platform_id:
            msg = "platform_id must be a non-empty string"
            raise ValueError(msg)
        if not self.antenna_id:
            msg = "antenna_id must be a non-empty string"
            raise ValueError(msg)
        if self.carrier_frequency_hz <= 0.0:
            msg = f"carrier_frequency_hz must be > 0, got {self.carrier_frequency_hz}"
            raise ValueError(msg)
