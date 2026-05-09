"""Unit tests for workbench.physics.dynamics.surface_vessel (Phase 2.4f)."""

from __future__ import annotations

import math

import pytest

from workbench.physics.dynamics.reference import Waypoint
from workbench.physics.dynamics.surface_vessel import (
    SurfaceVesselDynamics,
    WaveCoupling,
    surface_vessel_pose,
    wave_heave_velocity_mps,
    wave_oscillation,
)

# ---------------------------------------------------------------------
# WaveCoupling
# ---------------------------------------------------------------------


def test_wave_coupling_defaults_zero() -> None:
    c = WaveCoupling()
    assert c.heave_factor == 0.0
    assert c.pitch_factor == 0.0
    assert c.roll_factor == 0.0


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"heave_factor": -0.1}, r"heave_factor"),
        ({"heave_factor": 1.5}, r"heave_factor"),
        ({"pitch_factor": -0.1}, r"pitch_factor"),
        ({"roll_factor": -0.1}, r"roll_factor"),
    ],
)
def test_wave_coupling_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        WaveCoupling(**override)


# ---------------------------------------------------------------------
# wave_oscillation
# ---------------------------------------------------------------------


def test_wave_zero_amplitude_no_oscillation() -> None:
    c = WaveCoupling(heave_factor=1.0, pitch_factor=0.1, roll_factor=0.1)
    assert wave_oscillation(c, wave_amplitude_m=0.0, wave_period_s=5.0, sim_t_s=1.0) == (
        0.0,
        0.0,
        0.0,
    )


def test_wave_zero_period_no_oscillation() -> None:
    c = WaveCoupling(heave_factor=1.0, pitch_factor=0.1, roll_factor=0.1)
    assert wave_oscillation(c, wave_amplitude_m=2.0, wave_period_s=0.0, sim_t_s=1.0) == (
        0.0,
        0.0,
        0.0,
    )


def test_wave_at_t_zero_is_zero() -> None:
    # sin(0) = 0
    c = WaveCoupling(heave_factor=0.7, pitch_factor=0.15, roll_factor=0.20)
    heave, roll, pitch = wave_oscillation(c, wave_amplitude_m=2.0, wave_period_s=4.0, sim_t_s=0.0)
    assert heave == pytest.approx(0.0, abs=1e-12)
    assert roll == pytest.approx(0.0, abs=1e-12)
    assert pitch == pytest.approx(0.0, abs=1e-12)


def test_wave_at_quarter_period_is_peak() -> None:
    # t = T/4 → sin(omega * t) = 1 → base = amplitude
    c = WaveCoupling(heave_factor=0.7, pitch_factor=0.15, roll_factor=0.20)
    heave, roll, pitch = wave_oscillation(c, wave_amplitude_m=2.0, wave_period_s=4.0, sim_t_s=1.0)
    assert heave == pytest.approx(2.0 * 0.7, abs=1e-12)
    assert roll == pytest.approx(2.0 * 0.20, abs=1e-12)
    assert pitch == pytest.approx(2.0 * 0.15, abs=1e-12)


def test_wave_heave_velocity_at_t_zero_is_peak() -> None:
    # cos(0) = 1 → v_heave = omega * A * heave_factor
    c = WaveCoupling(heave_factor=0.7)
    period = 4.0
    amp = 2.0
    expected = (2.0 * math.pi / period) * amp * 0.7
    v = wave_heave_velocity_mps(c, wave_amplitude_m=amp, wave_period_s=period, sim_t_s=0.0)
    assert v == pytest.approx(expected, abs=1e-12)


def test_wave_heave_velocity_at_quarter_period_is_zero() -> None:
    # cos(omega * T/4) = cos(pi/2) = 0 → v_heave = 0
    c = WaveCoupling(heave_factor=1.0)
    v = wave_heave_velocity_mps(c, wave_amplitude_m=2.0, wave_period_s=4.0, sim_t_s=1.0)
    assert v == pytest.approx(0.0, abs=1e-12)


def test_wave_heave_velocity_zero_amplitude() -> None:
    c = WaveCoupling(heave_factor=1.0)
    assert wave_heave_velocity_mps(c, wave_amplitude_m=0.0, wave_period_s=5.0, sim_t_s=1.0) == 0.0


# ---------------------------------------------------------------------
# surface_vessel_pose
# ---------------------------------------------------------------------


def _trajectory() -> tuple[Waypoint, ...]:
    return (
        Waypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0, heading_rad=0.0),
        Waypoint(t_s=10.0, east_m=100.0, north_m=0.0, altitude_m=0.0, heading_rad=math.pi / 2),
    )


def _dynamics() -> SurfaceVesselDynamics:
    return SurfaceVesselDynamics(
        wave_coupling=WaveCoupling(heave_factor=0.7, pitch_factor=0.1, roll_factor=0.1)
    )


def test_pose_xy_from_trajectory_at_midpoint() -> None:
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=0.0,
        wave_period_s=5.0,
        sim_t_s=5.0,
    )
    assert s.east_m == pytest.approx(50.0, abs=1e-12)
    assert s.north_m == pytest.approx(0.0, abs=1e-12)


def test_pose_z_from_sea_surface_plus_heave() -> None:
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=10.0,
        wave_amplitude_m=2.0,
        wave_period_s=4.0,
        sim_t_s=1.0,  # quarter period → peak heave
    )
    # 10 + 2.0 * 0.7 = 11.4
    assert s.altitude_m == pytest.approx(11.4, abs=1e-12)


def test_pose_velocity_xy_from_trajectory_slope() -> None:
    # 10 m → 100 m over 10 s → vE = 10 m/s
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=0.0,
        wave_period_s=5.0,
        sim_t_s=5.0,
    )
    assert s.velocity_east_mps == pytest.approx(10.0, abs=1e-12)
    assert s.velocity_north_mps == pytest.approx(0.0, abs=1e-12)


def test_pose_velocity_up_from_heave_derivative() -> None:
    # At t = 0, v_heave = omega * A * heave_factor
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=2.0,
        wave_period_s=4.0,
        sim_t_s=0.0,
    )
    expected = (2.0 * math.pi / 4.0) * 2.0 * 0.7
    assert s.velocity_up_mps == pytest.approx(expected, abs=1e-12)


def test_pose_yaw_from_trajectory_heading() -> None:
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=0.0,
        wave_period_s=5.0,
        sim_t_s=5.0,
    )
    # Linear interpolation 0 → pi/2 at t=5 → pi/4
    assert s.yaw_rad == pytest.approx(math.pi / 4, abs=1e-12)


def test_pose_roll_pitch_from_wave_at_peak() -> None:
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=2.0,
        wave_period_s=4.0,
        sim_t_s=1.0,
    )
    assert s.roll_rad == pytest.approx(2.0 * 0.1, abs=1e-12)
    assert s.pitch_rad == pytest.approx(2.0 * 0.1, abs=1e-12)


def test_pose_carries_sim_t_s() -> None:
    s = surface_vessel_pose(
        _dynamics(),
        _trajectory(),
        sea_surface_z_m=0.0,
        wave_amplitude_m=0.0,
        wave_period_s=5.0,
        sim_t_s=3.5,
    )
    assert s.sim_t_s == 3.5


def test_pose_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match=r"at least one waypoint"):
        surface_vessel_pose(
            _dynamics(),
            (),
            sea_surface_z_m=0.0,
            wave_amplitude_m=0.0,
            wave_period_s=5.0,
            sim_t_s=0.0,
        )
