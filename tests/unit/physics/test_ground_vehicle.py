"""Unit tests for workbench.physics.dynamics.ground_vehicle (Phase 2.4f)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.dynamics.ground_vehicle import (
    GroundVehicleDynamics,
    ground_vehicle_pose,
)
from workbench.physics.dynamics.reference import Waypoint

# ---------------------------------------------------------------------
# GroundVehicleDynamics
# ---------------------------------------------------------------------


def test_ground_vehicle_default_max_speed() -> None:
    d = GroundVehicleDynamics()
    assert d.max_speed_mps == 60.0


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_ground_vehicle_rejects_non_positive_max_speed(bad: float) -> None:
    with pytest.raises(ValueError, match=r"max_speed_mps"):
        GroundVehicleDynamics(max_speed_mps=bad)


# ---------------------------------------------------------------------
# ground_vehicle_pose
# ---------------------------------------------------------------------


def _trajectory() -> tuple[Waypoint, ...]:
    return (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0, heading_rad=0.0),
        Waypoint(t_s=20.0, east_m=200.0, north_m=400.0, altitude_m=999.0, heading_rad=math.pi),
    )


def test_pose_xy_at_midpoint() -> None:
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=42.0,
        sim_t_s=10.0,
    )
    assert s.east_m == pytest.approx(100.0, abs=1e-12)
    assert s.north_m == pytest.approx(200.0, abs=1e-12)


def test_pose_z_from_dem_ignores_trajectory_altitude() -> None:
    # Trajectory altitude=999 at t=20, but DEM says 42 → DEM wins.
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=42.0,
        sim_t_s=20.0,
    )
    assert s.altitude_m == 42.0


def test_pose_velocity_xy_from_trajectory_slope() -> None:
    # 0 → 200 East over 20 s → 10 m/s; 0 → 400 North over 20 s → 20 m/s.
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=0.0,
        sim_t_s=10.0,
    )
    assert s.velocity_east_mps == pytest.approx(10.0, abs=1e-12)
    assert s.velocity_north_mps == pytest.approx(20.0, abs=1e-12)


def test_pose_velocity_up_zero() -> None:
    # MVP: ground vehicles have zero vertical velocity (DEM-bound).
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=42.0,
        sim_t_s=10.0,
    )
    assert s.velocity_up_mps == 0.0


def test_pose_attitude_flat_at_mvp() -> None:
    # MVP: ground vehicle roll / pitch always 0.
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=0.0,
        sim_t_s=10.0,
    )
    assert s.roll_rad == 0.0
    assert s.pitch_rad == 0.0


def test_pose_yaw_from_trajectory_heading() -> None:
    # heading 0 → pi linear at t=10 → pi/2.
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=0.0,
        sim_t_s=10.0,
    )
    assert s.yaw_rad == pytest.approx(math.pi / 2, abs=1e-12)


def test_pose_carries_sim_t_s() -> None:
    s = ground_vehicle_pose(
        GroundVehicleDynamics(),
        _trajectory(),
        dem_z_m=0.0,
        sim_t_s=7.5,
    )
    assert s.sim_t_s == 7.5


def test_pose_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match=r"at least one waypoint"):
        ground_vehicle_pose(
            GroundVehicleDynamics(),
            (),
            dem_z_m=0.0,
            sim_t_s=0.0,
        )
