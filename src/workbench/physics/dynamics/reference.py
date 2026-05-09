"""Trajectory reference for dynamics tracking (plan/14 § 14.7).

Phase 2.4d (shared by 2.4d/e/f) — converts a tuple of physics-layer
:class:`Waypoint` samples into a sample-able reference function for
the dynamics solver.

The dynamics modules (aircraft, powered-flight, surface-vessel,
ground-vehicle) treat the trajectory CSV as a **target** that PD
controllers track, not as ground truth (plan/14 § 14.2.3 — "Trajectory
= reference, actual motion = dynamics"). For BALLISTIC targets the
trajectory is ignored entirely (initial conditions only).

Layering (plan/02 § 2.5): physics is the bottom layer and must not
import from :mod:`workbench.domain`. The higher-level
:class:`workbench.domain.target.TargetWaypoint` is structurally
identical to :class:`Waypoint` here; converting a domain trajectory to
the physics-layer form is a one-liner left to the orchestration layer
(Phase 3 ``RadarPipeline`` / ``Scenario``).

Linear interpolation in time:

- Times are assumed strictly increasing (validated at the source —
  TargetEntity does this for domain trajectories; this module accepts
  whatever the caller passes and only protects against the empty case).
- Outside ``[t_first, t_last]`` the boundary value is clamped (no
  extrapolation).
- ``heading_rad`` interpolates linearly without wrap-around handling
  — Editor presets are short and smooth at MVP. Wrap-aware spherical
  interpolation is MVP+alpha (Open Question 14.12).

References:

- plan/14 § 14.7 — Trajectory Reference.
- plan/03 § 3.2.1g / plan/12 § 12.7 — TargetWaypoint shape.
- plan/02 § 2.5 — Layer dependency rules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Waypoint:
    """Physics-layer trajectory sample (plan/14 § 14.7).

    Same shape as :class:`workbench.domain.target.TargetWaypoint`,
    duplicated here so the physics layer does not import from domain
    (plan/02 § 2.5).

    Attributes:
        t_s: Sample time relative to simulation start [s].
        east_m: East position in Map ENU [m].
        north_m: North position in Map ENU [m].
        altitude_m: Up position in Map ENU [m]. Interpretation depends
            on the consuming dynamics module — AIRCRAFT treats it as
            absolute altitude, SURFACE_VESSEL ignores it, etc.
            (plan/14 § 14.7.3).
        heading_rad: Heading at this sample (CW from North) [rad].
    """

    t_s: float
    east_m: float
    north_m: float
    altitude_m: float
    heading_rad: float = 0.0


@dataclass(frozen=True, slots=True)
class TrajectoryReference:
    """Sampled reference state for the dynamics PD trackers.

    Same shape as :class:`Waypoint` plus ``sim_t_s`` so the consumer
    can record / log the sample time.

    Attributes:
        east_m: Reference east position [m].
        north_m: Reference north position [m].
        altitude_m: Reference altitude [m] (motion-kind dependent —
            see plan/14 § 14.7.3).
        heading_rad: Reference heading [rad] (CW from North).
        sim_t_s: Sample time [s].
    """

    east_m: float
    north_m: float
    altitude_m: float
    heading_rad: float
    sim_t_s: float


def interpolate_reference(
    trajectory: tuple[Waypoint, ...],
    sim_t_s: float,
) -> TrajectoryReference:
    """Linearly interpolate a trajectory at ``sim_t_s``.

    - Empty trajectories are rejected.
    - Single-waypoint trajectories return that waypoint at every time.
    - Multi-waypoint: linear interpolation between bracketing samples.
      Outside ``[t_first, t_last]`` the first / last waypoint is held.

    Args:
        trajectory: Source waypoints, ``t_s`` strictly increasing.
        sim_t_s: Time at which to sample [s].

    Returns:
        :class:`TrajectoryReference` at ``sim_t_s``.

    Raises:
        ValueError: If ``trajectory`` is empty.
    """
    n = len(trajectory)
    if n == 0:
        msg = "trajectory must contain at least one waypoint"
        raise ValueError(msg)

    first = trajectory[0]
    if n == 1 or sim_t_s <= first.t_s:
        return TrajectoryReference(
            east_m=first.east_m,
            north_m=first.north_m,
            altitude_m=first.altitude_m,
            heading_rad=first.heading_rad,
            sim_t_s=sim_t_s,
        )

    last = trajectory[-1]
    if sim_t_s >= last.t_s:
        return TrajectoryReference(
            east_m=last.east_m,
            north_m=last.north_m,
            altitude_m=last.altitude_m,
            heading_rad=last.heading_rad,
            sim_t_s=sim_t_s,
        )

    # Locate enclosing segment. Trajectories are short — typical
    # Editor presets have under 50 waypoints — so a linear scan beats
    # importing bisect for one call site.
    for i in range(n - 1):
        a = trajectory[i]
        b = trajectory[i + 1]
        if a.t_s <= sim_t_s <= b.t_s:
            # Caller-supplied invariant: b.t_s > a.t_s.
            w = (sim_t_s - a.t_s) / (b.t_s - a.t_s)
            return TrajectoryReference(
                east_m=a.east_m + w * (b.east_m - a.east_m),
                north_m=a.north_m + w * (b.north_m - a.north_m),
                altitude_m=a.altitude_m + w * (b.altitude_m - a.altitude_m),
                heading_rad=a.heading_rad + w * (b.heading_rad - a.heading_rad),
                sim_t_s=sim_t_s,
            )
    # Unreachable — sim_t_s is bracketed by the two clamps above.
    return TrajectoryReference(
        east_m=last.east_m,
        north_m=last.north_m,
        altitude_m=last.altitude_m,
        heading_rad=last.heading_rad,
        sim_t_s=sim_t_s,
    )


def reference_velocity_enu(
    trajectory: tuple[Waypoint, ...],
    sim_t_s: float,
) -> tuple[float, float, float]:
    """Piecewise-constant ENU velocity from a trajectory (plan/14 § 14.7).

    Slope of the linear segment containing ``sim_t_s`` —
    ``(d_east/dt, d_north/dt, d_altitude/dt)`` in m/s. Used by the
    kinematic dynamics modules (surface_vessel, ground_vehicle) to
    populate :class:`RigidBodyState.velocity_*` so radar Doppler
    measurements pick up the trajectory motion.

    Edge cases:

    - Empty or single-waypoint trajectories return ``(0, 0, 0)``.
    - Outside ``[t_first, t_last]`` velocity is ``(0, 0, 0)`` (target
      is "at rest" before / after the trajectory window).

    Args:
        trajectory: Source waypoints (need not be strictly increasing
            for a single-element case, but linearly increasing for
            multi-element).
        sim_t_s: Time at which to sample velocity [s].

    Returns:
        ``(velocity_east_mps, velocity_north_mps, velocity_up_mps)``.
    """
    n = len(trajectory)
    if n < 2:
        return (0.0, 0.0, 0.0)
    first = trajectory[0]
    last = trajectory[-1]
    if sim_t_s < first.t_s or sim_t_s > last.t_s:
        return (0.0, 0.0, 0.0)
    for i in range(n - 1):
        a = trajectory[i]
        b = trajectory[i + 1]
        if a.t_s <= sim_t_s <= b.t_s:
            dt = b.t_s - a.t_s
            if dt <= 0.0:
                return (0.0, 0.0, 0.0)
            return (
                (b.east_m - a.east_m) / dt,
                (b.north_m - a.north_m) / dt,
                (b.altitude_m - a.altitude_m) / dt,
            )
    return (0.0, 0.0, 0.0)
