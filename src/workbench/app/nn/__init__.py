"""NN integration App layer (plan/07 § 7.4).

- Phase 6.3 :func:`write_dataset` / :func:`read_dataset` — HDF5
  dataset I/O (plan/07 § 7.4.4).
- Phase 6.4a :class:`DatasetBuilder` — streaming sample append +
  progress callback + finalize (plan/07 § 7.4.3).
- Phase 6.5 :class:`NumpyPairingNN` — first NNPluginMixin reference
  baseline (plan/07 § 7.4.5b).
- Phase 6.6 :class:`NNEvalResult` + :func:`evaluate` + :func:`pairing_loss`
  — 4-error diagnostic (plan/07 § 7.6).
- Phase 6.7 :class:`TrainingJob` + :class:`TrainingResult` +
  :class:`TrainerService` — training-loop schema + fake-loop service
  stub (plan/07 § 7.5).
"""

from __future__ import annotations

from workbench.app.nn.data_exporter import read_dataset, write_dataset
from workbench.app.nn.dataset_builder import DatasetBuilder, ProgressCallback
from workbench.app.nn.evaluator import NNEvalResult, evaluate, pairing_loss
from workbench.app.nn.pairing_nn import NumpyPairingNN
from workbench.app.nn.trainer import (
    EpochCallback,
    TrainerService,
    TrainingJob,
    TrainingResult,
)

__all__ = [
    "DatasetBuilder",
    "EpochCallback",
    "NNEvalResult",
    "NumpyPairingNN",
    "ProgressCallback",
    "TrainerService",
    "TrainingJob",
    "TrainingResult",
    "evaluate",
    "pairing_loss",
    "read_dataset",
    "write_dataset",
]
