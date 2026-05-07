"""Unit tests for :mod:`workbench.domain.placement`."""

from __future__ import annotations

import pytest

from workbench.domain.placement import CurrentPose, MotionKind, PlacedEntity
from workbench.domain.types import PositionENU, Time, VelocityENU

# ---------------------------------------------------------------------------
# MotionKind enum
# ---------------------------------------------------------------------------


def test_motion_kind_seven_members() -> None:
    """Seven members per plan/12 § 12.3 (v0.21 + v0.27 expansion)."""
    assert {m.name for m in MotionKind} == {
        "FIXED_GROUND",
        "GROUND_VEHICLE",
        "SURFACE_VESSEL",
        "FLOATING_STATIC",
        "AIRCRAFT",
        "POWERED_FLIGHT",
        "BALLISTIC",
    }


def test_motion_kind_lowercase_values() -> None:
    """String values are TOML-friendly lowercase identifiers."""
    assert MotionKind.FIXED_GROUND.value == "fixed_ground"
    assert MotionKind.SURFACE_VESSEL.value == "surface_vessel"
    assert MotionKind.AIRCRAFT.value == "aircraft"
    assert MotionKind.POWERED_FLIGHT.value == "powered_flight"
    assert MotionKind.BALLISTIC.value == "ballistic"


# ---------------------------------------------------------------------------
# PlacedEntity
# ---------------------------------------------------------------------------


def test_placed_entity_minimal() -> None:
    """Minimal PlacedEntity: id + motion_kind + base_position. Defaults to 0."""
    e = PlacedEntity(
        entity_id="radar_01",
        motion_kind=MotionKind.FIXED_GROUND,
        base_position=PositionENU(x=100.0, y=200.0, z=10.0),
    )
    assert e.entity_id == "radar_01"
    assert e.motion_kind is MotionKind.FIXED_GROUND
    assert e.base_position.x == 100.0
    assert e.base_heading_rad == 0.0
    assert e.base_pitch_rad == 0.0
    assert e.base_roll_rad == 0.0


def test_placed_entity_full_attitude() -> None:
    """Heading / pitch / roll can be set explicitly."""
    e = PlacedEntity(
        entity_id="vessel_01",
        motion_kind=MotionKind.SURFACE_VESSEL,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
        base_heading_rad=1.5708,
        base_pitch_rad=0.05,
        base_roll_rad=-0.02,
    )
    assert e.base_heading_rad == pytest.approx(1.5708)
    assert e.base_pitch_rad == pytest.approx(0.05)
    assert e.base_roll_rad == pytest.approx(-0.02)


def test_placed_entity_immutable() -> None:
    """frozen=True forbids mutation."""
    e = PlacedEntity(
        entity_id="x",
        motion_kind=MotionKind.AIRCRAFT,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    with pytest.raises((AttributeError, TypeError)):
        e.entity_id = "y"  # type: ignore[misc]


def test_placed_entity_empty_id_raises() -> None:
    """Empty entity_id is rejected."""
    with pytest.raises(ValueError, match="entity_id"):
        PlacedEntity(
            entity_id="",
            motion_kind=MotionKind.FIXED_GROUND,
            base_position=PositionENU(x=0.0, y=0.0, z=0.0),
        )


@pytest.mark.parametrize(
    "kind",
    [
        MotionKind.FIXED_GROUND,
        MotionKind.GROUND_VEHICLE,
        MotionKind.SURFACE_VESSEL,
        MotionKind.FLOATING_STATIC,
        MotionKind.AIRCRAFT,
        MotionKind.POWERED_FLIGHT,
        MotionKind.BALLISTIC,
    ],
)
def test_placed_entity_accepts_all_motion_kinds(kind: MotionKind) -> None:
    """All seven MotionKind values are accepted."""
    e = PlacedEntity(
        entity_id="test",
        motion_kind=kind,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    assert e.motion_kind is kind


# ---------------------------------------------------------------------------
# CurrentPose
# ---------------------------------------------------------------------------


def test_current_pose_creation() -> None:
    """CurrentPose holds runtime position/velocity/attitude/time."""
    p = CurrentPose(
        position=PositionENU(x=1000.0, y=2000.0, z=100.0),
        velocity=VelocityENU(vx=10.0, vy=0.0, vz=-2.0),
        heading_rad=0.3,
        pitch_rad=0.0,
        roll_rad=0.0,
        timestamp=Time(seconds=12.5),
    )
    assert p.position.x == 1000.0
    assert p.velocity.vx == 10.0
    assert p.timestamp.seconds == 12.5


def test_current_pose_immutable() -> None:
    """frozen=True forbids mutation."""
    p = CurrentPose(
        position=PositionENU(x=0.0, y=0.0, z=0.0),
        velocity=VelocityENU(vx=0.0, vy=0.0, vz=0.0),
        heading_rad=0.0,
        pitch_rad=0.0,
        roll_rad=0.0,
        timestamp=Time(seconds=0.0),
    )
    with pytest.raises((AttributeError, TypeError)):
        p.heading_rad = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Distinct types — base/current split (plan/12 § 12.4)
# ---------------------------------------------------------------------------


def test_placed_entity_and_current_pose_are_distinct_types() -> None:
    """The two types are intentionally separate (plan/12 § 12.4 base/current)."""
    e = PlacedEntity(
        entity_id="x",
        motion_kind=MotionKind.FIXED_GROUND,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    p = CurrentPose(
        position=PositionENU(x=0.0, y=0.0, z=0.0),
        velocity=VelocityENU(vx=0.0, vy=0.0, vz=0.0),
        heading_rad=0.0,
        pitch_rad=0.0,
        roll_rad=0.0,
        timestamp=Time(seconds=0.0),
    )
    assert type(e) is not type(p)
