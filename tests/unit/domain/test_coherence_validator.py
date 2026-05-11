"""Coherence validator tests (Phase 5.15)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.domain.building import make_default_building
from workbench.domain.coherence_validator import (
    ValidatorMessage,
    ValidatorSeverity,
    has_errors,
    validate_buildings,
    validate_map,
    validate_targets,
)
from workbench.domain.geo import GeoOrigin
from workbench.domain.map_resource import Map, MapBounds, SeaSurface, WorkbenchTerrain
from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.target import TargetEntity, TargetWaypoint
from workbench.domain.types import PositionENU


def _clean_map(elevation: float = 100.0, sea_surface_z: float = 0.0) -> Map:
    """All-land 3x3 grid, flat elevation."""
    g = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    terrain = WorkbenchTerrain(
        grid_east_m=g,
        grid_north_m=g,
        elevation_m=np.full((3, 3), elevation, dtype=np.float64),
        land_mask=np.ones((3, 3), dtype=np.bool_),
        resolution_m=100.0,
    )
    return Map(
        map_id="clean",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=127.0, alt_m=0.0),
        bounds=MapBounds(0.0, 200.0, 0.0, 200.0),
        terrain=terrain,
        sea_surface=SeaSurface(z_at_sea_m=sea_surface_z),
    )


# ---------------------------------------------------------------------
# Map coherence
# ---------------------------------------------------------------------


def test_validate_map_clean_returns_empty() -> None:
    """Note: an all-land map yields the INFO 'no_sea_cells' message."""
    msgs = validate_map(_clean_map())
    assert all(m.severity is ValidatorSeverity.INFO for m in msgs)
    assert all(m.code == "map.no_sea_cells" for m in msgs)


def test_validate_map_sea_cell_above_surface_warns() -> None:
    g = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    elev = np.full((3, 3), 100.0, dtype=np.float64)
    elev[0, 0] = 5.0  # sea cell sitting 5 m above sea level (0)
    land = np.ones((3, 3), dtype=np.bool_)
    land[0, 0] = False
    terrain = WorkbenchTerrain(
        grid_east_m=g,
        grid_north_m=g,
        elevation_m=elev,
        land_mask=land,
        resolution_m=100.0,
    )
    m = Map(
        map_id="sea_above",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=127.0, alt_m=0.0),
        bounds=MapBounds(0.0, 200.0, 0.0, 200.0),
        terrain=terrain,
    )
    msgs = validate_map(m)
    codes = {x.code for x in msgs}
    assert "map.sea_cell_above_surface" in codes


def test_validate_map_all_sea_emits_info() -> None:
    g = np.array([0.0, 100.0, 200.0], dtype=np.float64)
    terrain = WorkbenchTerrain(
        grid_east_m=g,
        grid_north_m=g,
        elevation_m=np.full((3, 3), -10.0, dtype=np.float64),
        land_mask=np.zeros((3, 3), dtype=np.bool_),
        resolution_m=100.0,
    )
    m = Map(
        map_id="all_sea",
        geo_origin=GeoOrigin(lat_deg=37.5, lon_deg=127.0, alt_m=0.0),
        bounds=MapBounds(0.0, 200.0, 0.0, 200.0),
        terrain=terrain,
    )
    msgs = validate_map(m)
    codes = {x.code for x in msgs}
    assert "map.no_land_cells" in codes


# ---------------------------------------------------------------------
# Target coherence
# ---------------------------------------------------------------------


def _aircraft_target(*, altitude_m: float = 1000.0, target_id: int = 0) -> TargetEntity:
    return TargetEntity(
        placement=PlacedEntity(
            entity_id=f"acft_{target_id}",
            motion_kind=MotionKind.AIRCRAFT,
            base_position=PositionENU(x=100.0, y=100.0, z=altitude_m),
        ),
        target_id=target_id,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=100.0, north_m=100.0, altitude_m=altitude_m),),
    )


def _ship_target(*, altitude_m: float = 0.0, target_id: int = 1) -> TargetEntity:
    return TargetEntity(
        placement=PlacedEntity(
            entity_id=f"ship_{target_id}",
            motion_kind=MotionKind.SURFACE_VESSEL,
            base_position=PositionENU(x=100.0, y=100.0, z=altitude_m),
        ),
        target_id=target_id,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=100.0, north_m=100.0, altitude_m=altitude_m),),
    )


def test_validate_targets_aircraft_above_terrain_is_clean() -> None:
    m = _clean_map(elevation=100.0)
    msgs = validate_targets((_aircraft_target(altitude_m=1000.0),), m)
    assert msgs == ()


def test_validate_targets_aircraft_below_terrain_errors() -> None:
    m = _clean_map(elevation=200.0)
    msgs = validate_targets((_aircraft_target(altitude_m=50.0),), m)
    assert any(
        x.severity is ValidatorSeverity.ERROR and x.code == "target.airborne_below_terrain"
        for x in msgs
    )


def test_validate_targets_waypoint_outside_bounds_errors() -> None:
    m = _clean_map()
    bad = TargetEntity(
        placement=PlacedEntity(
            entity_id="off_map",
            motion_kind=MotionKind.AIRCRAFT,
            base_position=PositionENU(x=999.0, y=999.0, z=1000.0),
        ),
        target_id=5,
        trajectory=(TargetWaypoint(t_s=0.0, east_m=999.0, north_m=999.0, altitude_m=1000.0),),
    )
    msgs = validate_targets((bad,), m)
    assert any(x.code == "target.waypoint_outside_bounds" for x in msgs)


def test_validate_targets_ship_far_above_sea_warns() -> None:
    m = _clean_map()
    ship_up = _ship_target(altitude_m=5.0)  # 5 m above sea, tol default 1 m
    msgs = validate_targets((ship_up,), m)
    assert any(
        x.severity is ValidatorSeverity.WARN and x.code == "target.surface_altitude_far_from_sea"
        for x in msgs
    )


def test_validate_targets_ship_near_sea_clean() -> None:
    m = _clean_map()
    ship_ok = _ship_target(altitude_m=0.3)  # within 1 m tolerance
    msgs = validate_targets((ship_ok,), m)
    assert msgs == ()


# ---------------------------------------------------------------------
# Building coherence
# ---------------------------------------------------------------------


def test_validate_buildings_inside_bounds_clean() -> None:
    m = _clean_map()
    b = make_default_building("tower_1", 50.0, 80.0)
    assert validate_buildings((b,), m) == ()


def test_validate_buildings_outside_bounds_errors() -> None:
    m = _clean_map()
    b = make_default_building("offmap_tower", 9999.0, 9999.0)
    msgs = validate_buildings((b,), m)
    assert any(x.code == "building.base_outside_bounds" for x in msgs)


# ---------------------------------------------------------------------
# has_errors helper
# ---------------------------------------------------------------------


def test_has_errors_true_when_any_error_present() -> None:
    msgs = (
        ValidatorMessage(ValidatorSeverity.INFO, "i", ""),
        ValidatorMessage(ValidatorSeverity.WARN, "w", ""),
        ValidatorMessage(ValidatorSeverity.ERROR, "e", ""),
    )
    assert has_errors(msgs) is True


def test_has_errors_false_when_only_warnings() -> None:
    msgs = (
        ValidatorMessage(ValidatorSeverity.INFO, "i", ""),
        ValidatorMessage(ValidatorSeverity.WARN, "w", ""),
    )
    assert has_errors(msgs) is False


def test_has_errors_false_when_empty() -> None:
    assert has_errors(()) is False


# ---------------------------------------------------------------------
# Severity enum + dataclass sanity
# ---------------------------------------------------------------------


def test_validator_severity_three_rungs() -> None:
    assert ValidatorSeverity.INFO.value == "info"
    assert ValidatorSeverity.WARN.value == "warn"
    assert ValidatorSeverity.ERROR.value == "error"


def test_validator_message_is_frozen() -> None:
    m = ValidatorMessage(ValidatorSeverity.INFO, "code.x", "msg")
    with pytest.raises(Exception):  # noqa: B017
        m.code = "code.y"  # type: ignore[misc]
