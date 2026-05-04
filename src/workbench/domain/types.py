"""Core domain types — coordinate, time, and basic dataclasses.

Phase 0.4 first dataclasses:
- :class:`PositionENU`: (x, y, z) in meters, Map ENU frame (plan/11 § 11.3).
- :class:`VelocityENU`: velocity vector in ENU frame.
- :class:`Time`: simulation time, seconds (plan/02 § 2.2b SimulationClock).

All types are immutable (``frozen=True``) per plan/02 § 2.1 원칙 4 (Observable).
"""

from __future__ import annotations

from dataclasses import dataclass


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
        return (self.vx**2 + self.vy**2 + self.vz**2) ** 0.5


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
