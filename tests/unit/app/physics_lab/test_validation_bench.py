"""Generalized ValidationBench tests (Phase 9 § 19.7.5+ P2)."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np
import pytest

from workbench.app.physics_lab import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
    ValidationBench,
    ValidationConfig,
)

# ---------------------------------------------------------------------
# ValidationConfig validation
# ---------------------------------------------------------------------


def test_config_rejects_nonpositive_dt_s() -> None:
    with pytest.raises(ValueError, match=r"dt_s must be > 0"):
        ValidationConfig(output_field="y", dt_s=0.0)


def test_config_rejects_too_few_samples() -> None:
    with pytest.raises(ValueError, match=r"n_samples must be >= 2"):
        ValidationConfig(output_field="y", n_samples=1)


# ---------------------------------------------------------------------
# Bench construction
# ---------------------------------------------------------------------


class _BadModeModel:
    """PhysicsModelProtocol-like object with an invalid time_mode."""

    name = "bad"
    category = "dynamics"
    time_mode = "garbage"
    visualization = "2d"

    @property
    def parameters(self) -> tuple:  # type: ignore[override]
        return ()

    def compute(
        self, state: Mapping[str, Any], params: Mapping[str, float], dt_s: float | None
    ) -> Mapping[str, Any]:
        return {}


def test_bench_rejects_unknown_time_mode() -> None:
    with pytest.raises(ValueError, match=r"unsupported time_mode"):
        ValidationBench(model=_BadModeModel())  # type: ignore[arg-type]


# ---------------------------------------------------------------------
# Dynamic model — GravityOnly free fall
# ---------------------------------------------------------------------


def test_dynamic_gravity_only_matches_closed_form() -> None:
    """Free fall: y(t) = h0 - 0.5 g t^2. ValidationBench should report
    very low RMSE when the model is exactly the same physics."""
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    g = 9.81
    h0 = 100.0
    measured_t = np.linspace(0.01, 4.0, 50, dtype=np.float64)
    measured_y = h0 - 0.5 * g * measured_t**2
    sim_x, sim_y, metrics = bench.evaluate(
        measured_x=measured_t,
        measured_y=measured_y,
        params={"gravity_m_s2": g},
        config=ValidationConfig(
            output_field="position_m",
            initial_state={"time_s": 0.0, "position_m": h0, "velocity_m_s": 0.0},
            dt_s=0.005,
        ),
    )
    assert sim_x.size > 0
    assert sim_x.size == sim_y.size
    assert metrics.rmse < 0.5
    assert metrics.pearson_correlation > 0.99


def test_dynamic_bouncing_ball_smoke() -> None:
    """A self-comparison: feed the simulator's own trace back in as the
    measurement and expect ~zero error."""
    model = BouncingBallModel()
    bench = ValidationBench(model=model)
    params = {
        "gravity_m_s2": 9.81,
        "restitution": 0.7,
        "initial_height_m": 5.0,
        "initial_velocity_m_s": 0.0,
        "drag_coefficient_k": 0.0,
    }
    config = ValidationConfig(
        output_field="position_m",
        initial_state={
            "time_s": 0.0,
            "position_m": 5.0,
            "velocity_m_s": 0.0,
            "bounces": 0,
        },
        dt_s=0.01,
    )
    # First pass — generate a reference trace from the model itself.
    measured_t = np.linspace(0.05, 3.0, 60, dtype=np.float64)
    reference_x, reference_y, _ = bench.evaluate(
        measured_x=measured_t,
        measured_y=np.zeros_like(measured_t),  # ignored, we just want sim_*
        params=params,
        config=config,
    )
    # Now interpolate that reference onto measured_t and use *that* as
    # the measurement — the bench should report near-zero RMSE.
    measured_y = np.interp(measured_t, reference_x, reference_y)
    _, _, metrics = bench.evaluate(
        measured_x=measured_t,
        measured_y=measured_y,
        params=params,
        config=config,
    )
    assert metrics.rmse < 1e-6
    assert metrics.pearson_correlation > 0.999


def test_dynamic_rejects_nonpositive_measured_x() -> None:
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    measured_t = np.array([-1.0, -0.5], dtype=np.float64)
    measured_y = np.array([1.0, 2.0], dtype=np.float64)
    with pytest.raises(ValueError, match=r"dynamic mode requires measured_x"):
        bench.evaluate(
            measured_x=measured_t,
            measured_y=measured_y,
            params={"gravity_m_s2": 9.81},
            config=ValidationConfig(
                output_field="position_m",
                initial_state={"time_s": 0.0, "position_m": 1.0},
                dt_s=0.01,
            ),
        )


# ---------------------------------------------------------------------
# Static model — FreeSpaceLossModel
# ---------------------------------------------------------------------


def test_static_free_space_loss_matches_friis() -> None:
    """FSL: 10 log10((4 pi R / lambda)^2). Self-validation must be exact."""
    model = FreeSpaceLossModel()
    bench = ValidationBench(model=model)
    freq_hz = 9.4e9
    wavelength_m = 299_792_458.0 / freq_hz
    measured_range_m = np.linspace(10.0, 5_000.0, 20, dtype=np.float64)
    measured_loss_db = 10.0 * np.log10((4.0 * math.pi * measured_range_m / wavelength_m) ** 2)
    sim_x, sim_y, metrics = bench.evaluate(
        measured_x=measured_range_m,
        measured_y=measured_loss_db,
        params={"freq_hz": freq_hz},
        config=ValidationConfig(
            output_field="loss_db",
            input_field="range_m",
            n_samples=64,
        ),
    )
    # Static sweep covers exactly [min, max] of measured_x.
    assert sim_x[0] == pytest.approx(measured_range_m.min())
    assert sim_x[-1] == pytest.approx(measured_range_m.max())
    # RMSE should be tiny — only interpolation error remains.
    assert metrics.rmse < 0.1
    assert metrics.pearson_correlation > 0.999
    # Static sweep returns exactly n_samples points.
    assert sim_y.size == 64


def test_static_requires_input_field() -> None:
    model = FreeSpaceLossModel()
    bench = ValidationBench(model=model)
    with pytest.raises(ValueError, match=r"static models require"):
        bench.evaluate(
            measured_x=np.array([1.0, 2.0]),
            measured_y=np.array([1.0, 2.0]),
            params={"freq_hz": 9.4e9},
            config=ValidationConfig(
                output_field="loss_db",
                input_field=None,
            ),
        )


def test_static_rejects_zero_x_span() -> None:
    model = FreeSpaceLossModel()
    bench = ValidationBench(model=model)
    with pytest.raises(ValueError, match=r"static measured_x must span"):
        bench.evaluate(
            measured_x=np.array([5.0, 5.0]),
            measured_y=np.array([1.0, 2.0]),
            params={"freq_hz": 9.4e9},
            config=ValidationConfig(
                output_field="loss_db",
                input_field="range_m",
            ),
        )


# ---------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------


def test_evaluate_rejects_2d_measured_arrays() -> None:
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    with pytest.raises(ValueError, match=r"measured arrays must be 1-D"):
        bench.evaluate(
            measured_x=np.zeros((4, 2)),
            measured_y=np.zeros((4, 2)),
            params={"gravity_m_s2": 9.81},
            config=ValidationConfig(
                output_field="position_m",
                initial_state={"time_s": 0.0, "position_m": 1.0},
            ),
        )


def test_evaluate_rejects_empty_measured_arrays() -> None:
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    with pytest.raises(ValueError, match=r"measured arrays must be non-empty"):
        bench.evaluate(
            measured_x=np.array([]),
            measured_y=np.array([]),
            params={"gravity_m_s2": 9.81},
            config=ValidationConfig(
                output_field="position_m",
                initial_state={"time_s": 0.0, "position_m": 1.0},
            ),
        )


def test_evaluate_rejects_mismatched_shapes() -> None:
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    with pytest.raises(ValueError, match=r"measured_x .* != measured_y"):
        bench.evaluate(
            measured_x=np.array([1.0, 2.0, 3.0]),
            measured_y=np.array([1.0, 2.0]),
            params={"gravity_m_s2": 9.81},
            config=ValidationConfig(
                output_field="position_m",
                initial_state={"time_s": 0.0, "position_m": 1.0},
            ),
        )


def test_evaluate_raises_keyerror_for_missing_output_field() -> None:
    """A compute() that does not return the requested output_field
    must surface a KeyError listing the available keys."""
    model = FreeSpaceLossModel()
    bench = ValidationBench(model=model)
    with pytest.raises(KeyError, match=r"output_field 'bogus' missing"):
        bench.evaluate(
            measured_x=np.array([10.0, 100.0]),
            measured_y=np.array([1.0, 2.0]),
            params={"freq_hz": 9.4e9},
            config=ValidationConfig(
                output_field="bogus",
                input_field="range_m",
            ),
        )


# ---------------------------------------------------------------------
# Misc accessors
# ---------------------------------------------------------------------


def test_bench_model_property_returns_injected_model() -> None:
    model = GravityOnlyModel()
    bench = ValidationBench(model=model)
    assert bench.model is model
