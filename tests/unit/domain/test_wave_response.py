"""Unit tests for :mod:`workbench.domain.wave_response`."""

from __future__ import annotations

import pytest

from workbench.domain.wave_response import (
    WaveResponseModel,
    WaveResponsePreset,
    make_buoy,
    make_large_ship,
    make_none,
    make_small_boat,
)

# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


def test_preset_four_members() -> None:
    """Exactly 4 members per plan/12 § 12.5.2."""
    assert {m.name for m in WaveResponsePreset} == {
        "LARGE_SHIP",
        "SMALL_BOAT",
        "BUOY",
        "NONE",
    }


def test_preset_lowercase_values() -> None:
    """TOML-friendly lowercase identifiers."""
    assert WaveResponsePreset.LARGE_SHIP.value == "large_ship"
    assert WaveResponsePreset.SMALL_BOAT.value == "small_boat"
    assert WaveResponsePreset.BUOY.value == "buoy"
    assert WaveResponsePreset.NONE.value == "none"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_default_creation_is_rigid() -> None:
    """Defaults model a near-rigid entity (heave_factor=0)."""
    m = WaveResponseModel(preset=WaveResponsePreset.NONE)
    assert m.heave_factor == 0.0
    assert m.pitch_factor == 0.0
    assert m.roll_factor == 0.0


def test_immutable() -> None:
    """frozen=True forbids mutation."""
    m = make_buoy()
    with pytest.raises((AttributeError, TypeError)):
        m.heave_factor = 0.5  # type: ignore[misc]


@pytest.mark.parametrize("bad", [-0.1, 1.1, 100.0])
def test_heave_factor_out_of_range_raises(bad: float) -> None:
    """heave_factor outside [0, 1] raises."""
    with pytest.raises(ValueError, match="heave_factor"):
        WaveResponseModel(preset=WaveResponsePreset.NONE, heave_factor=bad)


def test_negative_pitch_factor_raises() -> None:
    """Negative pitch_factor raises."""
    with pytest.raises(ValueError, match="pitch_factor"):
        WaveResponseModel(preset=WaveResponsePreset.NONE, pitch_factor=-0.1)


def test_negative_roll_factor_raises() -> None:
    """Negative roll_factor raises."""
    with pytest.raises(ValueError, match="roll_factor"):
        WaveResponseModel(preset=WaveResponsePreset.NONE, roll_factor=-0.1)


def test_zero_natural_period_raises() -> None:
    """natural_period_s <= 0 raises."""
    with pytest.raises(ValueError, match="natural_period_s"):
        WaveResponseModel(preset=WaveResponsePreset.NONE, natural_period_s=0.0)


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_damping_ratio_out_of_range_raises(bad: float) -> None:
    """damping_ratio outside [0, 1] raises."""
    with pytest.raises(ValueError, match="damping_ratio"):
        WaveResponseModel(preset=WaveResponsePreset.NONE, damping_ratio=bad)


# ---------------------------------------------------------------------------
# Preset factories
# ---------------------------------------------------------------------------


def test_make_large_ship() -> None:
    """Heavy displacement, slow response."""
    m = make_large_ship()
    assert m.preset is WaveResponsePreset.LARGE_SHIP
    assert m.heave_factor == pytest.approx(0.3)
    assert m.natural_period_s == pytest.approx(12.0)


def test_make_small_boat() -> None:
    """Light, fast response."""
    m = make_small_boat()
    assert m.preset is WaveResponsePreset.SMALL_BOAT
    assert m.heave_factor == pytest.approx(0.7)
    assert m.natural_period_s == pytest.approx(4.0)


def test_make_buoy() -> None:
    """Near-full heave coupling."""
    m = make_buoy()
    assert m.preset is WaveResponsePreset.BUOY
    assert m.heave_factor == pytest.approx(0.95)


def test_make_none() -> None:
    """Rigid / no response."""
    m = make_none()
    assert m.preset is WaveResponsePreset.NONE
    assert m.heave_factor == 0.0
    assert m.pitch_factor == 0.0
    assert m.roll_factor == 0.0


def test_factories_return_distinct_instances() -> None:
    """Each call returns a fresh object (factory, not singleton)."""
    a = make_buoy()
    b = make_buoy()
    assert a is not b
    assert a == b  # value equality from dataclass


def test_preset_response_ordering() -> None:
    """Heave factor ranking: BUOY > SMALL_BOAT > LARGE_SHIP > NONE."""
    assert make_buoy().heave_factor > make_small_boat().heave_factor
    assert make_small_boat().heave_factor > make_large_ship().heave_factor
    assert make_large_ship().heave_factor > make_none().heave_factor


def test_preset_period_ordering() -> None:
    """LARGE_SHIP slowest (12s), BUOY fastest non-rigid (3s)."""
    assert make_large_ship().natural_period_s > make_small_boat().natural_period_s
    assert make_small_boat().natural_period_s > make_buoy().natural_period_s
