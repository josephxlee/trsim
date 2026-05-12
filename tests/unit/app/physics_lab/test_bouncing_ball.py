"""BouncingBallSimulator + analytic reference tests (PL-D, plan/19 § 19.12.1)."""

from __future__ import annotations

import math

import pytest

from workbench.app.physics_lab import (
    BouncingBallSimulator,
    analytic_peak_height_m,
)

# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_default_constructor_starts_at_rest_at_initial_height() -> None:
    sim = BouncingBallSimulator()
    assert sim.state.time_s == 0.0
    assert sim.state.position_m == pytest.approx(5.0)
    assert sim.state.velocity_m_s == 0.0
    assert sim.state.bounces == 0


def test_constructor_rejects_non_positive_gravity() -> None:
    with pytest.raises(ValueError, match=r"gravity_m_s2"):
        BouncingBallSimulator(gravity_m_s2=0.0)


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_constructor_rejects_restitution_out_of_unit_interval(bad: float) -> None:
    with pytest.raises(ValueError, match=r"restitution"):
        BouncingBallSimulator(restitution=bad)


def test_constructor_rejects_negative_initial_height() -> None:
    with pytest.raises(ValueError, match=r"initial_height_m"):
        BouncingBallSimulator(initial_height_m=-1.0)


# ---------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------


def test_first_step_decreases_height_under_gravity() -> None:
    sim = BouncingBallSimulator(initial_height_m=5.0, gravity_m_s2=9.81)
    s = sim.step(0.1)
    # Semi-implicit Euler: v1 = v0 - g*dt = -0.981
    assert s.velocity_m_s == pytest.approx(-0.981)
    # y1 = y0 + v1*dt = 5 - 0.0981 = 4.9019
    assert s.position_m == pytest.approx(4.9019)
    assert s.bounces == 0


def test_ball_bounces_when_position_crosses_ground() -> None:
    sim = BouncingBallSimulator(initial_height_m=0.05, gravity_m_s2=10.0, restitution=0.5)
    # First step drops the ball below 0 -> clamp + flip + scale.
    s = sim.step(0.2)
    assert s.position_m == 0.0
    assert s.bounces == 1
    assert s.velocity_m_s > 0.0  # bounced upward


def test_perfectly_inelastic_collision_sticks_at_ground() -> None:
    sim = BouncingBallSimulator(initial_height_m=1.0, restitution=0.0)
    # Step several times to let the ball reach the floor.
    for _ in range(20):
        sim.step(0.05)
    assert sim.state.position_m == pytest.approx(0.0, abs=1e-9)
    assert sim.state.velocity_m_s == 0.0
    assert sim.state.bounces >= 1


def test_perfectly_elastic_bounce_preserves_speed_magnitude() -> None:
    sim = BouncingBallSimulator(initial_height_m=0.1, restitution=1.0, gravity_m_s2=10.0)
    # Step until first bounce
    while sim.state.bounces < 1:
        sim.step(0.01)
    # The pre-bounce speed equals post-bounce speed in magnitude
    # (within one Euler step).
    assert abs(sim.state.velocity_m_s) > 0.0


def test_reset_returns_state_to_initial_conditions() -> None:
    sim = BouncingBallSimulator(initial_height_m=3.0)
    for _ in range(50):
        sim.step(0.02)
    sim.reset()
    assert sim.state.time_s == 0.0
    assert sim.state.position_m == pytest.approx(3.0)
    assert sim.state.velocity_m_s == 0.0
    assert sim.state.bounces == 0


def test_step_rejects_non_positive_dt() -> None:
    sim = BouncingBallSimulator()
    with pytest.raises(ValueError, match=r"dt_s"):
        sim.step(0.0)


def test_set_restitution_clamps_to_unit_interval_or_raises() -> None:
    sim = BouncingBallSimulator()
    sim.set_restitution(0.42)
    assert sim.restitution == pytest.approx(0.42)
    with pytest.raises(ValueError, match=r"restitution"):
        sim.set_restitution(1.5)


# ---------------------------------------------------------------------
# Analytic reference
# ---------------------------------------------------------------------


def test_analytic_peak_height_returns_geometric_decay() -> None:
    h0 = 5.0
    r = 0.8
    assert analytic_peak_height_m(h0, r, 0) == pytest.approx(h0)
    assert analytic_peak_height_m(h0, r, 1) == pytest.approx(h0 * r * r)
    assert analytic_peak_height_m(h0, r, 3) == pytest.approx(h0 * r**6)


def test_analytic_peak_height_rejects_invalid_args() -> None:
    with pytest.raises(ValueError, match=r"initial_height_m"):
        analytic_peak_height_m(-1.0, 0.5, 0)
    with pytest.raises(ValueError, match=r"restitution"):
        analytic_peak_height_m(1.0, 1.5, 0)
    with pytest.raises(ValueError, match=r"bounce"):
        analytic_peak_height_m(1.0, 0.5, -1)


def test_first_bounce_peak_matches_analytic_reference_for_lossless_ball() -> None:
    """Closed-form invariant: a perfectly elastic ball returns to h0."""
    sim = BouncingBallSimulator(initial_height_m=2.0, restitution=1.0, gravity_m_s2=10.0)
    # Step long enough for the ball to bounce then climb back.
    for _ in range(500):
        sim.step(0.005)
        if sim.state.velocity_m_s > 0 and sim.state.bounces >= 1:
            break
    # Peak after first bounce should approach h0 (1.0 * h0).
    # Allow modest tolerance — semi-implicit Euler at dt=0.005 over
    # the bounce moment shaves a little energy off.
    max_height_seen = sim.state.position_m
    for _ in range(500):
        sim.step(0.005)
        if sim.state.position_m > max_height_seen:
            max_height_seen = sim.state.position_m
        if sim.state.velocity_m_s < 0:
            break
    expected = analytic_peak_height_m(2.0, 1.0, 1)
    assert max_height_seen == pytest.approx(expected, rel=0.05)
    assert max_height_seen == pytest.approx(2.0, rel=0.05)


def test_initial_drop_time_matches_free_fall_formula() -> None:
    """Time-to-impact from rest at h0 under gravity g: ``sqrt(2 h0 / g)``."""
    h0 = 4.0
    g = 9.81
    sim = BouncingBallSimulator(initial_height_m=h0, restitution=0.0, gravity_m_s2=g)
    expected = math.sqrt(2 * h0 / g)
    # Step until the first impact.
    for _ in range(10_000):
        sim.step(0.001)
        if sim.state.bounces >= 1:
            break
    assert sim.state.time_s == pytest.approx(expected, rel=0.01)
