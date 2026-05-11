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
- Phase 6 후속 :class:`PairingScenarioSpec` + :class:`PipelineRunner`
  + :func:`default_pairing_scenario` — scenario-driven Pairing dataset
  build (plan/07 § 7.4.3).
"""

from __future__ import annotations

from workbench.app.nn.data_exporter import read_dataset, write_dataset
from workbench.app.nn.dataset_builder import DatasetBuilder, ProgressCallback
from workbench.app.nn.evaluator import NNEvalResult, evaluate, pairing_loss
from workbench.app.nn.numpy_mlp import (
    Activation as NumpyMLPActivation,
)
from workbench.app.nn.numpy_mlp import (
    NumpyMLPParams,
    flatten_inputs,
    flatten_labels,
    mse_loss,
)
from workbench.app.nn.numpy_mlp import (
    forward as numpy_mlp_forward,
)
from workbench.app.nn.numpy_mlp import (
    init_params as numpy_mlp_init_params,
)
from workbench.app.nn.numpy_mlp import (
    train_one_epoch as numpy_mlp_train_one_epoch,
)
from workbench.app.nn.pairing_nn import NumpyPairingNN
from workbench.app.nn.pipeline_runner import (
    PairingScenarioSpec,
    PipelineRunner,
    default_pairing_scenario,
)
from workbench.app.nn.trainer import (
    EpochCallback,
    TrainerService,
    TrainingBackend,
    TrainingJob,
    TrainingResult,
)
from workbench.app.nn.variant_runner import (
    VariantBuildPlan,
    VariantBuildResult,
    VariantBuildRunner,
    VariantProgressCallback,
    standard_pairing_build_plans,
)

__all__ = [
    "DatasetBuilder",
    "EpochCallback",
    "NNEvalResult",
    "NumpyMLPActivation",
    "NumpyMLPParams",
    "NumpyPairingNN",
    "PairingScenarioSpec",
    "PipelineRunner",
    "ProgressCallback",
    "TrainerService",
    "TrainingBackend",
    "TrainingJob",
    "TrainingResult",
    "VariantBuildPlan",
    "VariantBuildResult",
    "VariantBuildRunner",
    "VariantProgressCallback",
    "default_pairing_scenario",
    "evaluate",
    "flatten_inputs",
    "flatten_labels",
    "mse_loss",
    "numpy_mlp_forward",
    "numpy_mlp_init_params",
    "numpy_mlp_train_one_epoch",
    "pairing_loss",
    "read_dataset",
    "standard_pairing_build_plans",
    "write_dataset",
]
