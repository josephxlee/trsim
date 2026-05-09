"""Unit tests for workbench.physics.dynamics.reference (Phase 2.4d)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.dynamics.reference import (
    TrajectoryReference,
    Waypoint,
    interpolate_reference,
)

# ---------------------------------------------------------------------
# Waypoint
# ---------------------------------------------------------------------


def test_waypoint_default_heading_zero() -> None:
    wp = Waypoint(t_s=0.0, east_m=10.0, north_m=20.0, altitude_m=100.0)
    assert wp.heading_rad == 0.0


def test_waypoint_explicit_heading() -> None:
    wp = Waypoint(t_s=5.0, east_m=1.0, north_m=2.0, altitude_m=3.0, heading_rad=math.pi / 4)
    assert wp.heading_rad == pytest.approx(math.pi / 4, abs=1e-12)


# ---------------------------------------------------------------------
# interpolate_reference — boundary / clamping behavior
# ---------------------------------------------------------------------


def test_interpolate_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match=r"at least one waypoint"):
        interpolate_reference((), 0.0)


def test_interpolate_single_waypoint_returns_constant() -> None:
    wp = Waypoint(t_s=10.0, east_m=1.0, north_m=2.0, altitude_m=3.0, heading_rad=0.5)
    for t in (-100.0, 0.0, 10.0, 1000.0):
        ref = interpolate_reference((wp,), t)
        assert ref.east_m == 1.0
        assert ref.north_m == 2.0
        assert ref.altitude_m == 3.0
        assert ref.heading_rad == 0.5
        assert ref.sim_t_s == t


def test_interpolate_clamps_below_first() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=0.0, altitude_m=1000.0),
    )
    ref = interpolate_reference(traj, sim_t_s=-5.0)
    assert ref.east_m == 0.0
    assert ref.sim_t_s == -5.0


def test_interpolate_clamps_above_last() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=0.0, altitude_m=1000.0),
    )
    ref = interpolate_reference(traj, sim_t_s=15.0)
    assert ref.east_m == 100.0
    assert ref.sim_t_s == 15.0


def test_interpolate_returns_first_waypoint_at_t_first() -> None:
    traj = (
        Waypoint(t_s=2.0, east_m=10.0, north_m=20.0, altitude_m=300.0),
        Waypoint(t_s=8.0, east_m=70.0, north_m=120.0, altitude_m=600.0),
    )
    ref = interpolate_reference(traj, sim_t_s=2.0)
    assert ref.east_m == 10.0
    assert ref.north_m == 20.0
    assert ref.altitude_m == 300.0


def test_interpolate_returns_last_waypoint_at_t_last() -> None:
    traj = (
        Waypoint(t_s=2.0, east_m=10.0, north_m=20.0, altitude_m=300.0),
        Waypoint(t_s=8.0, east_m=70.0, north_m=120.0, altitude_m=600.0),
    )
    ref = interpolate_reference(traj, sim_t_s=8.0)
    assert ref.east_m == 70.0
    assert ref.north_m == 120.0
    assert ref.altitude_m == 600.0


# ---------------------------------------------------------------------
# Linear interpolation
# ---------------------------------------------------------------------


def test_interpolate_midpoint() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=200.0, altitude_m=1500.0),
    )
    ref = interpolate_reference(traj, sim_t_s=5.0)
    assert ref.east_m == pytest.approx(50.0, abs=1e-12)
    assert ref.north_m == pytest.approx(100.0, abs=1e-12)
    assert ref.altitude_m == pytest.approx(1250.0, abs=1e-12)


def test_interpolate_quarter_point() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),
        Waypoint(t_s=4.0, east_m=400.0, north_m=800.0, altitude_m=2000.0),
    )
    ref = interpolate_reference(traj, sim_t_s=1.0)
    # w = 0.25
    assert ref.east_m == pytest.approx(100.0, abs=1e-12)
    assert ref.north_m == pytest.approx(200.0, abs=1e-12)
    assert ref.altitude_m == pytest.approx(500.0, abs=1e-12)


def test_interpolate_heading_linear() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0, heading_rad=0.0),
        Waypoint(t_s=10.0, east_m=0.0, north_m=0.0, altitude_m=0.0, heading_rad=1.0),
    )
    ref = interpolate_reference(traj, sim_t_s=3.0)
    assert ref.heading_rad == pytest.approx(0.3, abs=1e-12)


def test_interpolate_multi_segment_picks_correct_segment() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=0.0, altitude_m=0.0),
        Waypoint(t_s=20.0, east_m=100.0, north_m=200.0, altitude_m=0.0),
    )
    # Mid-point of the second segment (t=15) — east is constant 100,
    # north linearly interpolates 0 → 200, w=0.5 → 100.
    ref = interpolate_reference(traj, sim_t_s=15.0)
    assert ref.east_m == pytest.approx(100.0, abs=1e-12)
    assert ref.north_m == pytest.approx(100.0, abs=1e-12)


def test_interpolate_carries_sim_t_s() -> None:
    traj = (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=0.0, altitude_m=0.0),
    )
    ref = interpolate_reference(traj, sim_t_s=7.5)
    assert ref.sim_t_s == 7.5


def test_trajectory_reference_is_frozen() -> None:
    ref = TrajectoryReference(east_m=1.0, north_m=2.0, altitude_m=3.0, heading_rad=0.0, sim_t_s=0.0)
    with pytest.raises(Exception):  # noqa: B017
        ref.east_m = 5.0  # type: ignore[misc]
