"""NN Mode panels (Phase 4.11, plan/07 + plan/05 § 5.1 principle 6).

The Simulator workspace exposes two top-level Modes - DSP (default
performance verification) and NN Development. NN Mode is itself a
2-step workflow (plan/07):

- Step 1: Dataset Builder. Pick a Scenario, drive a probe, write a
  HDF5 / Parquet dataset.
- Step 2: NN Evaluation. Pick a dataset + a NN plugin, run inference,
  inspect the 4-error diagnostic.

Phase 4.11 ships placeholder widgets for both steps so the menu hook
(View > Mode > NN Development, Phase 4.12) has something to mount.
"""

from __future__ import annotations

from workbench.ui.simulator.nn_mode.step1_dataset import (
    Step1DatasetPanel,
)
from workbench.ui.simulator.nn_mode.step2_eval import (
    ERROR_CATEGORIES,
    Step2EvalPanel,
)

__all__ = ["ERROR_CATEGORIES", "Step1DatasetPanel", "Step2EvalPanel"]
