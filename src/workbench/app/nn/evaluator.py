"""NN evaluator — 4-error diagnostic (plan/07 § 7.6).

Phase 6.6 — runs a Pairing NN plugin across the training / dev / test
HDF5 datasets and produces an :class:`NNEvalResult` carrying the four
losses + interpretive gaps (avoidable bias / variance / data mismatch)
+ a one-line diagnosis hint. Step 2 of the NN-mode UI consumes this
record to populate its diagnostic table (plan/07 § 7.6.2).

Loss function:

- Pairing: ``1 - accuracy`` over the GT-valid (``pair_indices >= 0``)
  positions, summed across the file. ``loss = 0`` when every up beat
  is matched to the correct down beat.

Bayes error is optional. Without it the evaluator returns the 3-error
mode (avoidable_bias = None) — plan/07 § 7.6.0 explicitly allows
this. With a user-supplied or Variant-A-derived Bayes value, the
``avoidable_bias = training - bayes`` gap is reported and feeds the
diagnosis hint.

References:

- plan/07 § 7.6 — 4-error diagnostic.
- plan/03 § 3.5.1a — :class:`NNEvalResult` schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from workbench.app.nn.data_exporter import read_dataset

_GAP_FLAG_THRESHOLD: float = 0.10
"""Loss-gap above this triggers the matching diagnosis bullet
(``avoidable bias`` / ``variance`` / ``data mismatch``). 0.10 = 10
percentage points of accuracy on the Pairing baseline — large enough
to be a real signal, small enough to flag drifts during tuning.
"""


class _PairingPredictor(Protocol):
    """Minimal surface the evaluator needs from a Pairing plugin."""

    def predict(
        self,
        up_beats: NDArray[np.complexfloating],
        down_beats: NDArray[np.complexfloating],
    ) -> NDArray[np.int32]: ...


@dataclass(frozen=True, slots=True)
class NNEvalResult:
    """Container for one full 4-error evaluation (plan/03 § 3.5.1a).

    Attributes:
        bayes_error: Theoretical lower bound estimate, or ``None`` if
            the user skipped Bayes estimation.
        training_error: Loss on the training-split dataset.
        dev_error: Loss on the dev-split (holdout) dataset.
        test_error: Loss on the test-split (unseen scenario) dataset.
        avoidable_bias: ``training - bayes`` if ``bayes_error`` is
            provided, else ``None``. plan/07 § 7.6.0 "Training - Bayes
            = avoidable bias".
        variance: ``dev - training``. "Variance" gap (overfitting).
        data_mismatch: ``test - dev``. "Data mismatch" gap (training
            distribution drift vs. real scenarios).
        diagnosis_hint: One-line human-readable interpretation
            (English; the Editor renders it verbatim).
        dataset_paths: ``(training, dev, test)`` tuple for the record.
    """

    bayes_error: float | None
    training_error: float
    dev_error: float
    test_error: float
    avoidable_bias: float | None
    variance: float
    data_mismatch: float
    diagnosis_hint: str
    dataset_paths: tuple[Path, Path, Path]


def pairing_loss(plugin: _PairingPredictor, dataset_path: Path | str) -> float:
    """Compute ``1 - accuracy`` over a Pairing HDF5 dataset.

    Iterates each sample in the file, runs ``plugin.predict(up, down)``,
    and compares against the GT ``pair_indices``. Positions where the
    GT label is ``-1`` (no ground-truth pair) are excluded from the
    denominator.

    Args:
        plugin: Object exposing the
            :class:`workbench.app.nn.NumpyPairingNN`-style
            ``predict(up, down) -> int32 array``.
        dataset_path: HDF5 file written by :func:`write_dataset` with
            ``inputs/up_beats``, ``inputs/down_beats``,
            ``labels/pair_indices``.

    Returns:
        Loss in ``[0, 1]``. ``0`` = every GT-valid match recovered.

    Raises:
        ValueError: If the dataset is missing the expected fields.
    """
    _meta, inputs, labels = read_dataset(dataset_path)
    if "up_beats" not in inputs or "down_beats" not in inputs:
        msg = f"{dataset_path}: pairing_loss requires inputs/up_beats and inputs/down_beats"
        raise ValueError(msg)
    if "pair_indices" not in labels:
        msg = f"{dataset_path}: pairing_loss requires labels/pair_indices"
        raise ValueError(msg)

    up = inputs["up_beats"]
    down = inputs["down_beats"]
    gt = labels["pair_indices"]

    total = 0
    correct = 0
    n_samples = int(up.shape[0])
    for i in range(n_samples):
        up_i = np.asarray(up[i], dtype=np.complex64)
        down_i = np.asarray(down[i], dtype=np.complex64)
        gt_i = np.asarray(gt[i], dtype=np.int32)
        pred = plugin.predict(up_i, down_i)
        valid = gt_i >= 0
        total += int(valid.sum())
        correct += int(((pred == gt_i) & valid).sum())

    if total == 0:
        # No GT-valid positions to score -> treat as perfectly evaluable.
        return 0.0
    return 1.0 - (correct / total)


# ---------------------------------------------------------------------
# A1-c — per-category loss stubs (Step 2 Tracker / Predictor / Classifier)
# ---------------------------------------------------------------------


def tracker_loss(plugin: object, dataset_path: Path | str) -> float:
    """Position RMSE for Tracker NN plugins (plan/07 § 7.6 stub).

    Concrete implementation lands when a Tracker NN plugin (TrackerProtocol
    + NNPluginMixin) ships alongside a track-truth dataset spec. The
    Step 2 controller catches the NotImplementedError raised here and
    renders ``n/a`` in the Tracker row of the 4-error table — so the
    UI surfaces the unsupported state explicitly instead of silently
    leaving the row at the ``--`` placeholder.

    ``plugin`` is typed as :class:`object` because the call surface for
    Tracker NN plugins isn't pinned down yet — the controller passes
    whatever Pairing plugin the user selected, and the stub rejects it
    by raising NotImplementedError before type narrowing matters.

    Args:
        plugin: Reserved for the future TrackerNNPlugin call surface.
        dataset_path: HDF5 file with track-truth labels.

    Raises:
        NotImplementedError: Always — this is a stub awaiting the
            plan/16 § 16.3.3 + plan/07 § 7.6.x wiring.
    """
    del plugin, dataset_path
    msg = "tracker_loss not yet wired — Phase 6 follow-up (TrackerNNPlugin)"
    raise NotImplementedError(msg)


def predictor_loss(plugin: object, dataset_path: Path | str) -> float:
    """Next-frame position RMSE for Predictor NN plugins (stub).

    Same shape as :func:`tracker_loss` — raises NotImplementedError so
    the Step 2 controller can mark the row ``n/a`` until a
    PredictorNNPlugin ships.
    """
    del plugin, dataset_path
    msg = "predictor_loss not yet wired — Phase 6 follow-up (PredictorNNPlugin)"
    raise NotImplementedError(msg)


def classifier_loss(plugin: object, dataset_path: Path | str) -> float:
    """``1 - accuracy`` for Classifier NN plugins (stub).

    Same shape as :func:`tracker_loss` — raises NotImplementedError so
    the Step 2 controller can mark the row ``n/a`` until a
    ClassifierNNPlugin ships.
    """
    del plugin, dataset_path
    msg = "classifier_loss not yet wired — Phase 6 follow-up (ClassifierNNPlugin)"
    raise NotImplementedError(msg)


def _make_diagnosis_hint(
    avoidable_bias: float | None,
    variance: float,
    data_mismatch: float,
) -> str:
    """Translate the three gaps into a one-line interpretive note.

    Each gap that exceeds :data:`_GAP_FLAG_THRESHOLD` contributes a
    short bullet; gaps within the threshold are skipped. If every gap
    is small the hint reports ``"balanced"`` so the Editor still has
    something to display.
    """
    bullets: list[str] = []
    if avoidable_bias is not None and avoidable_bias > _GAP_FLAG_THRESHOLD:
        bullets.append("avoidable bias high (increase capacity or train longer)")
    if variance > _GAP_FLAG_THRESHOLD:
        bullets.append("variance high (regularize or add dev data)")
    if data_mismatch > _GAP_FLAG_THRESHOLD:
        bullets.append("data mismatch (training distribution drifts from test)")
    if not bullets:
        return "balanced"
    return "; ".join(bullets)


def evaluate(
    plugin: _PairingPredictor,
    *,
    training_path: Path | str,
    dev_path: Path | str,
    test_path: Path | str,
    bayes_error: float | None = None,
) -> NNEvalResult:
    """Run a Pairing plugin against the three dataset splits.

    Args:
        plugin: NN plugin exposing
            ``predict(up, down) -> int32 array`` (Phase 6.5
            :class:`NumpyPairingNN` qualifies).
        training_path: HDF5 path for the training split.
        dev_path: HDF5 path for the dev / validation split.
        test_path: HDF5 path for the test / unseen-scenario split.
        bayes_error: Optional theoretical lower-bound loss for the
            avoidable-bias gap. ``None`` enters the 3-error mode.

    Returns:
        :class:`NNEvalResult` with the four losses + three gaps +
        diagnosis hint.

    Raises:
        ValueError: If ``bayes_error`` is supplied but outside
            ``[0, 1]``.
    """
    if bayes_error is not None and not (0.0 <= bayes_error <= 1.0):
        msg = f"bayes_error must be in [0, 1] or None, got {bayes_error}"
        raise ValueError(msg)

    tr = pairing_loss(plugin, training_path)
    de = pairing_loss(plugin, dev_path)
    te = pairing_loss(plugin, test_path)

    avoidable = None if bayes_error is None else tr - bayes_error
    variance = de - tr
    data_mismatch = te - de
    hint = _make_diagnosis_hint(avoidable, variance, data_mismatch)

    return NNEvalResult(
        bayes_error=bayes_error,
        training_error=tr,
        dev_error=de,
        test_error=te,
        avoidable_bias=avoidable,
        variance=variance,
        data_mismatch=data_mismatch,
        diagnosis_hint=hint,
        dataset_paths=(Path(training_path), Path(dev_path), Path(test_path)),
    )
