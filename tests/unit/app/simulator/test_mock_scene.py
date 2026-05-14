"""MockSceneGenerator unit tests (Phase 4 L4)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.app.simulator import MockSceneFrame, MockSceneGenerator

# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_default_constructor_radar_at_origin() -> None:
    gen = MockSceneGenerator()
    radar = gen.radar_position_enu_m()
    np.testing.assert_array_equal(radar, np.array([0.0, 0.0, 0.0]))


def test_constructor_rejects_negative_orbit_radius() -> None:
    with pytest.raises(ValueError, match=r"target_orbit_radius_m must be >= 0"):
        MockSceneGenerator(target_orbit_radius_m=-1.0)


def test_constructor_rejects_zero_orbit_period() -> None:
    with pytest.raises(ValueError, match=r"target_orbit_period_s must be > 0"):
        MockSceneGenerator(target_orbit_period_s=0.0)


def test_constructor_rejects_nonpositive_terrain_halfspan() -> None:
    with pytest.raises(ValueError, match=r"terrain_halfspan_m must be > 0"):
        MockSceneGenerator(terrain_halfspan_m=0.0)


def test_constructor_rejects_bad_radar_position_shape() -> None:
    with pytest.raises(ValueError, match=r"radar_position_enu_m must be a 3-tuple"):
        MockSceneGenerator(radar_position_enu_m=(0.0, 1.0))  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# Target trajectory
# ---------------------------------------------------------------------


def test_target_position_at_zero_is_east_of_radar() -> None:
    """cos(0) = 1 → target sits at (radius, 0, altitude)."""
    gen = MockSceneGenerator(
        target_orbit_radius_m=1_000.0,
        target_altitude_m=200.0,
    )
    pos = gen.target_position_at(0.0)
    assert pos[0] == pytest.approx(1_000.0)
    assert pos[1] == pytest.approx(0.0)
    assert pos[2] == pytest.approx(200.0)


def test_target_position_traces_circle() -> None:
    """One full period -> back to start; quarter period -> +Y peak."""
    gen = MockSceneGenerator(
        target_orbit_radius_m=500.0,
        target_orbit_period_s=4.0,
        target_altitude_m=100.0,
    )
    start = gen.target_position_at(0.0)
    quarter = gen.target_position_at(1.0)
    full = gen.target_position_at(4.0)
    # Quarter period -> (0, radius, alt).
    assert quarter[0] == pytest.approx(0.0, abs=1e-9)
    assert quarter[1] == pytest.approx(500.0)
    # Full period -> back to start (cos = 1, sin = 0).
    assert full[0] == pytest.approx(start[0])
    assert full[1] == pytest.approx(start[1], abs=1e-9)


def test_target_altitude_is_constant() -> None:
    gen = MockSceneGenerator(target_altitude_m=750.0)
    for t in (0.0, 0.5, 1.2, 3.7, 12.4):
        assert gen.target_position_at(t)[2] == pytest.approx(750.0)


def test_target_is_offset_from_non_origin_radar() -> None:
    """Radar at non-origin -> target orbits the radar, not the origin."""
    gen = MockSceneGenerator(
        radar_position_enu_m=(100.0, 200.0, 30.0),
        target_orbit_radius_m=10.0,
    )
    pos = gen.target_position_at(0.0)
    # cos(0) = 1 -> east component = radar_east + radius.
    assert pos[0] == pytest.approx(110.0)
    assert pos[1] == pytest.approx(200.0)


# ---------------------------------------------------------------------
# scene_for
# ---------------------------------------------------------------------


def test_scene_for_returns_frame_with_consistent_state() -> None:
    gen = MockSceneGenerator()
    frame = gen.scene_for(0.5)
    assert isinstance(frame, MockSceneFrame)
    assert frame.sim_t_s == pytest.approx(0.5)
    assert frame.radar_position_enu_m.shape == (3,)
    assert frame.target_position_enu_m.shape == (3,)
    assert frame.terrain_halfspan_m > 0.0


def test_scene_for_rejects_negative_sim_t_s() -> None:
    gen = MockSceneGenerator()
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        gen.scene_for(-0.1)


def test_scene_for_is_deterministic_per_sim_t_s() -> None:
    gen = MockSceneGenerator()
    a = gen.scene_for(1.0)
    b = gen.scene_for(1.0)
    np.testing.assert_array_equal(a.target_position_enu_m, b.target_position_enu_m)


def test_different_sim_t_s_moves_target() -> None:
    gen = MockSceneGenerator()
    a = gen.scene_for(1.0)
    b = gen.scene_for(1.0 + 0.5)
    assert not np.allclose(a.target_position_enu_m, b.target_position_enu_m)


def test_radar_position_array_is_independent_copy() -> None:
    gen = MockSceneGenerator()
    r = gen.radar_position_enu_m()
    r[0] = math.pi
    fresh = gen.radar_position_enu_m()
    assert fresh[0] == pytest.approx(0.0)
