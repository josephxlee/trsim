"""NN integration domain schema (plan/07 § 7.4).

Phase 6.1 — schema-only entry point. The actual data export / training
/ evaluation logic lives in ``workbench.app.nn`` (App layer); this
module only carries the frozen dataclasses that the App and UI layers
share to describe an NN dataset.

See :mod:`workbench.domain.nn.sample_spec` for the SampleSpec /
FieldSpec / DatasetVariant / DatasetMeta declarations.
"""

from __future__ import annotations

from workbench.domain.nn.sample_spec import (
    DatasetMeta,
    DatasetVariant,
    FieldSpec,
    SampleSpec,
)

__all__ = [
    "DatasetMeta",
    "DatasetVariant",
    "FieldSpec",
    "SampleSpec",
]
