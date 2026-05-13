"""NN evaluator + 4-error diagnostic tests (Phase 6.6)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import (
    DatasetBuilder,
    NumpyPairingNN,
    evaluate,
    pairing_loss,
)
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec

# ---------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------


def _pairing_spec(beat_count: int = 4) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (beat_count,), "complex64"),
            FieldSpec("down_beats", (beat_count,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (beat_count,), "int32"),),
    )


def _build_identity_dataset(tmp_path: Path, n_samples: int, beat_count: int = 4) -> Path:
    """Build a dataset where ``down = up`` and GT = diagonal pairing."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    spec = _pairing_spec(beat_count)
    out = tmp_path / "identity.h5"
    builder = DatasetBuilder(
        spec=spec,
        variant=DatasetVariant(variant_id="A"),
        dataset_id="identity",
        output_path=out,
    )
    rng = np.random.default_rng(seed=0)
    diagonal = np.arange(beat_count, dtype=np.int32)
    for _ in range(n_samples):
        up = rng.standard_normal(beat_count).astype(np.complex64)
        builder.append({"up_beats": up, "down_beats": up}, {"pair_indices": diagonal})
    builder.finalize()
    return out


def _build_wrong_label_dataset(tmp_path: Path, n_samples: int, beat_count: int = 4) -> Path:
    """Same arrays but GT label is shifted by 1 -> NumpyPairingNN
    predicts the diagonal -> 100% wrong."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    spec = _pairing_spec(beat_count)
    out = tmp_path / "wrong.h5"
    builder = DatasetBuilder(
        spec=spec,
        variant=DatasetVariant(variant_id="A"),
        dataset_id="wrong",
        output_path=out,
    )
    rng = np.random.default_rng(seed=1)
    shifted = np.roll(np.arange(beat_count, dtype=np.int32), 1)
    for _ in range(n_samples):
        up = rng.standard_normal(beat_count).astype(np.complex64)
        builder.append({"up_beats": up, "down_beats": up}, {"pair_indices": shifted})
    builder.finalize()
    return out


# ---------------------------------------------------------------------
# pairing_loss
# ---------------------------------------------------------------------


def test_pairing_loss_zero_on_identity_dataset(tmp_path: Path) -> None:
    path = _build_identity_dataset(tmp_path, n_samples=4)
    loss = pairing_loss(NumpyPairingNN(), path)
    assert loss == pytest.approx(0.0, abs=1e-12)


def test_pairing_loss_one_on_fully_wrong_dataset(tmp_path: Path) -> None:
    path = _build_wrong_label_dataset(tmp_path, n_samples=4)
    loss = pairing_loss(NumpyPairingNN(), path)
    assert loss == pytest.approx(1.0, abs=1e-12)


def test_tracker_loss_is_a_not_yet_wired_stub(tmp_path: Path) -> None:
    """A1-c — Tracker NN plugin loss is a stub; controller turns
    NotImplementedError into ``n/a`` in the Step 2 table.
    """
    from workbench.app.nn.evaluator import tracker_loss

    path = _build_identity_dataset(tmp_path, n_samples=2)
    with pytest.raises(NotImplementedError, match=r"tracker_loss"):
        tracker_loss(NumpyPairingNN(), path)


def test_predictor_loss_is_a_not_yet_wired_stub(tmp_path: Path) -> None:
    """A1-c — same shape as :func:`tracker_loss`."""
    from workbench.app.nn.evaluator import predictor_loss

    path = _build_identity_dataset(tmp_path, n_samples=2)
    with pytest.raises(NotImplementedError, match=r"predictor_loss"):
        predictor_loss(NumpyPairingNN(), path)


def test_classifier_loss_is_a_not_yet_wired_stub(tmp_path: Path) -> None:
    """A1-c — same shape as :func:`tracker_loss`."""
    from workbench.app.nn.evaluator import classifier_loss

    path = _build_identity_dataset(tmp_path, n_samples=2)
    with pytest.raises(NotImplementedError, match=r"classifier_loss"):
        classifier_loss(NumpyPairingNN(), path)


def test_multi_step_rollout_rmse_is_a_not_yet_wired_stub(tmp_path: Path) -> None:
    """A1-d — sequence-level rollout RMSE (stub) raises NotImplementedError."""
    from workbench.app.nn.evaluator import multi_step_rollout_rmse

    path = _build_identity_dataset(tmp_path, n_samples=2)
    with pytest.raises(NotImplementedError, match=r"multi_step_rollout_rmse"):
        multi_step_rollout_rmse(NumpyPairingNN(), path, n_steps=4)


def test_multi_step_rollout_rmse_rejects_non_positive_n_steps(tmp_path: Path) -> None:
    """Input validation fires *before* the NotImplementedError so
    callers get a deterministic error for malformed n_steps even
    while the metric body is stubbed.
    """
    from workbench.app.nn.evaluator import multi_step_rollout_rmse

    path = _build_identity_dataset(tmp_path, n_samples=2)
    with pytest.raises(ValueError, match=r"n_steps must be > 0"):
        multi_step_rollout_rmse(NumpyPairingNN(), path, n_steps=0)
    with pytest.raises(ValueError, match=r"n_steps must be > 0"):
        multi_step_rollout_rmse(NumpyPairingNN(), path, n_steps=-3)


def test_pairing_loss_excludes_unlabelled_positions(tmp_path: Path) -> None:
    """``pair_indices == -1`` are skipped — they do not count as wrong."""
    spec = _pairing_spec(4)
    out = tmp_path / "partial.h5"
    builder = DatasetBuilder(
        spec=spec,
        variant=DatasetVariant(variant_id="A"),
        dataset_id="partial",
        output_path=out,
    )
    rng = np.random.default_rng(seed=2)
    up = rng.standard_normal(4).astype(np.complex64)
    # GT: only first two positions labelled, rest are -1.
    gt = np.array([0, 1, -1, -1], dtype=np.int32)
    builder.append({"up_beats": up, "down_beats": up}, {"pair_indices": gt})
    builder.finalize()

    loss = pairing_loss(NumpyPairingNN(), out)
    assert loss == pytest.approx(0.0, abs=1e-12)


# ---------------------------------------------------------------------
# evaluate() — 4-error result
# ---------------------------------------------------------------------


def test_evaluate_three_datasets_returns_zero_losses_when_all_identity(
    tmp_path: Path,
) -> None:
    tr = _build_identity_dataset(tmp_path / "tr", n_samples=3)
    de = _build_identity_dataset(tmp_path / "de", n_samples=3)
    te = _build_identity_dataset(tmp_path / "te", n_samples=3)
    result = evaluate(NumpyPairingNN(), training_path=tr, dev_path=de, test_path=te)
    assert result.training_error == pytest.approx(0.0, abs=1e-12)
    assert result.dev_error == pytest.approx(0.0, abs=1e-12)
    assert result.test_error == pytest.approx(0.0, abs=1e-12)
    assert result.bayes_error is None
    assert result.avoidable_bias is None
    assert result.diagnosis_hint == "balanced"


def test_evaluate_detects_data_mismatch_when_test_is_wrong(tmp_path: Path) -> None:
    """Training / dev are identity (0% loss); test is fully wrong (100% loss).
    The dev-test gap is 1.0 -> "data mismatch" bullet must appear.
    """
    tr = _build_identity_dataset(tmp_path / "tr", n_samples=3)
    de = _build_identity_dataset(tmp_path / "de", n_samples=3)
    te = _build_wrong_label_dataset(tmp_path / "te", n_samples=3)
    result = evaluate(NumpyPairingNN(), training_path=tr, dev_path=de, test_path=te)
    assert result.training_error == pytest.approx(0.0, abs=1e-12)
    assert result.dev_error == pytest.approx(0.0, abs=1e-12)
    assert result.test_error == pytest.approx(1.0, abs=1e-12)
    assert result.variance == pytest.approx(0.0, abs=1e-12)
    assert result.data_mismatch == pytest.approx(1.0, abs=1e-12)
    assert "data mismatch" in result.diagnosis_hint


def test_evaluate_detects_variance_when_dev_is_wrong(tmp_path: Path) -> None:
    """Training is identity, dev is fully wrong, test = dev. The
    training-dev gap is "variance".
    """
    tr = _build_identity_dataset(tmp_path / "tr", n_samples=3)
    de = _build_wrong_label_dataset(tmp_path / "de", n_samples=3)
    te = _build_wrong_label_dataset(tmp_path / "te", n_samples=3)
    result = evaluate(NumpyPairingNN(), training_path=tr, dev_path=de, test_path=te)
    assert result.variance == pytest.approx(1.0, abs=1e-12)
    assert "variance" in result.diagnosis_hint


def test_evaluate_with_bayes_reports_avoidable_bias(tmp_path: Path) -> None:
    tr = _build_wrong_label_dataset(tmp_path / "tr", n_samples=3)  # loss=1
    de = _build_wrong_label_dataset(tmp_path / "de", n_samples=3)
    te = _build_wrong_label_dataset(tmp_path / "te", n_samples=3)
    result = evaluate(
        NumpyPairingNN(),
        training_path=tr,
        dev_path=de,
        test_path=te,
        bayes_error=0.0,
    )
    assert result.bayes_error == 0.0
    assert result.avoidable_bias == pytest.approx(1.0, abs=1e-12)
    assert "avoidable bias" in result.diagnosis_hint


def test_evaluate_rejects_bayes_outside_unit_interval(tmp_path: Path) -> None:
    tr = _build_identity_dataset(tmp_path, n_samples=1)
    with pytest.raises(ValueError, match=r"bayes_error"):
        evaluate(
            NumpyPairingNN(),
            training_path=tr,
            dev_path=tr,
            test_path=tr,
            bayes_error=1.5,
        )


def test_evaluate_dataset_paths_round_trip(tmp_path: Path) -> None:
    tr = _build_identity_dataset(tmp_path / "tr", n_samples=2)
    de = _build_identity_dataset(tmp_path / "de", n_samples=2)
    te = _build_identity_dataset(tmp_path / "te", n_samples=2)
    result = evaluate(NumpyPairingNN(), training_path=tr, dev_path=de, test_path=te)
    assert result.dataset_paths == (Path(tr), Path(de), Path(te))
