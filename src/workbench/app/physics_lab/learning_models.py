"""Learning-based PhysicsModel implementations (PL-9.3c + 9.3d).

Two reference plugins demonstrating the "NN replaces physics" (form 2)
and "symbolic regression" (form 4) workflows from plan/19 § 19.9.5.
Both wrap pure-numpy / scipy machinery so they ship with the workbench
without pulling in PySR / Julia / Torch.

- :class:`NumpyNNPhysicsModel` (9.3c) wraps the Phase 6
  :mod:`workbench.app.nn.numpy_mlp` MLP. ``train(x, y)`` learns a
  ``y = f(x)`` map; ``compute`` evaluates the learned network.
  ``time_mode = "static"`` because the network is a pure function
  of its inputs.
- :class:`PolynomialFitModel` (9.3d) fits a polynomial of degree
  ``degree`` using :func:`numpy.polyfit` (Vandermonde least-squares).
  Acts as the "symbolic regression" baseline — its closed-form
  coefficients are inspectable + the residuals + R^2 indicate fit
  quality.

Neither model exposes weights / coefficients as user-facing
``PhysicsParam`` sliders (Auto-Parameters can't usefully drive a
gradient-descent variable). The :attr:`parameters` tuple is empty
for the NN model and carries ``degree`` for the polynomial.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from workbench.app.nn.numpy_mlp import (
    Activation,
    NumpyMLPParams,
    forward,
    init_params,
    train_one_epoch,
)
from workbench.domain.physics_lab import PhysicsParam


class NumpyNNPhysicsModel:
    """NN-backed scalar regressor — Phase 6 numpy_mlp behind PhysicsModel.

    Attributes:
        hidden_dims: Hidden-layer widths. Default ``(8,)`` = one
            hidden layer of 8 units.
        activation: ``"relu"`` (default) or ``"tanh"`` for the hidden
            layers; the output layer is always linear.

    The model expects ``state["x"]`` as the scalar input and produces
    ``{"y_pred": float}``. Training reshapes ``(N,)`` arrays into
    ``(N, 1)`` float32 matrices to match
    :mod:`workbench.app.nn.numpy_mlp`'s API.
    """

    name = "NN-Physics (numpy MLP)"
    category = "other"
    time_mode = "static"
    visualization = "2d"

    def __init__(
        self,
        *,
        hidden_dims: tuple[int, ...] = (8,),
        activation: Activation = "relu",
        rng_seed: int = 0,
    ) -> None:
        if any(h <= 0 for h in hidden_dims):
            msg = f"hidden_dims must all be > 0, got {hidden_dims}"
            raise ValueError(msg)
        self._hidden_dims = hidden_dims
        self._activation: Literal["relu", "tanh"] = activation
        self._rng_seed = rng_seed
        self._params: NumpyMLPParams | None = None

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return ()

    @property
    def is_trained(self) -> bool:
        return self._params is not None

    def train(
        self,
        x: NDArray[np.float64],
        y: NDArray[np.float64],
        *,
        epochs: int = 200,
        learning_rate: float = 0.05,
        batch_size: int = 32,
    ) -> float:
        """Fit the network on ``(x, y)`` and return the final MSE.

        Both arrays may be 1-D ``(N,)`` or 2-D ``(N, D)``; the helper
        reshapes scalar inputs into ``(N, 1)``.
        """
        if x.size == 0 or y.size == 0:
            msg = "NumpyNNPhysicsModel.train: empty inputs"
            raise ValueError(msg)
        x_flat = np.atleast_2d(x.astype(np.float32))
        if (x_flat.shape[0] != x.shape[0] and x.ndim == 1) or x.ndim == 1:
            x_flat = x.astype(np.float32).reshape(-1, 1)
        y_flat = np.atleast_2d(y.astype(np.float32))
        if y.ndim == 1:
            y_flat = y.astype(np.float32).reshape(-1, 1)
        layer_dims = (x_flat.shape[1], *self._hidden_dims, y_flat.shape[1])
        self._params = init_params(
            layer_dims,
            activation=self._activation,
            rng_seed=self._rng_seed,
        )
        rng = np.random.default_rng(self._rng_seed)
        final_loss = float("inf")
        for _ in range(epochs):
            final_loss = train_one_epoch(
                self._params,
                x_flat,
                y_flat,
                learning_rate=learning_rate,
                batch_size=batch_size,
                rng=rng,
            )
        return final_loss

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        del params, dt_s  # Static + parameter-free at the user level.
        if self._params is None:
            msg = "NumpyNNPhysicsModel.compute: model not trained yet"
            raise RuntimeError(msg)
        x_value = float(state.get("x", 0.0))
        x_in = np.array([[x_value]], dtype=np.float32)
        y_pred = forward(self._params, x_in)
        return {"y_pred": float(y_pred[0, 0])}


class PolynomialFitModel:
    """Polynomial regression via :func:`numpy.polyfit` (PL-9.3d).

    Symbolic-regression baseline. Fits ``y = c_n x^n + ... + c_0``
    of degree ``degree`` (1..5 in practice). ``coefficients`` returns
    the Polynomial coefficients in numpy's high-to-low order.
    """

    name = "Polynomial fit"
    category = "other"
    time_mode = "static"
    visualization = "2d"

    _DEFAULT_DEGREE: int = 2
    _MIN_DEGREE: int = 1
    _MAX_DEGREE: int = 5

    def __init__(self, *, degree: int = 2) -> None:
        if not self._MIN_DEGREE <= degree <= self._MAX_DEGREE:
            msg = (
                f"PolynomialFitModel.degree must be in "
                f"[{self._MIN_DEGREE}, {self._MAX_DEGREE}], got {degree}"
            )
            raise ValueError(msg)
        self._degree = int(degree)
        self._coefficients: tuple[float, ...] = ()

    @property
    def degree(self) -> int:
        return self._degree

    @property
    def coefficients(self) -> tuple[float, ...]:
        """Highest-order first (matches :func:`numpy.polyval`)."""
        return self._coefficients

    @property
    def is_fitted(self) -> bool:
        return bool(self._coefficients)

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return (
            PhysicsParam(
                name="degree",
                min_value=float(self._MIN_DEGREE),
                max_value=float(self._MAX_DEGREE),
                scale="linear",
                unit="",
                default=float(self._DEFAULT_DEGREE),
                description=(
                    "Polynomial degree. ``compute`` uses the coefficients "
                    "stored from the most recent ``fit`` call; the slider "
                    "drives the next fit."
                ),
            ),
        )

    def fit(
        self,
        x: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> tuple[float, ...]:
        """Run a least-squares polyfit and store the coefficients."""
        if x.size == 0 or y.size == 0 or x.shape != y.shape:
            msg = (
                "PolynomialFitModel.fit: x + y must be the same non-empty "
                f"shape, got {x.shape} / {y.shape}"
            )
            raise ValueError(msg)
        if x.size <= self._degree:
            msg = (
                f"PolynomialFitModel.fit: need at least degree+1 "
                f"({self._degree + 1}) samples, got {x.size}"
            )
            raise ValueError(msg)
        coeffs = np.polyfit(x, y, deg=self._degree)
        self._coefficients = tuple(float(c) for c in coeffs)
        return self._coefficients

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        del dt_s
        # The runtime ``degree`` slider can override the stored degree
        # for the *next* fit but does not affect ``compute`` (which
        # uses the coefficients already learned).
        del params
        x_value = float(state.get("x", 0.0))
        if not self._coefficients:
            return {"y_pred": 0.0}
        y_pred = float(np.polyval(self._coefficients, x_value))
        return {"y_pred": y_pred}
