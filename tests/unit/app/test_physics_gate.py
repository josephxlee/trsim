"""Unit tests for app.physics_gate (Phase 3 D2)."""

from __future__ import annotations

import math

import pytest

from workbench.app.physics_gate import (
    C_LIGHT_M_S,
    PhysicsCheckResult,
    PhysicsGateReport,
    check_altitude_plausible,
    check_finite_position,
    check_frequency_radar_band,
    check_mass_positive,
    check_velocity_below_light_speed,
    run_physics_gate,
)

# ---------------------------------------------------------------------
# check_velocity_below_light_speed
# ---------------------------------------------------------------------


def test_velocity_below_c_passes_for_normal_speed() -> None:
    r = check_velocity_below_light_speed((300.0, 0.0, 0.0))
    assert r.ok
    assert r.reason == ""


def test_velocity_at_or_above_c_fails() -> None:
    r = check_velocity_below_light_speed((C_LIGHT_M_S, 0.0, 0.0))
    assert not r.ok
    assert ">= c" in r.reason


def test_velocity_magnitude_uses_three_axes() -> None:
    """|v| = sqrt(3) * c / 2 (just under c on each axis) -> still fails."""
    per_axis = C_LIGHT_M_S * 0.6
    r = check_velocity_below_light_speed((per_axis, per_axis, per_axis))
    assert not r.ok


# ---------------------------------------------------------------------
# check_mass_positive
# ---------------------------------------------------------------------


def test_mass_positive_passes_for_normal_mass() -> None:
    assert check_mass_positive(10.0).ok


@pytest.mark.parametrize("bad", [0.0, -1.0, -1e9])
def test_mass_zero_or_negative_fails(bad: float) -> None:
    r = check_mass_positive(bad)
    assert not r.ok
    assert "<= 0" in r.reason


def test_mass_nan_fails() -> None:
    r = check_mass_positive(math.nan)
    assert not r.ok
    assert "not finite" in r.reason


def test_mass_inf_fails() -> None:
    r = check_mass_positive(math.inf)
    assert not r.ok


# ---------------------------------------------------------------------
# check_altitude_plausible
# ---------------------------------------------------------------------


@pytest.mark.parametrize("alt", [0.0, 100.0, 10_000.0, -500.0, 100_000.0])
def test_altitude_inside_range_passes(alt: float) -> None:
    assert check_altitude_plausible(alt).ok


@pytest.mark.parametrize("alt", [-501.0, 100_001.0, -1e6, 1e9])
def test_altitude_outside_range_fails(alt: float) -> None:
    r = check_altitude_plausible(alt)
    assert not r.ok
    assert "outside" in r.reason


def test_altitude_non_finite_fails() -> None:
    assert not check_altitude_plausible(math.nan).ok
    assert not check_altitude_plausible(math.inf).ok


def test_altitude_custom_bounds_respected() -> None:
    r = check_altitude_plausible(5.0, min_m=0.0, max_m=10.0)
    assert r.ok
    r = check_altitude_plausible(11.0, min_m=0.0, max_m=10.0)
    assert not r.ok


# ---------------------------------------------------------------------
# check_frequency_radar_band
# ---------------------------------------------------------------------


@pytest.mark.parametrize("f", [100e6, 1e9, 9.4e9, 35e9, 100e9])
def test_frequency_inside_band_passes(f: float) -> None:
    assert check_frequency_radar_band(f).ok


@pytest.mark.parametrize("f", [50e6, 200e9, 1.0, 1e15])
def test_frequency_outside_band_fails(f: float) -> None:
    r = check_frequency_radar_band(f)
    assert not r.ok


def test_frequency_non_finite_fails() -> None:
    assert not check_frequency_radar_band(math.nan).ok


# ---------------------------------------------------------------------
# check_finite_position
# ---------------------------------------------------------------------


def test_finite_position_passes_for_normal_vector() -> None:
    assert check_finite_position((1000.0, 2000.0, 500.0)).ok


@pytest.mark.parametrize(
    "pos",
    [
        (math.nan, 0.0, 0.0),
        (0.0, math.inf, 0.0),
        (0.0, 0.0, -math.inf),
    ],
)
def test_finite_position_rejects_nan_or_inf(pos: tuple[float, float, float]) -> None:
    r = check_finite_position(pos)
    assert not r.ok
    assert "not finite" in r.reason


# ---------------------------------------------------------------------
# run_physics_gate + PhysicsGateReport
# ---------------------------------------------------------------------


def test_run_physics_gate_aggregates_results() -> None:
    report = run_physics_gate(
        [
            check_mass_positive(10.0),
            check_velocity_below_light_speed((100.0, 0.0, 0.0)),
            check_altitude_plausible(500.0),
        ]
    )
    assert isinstance(report, PhysicsGateReport)
    assert len(report.results) == 3
    assert not report.has_failures
    assert report.failures == ()


def test_run_physics_gate_has_failures_when_any_check_fails() -> None:
    report = run_physics_gate(
        [
            check_mass_positive(10.0),  # ok
            check_mass_positive(-1.0),  # fail
            check_altitude_plausible(50.0),  # ok
        ]
    )
    assert report.has_failures
    assert len(report.failures) == 1
    assert report.failures[0].name == "mass_positive"


def test_physics_check_result_default_reason_is_empty() -> None:
    r = PhysicsCheckResult(name="custom", ok=True)
    assert r.reason == ""
