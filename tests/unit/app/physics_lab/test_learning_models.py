"""NN + polynomial PhysicsModel tests (PL-9.3c + 9.3d)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.app.physics_lab import (
    NumpyNNPhysicsModel,
    PolynomialFitModel,
)
from workbench.sdk.protocols import PhysicsModelProtocol

# ---------------------------------------------------------------------
# NumpyNNPhysicsModel (9.3c)
# ---------------------------------------------------------------------


def test_nn_physics_model_satisfies_protocol() -> None:
    assert isinstance(NumpyNNPhysicsModel(), PhysicsModelProtocol)


def test_nn_metadata_static_mode() -> None:
    m = NumpyNNPhysicsModel()
    assert m.time_mode == "static"
    assert m.category == "other"
    assert m.visualization == "2d"
    assert m.parameters == ()  # weights, not user-facing
    assert m.is_trained is False


def test_nn_compute_before_training_raises() -> None:
    m = NumpyNNPhysicsModel()
    with pytest.raises(RuntimeError, match=r"not trained"):
        m.compute({"x": 1.0}, {}, dt_s=None)


def test_nn_learns_linear_map() -> None:
    """Train on ``y = 2x + 3`` and verify a few predictions land
    within ~10% (loose tolerance because the MLP is tiny + epochs
    are short).
    """
    rng = np.random.default_rng(7)
    x = rng.uniform(-1.0, 1.0, size=128)
    y = 2.0 * x + 3.0
    m = NumpyNNPhysicsModel(hidden_dims=(16,), rng_seed=7)
    final_loss = m.train(x, y, epochs=400, learning_rate=0.05)
    assert m.is_trained is True
    assert final_loss < 0.05
    for x_test in (-0.5, 0.0, 0.5):
        out = m.compute({"x": x_test}, {}, dt_s=None)
        assert out["y_pred"] == pytest.approx(2.0 * x_test + 3.0, abs=0.5)


def test_nn_train_rejects_empty_inputs() -> None:
    m = NumpyNNPhysicsModel()
    with pytest.raises(ValueError, match=r"empty inputs"):
        m.train(np.array([]), np.array([]))


def test_nn_rejects_non_positive_hidden_dims() -> None:
    with pytest.raises(ValueError, match=r"hidden_dims must all be > 0"):
        NumpyNNPhysicsModel(hidden_dims=(8, 0))


# ---------------------------------------------------------------------
# PolynomialFitModel (9.3d)
# ---------------------------------------------------------------------


def test_polynomial_model_satisfies_protocol() -> None:
    assert isinstance(PolynomialFitModel(), PhysicsModelProtocol)


def test_polynomial_metadata_default_degree() -> None:
    m = PolynomialFitModel()
    assert m.degree == 2
    assert m.time_mode == "static"
    assert m.category == "other"
    assert m.is_fitted is False
    # Single user-facing parameter: degree.
    assert len(m.parameters) == 1
    assert m.parameters[0].name == "degree"


def test_polynomial_degree_validation() -> None:
    with pytest.raises(ValueError, match=r"degree must be in"):
        PolynomialFitModel(degree=0)
    with pytest.raises(ValueError, match=r"degree must be in"):
        PolynomialFitModel(degree=10)


def test_polynomial_fit_recovers_quadratic() -> None:
    """Fit ``y = x^2`` with degree=2 — coefficients should be (1, 0, 0)."""
    x = np.linspace(-2.0, 2.0, 21)
    y = x * x
    m = PolynomialFitModel(degree=2)
    coeffs = m.fit(x, y)
    assert m.is_fitted is True
    assert coeffs[0] == pytest.approx(1.0, abs=1e-9)
    assert coeffs[1] == pytest.approx(0.0, abs=1e-9)
    assert coeffs[2] == pytest.approx(0.0, abs=1e-9)


def test_polynomial_compute_uses_stored_coefficients() -> None:
    m = PolynomialFitModel(degree=2)
    m.fit(np.linspace(-1.0, 1.0, 11), np.array([1.0] * 11))  # y = 1 constant
    out = m.compute({"x": 2.5}, {}, dt_s=None)
    assert out["y_pred"] == pytest.approx(1.0, abs=1e-9)


def test_polynomial_compute_without_fit_returns_zero() -> None:
    m = PolynomialFitModel()
    out = m.compute({"x": 5.0}, {}, dt_s=None)
    assert out["y_pred"] == pytest.approx(0.0)


def test_polynomial_fit_rejects_too_few_samples() -> None:
    """Need at least ``degree + 1`` samples."""
    m = PolynomialFitModel(degree=3)
    with pytest.raises(ValueError, match=r"degree\+1"):
        m.fit(np.array([0.0, 1.0]), np.array([0.0, 1.0]))


def test_polynomial_fit_rejects_mismatched_shapes() -> None:
    m = PolynomialFitModel(degree=2)
    with pytest.raises(ValueError, match=r"same non-empty shape"):
        m.fit(np.array([0.0, 1.0, 2.0]), np.array([0.0, 1.0]))


def test_polynomial_higher_degree_better_fit() -> None:
    """Cubic data fits perfectly with degree=3; degree=2 leaves
    residual.
    """
    x = np.linspace(-1.0, 1.0, 51)
    y = x**3 - 0.5 * x

    m3 = PolynomialFitModel(degree=3)
    m3.fit(x, y)
    rmse_3 = float(np.sqrt(np.mean((np.polyval(m3.coefficients, x) - y) ** 2)))

    m2 = PolynomialFitModel(degree=2)
    m2.fit(x, y)
    rmse_2 = float(np.sqrt(np.mean((np.polyval(m2.coefficients, x) - y) ** 2)))

    assert rmse_3 < rmse_2
    assert rmse_3 < 1e-9  # essentially perfect


def test_polynomial_predicts_after_round_trip() -> None:
    """End-to-end: fit y = 2x + 5, then predict — recover exactly."""
    x = np.linspace(-3.0, 3.0, 41)
    y = 2.0 * x + 5.0
    m = PolynomialFitModel(degree=1)
    m.fit(x, y)
    out = m.compute({"x": 10.0}, {}, dt_s=None)
    assert out["y_pred"] == pytest.approx(2.0 * 10.0 + 5.0, abs=1e-9)
