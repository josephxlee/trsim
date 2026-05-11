"""NN dataset schema dataclasses (plan/07 § 7.4.4 / § 7.4.5a).

Phase 6.1 — minimum viable schema layer. Defines the frozen records
the App layer's DataExporter / DatasetBuilder (plan/07 § 7.4) and
the Editor's NN-mode Step 1 panel agree on:

- :class:`FieldSpec` — one input or label field (name, shape, dtype,
  description).
- :class:`SampleSpec` — a named template binding a probe stage to a
  list of input fields and a list of label fields (the "Pairing" /
  "Angle estimation" / etc. templates from plan/07 § 7.4.5).
- :class:`DatasetVariant` — physics-condition flags that separate a
  dataset file from its sibling variants (plan/07 § 7.4.5a "Pairing
  Variant 4종").
- :class:`DatasetMeta` — the on-disk metadata header (dataset_id,
  spec, variant, sample count) that DataExporter writes alongside
  the HDF5 arrays.

This module never touches HDF5 — it is pure schema. The actual
:mod:`workbench.app.nn.data_exporter` reads these dataclasses to
decide what fields to record and how to label the resulting file.

The dtype field is a plain string (``"complex64"`` / ``"float32"`` /
``"int32"`` / etc.) rather than a numpy dtype so the schema can round-
trip through TOML / JSON without an import dependency on numpy at
the domain layer. The App layer translates the string to ``np.dtype``
when materialising arrays.

References:

- plan/07 § 7.3 — NN Plugin Contract.
- plan/07 § 7.4 — Data Export pipeline.
- plan/07 § 7.4.4 — Dataset HDF5 layout.
- plan/07 § 7.4.5 — Wave-by-Wave template SampleSpec.
- plan/07 § 7.4.5a — Dataset Variant (4-tier physics-condition split).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Final

# String dtypes that the HDF5 exporter accepts. Kept as a string set so
# the schema layer has no numpy dependency. App layer translates these
# to np.dtype(...) when writing.
_ALLOWED_DTYPES: Final[frozenset[str]] = frozenset(
    {
        "bool",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "float16",
        "float32",
        "float64",
        "complex64",
        "complex128",
    }
)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """One input or label field declared in a :class:`SampleSpec`.

    Attributes:
        name: Unique identifier within its sample spec, lower_snake_case.
        shape: Per-sample shape as a tuple of positive integers. The
            leading sample-count axis is added by the exporter and is
            **not** included here. ``(4,)`` for a 4-channel phase
            vector, ``(2, 8)`` for a 2x8 matrix, ``()`` for a scalar.
        dtype: Dtype string accepted by numpy
            (``"complex64"`` / ``"float32"`` / ``"int32"`` / ...).
            Must be one of :data:`_ALLOWED_DTYPES`.
        description: Free-form note shown in the Editor's preview.

    Raises:
        ValueError: For empty name, non-positive shape entries,
            unknown dtype.
    """

    name: str
    shape: tuple[int, ...]
    dtype: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            msg = "FieldSpec.name must be a non-empty string"
            raise ValueError(msg)
        for dim in self.shape:
            if dim <= 0:
                msg = f"FieldSpec.shape entries must be > 0, got {self.shape}"
                raise ValueError(msg)
        if self.dtype not in _ALLOWED_DTYPES:
            msg = f"FieldSpec.dtype {self.dtype!r} not in allowed set {sorted(_ALLOWED_DTYPES)}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class SampleSpec:
    """Template binding a probe stage to a list of input + label fields.

    plan/07 § 7.4.5 ships a SampleSpec template per Wave; the Editor's
    NN-mode Step 1 panel lets the user pick one of those templates and
    optionally tweak it. The Dataset Builder runs the scenario, hooks
    the probe stage, and writes one record per frame into HDF5 using
    the field list below.

    Attributes:
        spec_id: Stable identifier (e.g. ``"pairing"``,
            ``"angle_estimation"``). Used by the dataset manifest.
        probe_stage: Pipeline stage that produces the records
            (``"pairing"`` / ``"angle_estimator"`` / ``"detector"`` /
            ``"tracker"`` / ``"classifier"``). The App layer maps this
            to the Pipeline stage hook.
        inputs: Tuple of :class:`FieldSpec`, ``len >= 1``. Order is
            stable — exporter writes datasets in this order.
        labels: Tuple of :class:`FieldSpec`, ``len >= 1``. Same order
            contract.
        description: Free-form note shown in the Editor.

    Raises:
        ValueError: For empty spec_id / probe_stage, empty inputs or
            labels, duplicate field names across the input + label
            tuples (HDF5 path must be unique).
    """

    spec_id: str
    probe_stage: str
    inputs: tuple[FieldSpec, ...]
    labels: tuple[FieldSpec, ...]
    description: str = ""

    def __post_init__(self) -> None:
        if not self.spec_id:
            msg = "SampleSpec.spec_id must be a non-empty string"
            raise ValueError(msg)
        if not self.probe_stage:
            msg = "SampleSpec.probe_stage must be a non-empty string"
            raise ValueError(msg)
        if not self.inputs:
            msg = "SampleSpec.inputs must contain at least one FieldSpec"
            raise ValueError(msg)
        if not self.labels:
            msg = "SampleSpec.labels must contain at least one FieldSpec"
            raise ValueError(msg)
        # HDF5 layout uses /inputs/<name> and /labels/<name> — names
        # cannot collide across the two groups for a given sample.
        seen: set[str] = set()
        for f_ in (*self.inputs, *self.labels):
            if f_.name in seen:
                msg = (
                    f"SampleSpec.{self.spec_id}: duplicate FieldSpec name "
                    f"{f_.name!r} across inputs + labels"
                )
                raise ValueError(msg)
            seen.add(f_.name)


@dataclass(frozen=True, slots=True)
class DatasetVariant:
    """Physics-condition flags separating a dataset from its siblings.

    plan/07 § 7.4.5a "Pairing Variant 4종" ships the canonical
    A (ideal) / B (attitude only) / C (sidelobe only) / D (full
    realistic) split. The exporter records the variant_id alongside
    the data so the manifest can recover the physics conditions later.

    Attributes:
        variant_id: Stable identifier (``"A"`` / ``"B"`` / ``"C"`` /
            ``"D"`` for the standard 4; any string for user-defined).
        sea_state: WMO sea state 0-9 (matches
            :class:`workbench.domain.map_resource.SeaSurface.sea_state`).
        attitude_on: ``True`` if platform attitude dynamics are
            enabled (yaw / pitch / roll integration).
        sidelobe_on: ``True`` if antenna sidelobes participate in the
            simulated return (matters for sidelobe-rich scenarios).
        description: Free-form note shown in the Editor.

    Raises:
        ValueError: For empty variant_id, sea_state outside [0, 9].
    """

    variant_id: str
    sea_state: int = 0
    attitude_on: bool = False
    sidelobe_on: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        if not self.variant_id:
            msg = "DatasetVariant.variant_id must be a non-empty string"
            raise ValueError(msg)
        if not 0 <= self.sea_state <= 9:
            msg = f"DatasetVariant.sea_state must be in [0, 9], got {self.sea_state}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DatasetMeta:
    """On-disk metadata header for one HDF5 dataset file.

    plan/07 § 7.4.4 places this in HDF5 root attrs as ``meta``. It
    accompanies the schema (FieldSpec list) and lets the Step 2 Eval
    panel show which Variant / Spec / scenario produced each file
    without re-loading the underlying arrays.

    Attributes:
        dataset_id: File-unique identifier
            (``"pairing_variant_A_2026-05-11"``).
        spec: :class:`SampleSpec` template the file was built from.
        variant: :class:`DatasetVariant` flags used during simulation.
        total_samples: Number of records in the file. ``>= 0`` — zero
            is allowed (empty file from a cancelled build).
        created_at_iso: ISO-8601 timestamp string (``""`` when not yet
            recorded; the exporter fills it on save).
        scenarios: Tuple of scenario IDs that contributed records.
        extra: Optional free-form key/value extras (job_id, git_hash,
            user notes). Values are strings to keep the on-disk
            schema TOML-friendly.

    Raises:
        ValueError: For empty dataset_id or ``total_samples < 0``.
    """

    dataset_id: str
    spec: SampleSpec
    variant: DatasetVariant
    total_samples: int = 0
    created_at_iso: str = ""
    scenarios: tuple[str, ...] = ()
    extra: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dataset_id:
            msg = "DatasetMeta.dataset_id must be a non-empty string"
            raise ValueError(msg)
        if self.total_samples < 0:
            msg = f"DatasetMeta.total_samples must be >= 0, got {self.total_samples}"
            raise ValueError(msg)
