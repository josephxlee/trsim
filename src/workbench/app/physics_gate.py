"""Physics sanity gate (Phase 3 D2, plan/04 § 4.3).

A lightweight pre-flight check that catches obviously unphysical
values *before* the Pipeline starts simulating. The Pipeline itself
already validates everything via dataclass ``__post_init__``s, but
those run at construction time; the physics gate runs at *Run
start* against the live composed state so the user sees a clear
"this scenario can't be real" message instead of a numerical NaN
exploding 1000 frames in.

Scope (MVP):

- :func:`check_velocity_below_light_speed` — magnitude < c (any
  velocity vector entering the pipeline).
- :func:`check_mass_positive` — mass > 0 for any dynamic body.
- :func:`check_altitude_plausible` — altitude in [-500, 100_000] m
  (sub-sea drilling rig to upper edge of "tracking radar" regime).
- :func:`check_frequency_radar_band` — carrier between 100 MHz
  (HF radar) and 100 GHz (mm-wave).
- :func:`check_finite_position` — east/north/up all finite (catches
  NaN / Inf creeping in from broken trajectory imports).

API shape:

- :class:`PhysicsCheckResult` — single check outcome (name, ok,
  reason).
- :func:`run_physics_gate(checks)` — fan out checks, collect
  results into a :class:`PhysicsGateReport`.
- :class:`PhysicsGateReport.has_failures` — Run-start gate; the
  Run UI refuses to start when this returns True.

The gate is intentionally synchronous and side-effect free so it
fits inside any controller / CLI / batch loop without taking on
extra dependencies.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

C_LIGHT_M_S: float = 299_792_458.0
"""Speed of light in vacuum (NIST CODATA, 2018)."""

MIN_ALTITUDE_M: float = -500.0
"""Lowest plausible altitude (~deepest fixed offshore platform)."""

MAX_ALTITUDE_M: float = 100_000.0
"""Highest plausible altitude (~upper-edge "tracking radar" regime)."""

MIN_RADAR_FREQ_HZ: float = 100e6
"""Lowest plausible radar carrier (HF radar floor)."""

MAX_RADAR_FREQ_HZ: float = 100e9
"""Highest plausible radar carrier (mm-wave ceiling)."""


@dataclass(frozen=True, slots=True)
class PhysicsCheckResult:
    """Outcome of one sanity check.

    Attributes:
        name: Short tag, e.g. ``"velocity_below_c"``.
        ok: ``True`` = check passed.
        reason: Empty when ``ok``; otherwise a one-line diagnostic.
    """

    name: str
    ok: bool
    reason: str = ""


@dataclass(frozen=True, slots=True)
class PhysicsGateReport:
    """Aggregate of multiple :class:`PhysicsCheckResult` outcomes.

    Attributes:
        results: All check outcomes in registration order.
    """

    results: tuple[PhysicsCheckResult, ...]

    @property
    def has_failures(self) -> bool:
        """``True`` if any check failed — Run UI gates on this."""
        return any(not r.ok for r in self.results)

    @property
    def failures(self) -> tuple[PhysicsCheckResult, ...]:
        """Subset of :attr:`results` that failed."""
        return tuple(r for r in self.results if not r.ok)


def run_physics_gate(results: Iterable[PhysicsCheckResult]) -> PhysicsGateReport:
    """Bundle a stream of check results into a :class:`PhysicsGateReport`."""
    return PhysicsGateReport(results=tuple(results))


# ---------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------


def check_velocity_below_light_speed(
    velocity_mps: tuple[float, float, float],
    *,
    name: str = "velocity_below_c",
) -> PhysicsCheckResult:
    """Reject |v| >= c.

    Args:
        velocity_mps: ``(east, north, up)`` velocity in m/s.
        name: Result tag (default ``"velocity_below_c"``).
    """
    speed = math.sqrt(sum(v * v for v in velocity_mps))
    if speed >= C_LIGHT_M_S:
        return PhysicsCheckResult(
            name=name,
            ok=False,
            reason=f"|v| = {speed:.3e} m/s >= c ({C_LIGHT_M_S:.3e} m/s)",
        )
    return PhysicsCheckResult(name=name, ok=True)


def check_mass_positive(mass_kg: float, *, name: str = "mass_positive") -> PhysicsCheckResult:
    """Reject mass <= 0 or non-finite mass."""
    if not math.isfinite(mass_kg):
        return PhysicsCheckResult(
            name=name, ok=False, reason=f"mass_kg = {mass_kg!r} is not finite"
        )
    if mass_kg <= 0.0:
        return PhysicsCheckResult(name=name, ok=False, reason=f"mass_kg = {mass_kg} <= 0")
    return PhysicsCheckResult(name=name, ok=True)


def check_altitude_plausible(
    altitude_m: float,
    *,
    name: str = "altitude_plausible",
    min_m: float = MIN_ALTITUDE_M,
    max_m: float = MAX_ALTITUDE_M,
) -> PhysicsCheckResult:
    """Reject altitudes outside [min_m, max_m]."""
    if not math.isfinite(altitude_m):
        return PhysicsCheckResult(
            name=name, ok=False, reason=f"altitude_m = {altitude_m!r} is not finite"
        )
    if altitude_m < min_m or altitude_m > max_m:
        return PhysicsCheckResult(
            name=name,
            ok=False,
            reason=f"altitude_m = {altitude_m} outside [{min_m}, {max_m}]",
        )
    return PhysicsCheckResult(name=name, ok=True)


def check_frequency_radar_band(
    frequency_hz: float,
    *,
    name: str = "frequency_radar_band",
    min_hz: float = MIN_RADAR_FREQ_HZ,
    max_hz: float = MAX_RADAR_FREQ_HZ,
) -> PhysicsCheckResult:
    """Reject carrier frequencies outside [100 MHz, 100 GHz]."""
    if not math.isfinite(frequency_hz):
        return PhysicsCheckResult(
            name=name, ok=False, reason=f"frequency_hz = {frequency_hz!r} is not finite"
        )
    if frequency_hz < min_hz or frequency_hz > max_hz:
        return PhysicsCheckResult(
            name=name,
            ok=False,
            reason=f"frequency_hz = {frequency_hz} outside [{min_hz}, {max_hz}]",
        )
    return PhysicsCheckResult(name=name, ok=True)


def check_finite_position(
    position_enu_m: tuple[float, float, float],
    *,
    name: str = "finite_position",
) -> PhysicsCheckResult:
    """Reject positions with any NaN / Inf component."""
    for axis, value in zip(("E", "N", "U"), position_enu_m, strict=True):
        if not math.isfinite(value):
            return PhysicsCheckResult(
                name=name, ok=False, reason=f"{axis} component is {value!r} (not finite)"
            )
    return PhysicsCheckResult(name=name, ok=True)
