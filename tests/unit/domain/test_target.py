"""Unit tests for workbench.domain.target (Phase 2.3d)."""

from __future__ import annotations

import math

import pytest

from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.target import (
    TargetEntity,
    TargetWaypoint,
    make_default_aircraft_target,
)
from workbench.domain.types import PositionENU
from workbench.domain.wave_response import make_large_ship

# ---------------------------------------------------------------------
# TargetWaypoint
# ---------------------------------------------------------------------


def test_target_waypoint_defaults() -> None:
    wp = TargetWaypoint(t_s=0.0, east_m=100.0, north_m=200.0, altitude_m=500.0)
    assert wp.t_s == 0.0
    assert wp.east_m == 100.0
    assert wp.north_m == 200.0
    assert wp.altitude_m == 500.0
    assert wp.heading_rad == 0.0


def test_target_waypoint_explicit_heading() -> None:
    wp = TargetWaypoint(t_s=10.0, east_m=0.0, north_m=0.0, altitude_m=0.0, heading_rad=math.pi / 4)
    assert wp.heading_rad == pytest.approx(math.pi / 4)


def test_target_waypoint_is_frozen() -> None:
    wp = TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0)
    with pytest.raises(AttributeError):
        wp.t_s = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------
# TargetEntity
# ---------------------------------------------------------------------


def _aircraft_placement(entity_id: str = "tgt_001") -> PlacedEntity:
    return PlacedEntity(
        entity_id=entity_id,
        motion_kind=MotionKind.AIRCRAFT,
        base_position=PositionENU(x=0.0, y=0.0, z=1000.0),
    )


def test_target_entity_minimal_single_waypoint() -> None:
    tgt = TargetEntity(
        placement=_aircraft_placement(),
        target_id=1,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),),
    )
    assert tgt.target_id == 1
    assert tgt.rcs_model == "simple_aspect"  # default placeholder
    assert tgt.wave_response is None
    assert len(tgt.trajectory) == 1


def test_target_entity_multi_waypoint_increasing() -> None:
    tgt = TargetEntity(
        placement=_aircraft_placement(),
        target_id=2,
        trajectory=(
            TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=1000.0),
            TargetWaypoint(t_s=5.0, east_m=500.0, north_m=0.0, altitude_m=1000.0),
            TargetWaypoint(t_s=10.0, east_m=1000.0, north_m=0.0, altitude_m=1000.0),
        ),
    )
    assert len(tgt.trajectory) == 3


def test_target_entity_rejects_fixed_ground() -> None:
    fixed = PlacedEntity(
        entity_id="bad_tgt",
        motion_kind=MotionKind.FIXED_GROUND,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    with pytest.raises(ValueError, match="FIXED_GROUND"):
        TargetEntity(
            placement=fixed,
            target_id=0,
            trajectory=(TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),),
        )


def test_target_entity_rejects_negative_target_id() -> None:
    with pytest.raises(ValueError, match=r"target_id must be >= 0"):
        TargetEntity(
            placement=_aircraft_placement(),
            target_id=-1,
            trajectory=(TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),),
        )


def test_target_entity_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError, match="at least one waypoint"):
        TargetEntity(
            placement=_aircraft_placement(),
            target_id=0,
            trajectory=(),
        )


@pytest.mark.parametrize(
    ("ts_seq",),
    [
        ((0.0, 0.0),),  # equal — not strictly increasing
        ((0.0, 5.0, 4.0),),  # decreasing somewhere
        ((1.0, 0.0),),  # decreasing from start
    ],
)
def test_target_entity_rejects_non_increasing_t_s(ts_seq: tuple[float, ...]) -> None:
    traj = tuple(TargetWaypoint(t_s=t, east_m=0.0, north_m=0.0, altitude_m=0.0) for t in ts_seq)
    with pytest.raises(ValueError, match="strictly"):
        TargetEntity(
            placement=_aircraft_placement(),
            target_id=0,
            trajectory=traj,
        )


@pytest.mark.parametrize(
    ("kind",),
    [
        (MotionKind.GROUND_VEHICLE,),
        (MotionKind.SURFACE_VESSEL,),
        (MotionKind.FLOATING_STATIC,),
        (MotionKind.AIRCRAFT,),
        (MotionKind.POWERED_FLIGHT,),
        (MotionKind.BALLISTIC,),
    ],
)
def test_target_entity_accepts_all_non_fixed_motion(kind: MotionKind) -> None:
    placement = PlacedEntity(
        entity_id="tgt_x",
        motion_kind=kind,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    tgt = TargetEntity(
        placement=placement,
        target_id=0,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),),
    )
    assert tgt.placement.motion_kind is kind


def test_target_entity_with_wave_response() -> None:
    placement = PlacedEntity(
        entity_id="ship_001",
        motion_kind=MotionKind.SURFACE_VESSEL,
        base_position=PositionENU(x=1000.0, y=2000.0, z=0.0),
    )
    wave = make_large_ship()
    tgt = TargetEntity(
        placement=placement,
        target_id=10,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=1000.0, north_m=2000.0, altitude_m=0.0),),
        wave_response=wave,
    )
    assert tgt.wave_response is wave


def test_target_entity_is_frozen() -> None:
    tgt = TargetEntity(
        placement=_aircraft_placement(),
        target_id=0,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=0.0, north_m=0.0, altitude_m=0.0),),
    )
    with pytest.raises(AttributeError):
        tgt.target_id = 99  # type: ignore[misc]


# ---------------------------------------------------------------------
# make_default_aircraft_target
# ---------------------------------------------------------------------


def test_make_default_aircraft_target_basic() -> None:
    tgt = make_default_aircraft_target(
        entity_id="default_tgt",
        target_id=5,
        east_m=0.0,
        north_m=0.0,
    )
    assert tgt.placement.entity_id == "default_tgt"
    assert tgt.placement.motion_kind is MotionKind.AIRCRAFT
    assert tgt.target_id == 5
    assert tgt.placement.base_position.z == 1000.0  # default altitude
    assert len(tgt.trajectory) == 2
    assert tgt.trajectory[0].t_s == 0.0
    assert tgt.trajectory[1].t_s == 60.0


def test_make_default_aircraft_target_overrides() -> None:
    tgt = make_default_aircraft_target(
        entity_id="custom_tgt",
        target_id=7,
        east_m=100.0,
        north_m=200.0,
        altitude_m=2000.0,
        velocity_east_mps=50.0,
        velocity_north_mps=50.0,
        duration_s=30.0,
        rcs_model="point",
    )
    assert tgt.placement.base_position.x == 100.0
    assert tgt.placement.base_position.y == 200.0
    assert tgt.placement.base_position.z == 2000.0
    assert tgt.rcs_model == "point"
    # second waypoint = start + v * duration
    assert tgt.trajectory[1].east_m == pytest.approx(100.0 + 50.0 * 30.0)
    assert tgt.trajectory[1].north_m == pytest.approx(200.0 + 50.0 * 30.0)
    assert tgt.trajectory[1].t_s == 30.0


def test_make_default_aircraft_target_heading_atan2() -> None:
    # purely east motion: heading = pi/2 (90 deg clockwise from North)
    tgt_east = make_default_aircraft_target(
        entity_id="e",
        target_id=0,
        east_m=0.0,
        north_m=0.0,
        velocity_east_mps=100.0,
        velocity_north_mps=0.0,
    )
    assert tgt_east.placement.base_heading_rad == pytest.approx(math.pi / 2)
    # purely north motion: heading = 0
    tgt_north = make_default_aircraft_target(
        entity_id="n",
        target_id=0,
        east_m=0.0,
        north_m=0.0,
        velocity_east_mps=0.0,
        velocity_north_mps=100.0,
    )
    assert tgt_north.placement.base_heading_rad == pytest.approx(0.0)


def test_make_default_aircraft_target_rejects_zero_duration() -> None:
    with pytest.raises(ValueError, match=r"duration_s must be > 0"):
        make_default_aircraft_target(
            entity_id="x", target_id=0, east_m=0.0, north_m=0.0, duration_s=0.0
        )


def test_make_default_aircraft_target_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match=r"duration_s must be > 0"):
        make_default_aircraft_target(
            entity_id="x", target_id=0, east_m=0.0, north_m=0.0, duration_s=-1.0
        )


def test_make_default_aircraft_target_distinct_instances() -> None:
    a = make_default_aircraft_target(entity_id="a", target_id=0, east_m=0.0, north_m=0.0)
    b = make_default_aircraft_target(entity_id="b", target_id=1, east_m=0.0, north_m=0.0)
    assert a is not b
    assert a.placement.entity_id != b.placement.entity_id
