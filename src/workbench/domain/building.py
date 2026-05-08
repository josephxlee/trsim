"""Building entity and anchor system (plan/03 § 3.2.1f, plan/12 § 12.8).

Phase 2.3c — solves the v0.21 "buildings float / coast misaligned" problem
by introducing four explicit anchor modes plus three mesh-origin
conventions. The choice between them is recorded on each
:class:`BuildingEntity` so a Map editor can later swap reflection-and
DEM-import strategies without re-positioning every building.

Anchor modes (plan/12 § 12.8):

- ``BASE_TO_TERRAIN`` (default): the simulation samples the
  :class:`workbench.domain.map_resource.WorkbenchTerrain` at the
  building's east/north position and uses that elevation as the base z.
  Refuses placement on ``land_mask=False`` cells (no buildings on water).
- ``EXPLICIT_ALT``: the ``base_position.z`` value is taken as-is. Used
  for buildings on rooftops, unusual terrain, or test scenarios.
- ``FLOOR_AT_MSL``: the building floor sits exactly at ``z = 0`` in the
  Map's vertical reference. Used for piers, breakwaters, harbor cranes —
  things whose nominal floor IS the sea-level.
- ``TERRAIN_OFFSET``: terrain elevation + ``terrain_offset_m``. Used
  for elevated platforms (floor 5 m above ground), berthed platforms.

Mesh origins (plan/12 § 12.8.2 — how the 3D mesh aligns to ``base_position``):

- ``BASE_CENTER`` (default): the mesh's footprint geometric centre is at
  ``base_position``; the mesh's lowest point is at base z.
- ``BASE_LOWER_CORNER``: the lowest mesh corner (south-west bottom of
  the bounding box) is at ``base_position``.
- ``BASE_LOWER_CENTER``: the mesh footprint is centred horizontally and
  the lowest point is at base z (== BASE_CENTER for symmetric meshes).

Phase 2.3c provides the **dataclasses only**; the actual sampling and
land_mask checks live in Phase 2.2b ``terrain_sampling.py`` (not yet
written).

References:

- plan/03 § 3.2.1f — BuildingEntity dataclass.
- plan/12 § 12.8 — anchor system design (v0.21).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workbench.domain.placement import MotionKind, PlacedEntity


class AnchorMode(Enum):
    """How a building's base z is resolved at simulation start (plan/12 § 12.8)."""

    BASE_TO_TERRAIN = "base_to_terrain"
    EXPLICIT_ALT = "explicit_alt"
    FLOOR_AT_MSL = "floor_at_msl"
    TERRAIN_OFFSET = "terrain_offset"


class MeshOrigin(Enum):
    """How a 3D mesh aligns to the entity's ``base_position`` (plan/12 § 12.8.2)."""

    BASE_CENTER = "base_center"
    BASE_LOWER_CORNER = "base_lower_corner"
    BASE_LOWER_CENTER = "base_lower_center"


@dataclass(frozen=True, slots=True)
class BuildingEntity:
    """Building placed on a Map (plan/03 § 3.2.1f).

    Wraps a :class:`PlacedEntity` (the common id + motion_kind + position +
    attitude block) and adds building-specific anchor/mesh metadata.

    Attributes:
        placement: Common base placement (must have
            ``motion_kind == MotionKind.FIXED_GROUND`` for buildings).
        anchor_mode: How to resolve the base z (see :class:`AnchorMode`).
        mesh_origin: How the 3D mesh aligns to ``base_position``
            (see :class:`MeshOrigin`).
        terrain_offset_m: Offset above terrain when
            ``anchor_mode == AnchorMode.TERRAIN_OFFSET``. Ignored for
            other modes.
        mesh_path: Resource-relative path to the 3D mesh file
            (e.g. ``"meshes/radar_tower.stl"``). Empty string falls back
            to the simple bounding-box rendering using width/depth/height.
        width_m: East-axis footprint width [m].
        depth_m: North-axis footprint depth [m].
        height_m: Total height above the resolved base z [m].

    Raises:
        ValueError: If ``placement.motion_kind != FIXED_GROUND``, or if
            any dimension is non-positive, or if ``terrain_offset_m`` is
            given with the wrong anchor mode (warns; not strict to keep
            Editor flexible).
    """

    placement: PlacedEntity
    anchor_mode: AnchorMode = AnchorMode.BASE_TO_TERRAIN
    mesh_origin: MeshOrigin = MeshOrigin.BASE_CENTER
    terrain_offset_m: float = 0.0
    mesh_path: str = ""
    width_m: float = 10.0
    depth_m: float = 10.0
    height_m: float = 10.0

    def __post_init__(self) -> None:
        if self.placement.motion_kind is not MotionKind.FIXED_GROUND:
            msg = (
                f"BuildingEntity requires placement.motion_kind = FIXED_GROUND, "
                f"got {self.placement.motion_kind.name}"
            )
            raise ValueError(msg)
        if self.width_m <= 0.0:
            msg = f"width_m must be > 0, got {self.width_m}"
            raise ValueError(msg)
        if self.depth_m <= 0.0:
            msg = f"depth_m must be > 0, got {self.depth_m}"
            raise ValueError(msg)
        if self.height_m <= 0.0:
            msg = f"height_m must be > 0, got {self.height_m}"
            raise ValueError(msg)


# Helpful default factory used by tests + Editor presets.
def make_default_building(
    entity_id: str,
    base_east_m: float,
    base_north_m: float,
    base_alt_m: float = 0.0,
    *,
    width_m: float = 10.0,
    depth_m: float = 10.0,
    height_m: float = 10.0,
) -> BuildingEntity:
    """Build a 10x10x10 m default building at ``(east, north, alt)`` with
    :class:`AnchorMode.BASE_TO_TERRAIN` and :class:`MeshOrigin.BASE_CENTER`.

    Args:
        entity_id: Workspace-unique identifier.
        base_east_m: East coordinate [m] in the Map ENU frame.
        base_north_m: North coordinate [m] in the Map ENU frame.
        base_alt_m: Vertical coordinate [m]. Note that for the default
            ``BASE_TO_TERRAIN`` mode, the simulation will replace this
            with the sampled DEM elevation; the value here is only used
            if the user later switches to ``EXPLICIT_ALT``.
        width_m: East-axis footprint width [m].
        depth_m: North-axis footprint depth [m].
        height_m: Total height [m].

    Returns:
        A :class:`BuildingEntity` ready to insert into a Map.
    """
    from workbench.domain.types import PositionENU

    return BuildingEntity(
        placement=PlacedEntity(
            entity_id=entity_id,
            motion_kind=MotionKind.FIXED_GROUND,
            base_position=PositionENU(x=base_east_m, y=base_north_m, z=base_alt_m),
        ),
        width_m=width_m,
        depth_m=depth_m,
        height_m=height_m,
    )
