"""Unit tests for :mod:`workbench.domain.building`."""

from __future__ import annotations

import pytest

from workbench.domain.building import (
    AnchorMode,
    BuildingEntity,
    MeshOrigin,
    make_default_building,
)
from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.types import PositionENU

# ---------------------------------------------------------------------------
# AnchorMode enum
# ---------------------------------------------------------------------------


def test_anchor_mode_four_members() -> None:
    """Four members per plan/12 § 12.8."""
    assert {m.name for m in AnchorMode} == {
        "BASE_TO_TERRAIN",
        "EXPLICIT_ALT",
        "FLOOR_AT_MSL",
        "TERRAIN_OFFSET",
    }


def test_anchor_mode_lowercase_values() -> None:
    """TOML-friendly lowercase identifiers."""
    assert AnchorMode.BASE_TO_TERRAIN.value == "base_to_terrain"
    assert AnchorMode.EXPLICIT_ALT.value == "explicit_alt"
    assert AnchorMode.FLOOR_AT_MSL.value == "floor_at_msl"
    assert AnchorMode.TERRAIN_OFFSET.value == "terrain_offset"


# ---------------------------------------------------------------------------
# MeshOrigin enum
# ---------------------------------------------------------------------------


def test_mesh_origin_three_members() -> None:
    """Three members per plan/12 § 12.8.2."""
    assert {m.name for m in MeshOrigin} == {
        "BASE_CENTER",
        "BASE_LOWER_CORNER",
        "BASE_LOWER_CENTER",
    }


def test_mesh_origin_lowercase_values() -> None:
    """TOML-friendly lowercase identifiers."""
    assert MeshOrigin.BASE_CENTER.value == "base_center"
    assert MeshOrigin.BASE_LOWER_CORNER.value == "base_lower_corner"
    assert MeshOrigin.BASE_LOWER_CENTER.value == "base_lower_center"


# ---------------------------------------------------------------------------
# BuildingEntity
# ---------------------------------------------------------------------------


def _make_placement(entity_id: str = "b1") -> PlacedEntity:
    return PlacedEntity(
        entity_id=entity_id,
        motion_kind=MotionKind.FIXED_GROUND,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )


def test_building_minimal_defaults() -> None:
    """Defaults: BASE_TO_TERRAIN + BASE_CENTER + 10x10x10."""
    b = BuildingEntity(placement=_make_placement())
    assert b.anchor_mode is AnchorMode.BASE_TO_TERRAIN
    assert b.mesh_origin is MeshOrigin.BASE_CENTER
    assert b.terrain_offset_m == 0.0
    assert b.mesh_path == ""
    assert b.width_m == 10.0
    assert b.depth_m == 10.0
    assert b.height_m == 10.0


def test_building_explicit_alt_with_mesh() -> None:
    """EXPLICIT_ALT + custom mesh path + dimensions."""
    b = BuildingEntity(
        placement=_make_placement("radar_tower"),
        anchor_mode=AnchorMode.EXPLICIT_ALT,
        mesh_origin=MeshOrigin.BASE_LOWER_CORNER,
        mesh_path="meshes/radar_tower.stl",
        width_m=5.0,
        depth_m=5.0,
        height_m=30.0,
    )
    assert b.anchor_mode is AnchorMode.EXPLICIT_ALT
    assert b.mesh_path == "meshes/radar_tower.stl"
    assert b.height_m == 30.0


def test_building_terrain_offset() -> None:
    """TERRAIN_OFFSET stores the offset value."""
    b = BuildingEntity(
        placement=_make_placement("platform"),
        anchor_mode=AnchorMode.TERRAIN_OFFSET,
        terrain_offset_m=5.0,
    )
    assert b.terrain_offset_m == 5.0


def test_building_immutable() -> None:
    """frozen=True forbids mutation."""
    b = BuildingEntity(placement=_make_placement())
    with pytest.raises((AttributeError, TypeError)):
        b.height_m = 99.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_building_rejects_non_fixed_ground_motion_kind() -> None:
    """A building's placement.motion_kind must be FIXED_GROUND."""
    moving = PlacedEntity(
        entity_id="moving",
        motion_kind=MotionKind.SURFACE_VESSEL,
        base_position=PositionENU(x=0.0, y=0.0, z=0.0),
    )
    with pytest.raises(ValueError, match="FIXED_GROUND"):
        BuildingEntity(placement=moving)


@pytest.mark.parametrize("dim", ["width_m", "depth_m", "height_m"])
def test_building_rejects_non_positive_dimensions(dim: str) -> None:
    """All three dimensions must be > 0."""
    kwargs: dict[str, float] = {"width_m": 1.0, "depth_m": 1.0, "height_m": 1.0}
    kwargs[dim] = 0.0
    with pytest.raises(ValueError, match=dim):
        BuildingEntity(placement=_make_placement(), **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def test_make_default_building() -> None:
    """make_default_building returns a 10x10x10 BASE_TO_TERRAIN building."""
    b = make_default_building("b1", base_east_m=100.0, base_north_m=200.0)
    assert b.placement.entity_id == "b1"
    assert b.placement.motion_kind is MotionKind.FIXED_GROUND
    assert b.placement.base_position.x == 100.0
    assert b.placement.base_position.y == 200.0
    assert b.anchor_mode is AnchorMode.BASE_TO_TERRAIN
    assert b.width_m == 10.0


def test_make_default_building_overrides() -> None:
    """Factory accepts explicit dimensions."""
    b = make_default_building(
        "tower",
        base_east_m=0.0,
        base_north_m=0.0,
        base_alt_m=50.0,
        width_m=3.0,
        depth_m=3.0,
        height_m=40.0,
    )
    assert b.placement.base_position.z == 50.0
    assert (b.width_m, b.depth_m, b.height_m) == (3.0, 3.0, 40.0)


def test_make_default_building_returns_distinct_instances() -> None:
    """Each call returns a fresh object."""
    a = make_default_building("a", 0.0, 0.0)
    b = make_default_building("a", 0.0, 0.0)
    assert a is not b
    assert a == b
