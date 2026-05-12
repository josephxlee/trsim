"""ValidationMetrics + compute_validation_metrics tests (PL-9.2c)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.domain.physics_lab import (
    ValidationMetrics,
    compute_validation_metrics,
)

# ---------------------------------------------------------------------
# Identical curves
# ---------------------------------------------------------------------


def test_identical_curves_yield_zero_error_and_unit_correlation() -> None:
    x = np.linspace(0.0, 1.0, 11)
    y = np.sin(x)
    m = compute_validation_metrics(x, y, x, y)
    assert m.rmse == pytest.approx(0.0)
    assert m.max_abs_error == pytest.approx(0.0)
    assert m.pearson_correlation == pytest.approx(1.0)
    assert m.n_samples == 11


# ---------------------------------------------------------------------
# Constant offset
# ---------------------------------------------------------------------


def test_constant_offset_drives_rmse_to_offset_magnitude() -> None:
    x = np.linspace(0.0, 1.0, 11)
    measured_y = np.zeros_like(x)
    sim_y = np.full_like(x, 0.5)
    m = compute_validation_metrics(x, measured_y, x, sim_y)
    assert m.rmse == pytest.approx(0.5)
    assert m.max_abs_error == pytest.approx(0.5)
    # Both arrays have zero variance after the constant shift -> corr = 0.
    assert m.pearson_correlation == 0.0


# ---------------------------------------------------------------------
# Interpolation
# ---------------------------------------------------------------------


def test_simulation_interpolates_onto_measured_grid() -> None:
    """Sim sampled coarsely should still match measurement after
    linear interpolation onto the dense measured grid.
    """
    measured_x = np.linspace(0.0, 10.0, 101)
    measured_y = 2.0 * measured_x  # linear
    sim_x = np.linspace(0.0, 10.0, 11)  # 10 samples vs 101
    sim_y = 2.0 * sim_x
    m = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
    assert m.rmse == pytest.approx(0.0, abs=1e-10)
    assert m.pearson_correlation == pytest.approx(1.0)


def test_measurements_outside_sim_range_are_dropped() -> None:
    measured_x = np.array([0.0, 5.0, 12.0])
    measured_y = np.array([0.0, 5.0, 12.0])
    sim_x = np.linspace(0.0, 10.0, 11)
    sim_y = sim_x.copy()
    m = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
    # 12.0 is outside sim range -> 2 effective samples (0.0, 5.0).
    assert m.n_samples == 2
    assert m.rmse == pytest.approx(0.0)


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_mismatched_shapes_rejected() -> None:
    with pytest.raises(ValueError, match=r"measured_x"):
        compute_validation_metrics(
            np.array([0.0, 1.0]),
            np.array([0.0]),
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
        )
    with pytest.raises(ValueError, match=r"sim_x"):
        compute_validation_metrics(
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
            np.array([0.0]),
        )


def test_empty_arrays_rejected() -> None:
    with pytest.raises(ValueError, match=r"empty input"):
        compute_validation_metrics(
            np.array([]),
            np.array([]),
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
        )


def test_non_1d_inputs_rejected() -> None:
    with pytest.raises(ValueError, match=r"must be 1-D"):
        compute_validation_metrics(
            np.zeros((2, 2)),
            np.zeros((2, 2)),
            np.array([0.0, 1.0]),
            np.array([0.0, 1.0]),
        )


def test_no_overlap_rejected() -> None:
    measured_x = np.array([10.0, 20.0])
    measured_y = np.array([0.0, 1.0])
    sim_x = np.array([0.0, 1.0])
    sim_y = np.array([0.0, 1.0])
    with pytest.raises(ValueError, match=r"no measured points"):
        compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)


def test_unsorted_sim_x_handled() -> None:
    """The function sorts sim_x before interpolating, so unordered
    input is accepted.
    """
    measured_x = np.array([0.5, 1.5, 2.5])
    measured_y = np.array([5.0, 15.0, 25.0])
    sim_x = np.array([3.0, 0.0, 1.0, 2.0])
    sim_y = np.array([30.0, 0.0, 10.0, 20.0])
    m = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
    assert m.rmse == pytest.approx(0.0)


def test_returned_type_is_validation_metrics() -> None:
    m = compute_validation_metrics(
        np.array([0.0, 1.0]),
        np.array([0.0, 1.0]),
        np.array([0.0, 1.0]),
        np.array([0.0, 1.0]),
    )
    assert isinstance(m, ValidationMetrics)
