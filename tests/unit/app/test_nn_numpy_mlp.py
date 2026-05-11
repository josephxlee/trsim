"""Numpy MLP backend helper tests (Task C, plan/07 § 7.5.3)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.app.nn import (
    NumpyMLPParams,
    flatten_inputs,
    flatten_labels,
    mse_loss,
    numpy_mlp_forward,
    numpy_mlp_init_params,
    numpy_mlp_train_one_epoch,
)
from workbench.domain.nn import FieldSpec, SampleSpec

# ---------------------------------------------------------------------
# init_params
# ---------------------------------------------------------------------


def test_init_params_layer_shapes() -> None:
    params = numpy_mlp_init_params((3, 8, 8, 2))
    assert tuple(w.shape for w in params.weights) == ((3, 8), (8, 8), (8, 2))
    assert tuple(b.shape for b in params.biases) == ((8,), (8,), (2,))
    assert params.layer_dims == (3, 8, 8, 2)


def test_init_params_relu_uses_he_init_scale() -> None:
    params = numpy_mlp_init_params((100, 50), activation="relu", rng_seed=0)
    # He init: std ~ sqrt(2 / fan_in). Sample std must be within a wide
    # tolerance of that value (single 100x50 matrix).
    expected_std = float(np.sqrt(2.0 / 100))
    assert params.weights[0].std() == pytest.approx(expected_std, rel=0.25)


def test_init_params_rejects_short_dims() -> None:
    with pytest.raises(ValueError, match=r"at least two entries"):
        numpy_mlp_init_params((4,))


def test_init_params_rejects_non_positive_dim() -> None:
    with pytest.raises(ValueError, match=r"values must be > 0"):
        numpy_mlp_init_params((4, 0, 2))


def test_init_params_seed_is_reproducible() -> None:
    a = numpy_mlp_init_params((3, 4), rng_seed=42)
    b = numpy_mlp_init_params((3, 4), rng_seed=42)
    assert np.allclose(a.weights[0], b.weights[0])


# ---------------------------------------------------------------------
# forward / mse_loss
# ---------------------------------------------------------------------


def test_forward_zero_weights_returns_biases() -> None:
    params = NumpyMLPParams(
        weights=[np.zeros((2, 3), dtype=np.float32)],
        biases=[np.array([1.0, 2.0, 3.0], dtype=np.float32)],
        activation="relu",
    )
    out = numpy_mlp_forward(params, np.ones((4, 2), dtype=np.float32))
    assert np.allclose(out, np.tile([1.0, 2.0, 3.0], (4, 1)))


def test_mse_loss_matches_numpy_mean() -> None:
    pred = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    target = np.array([[1.0, 2.0], [3.0, 5.0]], dtype=np.float32)
    # diff = [[0,0],[0,-1]], sq = [[0,0],[0,1]], mean over 4 cells = 0.25
    assert mse_loss(pred, target) == pytest.approx(0.25)


# ---------------------------------------------------------------------
# train_one_epoch — loss must decrease on a linear task
# ---------------------------------------------------------------------


def _linear_dataset(n: int, d_in: int, d_out: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    w = rng.standard_normal((d_in, d_out)).astype(np.float32)
    x = rng.standard_normal((n, d_in)).astype(np.float32)
    y = (x @ w).astype(np.float32)
    return x, y


def test_train_one_epoch_decreases_loss_on_linear_data() -> None:
    x, y = _linear_dataset(n=64, d_in=4, d_out=2, seed=0)
    params = numpy_mlp_init_params((4, 16, 2), activation="relu", rng_seed=0)

    loss_before = mse_loss(numpy_mlp_forward(params, x), y)
    loss_after = numpy_mlp_train_one_epoch(
        params,
        x,
        y,
        learning_rate=0.05,
        batch_size=16,
        rng=np.random.default_rng(1),
    )
    assert loss_after < loss_before


def test_train_multiple_epochs_drives_loss_low() -> None:
    x, y = _linear_dataset(n=128, d_in=3, d_out=1, seed=0)
    params = numpy_mlp_init_params((3, 32, 1), activation="relu", rng_seed=0)
    rng = np.random.default_rng(1)

    loss = mse_loss(numpy_mlp_forward(params, x), y)
    for _ in range(50):
        loss = numpy_mlp_train_one_epoch(params, x, y, learning_rate=0.05, batch_size=16, rng=rng)
    # 50 epochs over a small linear task — final loss should be much
    # smaller than the random-init starting loss.
    assert loss < 0.1


def test_train_one_epoch_rejects_mismatched_axes() -> None:
    params = numpy_mlp_init_params((2, 1))
    with pytest.raises(ValueError, match=r"leading axis"):
        numpy_mlp_train_one_epoch(
            params,
            np.zeros((3, 2), dtype=np.float32),
            np.zeros((4, 1), dtype=np.float32),
            learning_rate=0.1,
            batch_size=1,
            rng=np.random.default_rng(0),
        )


def test_train_one_epoch_rejects_non_positive_lr() -> None:
    params = numpy_mlp_init_params((2, 1))
    with pytest.raises(ValueError, match=r"learning_rate must be > 0"):
        numpy_mlp_train_one_epoch(
            params,
            np.zeros((4, 2), dtype=np.float32),
            np.zeros((4, 1), dtype=np.float32),
            learning_rate=0.0,
            batch_size=1,
            rng=np.random.default_rng(0),
        )


# ---------------------------------------------------------------------
# flatten_inputs / flatten_labels
# ---------------------------------------------------------------------


def _pairing_spec(buffer: int = 4) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (buffer,), "complex64"),
            FieldSpec("down_beats", (buffer,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (buffer,), "int32"),),
    )


def test_flatten_inputs_splits_complex_into_real_imag() -> None:
    spec = _pairing_spec(buffer=2)
    up = np.array([[1 + 2j, 3 + 4j]], dtype=np.complex64)
    down = np.array([[5 + 6j, 7 + 8j]], dtype=np.complex64)
    x = flatten_inputs(spec, {"up_beats": up, "down_beats": down}, n=1)
    # up.re | up.im | down.re | down.im = 1,3 | 2,4 | 5,7 | 6,8
    assert x.shape == (1, 8)
    assert x.dtype == np.float32
    assert np.allclose(x[0], np.array([1.0, 3.0, 2.0, 4.0, 5.0, 7.0, 6.0, 8.0]))


def test_flatten_labels_int_to_float32() -> None:
    spec = _pairing_spec(buffer=3)
    labels = {"pair_indices": np.array([[0, 1, -1]], dtype=np.int32)}
    y = flatten_labels(spec, labels, n=1)
    assert y.shape == (1, 3)
    assert y.dtype == np.float32
    assert np.allclose(y[0], np.array([0.0, 1.0, -1.0]))


def test_flatten_inputs_rejects_wrong_leading_axis() -> None:
    spec = _pairing_spec(buffer=2)
    with pytest.raises(ValueError, match=r"leading axis"):
        flatten_inputs(
            spec,
            {
                "up_beats": np.zeros((3, 2), dtype=np.complex64),
                "down_beats": np.zeros((3, 2), dtype=np.complex64),
            },
            n=4,
        )
