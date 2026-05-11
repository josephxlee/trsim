"""NN Training Workflow UI (plan/07 § 7.5.3).

Phase 6 task 3 — single TrainingPanel widget + NNTrainingController.
The 5-step wizard mentioned in plan/07 lands in a later sub-step;
the MVP is one panel that drives the synchronous fake-loop
:class:`TrainerService`.
"""

from __future__ import annotations

from workbench.ui.nn_training.training_controller import NNTrainingController
from workbench.ui.nn_training.training_panel import TrainingPanel

__all__ = ["NNTrainingController", "TrainingPanel"]
