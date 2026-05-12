"""@physics_param decorator + PhysicsParam tests (PL-9.1c, plan/19 § 19.5.5)."""

from __future__ import annotations

import pytest

from workbench.domain.physics_lab import (
    BOUNCING_BALL_PARAM_SPECS,
    PhysicsParam,
    get_physics_params,
    physics_param,
)

# ---------------------------------------------------------------------
# PhysicsParam validation
# ---------------------------------------------------------------------


def test_default_construction_linear() -> None:
    p = PhysicsParam("restitution", min_value=0.0, max_value=1.0)
    assert p.scale == "linear"
    assert p.unit == ""
    assert p.default is None


def test_log_scale_requires_positive_min() -> None:
    with pytest.raises(ValueError, match=r"log scale requires min_value > 0"):
        PhysicsParam("range_m", min_value=0.0, max_value=100.0, scale="log")


def test_log_scale_with_positive_min_ok() -> None:
    p = PhysicsParam("range_m", min_value=1.0, max_value=1e5, scale="log")
    assert p.scale == "log"


def test_non_increasing_range_rejected() -> None:
    with pytest.raises(ValueError, match=r"min_value must be < max_value"):
        PhysicsParam("x", min_value=1.0, max_value=1.0)
    with pytest.raises(ValueError, match=r"min_value must be < max_value"):
        PhysicsParam("x", min_value=2.0, max_value=1.0)


def test_empty_name_rejected() -> None:
    with pytest.raises(ValueError, match=r"name must be non-empty"):
        PhysicsParam("", min_value=0.0, max_value=1.0)


def test_default_outside_range_rejected() -> None:
    with pytest.raises(ValueError, match=r"default 2\.0 outside"):
        PhysicsParam("x", min_value=0.0, max_value=1.0, default=2.0)


def test_default_at_endpoint_accepted() -> None:
    # Endpoint inclusion is documented behaviour.
    PhysicsParam("x", min_value=0.0, max_value=1.0, default=0.0)
    PhysicsParam("x", min_value=0.0, max_value=1.0, default=1.0)


# ---------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------


def test_decorator_attaches_param_to_function() -> None:
    @physics_param("x", min_value=0.0, max_value=1.0)
    def f() -> None:
        pass

    params = get_physics_params(f)
    assert len(params) == 1
    assert params[0].name == "x"


def test_decorator_stacks_in_source_order() -> None:
    """Top-most decorator (closest to user line 1) appears first in
    the returned tuple — readers expect declaration order.
    """

    @physics_param("A", min_value=0.0, max_value=1.0)
    @physics_param("B", min_value=0.0, max_value=1.0)
    @physics_param("C", min_value=0.0, max_value=1.0)
    def f() -> None:
        pass

    names = [p.name for p in get_physics_params(f)]
    assert names == ["A", "B", "C"]


def test_no_decorator_returns_empty_tuple() -> None:
    def f() -> None:
        pass

    assert get_physics_params(f) == ()


def test_decorator_returns_original_callable() -> None:
    """The decorator must not wrap the function — calling it still
    runs the original body.
    """

    @physics_param("x", min_value=0.0, max_value=1.0)
    def f(value: int) -> int:
        return value * 2

    assert f(3) == 6


# ---------------------------------------------------------------------
# Bouncing Ball spec
# ---------------------------------------------------------------------


def test_bouncing_ball_param_specs_has_four_params() -> None:
    names = [p.name for p in BOUNCING_BALL_PARAM_SPECS]
    assert names == [
        "gravity_m_s2",
        "restitution",
        "initial_height_m",
        "initial_velocity_m_s",
    ]


def test_bouncing_ball_restitution_spec_matches_pl_d_defaults() -> None:
    by_name = {p.name: p for p in BOUNCING_BALL_PARAM_SPECS}
    rest = by_name["restitution"]
    assert rest.min_value == 0.0
    assert rest.max_value == 1.0
    assert rest.scale == "linear"
    assert rest.default == pytest.approx(0.70)


def test_bouncing_ball_gravity_spec_default_is_earth_g() -> None:
    by_name = {p.name: p for p in BOUNCING_BALL_PARAM_SPECS}
    g = by_name["gravity_m_s2"]
    assert g.default == pytest.approx(9.81)
    assert g.scale == "linear"


def test_bouncing_ball_initial_height_is_log_scale() -> None:
    by_name = {p.name: p for p in BOUNCING_BALL_PARAM_SPECS}
    h = by_name["initial_height_m"]
    assert h.scale == "log"
    assert h.min_value > 0.0
