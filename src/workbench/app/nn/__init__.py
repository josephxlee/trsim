"""NN integration App layer (plan/07 § 7.4).

Phase 6.3 lands the first concrete piece — :func:`write_dataset` /
:func:`read_dataset` for HDF5 dataset I/O. Higher-level orchestration
(DataExporter context object, DatasetBuilder, TrainerService,
NNEvaluator) layers on top in later sub-steps.
"""

from __future__ import annotations

from workbench.app.nn.data_exporter import read_dataset, write_dataset

__all__ = ["read_dataset", "write_dataset"]
