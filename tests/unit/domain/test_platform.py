"""Unit tests for workbench.domain.platform (Phase 2.11)."""

from __future__ import annotations

import math

import pytest

from workbench.domain.placement import MotionKind, PlacedEntity
from workbench.domain.platform import RadarPlatform, TrackerKind
from workbench.domain.types import PositionENU


def _placement() -> PlacedEntity:
    return PlacedEntity(
        entity_id="radar_host_01",
        motion_kind=MotionKind.FIXED_GROUND,
        base_position=PositionENU(x=0.0, y=0.0, z=10.0),
    )


def _platform(**overrides: object) -> RadarPlatform:
    base: dict[str, object] = {
        "platform_id": "radar_01",
        "placement": _placement(),
        "antenna_id": "parabolic_1m_9.4ghz",
        "carrier_frequency_hz": 9.4e9,
    }
    base.update(overrides)
    return RadarPlatform(**base)  # type: ignore[arg-type]


def test_tracker_kind_enum_values() -> None:
    assert TrackerKind.EKF.value == "ekf"
    assert TrackerKind.UKF.value == "ukf"


def test_platform_construction_defaults() -> None:
    p = _platform()
    assert p.tracker_kind is TrackerKind.EKF
    assert p.boresight_az_rad == 0.0
    assert p.boresight_el_rad == 0.0


def test_platform_explicit_boresight() -> None:
    p = _platform(boresight_az_rad=math.pi / 4, boresight_el_rad=0.1)
    assert p.boresight_az_rad == math.pi / 4
    assert p.boresight_el_rad == 0.1


def test_platform_ukf_selection() -> None:
    p = _platform(tracker_kind=TrackerKind.UKF)
    assert p.tracker_kind is TrackerKind.UKF


@pytest.mark.parametrize(
    ("override", "match"),
    [
        ({"platform_id": ""}, r"platform_id"),
        ({"antenna_id": ""}, r"antenna_id"),
        ({"carrier_frequency_hz": 0.0}, r"carrier_frequency_hz"),
        ({"carrier_frequency_hz": -1.0}, r"carrier_frequency_hz"),
    ],
)
def test_platform_validation(override: dict, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        _platform(**override)


def test_platform_is_frozen() -> None:
    p = _platform()
    with pytest.raises(Exception):  # noqa: B017
        p.platform_id = "x"  # type: ignore[misc]
