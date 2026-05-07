"""Wave response — entity's mechanical response to sea-state oscillation.

Phase 2.3b — the **entity** side of the wave-response split (plan/12 § 12.5):
the Map's :class:`workbench.domain.map_resource.SeaSurface` carries the
**environment** (sea state, wave amplitude/period), while each placed
entity carries a :class:`WaveResponseModel` describing how strongly its
pose oscillates in that environment.

Four canonical presets, each constructed via a ``make_*()`` factory:

- ``LARGE_SHIP``: Heavy displacement, slow response. Used by warships,
  cargo ships, large naval platforms.
- ``SMALL_BOAT``: Light, fast response. Used by patrol boats, RIBs.
- ``BUOY``: Anchored, near-full heave coupling but no horizontal motion.
- ``NONE``: Rigid / no response. Used by ground vehicles, aircraft, fixed
  installations — anything that does not interact with the sea surface.

Factor convention:

- ``heave_factor`` is a dimensionless 0..1 multiplier on the sea-surface
  vertical displacement. ``1.0`` means the entity heaves the full wave
  amplitude; ``0.0`` is rigid.
- ``pitch_factor`` and ``roll_factor`` are couplings in [rad / m wave
  amplitude]. They convert wave amplitude into entity attitude wobble.
- ``natural_period_s`` and ``damping_ratio`` are second-order oscillator
  parameters used by the runtime solver (Phase 2.4 dynamics).

References:

- plan/03 § 3.2.1e — WaveResponseModel dataclass.
- plan/12 § 12.5 — SeaStateEnvironment vs WaveResponseModel split.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WaveResponsePreset(Enum):
    """Preset identifier for an entity's wave response (plan/12 § 12.5.2)."""

    LARGE_SHIP = "large_ship"
    SMALL_BOAT = "small_boat"
    BUOY = "buoy"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class WaveResponseModel:
    """Entity-level second-order oscillator parameters for sea-state response.

    Attributes:
        preset: Preset identifier (informational tag for serialisation).
        heave_factor: Vertical-axis coupling [dimensionless, 0..1]. 0 means
            rigid, 1 means the entity heaves the full surface amplitude.
        pitch_factor: Pitch coupling [rad / m wave amplitude].
        roll_factor: Roll coupling [rad / m wave amplitude].
        natural_period_s: Entity's own oscillation period [s].
        damping_ratio: Critical-damping fraction [dimensionless, 0..1].

    Raises:
        ValueError: If any factor is outside its valid range.
    """

    preset: WaveResponsePreset
    heave_factor: float = 0.0
    pitch_factor: float = 0.0
    roll_factor: float = 0.0
    natural_period_s: float = 5.0
    damping_ratio: float = 0.3

    def __post_init__(self) -> None:
        if not 0.0 <= self.heave_factor <= 1.0:
            msg = f"heave_factor must be in [0, 1], got {self.heave_factor}"
            raise ValueError(msg)
        if self.pitch_factor < 0.0:
            msg = f"pitch_factor must be >= 0, got {self.pitch_factor}"
            raise ValueError(msg)
        if self.roll_factor < 0.0:
            msg = f"roll_factor must be >= 0, got {self.roll_factor}"
            raise ValueError(msg)
        if self.natural_period_s <= 0.0:
            msg = f"natural_period_s must be > 0, got {self.natural_period_s}"
            raise ValueError(msg)
        if not 0.0 <= self.damping_ratio <= 1.0:
            msg = f"damping_ratio must be in [0, 1], got {self.damping_ratio}"
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Preset factories
# ---------------------------------------------------------------------------


def make_large_ship() -> WaveResponseModel:
    """Heavy displacement, slow response (warship / cargo ship / corvette)."""
    return WaveResponseModel(
        preset=WaveResponsePreset.LARGE_SHIP,
        heave_factor=0.3,
        pitch_factor=0.05,
        roll_factor=0.08,
        natural_period_s=12.0,
        damping_ratio=0.1,
    )


def make_small_boat() -> WaveResponseModel:
    """Light displacement, fast response (RIB, patrol boat)."""
    return WaveResponseModel(
        preset=WaveResponsePreset.SMALL_BOAT,
        heave_factor=0.7,
        pitch_factor=0.15,
        roll_factor=0.20,
        natural_period_s=4.0,
        damping_ratio=0.2,
    )


def make_buoy() -> WaveResponseModel:
    """Anchored buoy: near-full heave, mild pitch/roll, no horizontal motion."""
    return WaveResponseModel(
        preset=WaveResponsePreset.BUOY,
        heave_factor=0.95,
        pitch_factor=0.05,
        roll_factor=0.05,
        natural_period_s=3.0,
        damping_ratio=0.3,
    )


def make_none() -> WaveResponseModel:
    """Rigid / no response (used for ground vehicles, aircraft, fixed installs)."""
    return WaveResponseModel(
        preset=WaveResponsePreset.NONE,
        heave_factor=0.0,
        pitch_factor=0.0,
        roll_factor=0.0,
        natural_period_s=1.0,
        damping_ratio=1.0,
    )
