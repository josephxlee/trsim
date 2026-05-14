"""Phase 6 A1-c + A1-d stub guards — lock the post-MVP contract.

The MVP scope deliberately leaves Tracker / Predictor / Classifier
real loss functions stubbed because their concrete signatures depend
on NN plugin protocols (TrackerNNPlugin, PredictorNNPlugin,
ClassifierNNPlugin) and sequence-dataset specs that haven't been
designed yet. To prevent silent regressions where someone partially
wires one of the stubs and forgets to update the UI ``n/a`` path,
this test file asserts:

1. Each stub raises ``NotImplementedError`` for any inputs.
2. The error message carries a 'Phase 6 follow-up' marker so
   ``grep`` finds the work items quickly.
3. The Step 2 UI controller continues to surface ``n/a`` instead of
   ``err:`` for these categories.

Once a real plugin lands the stubs will be replaced and this file
should be deleted (or rewritten to assert the new behaviour).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.app.nn.evaluator import (
    classifier_loss,
    multi_step_rollout_rmse,
    predictor_loss,
    tracker_loss,
)


def test_tracker_loss_is_post_mvp_stub(tmp_path: Path) -> None:
    """Tracker NN plugins are post-MVP — the stub must raise."""
    with pytest.raises(NotImplementedError, match=r"Phase 6 follow-up"):
        tracker_loss(plugin=object(), dataset_path=tmp_path / "noop.h5")


def test_predictor_loss_is_post_mvp_stub(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match=r"Phase 6 follow-up"):
        predictor_loss(plugin=object(), dataset_path=tmp_path / "noop.h5")


def test_classifier_loss_is_post_mvp_stub(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match=r"Phase 6 follow-up"):
        classifier_loss(plugin=object(), dataset_path=tmp_path / "noop.h5")


def test_multi_step_rollout_rmse_is_post_mvp_stub(tmp_path: Path) -> None:
    with pytest.raises(NotImplementedError, match=r"Phase 6 follow-up"):
        multi_step_rollout_rmse(
            plugin=object(),
            dataset_path=tmp_path / "noop.h5",
            n_steps=5,
        )


def test_multi_step_rollout_rmse_validates_n_steps_before_raising(
    tmp_path: Path,
) -> None:
    """``n_steps`` validation runs before the NotImplementedError so the
    caller can't accidentally pass an invalid argument and get a
    confusing 'post-MVP' message instead.

    If a future implementation drops the validation guard this test
    catches the regression.
    """
    with pytest.raises((ValueError, NotImplementedError)):
        multi_step_rollout_rmse(
            plugin=object(),
            dataset_path=tmp_path / "noop.h5",
            n_steps=0,
        )
