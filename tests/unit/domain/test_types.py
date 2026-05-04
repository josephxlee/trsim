"""Unit tests for :mod:`workbench.domain.types`."""

from __future__ import annotations

import pytest

from workbench.domain.types import PositionENU, Time, VelocityENU


def test_position_enu_creation(sample_position: PositionENU) -> None:
    """PositionENU stores (x, y, z) coordinates as floats."""
    assert sample_position.x == 100.0
    assert sample_position.y == 200.0
    assert sample_position.z == 10.0


def test_position_enu_immutable() -> None:
    """PositionENU is frozen — cannot mutate after creation."""
    p = PositionENU(x=0.0, y=0.0, z=0.0)
    with pytest.raises((AttributeError, TypeError)):
        p.x = 100.0  # type: ignore[misc]


def test_velocity_enu_speed() -> None:
    """VelocityENU.speed is the L2 norm of (vx, vy, vz)."""
    v = VelocityENU(vx=3.0, vy=4.0, vz=0.0)
    assert v.speed == pytest.approx(5.0)


def test_velocity_enu_speed_zero() -> None:
    """Zero velocity has zero speed."""
    v = VelocityENU(vx=0.0, vy=0.0, vz=0.0)
    assert v.speed == 0.0


def test_time_advance() -> None:
    """Time.advance returns a new Time with seconds + dt (immutable)."""
    t = Time(seconds=10.0)
    t2 = t.advance(0.5)
    assert t.seconds == 10.0  # original unchanged
    assert t2.seconds == pytest.approx(10.5)
