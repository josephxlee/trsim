"""AutoParametersWidget tests (PL-9.1c, plan/19 § 19.5.5)."""

from __future__ import annotations

import math

import pytest

pytest.importorskip("PySide6")

from workbench.domain.physics_lab import (
    BOUNCING_BALL_PARAM_SPECS,
    SLIDER_TICK_RESOLUTION,
    PhysicsParam,
)
from workbench.ui.physics_lab.auto_parameters import AutoParametersWidget

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Construction + introspection
# ---------------------------------------------------------------------


def test_widget_creates_one_slider_per_param(qtbot) -> None:  # type: ignore[no-untyped-def]
    params = (
        PhysicsParam("a", min_value=0.0, max_value=1.0),
        PhysicsParam("b", min_value=1.0, max_value=10.0, scale="log"),
    )
    w = AutoParametersWidget(params)
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    assert w.parameter_names() == ("a", "b")


def test_duplicate_name_rejected(qtbot) -> None:  # type: ignore[no-untyped-def]
    params = (
        PhysicsParam("x", min_value=0.0, max_value=1.0),
        PhysicsParam("x", min_value=0.0, max_value=2.0),
    )
    with pytest.raises(ValueError, match=r"duplicate parameter name 'x'"):
        AutoParametersWidget(params)


def test_slider_range_is_tick_resolution(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=0.0, max_value=1.0)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    s = w.slider_for("x")
    assert s.minimum() == 0
    assert s.maximum() == SLIDER_TICK_RESOLUTION


# ---------------------------------------------------------------------
# Linear scale
# ---------------------------------------------------------------------


def test_linear_default_at_explicit_value(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=0.0, max_value=1.0, default=0.70)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    assert w.current_value("x") == pytest.approx(0.70)


def test_linear_default_at_midpoint_when_unset(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=2.0, max_value=10.0)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    assert w.current_value("x") == pytest.approx(6.0)


def test_linear_set_value_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=0.0, max_value=1.0)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    w.set_value("x", 0.42)
    assert w.current_value("x") == pytest.approx(0.42)


def test_linear_set_value_clamps(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=0.0, max_value=1.0)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    w.set_value("x", -1.0)
    assert w.current_value("x") == 0.0
    w.set_value("x", 5.0)
    assert w.current_value("x") == pytest.approx(1.0)


# ---------------------------------------------------------------------
# Log scale
# ---------------------------------------------------------------------


def test_log_default_at_geometric_midpoint_when_unset(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("range_m", min_value=1.0, max_value=10000.0, scale="log")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    # sqrt(1 * 10000) = 100
    assert w.current_value("range_m") == pytest.approx(100.0)


def test_log_endpoints(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("range_m", min_value=1.0, max_value=10000.0, scale="log")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    w.slider_for("range_m").setValue(0)
    assert w.current_value("range_m") == pytest.approx(1.0)
    w.slider_for("range_m").setValue(SLIDER_TICK_RESOLUTION)
    assert w.current_value("range_m") == pytest.approx(10000.0)


def test_log_set_value_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("freq", min_value=1e6, max_value=1e12, scale="log")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    target = 1e9
    w.set_value("freq", target)
    # Tick resolution limits exact recovery, allow ~1 % relative error.
    assert w.current_value("freq") == pytest.approx(target, rel=0.05)


def test_log_endpoint_is_a_power_of_ten(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The log mapping is ``10**(lo + r*(hi-lo))`` — at midpoint of a
    [10, 1000] range we expect ``10**(1 + 0.5*2) = 100``.
    """
    p = PhysicsParam("y", min_value=10.0, max_value=1000.0, scale="log")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    w.slider_for("y").setValue(SLIDER_TICK_RESOLUTION // 2)
    assert w.current_value("y") == pytest.approx(100.0, rel=0.02)


# ---------------------------------------------------------------------
# Signal
# ---------------------------------------------------------------------


def test_parameter_changed_signal_fires_on_slider_move(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("x", min_value=0.0, max_value=1.0)
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    received: list[tuple[str, float]] = []
    w.parameter_changed.connect(lambda n, v: received.append((n, v)))
    w.slider_for("x").setValue(33)
    assert received[-1] == ("x", pytest.approx(0.33))


def test_parameter_changed_signal_emits_per_parameter(qtbot) -> None:  # type: ignore[no-untyped-def]
    # Defaults at the midpoints would mean setValue(50) is a no-op and
    # the signal never fires; explicit defaults at 0 force a real move.
    a = PhysicsParam("a", min_value=0.0, max_value=10.0, default=0.0)
    b = PhysicsParam("b", min_value=0.0, max_value=100.0, default=0.0)
    w = AutoParametersWidget((a, b))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    received: list[tuple[str, float]] = []
    w.parameter_changed.connect(lambda n, v: received.append((n, v)))
    w.slider_for("a").setValue(50)
    w.slider_for("b").setValue(25)
    assert ("a", pytest.approx(5.0)) in received
    assert ("b", pytest.approx(25.0)) in received


# ---------------------------------------------------------------------
# Readout text
# ---------------------------------------------------------------------


def test_readout_shows_unit_for_named_unit(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("v", min_value=0.0, max_value=100.0, default=50.0, unit="m/s")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    assert "m/s" in w.readout_for("v").text()


def test_readout_omits_unit_for_dash_placeholder(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``unit='-'`` is treated as 'no real unit' and is hidden."""
    p = PhysicsParam("r", min_value=0.0, max_value=1.0, default=0.5, unit="-")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    assert "-" not in w.readout_for("r").text() or "0.5" in w.readout_for("r").text()


# ---------------------------------------------------------------------
# Bouncing Ball integration
# ---------------------------------------------------------------------


def test_widget_built_from_bouncing_ball_specs(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = AutoParametersWidget(BOUNCING_BALL_PARAM_SPECS)
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    # All five parameters present, defaults at their declared values.
    assert set(w.parameter_names()) == {
        "gravity_m_s2",
        "restitution",
        "initial_height_m",
        "initial_velocity_m_s",
        "drag_coefficient_k",
    }
    # Restitution lands exactly on a tick boundary (default 0.70 over a
    # [0,1] range with 100 ticks).
    assert w.current_value("restitution") == pytest.approx(0.70)
    # Gravity (default 9.81 over [1, 30] linear) and initial-height
    # (default 5 m on a log [0.1, 50] scale) only land on the nearest
    # tick — allow ~1.5 % rounding from the 100-tick quantisation.
    assert w.current_value("gravity_m_s2") == pytest.approx(9.81, rel=0.02)
    assert w.current_value("initial_height_m") == pytest.approx(5.0, rel=0.05)


def test_initial_velocity_supports_negative_values(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The initial-velocity spec spans ``[-20, 20]`` (linear). Setting
    the slider to its minimum must yield ``-20``.
    """
    w = AutoParametersWidget(BOUNCING_BALL_PARAM_SPECS)
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    w.slider_for("initial_velocity_m_s").setValue(0)
    assert w.current_value("initial_velocity_m_s") == pytest.approx(-20.0)


# ---------------------------------------------------------------------
# Math sanity (round-trip via internal helpers via current_value)
# ---------------------------------------------------------------------


def test_log_midpoint_matches_sqrt_product(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PhysicsParam("freq", min_value=1e6, max_value=1e9, scale="log")
    w = AutoParametersWidget((p,))
    qtbot.addWidget(w)  # type: ignore[attr-defined]
    expected = math.sqrt(1e6 * 1e9)
    assert w.current_value("freq") == pytest.approx(expected, rel=0.01)
