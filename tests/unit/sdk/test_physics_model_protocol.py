"""PhysicsModelProtocol tests (PL-9.3b, plan/19 § 19.8)."""

from __future__ import annotations

import pytest

from workbench.app.physics_lab import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
)
from workbench.sdk.protocols import PhysicsModelProtocol

# ---------------------------------------------------------------------
# runtime_checkable conformance
# ---------------------------------------------------------------------


def test_gravity_only_model_satisfies_protocol() -> None:
    assert isinstance(GravityOnlyModel(), PhysicsModelProtocol)


def test_bouncing_ball_model_satisfies_protocol() -> None:
    assert isinstance(BouncingBallModel(), PhysicsModelProtocol)


def test_free_space_loss_model_satisfies_protocol() -> None:
    assert isinstance(FreeSpaceLossModel(), PhysicsModelProtocol)


def test_random_object_rejected_by_protocol() -> None:
    class NotAModel:
        pass

    assert not isinstance(NotAModel(), PhysicsModelProtocol)


def test_partial_implementation_rejected_by_protocol() -> None:
    """Missing a single method (``compute``) fails the protocol
    check.
    """

    class HalfModel:
        name = "half"
        category = "dynamics"
        time_mode = "static"
        visualization = "2d"

        @property
        def parameters(self):
            return ()

        # No ``compute`` — runtime_checkable should reject.

    assert not isinstance(HalfModel(), PhysicsModelProtocol)


# ---------------------------------------------------------------------
# Metadata fields
# ---------------------------------------------------------------------


def test_gravity_only_model_metadata() -> None:
    m = GravityOnlyModel()
    assert m.name == "Gravity Only (analytic)"
    assert m.category == "dynamics"
    assert m.time_mode == "dynamic"
    assert m.visualization == "2d"
    assert len(m.parameters) == 3


def test_bouncing_ball_model_uses_canonical_param_specs() -> None:
    from workbench.domain.physics_lab import BOUNCING_BALL_PARAM_SPECS

    m = BouncingBallModel()
    assert m.parameters == BOUNCING_BALL_PARAM_SPECS


def test_free_space_loss_is_static() -> None:
    m = FreeSpaceLossModel()
    assert m.time_mode == "static"
    assert m.category == "rf_propagation"


# ---------------------------------------------------------------------
# compute() physics
# ---------------------------------------------------------------------


def test_gravity_only_model_matches_semi_implicit_euler() -> None:
    m = GravityOnlyModel()
    initial = {"time_s": 0.0, "position_m": 5.0, "velocity_m_s": 0.0}
    after = m.compute(initial, {"gravity_m_s2": 9.81}, dt_s=0.01)
    # Semi-implicit Euler: new_v = -g*dt; new_y = y0 + new_v*dt.
    assert after["velocity_m_s"] == pytest.approx(-9.81 * 0.01)
    assert after["position_m"] == pytest.approx(5.0 + (-9.81 * 0.01) * 0.01)
    assert after["time_s"] == pytest.approx(0.01)


def test_gravity_only_rejects_none_dt() -> None:
    m = GravityOnlyModel()
    with pytest.raises(ValueError, match=r"dt_s required"):
        m.compute({}, {"gravity_m_s2": 9.81}, dt_s=None)


def test_bouncing_ball_model_first_step_matches_simulator() -> None:
    """The PhysicsModelProtocol packaging must produce the same first
    step as :class:`BouncingBallSimulator` at the same dt.
    """
    from workbench.app.physics_lab import BouncingBallSimulator

    sim = BouncingBallSimulator(restitution=0.7, initial_height_m=5.0)
    after_sim = sim.step(0.01)

    model = BouncingBallModel()
    initial = {
        "time_s": 0.0,
        "position_m": 5.0,
        "velocity_m_s": 0.0,
        "bounces": 0,
    }
    after_model = model.compute(
        initial,
        {
            "gravity_m_s2": 9.81,
            "restitution": 0.7,
            "drag_coefficient_k": 0.0,
            "initial_height_m": 5.0,
            "initial_velocity_m_s": 0.0,
        },
        dt_s=0.01,
    )
    assert after_model["position_m"] == pytest.approx(after_sim.position_m)
    assert after_model["velocity_m_s"] == pytest.approx(after_sim.velocity_m_s)
    assert after_model["bounces"] == after_sim.bounces


def test_bouncing_ball_model_handles_bounce() -> None:
    """A state that crosses ground should bounce + count + flip
    velocity sign.
    """
    m = BouncingBallModel()
    pre_bounce = {
        "time_s": 1.0,
        "position_m": 0.005,
        "velocity_m_s": -1.0,
        "bounces": 0,
    }
    after = m.compute(
        pre_bounce,
        {
            "gravity_m_s2": 9.81,
            "restitution": 0.5,
            "drag_coefficient_k": 0.0,
        },
        dt_s=0.01,
    )
    assert after["position_m"] == pytest.approx(0.0)
    assert after["velocity_m_s"] > 0  # bounced upward
    assert after["bounces"] == 1


def test_free_space_loss_static_compute() -> None:
    """Loss at 1 km / 9.4 GHz against the closed form."""
    import math

    m = FreeSpaceLossModel()
    result = m.compute({}, {"range_m": 1000.0, "freq_hz": 9.4e9}, dt_s=None)
    wavelength = 299_792_458.0 / 9.4e9
    expected_db = 10.0 * math.log10((4.0 * math.pi * 1000.0 / wavelength) ** 2)
    assert result["loss_db"] == pytest.approx(expected_db)
    assert result["wavelength_m"] == pytest.approx(wavelength)


def test_free_space_loss_ignores_state_and_dt() -> None:
    """Static model: result depends only on params."""
    m = FreeSpaceLossModel()
    a = m.compute({"junk": 1.0}, {"range_m": 100.0, "freq_hz": 1e9}, dt_s=None)
    b = m.compute({"other": 2.0}, {"range_m": 100.0, "freq_hz": 1e9}, dt_s=1.0)
    assert a["loss_db"] == pytest.approx(b["loss_db"])
