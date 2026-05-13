"""SimulationDomain + OutsideEnvironment dataclass tests (plan/11 § 11.11.3)."""

from __future__ import annotations

import math

import pytest

from workbench.domain.map_resource import MapBounds
from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain

# ---------------------------------------------------------------------
# OutsideEnvironment enum
# ---------------------------------------------------------------------


def test_outside_environment_has_four_modes() -> None:
    assert {item.value for item in OutsideEnvironment} == {
        "open_sea",
        "open_land",
        "infinite_plane",
        "blocked",
    }


def test_outside_environment_is_str_subclass() -> None:
    # StrEnum members are real str values — TOML / JSON serialise as the
    # literal string with no extra conversion.
    assert OutsideEnvironment.OPEN_SEA == "open_sea"
    assert isinstance(OutsideEnvironment.OPEN_LAND, str)


# ---------------------------------------------------------------------
# SimulationDomain happy-path
# ---------------------------------------------------------------------


def _default_domain() -> SimulationDomain:
    return SimulationDomain(
        bounds_east=(-25000.0, 25000.0),
        bounds_north=(-30000.0, 20000.0),
    )


def test_default_ceiling_and_floor() -> None:
    d = _default_domain()
    assert d.ceiling_alt_m == 30000.0
    assert d.floor_alt_m == -100.0


def test_width_height_diagonal() -> None:
    d = _default_domain()
    assert d.width_m == 50000.0
    assert d.height_m == 50000.0
    assert d.diagonal_m == pytest.approx(math.hypot(50000.0, 50000.0))


def test_contains_planar_inside() -> None:
    d = _default_domain()
    assert d.contains(0.0, 0.0)
    assert d.contains(-25000.0, -30000.0)  # corner inclusive
    assert d.contains(25000.0, 20000.0)


def test_contains_planar_outside() -> None:
    d = _default_domain()
    assert not d.contains(25001.0, 0.0)
    assert not d.contains(0.0, -30001.0)


def test_contains_with_altitude_in_range() -> None:
    d = _default_domain()
    assert d.contains(0.0, 0.0, 0.0)
    assert d.contains(0.0, 0.0, 30000.0)
    assert d.contains(0.0, 0.0, -100.0)


def test_contains_with_altitude_out_of_range() -> None:
    d = _default_domain()
    assert not d.contains(0.0, 0.0, 30001.0)
    assert not d.contains(0.0, 0.0, -100.1)


def test_contains_bounds_strict_subset() -> None:
    d = _default_domain()
    inner = MapBounds(
        east_min_m=-5000.0,
        east_max_m=5000.0,
        north_min_m=-5000.0,
        north_max_m=5000.0,
    )
    assert d.contains_bounds(inner)


def test_contains_bounds_rejects_overflowing_map() -> None:
    d = _default_domain()
    too_wide = MapBounds(
        east_min_m=-30000.0,
        east_max_m=30000.0,
        north_min_m=-5000.0,
        north_max_m=5000.0,
    )
    assert not d.contains_bounds(too_wide)


def test_contains_bounds_accepts_exact_match() -> None:
    d = _default_domain()
    flush = MapBounds(
        east_min_m=-25000.0,
        east_max_m=25000.0,
        north_min_m=-30000.0,
        north_max_m=20000.0,
    )
    assert d.contains_bounds(flush)


# ---------------------------------------------------------------------
# from_map_bounds
# ---------------------------------------------------------------------


def test_from_map_bounds_zero_margin() -> None:
    b = MapBounds(
        east_min_m=-5000.0,
        east_max_m=5000.0,
        north_min_m=-3000.0,
        north_max_m=4000.0,
    )
    d = SimulationDomain.from_map_bounds(b)
    assert d.bounds_east == (-5000.0, 5000.0)
    assert d.bounds_north == (-3000.0, 4000.0)
    assert d.contains_bounds(b)


def test_from_map_bounds_with_margin_expands_box() -> None:
    b = MapBounds(
        east_min_m=-5000.0,
        east_max_m=5000.0,
        north_min_m=-3000.0,
        north_max_m=4000.0,
    )
    d = SimulationDomain.from_map_bounds(b, margin_m=1000.0)
    assert d.bounds_east == (-6000.0, 6000.0)
    assert d.bounds_north == (-4000.0, 5000.0)
    assert d.contains_bounds(b)


def test_from_map_bounds_propagates_altitude_overrides() -> None:
    b = MapBounds(east_min_m=-1.0, east_max_m=1.0, north_min_m=-1.0, north_max_m=1.0)
    d = SimulationDomain.from_map_bounds(
        b,
        margin_m=0.0,
        ceiling_alt_m=12000.0,
        floor_alt_m=-50.0,
    )
    assert d.ceiling_alt_m == 12000.0
    assert d.floor_alt_m == -50.0


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_collapsed_east_axis_rejected() -> None:
    with pytest.raises(ValueError, match=r"bounds_east\[1\] must exceed"):
        SimulationDomain(bounds_east=(10.0, 10.0), bounds_north=(0.0, 1.0))


def test_collapsed_north_axis_rejected() -> None:
    with pytest.raises(ValueError, match=r"bounds_north\[1\] must exceed"):
        SimulationDomain(bounds_east=(0.0, 1.0), bounds_north=(5.0, 4.0))


def test_ceiling_below_floor_rejected() -> None:
    with pytest.raises(ValueError, match=r"ceiling_alt_m must exceed floor_alt_m"):
        SimulationDomain(
            bounds_east=(0.0, 1.0),
            bounds_north=(0.0, 1.0),
            ceiling_alt_m=-10.0,
            floor_alt_m=0.0,
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bounds_east": (float("nan"), 1.0), "bounds_north": (0.0, 1.0)},
        {"bounds_east": (0.0, float("inf")), "bounds_north": (0.0, 1.0)},
        {
            "bounds_east": (0.0, 1.0),
            "bounds_north": (0.0, 1.0),
            "ceiling_alt_m": float("nan"),
        },
        {
            "bounds_east": (0.0, 1.0),
            "bounds_north": (0.0, 1.0),
            "floor_alt_m": float("-inf"),
        },
    ],
)
def test_non_finite_fields_rejected(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"must be finite"):
        SimulationDomain(**kwargs)  # type: ignore[arg-type]


def test_from_map_bounds_negative_margin_rejected() -> None:
    b = MapBounds(east_min_m=-1.0, east_max_m=1.0, north_min_m=-1.0, north_max_m=1.0)
    with pytest.raises(ValueError, match=r"margin_m must be non-negative"):
        SimulationDomain.from_map_bounds(b, margin_m=-1.0)


def test_from_map_bounds_nan_margin_rejected() -> None:
    b = MapBounds(east_min_m=-1.0, east_max_m=1.0, north_min_m=-1.0, north_max_m=1.0)
    with pytest.raises(ValueError, match=r"margin_m must be non-negative"):
        SimulationDomain.from_map_bounds(b, margin_m=float("nan"))


def test_frozen_instance() -> None:
    d = _default_domain()
    with pytest.raises(AttributeError):
        d.ceiling_alt_m = 1.0  # type: ignore[misc]
