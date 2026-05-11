"""Numpy-only MLP — minimal in-process training backend (plan/07 § 7.5.3).

Task C (real TrainerService backend) — replaces the Phase 6.7 fake
exponential-decay loop with an actual gradient-descent MLP so the
weights file the in-workbench Trainer writes reflects samples that
were learned, not constants. The implementation is intentionally
pure numpy: no Torch / TF / sklearn so the import-linter NN-isolation
contract stays unaffected and the workbench works in restricted
environments.

Scope:

- Fully-connected (dense) layers with ReLU or tanh hidden activation
  and a linear output head.
- Mean-squared-error loss on flattened input / label arrays. The
  caller is responsible for projecting complex / multi-dim fields
  into a 2-D ``(N, D)`` real matrix.
- Mini-batch SGD update (no Adam, no momentum). The optimiser
  family is :class:`TrainingJob.optimizer`; the MVP backend recognises
  ``"sgd"`` only and ignores the request silently for any other value.

Out of scope (future sub-step):

- Adam / AdaGrad / RMSProp.
- Weight decay / dropout / batch norm.
- GPU paths (numpy CPU only).

References:

- plan/07 § 7.5.3 — in-workbench TrainerService loop.
- plan/05 § 5.1 — NN principle 1 (the Algorithm == Plugin contract).
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from workbench.domain.nn.sample_spec import FieldSpec, SampleSpec

Activation = Literal["relu", "tanh"]


@dataclass(slots=True)
class NumpyMLPParams:
    """Trainable parameters for a feed-forward MLP.

    Attributes:
        weights: Tuple of ``(D_in, D_out)`` float32 matrices, one per
            dense layer. Length = number of layers.
        biases: Tuple of ``(D_out,)`` float32 vectors, same length.
        activation: Hidden activation function. The output layer is
            always linear.
    """

    weights: list[NDArray[np.float32]]
    biases: list[NDArray[np.float32]]
    activation: Activation

    @property
    def layer_dims(self) -> tuple[int, ...]:
        """``(D_in, hidden..., D_out)`` derived from the weight shapes."""
        if not self.weights:
            return ()
        dims = [int(self.weights[0].shape[0])]
        for w in self.weights:
            dims.append(int(w.shape[1]))
        return tuple(dims)


def init_params(
    layer_dims: Sequence[int],
    *,
    activation: Activation = "relu",
    rng_seed: int = 0,
) -> NumpyMLPParams:
    """Build randomly-initialised :class:`NumpyMLPParams`.

    Args:
        layer_dims: ``(D_in, hidden..., D_out)``. Must have at least
            two entries (a single dense layer).
        activation: ``"relu"`` or ``"tanh"``. The output layer is
            linear regardless.
        rng_seed: Seed for the He / Xavier random init.

    Raises:
        ValueError: For empty / one-entry ``layer_dims`` or a
            non-positive dimension.
    """
    dims = tuple(int(d) for d in layer_dims)
    if len(dims) < 2:
        msg = f"layer_dims must contain at least two entries, got {dims}"
        raise ValueError(msg)
    for d in dims:
        if d <= 0:
            msg = f"layer_dims values must be > 0, got {dims}"
            raise ValueError(msg)

    rng = np.random.default_rng(rng_seed)
    weights: list[NDArray[np.float32]] = []
    biases: list[NDArray[np.float32]] = []
    for i in range(len(dims) - 1):
        a, b = dims[i], dims[i + 1]
        # He init for ReLU, Xavier (1/sqrt(a)) for tanh / linear output.
        std = math.sqrt(2.0 / a) if activation == "relu" else math.sqrt(1.0 / a)
        weights.append(rng.standard_normal((a, b)).astype(np.float32) * np.float32(std))
        biases.append(np.zeros((b,), dtype=np.float32))
    return NumpyMLPParams(weights=weights, biases=biases, activation=activation)


def forward(params: NumpyMLPParams, x: NDArray[np.float32]) -> NDArray[np.float32]:
    """Return ``Y_pred`` for one mini-batch.

    Hidden layers use the configured activation; the last layer is
    linear (regression). Shape ``(N, D_out)``.
    """
    activations = _forward_with_cache(params, x)
    return activations[-1]


def mse_loss(y_pred: NDArray[np.float32], y_true: NDArray[np.float32]) -> float:
    """Mean-squared-error scalar, averaged across both batch + features."""
    diff = y_pred - y_true
    return float(np.mean(diff * diff))


def train_one_epoch(
    params: NumpyMLPParams,
    x_train: NDArray[np.float32],
    y_train: NDArray[np.float32],
    *,
    learning_rate: float,
    batch_size: int,
    rng: np.random.Generator,
) -> float:
    """Run one full pass of mini-batch SGD over ``(x_train, y_train)``.

    Updates ``params`` in place. Returns the *post-update* full-batch
    training loss so the caller can plot a clean monotone curve.

    Args:
        params: :class:`NumpyMLPParams` to update.
        x_train: ``(N, D_in)`` float32 input matrix.
        y_train: ``(N, D_out)`` float32 target matrix.
        learning_rate: SGD step size. Must be > 0.
        batch_size: Mini-batch size. Must be > 0.
        rng: Numpy generator driving the per-epoch shuffle.

    Returns:
        Mean-squared training loss after the parameter updates.
    """
    if x_train.shape[0] != y_train.shape[0]:
        msg = (
            f"x_train and y_train must share the leading axis; "
            f"got {x_train.shape[0]} vs {y_train.shape[0]}"
        )
        raise ValueError(msg)
    if learning_rate <= 0.0:
        msg = f"learning_rate must be > 0, got {learning_rate}"
        raise ValueError(msg)
    if batch_size <= 0:
        msg = f"batch_size must be > 0, got {batch_size}"
        raise ValueError(msg)

    n = x_train.shape[0]
    perm = rng.permutation(n)
    for start in range(0, n, batch_size):
        batch_idx = perm[start : start + batch_size]
        xb = x_train[batch_idx]
        yb = y_train[batch_idx]
        _sgd_step(params, xb, yb, learning_rate=learning_rate)

    return mse_loss(forward(params, x_train), y_train)


# ---------------------------------------------------------------------
# Feature projection helpers
# ---------------------------------------------------------------------


def flatten_fields(
    spec_fields: tuple[FieldSpec, ...],
    arrays: Mapping[str, NDArray[np.generic]],
    n_samples: int,
) -> NDArray[np.float32]:
    """Project per-field arrays into a single ``(N, D)`` float32 matrix.

    Complex fields contribute ``(real, imag)`` pairs so the MLP sees
    real numbers only. The fields are concatenated in spec order so
    two calls with the same spec produce the same column layout.
    """
    columns: list[NDArray[np.float32]] = []
    for f in spec_fields:
        arr = arrays[f.name]
        if arr.shape[0] != n_samples:
            msg = f"flatten_fields: {f.name!r} leading axis is {arr.shape[0]}, expected {n_samples}"
            raise ValueError(msg)
        flat = arr.reshape(arr.shape[0], -1)
        if np.iscomplexobj(flat):
            re = flat.real.astype(np.float32)
            im = flat.imag.astype(np.float32)
            columns.append(np.concatenate([re, im], axis=1))
        else:
            columns.append(flat.astype(np.float32))
    if not columns:
        return np.empty((n_samples, 0), dtype=np.float32)
    return np.concatenate(columns, axis=1)


def flatten_inputs(
    spec: SampleSpec, inputs: Mapping[str, NDArray[np.generic]], n: int
) -> NDArray[np.float32]:
    """Shortcut: :func:`flatten_fields` over ``spec.inputs``."""
    return flatten_fields(spec.inputs, inputs, n)


def flatten_labels(
    spec: SampleSpec, labels: Mapping[str, NDArray[np.generic]], n: int
) -> NDArray[np.float32]:
    """Shortcut: :func:`flatten_fields` over ``spec.labels``."""
    return flatten_fields(spec.labels, labels, n)


# ---------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------


def _forward_with_cache(
    params: NumpyMLPParams, x: NDArray[np.float32]
) -> list[NDArray[np.float32]]:
    """Return activations list ``[a0=x, a1, ..., a_L]``."""
    activations: list[NDArray[np.float32]] = [x.astype(np.float32, copy=False)]
    a = activations[0]
    for i, (w, b) in enumerate(zip(params.weights, params.biases, strict=True)):
        z = a @ w + b
        a = _activation_fn(z, params.activation) if i < len(params.weights) - 1 else z
        activations.append(a)
    return activations


def _sgd_step(
    params: NumpyMLPParams,
    xb: NDArray[np.float32],
    yb: NDArray[np.float32],
    *,
    learning_rate: float,
) -> None:
    activations = _forward_with_cache(params, xb)
    pred = activations[-1]

    batch_n = xb.shape[0]
    # d_loss / d_pred for MSE averaged across batch + features:
    # loss = mean((pred - yb)^2) = sum / (batch_n * D_out)
    # d/d_pred = 2 * (pred - yb) / (batch_n * D_out)
    d_out = pred.shape[1] if pred.ndim > 1 else 1
    grad = (2.0 / (batch_n * d_out)) * (pred - yb)

    for layer_idx in range(len(params.weights) - 1, -1, -1):
        a_prev = activations[layer_idx]
        if layer_idx < len(params.weights) - 1:
            # Backprop through the activation that produced
            # activations[layer_idx + 1] from preact z.
            grad = grad * _activation_grad(activations[layer_idx + 1], params.activation)
        grad_w = a_prev.T @ grad
        grad_b = grad.sum(axis=0)
        if layer_idx > 0:
            grad = grad @ params.weights[layer_idx].T
        params.weights[layer_idx] = params.weights[layer_idx] - np.float32(
            learning_rate
        ) * grad_w.astype(np.float32)
        params.biases[layer_idx] = params.biases[layer_idx] - np.float32(
            learning_rate
        ) * grad_b.astype(np.float32)


def _activation_fn(z: NDArray[np.float32], kind: Activation) -> NDArray[np.float32]:
    if kind == "relu":
        return np.maximum(z, np.float32(0.0))
    if kind == "tanh":
        return np.tanh(z).astype(np.float32, copy=False)
    msg = f"unsupported activation {kind!r}"
    raise ValueError(msg)


def _activation_grad(a: NDArray[np.float32], kind: Activation) -> NDArray[np.float32]:
    """Derivative evaluated at the **activation output** (already cached).

    - ReLU': 1 where a > 0, else 0.
    - tanh': 1 - a**2 (since a = tanh(z), so 1 - tanh(z)**2).
    """
    if kind == "relu":
        return (a > np.float32(0.0)).astype(np.float32)
    if kind == "tanh":
        return (np.float32(1.0) - a * a).astype(np.float32)
    msg = f"unsupported activation {kind!r}"
    raise ValueError(msg)
