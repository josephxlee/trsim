"""MockPrimaryTargetGenerator unit tests (Phase 4 L6)."""

from __future__ import annotations

import math

import pytest

from workbench.app.simulator import (
    MockPrimaryTargetGenerator,
    MockPrimaryTargetSnapshot,
)

# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_constructor_rejects_nonpositive_orbit_radius() -> None:
    with pytest.raises(ValueError, match=r"orbit_radius_m must be > 0"):
        MockPrimaryTargetGenerator(orbit_radius_m=0.0)


def test_constructor_rejects_nonpositive_orbit_period() -> None:
    with pytest.raises(ValueError, match=r"orbit_period_s must be > 0"):
        MockPrimaryTargetGenerator(orbit_period_s=0.0)


def test_constructor_rejects_nonpositive_scope_window() -> None:
    with pytest.raises(ValueError, match=r"scope_window_deg must be > 0"):
        MockPrimaryTargetGenerator(scope_window_deg=0.0)


def test_constructor_rejects_negative_lock_after() -> None:
    with pytest.raises(ValueError, match=r"lock_after_s must be >= 0"):
        MockPrimaryTargetGenerator(lock_after_s=-0.1)


# ---------------------------------------------------------------------
# snapshot_for
# ---------------------------------------------------------------------


def test_snapshot_for_rejects_negative_sim_t_s() -> None:
    gen = MockPrimaryTargetGenerator()
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        gen.snapshot_for(-0.1)


def test_snapshot_at_zero_is_east_of_radar() -> None:
    """cos(0)=1 -> east axis. atan2(east, north) -> 90 deg azimuth."""
    gen = MockPrimaryTargetGenerator(
        orbit_radius_m=1_000.0,
        target_altitude_m=0.0,
    )
    snap = gen.snapshot_for(0.0)
    assert snap.azimuth_deg == pytest.approx(90.0)
    assert snap.elevation_deg == pytest.approx(0.0, abs=1e-9)
    assert snap.range_m == pytest.approx(1_000.0)


def test_snapshot_speed_is_circumference_over_period() -> None:
    """v = 2*pi*R / T for a circular orbit."""
    gen = MockPrimaryTargetGenerator(
        orbit_radius_m=500.0,
        orbit_period_s=10.0,
    )
    snap = gen.snapshot_for(0.0)
    expected = (2.0 * math.pi * 500.0) / 10.0
    assert snap.speed_mps == pytest.approx(expected)


def test_actual_az_lags_commanded_az_by_servo_lag() -> None:
    gen = MockPrimaryTargetGenerator(servo_lag_deg=1.25)
    snap = gen.snapshot_for(0.0)
    assert snap.actual_az_deg == pytest.approx(snap.commanded_az_deg - 1.25)


def test_lock_flag_flips_after_lock_after() -> None:
    gen = MockPrimaryTargetGenerator(lock_after_s=0.5)
    assert gen.snapshot_for(0.0).is_locked is False
    assert gen.snapshot_for(0.49).is_locked is False
    assert gen.snapshot_for(0.5).is_locked is True
    assert gen.snapshot_for(1.0).is_locked is True


def test_cross_hair_x_reflects_servo_lag_over_scope_window() -> None:
    """x_offset = servo_lag / scope_window."""
    gen = MockPrimaryTargetGenerator(servo_lag_deg=2.5, scope_window_deg=10.0)
    snap = gen.snapshot_for(0.0)
    assert snap.cross_hair_norm[0] == pytest.approx(0.25)


def test_cross_hair_clamps_to_unit_box() -> None:
    """servo_lag >> scope_window -> x clamped to 1.0."""
    gen = MockPrimaryTargetGenerator(servo_lag_deg=100.0, scope_window_deg=10.0)
    snap = gen.snapshot_for(0.0)
    assert snap.cross_hair_norm[0] == pytest.approx(1.0)
    assert -1.0 <= snap.cross_hair_norm[1] <= 1.0


def test_snapshot_for_returns_dataclass() -> None:
    gen = MockPrimaryTargetGenerator()
    snap = gen.snapshot_for(1.0)
    assert isinstance(snap, MockPrimaryTargetSnapshot)
    assert snap.sim_t_s == pytest.approx(1.0)
    assert snap.range_m > 0.0


def test_snapshot_is_deterministic_per_sim_t_s() -> None:
    gen = MockPrimaryTargetGenerator()
    a = gen.snapshot_for(1.0)
    b = gen.snapshot_for(1.0)
    assert a == b


def test_different_sim_t_s_moves_target() -> None:
    gen = MockPrimaryTargetGenerator()
    a = gen.snapshot_for(0.0)
    b = gen.snapshot_for(1.0)
    assert a.azimuth_deg != pytest.approx(b.azimuth_deg)
