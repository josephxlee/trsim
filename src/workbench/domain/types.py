"""Core domain types — coordinate, time, state, and command primitives.

Phase 0.4 first dataclasses:
- :class:`PositionENU`: (x, y, z) in meters, Map ENU frame (plan/11 § 11.3).
- :class:`VelocityENU`: velocity vector in ENU frame.
- :class:`Time`: simulation time, seconds (plan/02 § 2.2b SimulationClock).

Phase 2.1 additions (v0.14 + v0.15 Run/Sim lifecycle and command path):
- :class:`CommandSource`: enum tagging where a positioner command came from.
- :class:`PositionerCommand`: Single-Command-Path message (plan/02 § 2.2a).
- :class:`RunState`: Target Run lifecycle (plan/03 § 3.5.0).
- :class:`RunTerminationReason`: why a Target Run ended.
- :class:`SimulationState`: outer SimulationClock state (plan/03 § 3.5.0b).
- :class:`SpeedMultiplier`: SimulationClock speed multiplier vs wall-clock.

All types are immutable (``frozen=True``) per plan/02 § 2.1 원칙 4 (Observable).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum


@dataclass(frozen=True, slots=True)
class PositionENU:
    """Position in Map ENU frame (East / North / Up), meters.

    The Map's :class:`GeoOrigin` (plan/11 § 11.3) defines ``(0, 0, 0)``.
    Origin is unchangeable across a Workspace's lifetime (plan/01 불변 원칙).
    """

    x: float
    """East-axis component [m]."""

    y: float
    """North-axis component [m]."""

    z: float
    """Up-axis component [m]."""


@dataclass(frozen=True, slots=True)
class VelocityENU:
    """Velocity in Map ENU frame, m/s."""

    vx: float
    """East-axis velocity [m/s]."""

    vy: float
    """North-axis velocity [m/s]."""

    vz: float
    """Up-axis velocity [m/s]."""

    @property
    def speed(self) -> float:
        """Magnitude of the velocity vector [m/s]."""
        return math.sqrt(self.vx**2 + self.vy**2 + self.vz**2)


@dataclass(frozen=True, slots=True)
class Time:
    """Simulation time, seconds from SimulationClock start.

    See plan/02 § 2.2b (SimulationClock) and plan/03 § 3.5.0b (two-layer time control).
    Wall clock is not used for physics — :class:`Time` is the authoritative
    sim-time and all environment / pipeline updates are gated by it.
    """

    seconds: float
    """Seconds since SimulationClock start (sim-time, not wall-clock)."""

    def advance(self, dt: float) -> Time:
        """Return a new :class:`Time` ``dt`` seconds later (immutable)."""
        return Time(self.seconds + dt)


# ---------------------------------------------------------------------------
# Single Command Path (v0.14, plan/02 § 2.2a, plan/03 § 3.5.1c)
# ---------------------------------------------------------------------------


class CommandSource(Enum):
    """Source tag for a positioner command (Single Command Path, v0.14).

    Only three sources are allowed; the CommandBus rejects everything else.
    See plan/02 § 2.2a and plan/03 § 3.5.1c.

    Members:
        TRACKER: Emitted by the EKF/UKF tracker during AUTO mode.
            ``source_track_id`` and ``source_frame_id`` MUST be set so
            that the GT Lineage check (plan/06 § 6.3.6a) can verify the
            command came from a legitimate track.
        MANUAL_USER: Emitted by the UI's arrow-key handler in MANUAL mode
            (or via the InputBuffer flush after un-pause).
        INITIAL_SCAN: Emitted by RunManager exactly once at Target Run
            start to point the antenna at the first scan direction.
    """

    TRACKER = "tracker"
    MANUAL_USER = "manual_user"
    INITIAL_SCAN = "initial_scan"


@dataclass(frozen=True, slots=True)
class PositionerCommand:
    """Positioner azimuth/elevation command on the Single Command Path.

    The CommandBus is the only path that may publish these to the
    PositionerController (plan/02 § 2.2a). The ``source`` tag and the
    optional Lineage IDs feed the post-Run GT Isolation audit
    (plan/06 § 6.3.6a, Level 3-2).

    Attributes:
        az_rad: Commanded azimuth [rad], clockwise from North.
        el_rad: Commanded elevation [rad], above horizon.
        source: Where this command came from (see :class:`CommandSource`).
        timestamp_s: Sim time at which the command was published [s].
        source_track_id: Track ID this command was derived from. Required
            when ``source == TRACKER``; ``None`` otherwise.
        source_frame_id: Pipeline frame ID this command was derived from.
            Required when ``source == TRACKER``; ``None`` otherwise.

    Raises:
        ValueError: If ``source == TRACKER`` and either lineage ID is
            ``None`` (would break the post-Run audit).
    """

    az_rad: float
    el_rad: float
    source: CommandSource
    timestamp_s: float
    source_track_id: int | None = None
    source_frame_id: int | None = None

    def __post_init__(self) -> None:
        if self.source is CommandSource.TRACKER and (
            self.source_track_id is None or self.source_frame_id is None
        ):
            msg = (
                "PositionerCommand with source=TRACKER requires both "
                "source_track_id and source_frame_id (GT Lineage)."
            )
            raise ValueError(msg)


# ---------------------------------------------------------------------------
# Target Run lifecycle (v0.14, plan/03 § 3.5.0)
# ---------------------------------------------------------------------------


class RunState(Enum):
    """Target Run lifecycle state (v0.14).

    A Target Run is the replay of a target trajectory; it is the inner
    layer of the v0.15 two-layer time control. The outer
    :class:`SimulationState` runs continuously even when the run is IDLE.

    Members:
        IDLE: No run scheduled or just stopped without start.
        RUNNING: Trajectory is being replayed; metrics being recorded.
        PAUSED: Trajectory frozen at current frame; sim clock may continue.
        ENDED: Run finished — see :class:`RunTerminationReason`.
    """

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    ENDED = "ended"


class RunTerminationReason(Enum):
    """Why a :class:`RunState` transitioned to ENDED (v0.14)."""

    COMPLETED = "completed"
    """Trajectory finished its full duration."""

    USER_STOPPED = "user_stopped"
    """User clicked Target Stop."""

    SIM_STOPPED = "sim_stopped"
    """Outer SimulationClock was stopped — run is forced IDLE."""

    ERROR = "error"
    """Pipeline / plugin raised; run aborted with an error report."""


# ---------------------------------------------------------------------------
# SimulationClock (outer layer, v0.15, plan/03 § 3.5.0b)
# ---------------------------------------------------------------------------


class SimulationState(Enum):
    """Outer SimulationClock state (v0.15).

    The Sim Clock is the time source for all environment / radar physics.
    It is independent from :class:`RunState`: a paused Sim freezes
    everything; a running Sim with an IDLE Run still advances the
    environment (waves, atmosphere, ownship motion).

    Members:
        STOPPED: ``sim_t = 0``; environment reset; no tick.
        RUNNING: Sim thread ticks; physics advancing.
        PAUSED: Sim thread waiting; ``sim_t`` frozen; UI input buffered.
    """

    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SpeedMultiplier(IntEnum):
    """SimulationClock speed multiplier vs wall-clock (v0.15).

    Powers of two from x1 to x8 are the only user-selectable values; the
    UI also reports the **actual** achieved multiplier (typically lower
    under heavy plugin load).
    """

    X1 = 1
    X2 = 2
    X4 = 4
    X8 = 8
