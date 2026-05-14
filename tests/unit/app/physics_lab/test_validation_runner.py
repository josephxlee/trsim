"""Generic Validation Bench runner tests (Phase 9 M1, plan/19 § 19.7.5+).

Verifies the validation layer dispatches correctly on
``PhysicsModelProtocol.time_mode`` and produces metrics that round-trip
through :func:`compute_validation_metrics`.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from workbench.app.physics_lab import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
    run_validation_for_model,
    simulate_dynamic_for_validation,
    sweep_static_for_validation,
)
from workbench.domain.physics_lab import ValidationRun

# ---------------------------------------------------------------------------
# simulate_dynamic_for_validation
# ---------------------------------------------------------------------------


def test_simulate_dynamic_returns_initial_state_first_entry() -> None:
    sim_x, sim_y = simulate_dynamic_for_validation(
        GravityOnlyModel(),
        params={"gravity_m_s2": 9.81},
        initial_state={"time_s": 0.0, "position_m": 5.0, "velocity_m_s": 0.0},
        dt_s=0.01,
        t_end_s=0.5,
        y_field="position_m",
    )
    assert sim_x[0] == pytest.approx(0.0)
    assert sim_y[0] == pytest.approx(5.0)
    # n_steps = ceil(0.5 / 0.01) = 50, plus initial entry = 51
    assert sim_x.size == 51
    assert sim_y.size == 51


def test_simulate_dynamic_gravity_only_matches_closed_form() -> None:
    """Semi-implicit Euler with small dt should track ``y = h - 0.5 g t^2``
    closely (gravity-only, no drag, no bounce, zero initial velocity).
    """
    model = GravityOnlyModel()
    h0 = 10.0
    g = 9.81
    sim_x, sim_y = simulate_dynamic_for_validation(
        model,
        params={"gravity_m_s2": g, "initial_height_m": h0, "initial_velocity_m_s": 0.0},
        initial_state={"position_m": h0, "velocity_m_s": 0.0},
        dt_s=1e-4,
        t_end_s=1.0,
        y_field="position_m",
    )
    expected = h0 - 0.5 * g * sim_x * sim_x
    assert sim_y == pytest.approx(expected, abs=5e-3)


def test_simulate_dynamic_bouncing_ball_decreasing_then_bounces() -> None:
    model = BouncingBallModel()
    sim_x, sim_y = simulate_dynamic_for_validation(
        model,
        params={
            "gravity_m_s2": 9.81,
            "restitution": 0.7,
            "initial_height_m": 5.0,
            "initial_velocity_m_s": 0.0,
            "drag_coefficient_k": 0.0,
        },
        initial_state={"position_m": 5.0, "velocity_m_s": 0.0, "bounces": 0},
        dt_s=0.005,
        t_end_s=3.0,
        y_field="position_m",
    )
    assert sim_y.min() == pytest.approx(0.0, abs=1e-9)
    # Position must never go negative.
    assert (sim_y >= 0.0).all()
    # Time grid must be monotonically increasing.
    assert (np.diff(sim_x) > 0.0).all()


def test_simulate_dynamic_zero_dt_rejected() -> None:
    with pytest.raises(ValueError, match=r"dt_s must be positive"):
        simulate_dynamic_for_validation(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            dt_s=0.0,
            t_end_s=1.0,
            y_field="position_m",
        )


def test_simulate_dynamic_negative_t_end_rejected() -> None:
    with pytest.raises(ValueError, match=r"t_end_s must be positive"):
        simulate_dynamic_for_validation(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            dt_s=0.01,
            t_end_s=-0.1,
            y_field="position_m",
        )


def test_simulate_dynamic_missing_y_field_raises() -> None:
    with pytest.raises(ValueError, match=r"did not return y_field 'unknown_key'"):
        simulate_dynamic_for_validation(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            initial_state={"position_m": 1.0, "velocity_m_s": 0.0},
            dt_s=0.01,
            t_end_s=0.1,
            y_field="unknown_key",
        )


def test_simulate_dynamic_defaults_initial_state_to_empty() -> None:
    """None initial_state should still work — model fills via defaults."""
    sim_x, sim_y = simulate_dynamic_for_validation(
        GravityOnlyModel(),
        params={"gravity_m_s2": 9.81, "initial_height_m": 3.0},
        initial_state=None,
        dt_s=0.01,
        t_end_s=0.1,
        y_field="position_m",
    )
    # First sample is the initial state -> y=0.0 (default get).
    # Subsequent samples come from GravityOnlyModel using h0=3.0 default.
    assert sim_x.size == sim_y.size
    assert sim_x[0] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# sweep_static_for_validation
# ---------------------------------------------------------------------------


def test_sweep_static_free_space_loss_matches_closed_form() -> None:
    """FSPL closed form ``L = 20 log10(4 pi R / lambda)`` at 9.4 GHz."""
    model = FreeSpaceLossModel()
    ranges = np.array([100.0, 1_000.0, 10_000.0], dtype=np.float64)
    freq_hz = 9.4e9
    wavelength_m = 299_792_458.0 / freq_hz
    sim_x, sim_y = sweep_static_for_validation(
        model,
        params={"freq_hz": freq_hz},
        x_values=ranges,
        x_field="range_m",
        y_field="loss_db",
    )
    expected = np.array(
        [20.0 * math.log10(4.0 * math.pi * r / wavelength_m) for r in ranges],
        dtype=np.float64,
    )
    assert sim_x == pytest.approx(ranges)
    assert sim_y == pytest.approx(expected, rel=1e-12)


def test_sweep_static_monotonic_loss_with_range() -> None:
    model = FreeSpaceLossModel()
    ranges = np.geomspace(10.0, 100_000.0, num=20).astype(np.float64)
    _, sim_y = sweep_static_for_validation(
        model,
        params={"freq_hz": 9.4e9},
        x_values=ranges,
        x_field="range_m",
        y_field="loss_db",
    )
    assert (np.diff(sim_y) > 0.0).all()


def test_sweep_static_empty_x_values_rejected() -> None:
    with pytest.raises(ValueError, match=r"x_values is empty"):
        sweep_static_for_validation(
            FreeSpaceLossModel(),
            params={"freq_hz": 9.4e9},
            x_values=np.array([], dtype=np.float64),
            x_field="range_m",
            y_field="loss_db",
        )


def test_sweep_static_2d_x_values_rejected() -> None:
    with pytest.raises(ValueError, match=r"x_values must be 1-D"):
        sweep_static_for_validation(
            FreeSpaceLossModel(),
            params={"freq_hz": 9.4e9},
            x_values=np.zeros((2, 3), dtype=np.float64),
            x_field="range_m",
            y_field="loss_db",
        )


def test_sweep_static_missing_y_field_raises() -> None:
    with pytest.raises(ValueError, match=r"did not return y_field 'no_such_field'"):
        sweep_static_for_validation(
            FreeSpaceLossModel(),
            params={"freq_hz": 9.4e9},
            x_values=np.array([1000.0], dtype=np.float64),
            x_field="range_m",
            y_field="no_such_field",
        )


# ---------------------------------------------------------------------------
# run_validation_for_model — dispatch + metrics integration
# ---------------------------------------------------------------------------


def test_run_validation_dynamic_self_consistency() -> None:
    """Feeding the simulator's own output back as 'measurement' gives RMSE 0."""
    model = GravityOnlyModel()
    params = {"gravity_m_s2": 9.81, "initial_height_m": 5.0, "initial_velocity_m_s": 0.0}
    initial_state = {"position_m": 5.0, "velocity_m_s": 0.0}
    sim_x, sim_y = simulate_dynamic_for_validation(
        model,
        params,
        initial_state=initial_state,
        dt_s=0.01,
        t_end_s=0.5,
        y_field="position_m",
    )
    run = run_validation_for_model(
        model,
        params=params,
        measured_x=sim_x,
        measured_y=sim_y,
        y_field="position_m",
        initial_state=initial_state,
        dt_s=0.01,
    )
    assert isinstance(run, ValidationRun)
    assert run.metrics.rmse == pytest.approx(0.0, abs=1e-9)
    assert run.metrics.max_abs_error == pytest.approx(0.0, abs=1e-9)
    assert run.metrics.pearson_correlation == pytest.approx(1.0, abs=1e-9)
    assert run.metrics.n_samples == sim_x.size


def test_run_validation_static_against_closed_form() -> None:
    model = FreeSpaceLossModel()
    freq_hz = 9.4e9
    wavelength_m = 299_792_458.0 / freq_hz
    ranges = np.array([500.0, 1_500.0, 5_000.0], dtype=np.float64)
    measured = np.array(
        [20.0 * math.log10(4.0 * math.pi * r / wavelength_m) for r in ranges],
        dtype=np.float64,
    )
    run = run_validation_for_model(
        model,
        params={"freq_hz": freq_hz},
        measured_x=ranges,
        measured_y=measured,
        y_field="loss_db",
        x_field="range_m",
    )
    assert run.metrics.rmse == pytest.approx(0.0, abs=1e-9)
    assert run.metrics.n_samples == ranges.size
    assert run.sim_y == pytest.approx(measured, rel=1e-12)


def test_run_validation_dynamic_missing_dt_raises() -> None:
    with pytest.raises(ValueError, match=r"dt_s required when model.time_mode == 'dynamic'"):
        run_validation_for_model(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            measured_x=np.array([0.0, 0.1, 0.2]),
            measured_y=np.array([5.0, 4.95, 4.8]),
            y_field="position_m",
        )


def test_run_validation_static_missing_x_field_raises() -> None:
    with pytest.raises(ValueError, match=r"x_field required when model.time_mode == 'static'"):
        run_validation_for_model(
            FreeSpaceLossModel(),
            params={"freq_hz": 9.4e9},
            measured_x=np.array([100.0, 1000.0]),
            measured_y=np.array([10.0, 30.0]),
            y_field="loss_db",
        )


def test_run_validation_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError, match=r"measured_x .* != measured_y"):
        run_validation_for_model(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            measured_x=np.array([0.0, 0.1, 0.2]),
            measured_y=np.array([5.0, 4.95]),
            y_field="position_m",
            dt_s=0.01,
        )


def test_run_validation_2d_measured_raises() -> None:
    with pytest.raises(ValueError, match=r"measured arrays must be 1-D"):
        run_validation_for_model(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            measured_x=np.zeros((2, 2)),
            measured_y=np.zeros((2, 2)),
            y_field="position_m",
            dt_s=0.01,
        )


def test_run_validation_empty_measured_raises() -> None:
    with pytest.raises(ValueError, match=r"measured arrays are empty"):
        run_validation_for_model(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            measured_x=np.array([], dtype=np.float64),
            measured_y=np.array([], dtype=np.float64),
            y_field="position_m",
            dt_s=0.01,
        )


def test_run_validation_dynamic_zero_max_x_raises() -> None:
    with pytest.raises(ValueError, match=r"dynamic measured_x must include a positive value"):
        run_validation_for_model(
            GravityOnlyModel(),
            params={"gravity_m_s2": 9.81},
            measured_x=np.array([0.0, 0.0]),
            measured_y=np.array([5.0, 5.0]),
            y_field="position_m",
            dt_s=0.01,
        )


def test_run_validation_unsupported_time_mode_raises() -> None:
    class WeirdModel:
        name = "weird"
        category = "dynamics"
        time_mode = "lazy"  # not in {static, dynamic}
        visualization = "2d"

        @property
        def parameters(self) -> tuple[()]:
            return ()

        def compute(self, state, params, dt_s):  # type: ignore[no-untyped-def]
            return {"y": 0.0}

    with pytest.raises(ValueError, match=r"unsupported model.time_mode 'lazy'"):
        run_validation_for_model(
            WeirdModel(),  # type: ignore[arg-type]
            params={},
            measured_x=np.array([0.0, 1.0]),
            measured_y=np.array([0.0, 0.0]),
            y_field="y",
            dt_s=0.1,
        )


def test_run_validation_returns_simulation_curve_with_metrics() -> None:
    """``ValidationRun`` packs both metrics *and* the (sim_x, sim_y) curve."""
    model = FreeSpaceLossModel()
    ranges = np.array([100.0, 1000.0, 10_000.0], dtype=np.float64)
    measured = np.array([20.0, 40.0, 60.0], dtype=np.float64)  # nonsense
    run = run_validation_for_model(
        model,
        params={"freq_hz": 9.4e9},
        measured_x=ranges,
        measured_y=measured,
        y_field="loss_db",
        x_field="range_m",
    )
    assert run.sim_x.shape == ranges.shape
    assert run.sim_y.shape == ranges.shape
    # The synthetic 'measured' here was a fake; metrics should be > 0.
    assert run.metrics.rmse > 0.0
