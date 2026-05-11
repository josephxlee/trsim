"""NN integration App layer (plan/07 § 7.4).

- Phase 6.3 :func:`write_dataset` / :func:`read_dataset` — HDF5
  dataset I/O (plan/07 § 7.4.4).
- Phase 6.4a :class:`DatasetBuilder` — streaming sample append +
  progress callback + finalize (plan/07 § 7.4.3).

Higher-level orchestration (Pipeline probe hook, Step 1 Editor
wiring, TrainerService, NNEvaluator) layers on top in later
sub-steps.
"""

from __future__ import annotations

from workbench.app.nn.data_exporter import read_dataset, write_dataset
from workbench.app.nn.dataset_builder import DatasetBuilder, ProgressCallback

__all__ = [
    "DatasetBuilder",
    "ProgressCallback",
    "read_dataset",
    "write_dataset",
]
