"""HDF5 dataset write / read for NN training data (plan/07 § 7.4.4).

Phase 6.3 — minimum viable on-disk layout for the Dataset Builder
(plan/07 § 7.4.3). The exporter writes a single HDF5 file per
:class:`DatasetMeta`; the reader pulls it back as ``(meta, inputs,
labels)`` so the App layer can hand it to a downstream trainer or
to the Step 2 evaluator.

File layout (plan/07 § 7.4.4):

::

    dataset.h5
    ├── root attrs:
    │   ├── meta_json      (JSON: dataset_id / total_samples / etc.)
    │   ├── schema_json    (JSON: SampleSpec serialisation)
    │   └── variant_json   (JSON: DatasetVariant serialisation)
    ├── inputs/<field>     (dataset, N x field.shape, field.dtype)
    └── labels/<field>     (dataset, N x field.shape, field.dtype)

The MVP is one-shot: build the full per-field array first, then call
:func:`write_dataset`. Streaming append (Editor's progress bar)
becomes :func:`DatasetBuilder` (Phase 6.4) layered on top.

Validation contract:

- Every field declared in ``meta.spec.inputs`` must appear in the
  ``inputs`` mapping with the right shape ``(meta.total_samples,
  *field.shape)`` and dtype.
- Same for ``labels``. Any mismatch raises :class:`ValueError`
  before HDF5 file creation — partial files are not produced.

References:

- plan/07 § 7.4.4 — Dataset HDF5 layout.
- plan/07 § 7.4.5a — Variant manifest tag.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import h5py
import numpy as np
from numpy.typing import NDArray

from workbench.domain.nn.sample_spec import (
    DatasetMeta,
    DatasetVariant,
    FieldSpec,
    SampleSpec,
)


def _field_to_dict(field: FieldSpec) -> dict[str, object]:
    return {
        "name": field.name,
        "shape": list(field.shape),
        "dtype": field.dtype,
        "description": field.description,
    }


def _spec_to_dict(spec: SampleSpec) -> dict[str, object]:
    return {
        "spec_id": spec.spec_id,
        "probe_stage": spec.probe_stage,
        "inputs": [_field_to_dict(f) for f in spec.inputs],
        "labels": [_field_to_dict(f) for f in spec.labels],
        "description": spec.description,
    }


def _variant_to_dict(variant: DatasetVariant) -> dict[str, object]:
    return {
        "variant_id": variant.variant_id,
        "sea_state": variant.sea_state,
        "attitude_on": variant.attitude_on,
        "sidelobe_on": variant.sidelobe_on,
        "description": variant.description,
    }


def _meta_to_dict(meta: DatasetMeta) -> dict[str, object]:
    return {
        "dataset_id": meta.dataset_id,
        "total_samples": meta.total_samples,
        "created_at_iso": meta.created_at_iso,
        "scenarios": list(meta.scenarios),
        "extra": dict(meta.extra),
    }


def _field_from_dict(raw: Mapping[str, object]) -> FieldSpec:
    shape_raw = raw["shape"]
    if not isinstance(shape_raw, list):
        msg = f"FieldSpec.shape must be a list, got {type(shape_raw).__name__}"
        raise ValueError(msg)
    return FieldSpec(
        name=str(raw["name"]),
        shape=tuple(int(d) for d in shape_raw),
        dtype=str(raw["dtype"]),
        description=str(raw.get("description", "")),
    )


def _spec_from_dict(raw: Mapping[str, object]) -> SampleSpec:
    inputs_raw = raw["inputs"]
    labels_raw = raw["labels"]
    if not isinstance(inputs_raw, list):
        msg = f"SampleSpec.inputs must be a list, got {type(inputs_raw).__name__}"
        raise ValueError(msg)
    if not isinstance(labels_raw, list):
        msg = f"SampleSpec.labels must be a list, got {type(labels_raw).__name__}"
        raise ValueError(msg)
    return SampleSpec(
        spec_id=str(raw["spec_id"]),
        probe_stage=str(raw["probe_stage"]),
        inputs=tuple(_field_from_dict(f) for f in inputs_raw),
        labels=tuple(_field_from_dict(f) for f in labels_raw),
        description=str(raw.get("description", "")),
    )


def _as_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        msg = f"{field_name} must be an integer, got {type(value).__name__}"
        raise ValueError(msg)
    return value


def _variant_from_dict(raw: Mapping[str, object]) -> DatasetVariant:
    return DatasetVariant(
        variant_id=str(raw["variant_id"]),
        sea_state=_as_int(raw["sea_state"], "sea_state"),
        attitude_on=bool(raw["attitude_on"]),
        sidelobe_on=bool(raw["sidelobe_on"]),
        description=str(raw.get("description", "")),
    )


def _meta_from_dict(
    raw: Mapping[str, object],
    spec: SampleSpec,
    variant: DatasetVariant,
) -> DatasetMeta:
    scenarios_raw = raw.get("scenarios", [])
    if not isinstance(scenarios_raw, list):
        msg = f"DatasetMeta.scenarios must be a list, got {type(scenarios_raw).__name__}"
        raise ValueError(msg)
    extra_raw = raw.get("extra", {})
    if not isinstance(extra_raw, dict):
        msg = f"DatasetMeta.extra must be a dict, got {type(extra_raw).__name__}"
        raise ValueError(msg)
    return DatasetMeta(
        dataset_id=str(raw["dataset_id"]),
        spec=spec,
        variant=variant,
        total_samples=_as_int(raw["total_samples"], "total_samples"),
        created_at_iso=str(raw.get("created_at_iso", "")),
        scenarios=tuple(str(s) for s in scenarios_raw),
        extra={str(k): str(v) for k, v in extra_raw.items()},
    )


def _validate_arrays(
    meta: DatasetMeta,
    arrays: Mapping[str, NDArray[np.generic]],
    fields: tuple[FieldSpec, ...],
    kind: str,
) -> None:
    declared = {f.name for f in fields}
    supplied = set(arrays.keys())
    missing = declared - supplied
    if missing:
        msg = f"{kind} missing fields declared in spec: {sorted(missing)}"
        raise ValueError(msg)
    extra = supplied - declared
    if extra:
        msg = f"{kind} contains undeclared fields: {sorted(extra)}"
        raise ValueError(msg)
    for f_ in fields:
        arr = arrays[f_.name]
        expected_shape = (meta.total_samples, *f_.shape)
        if arr.shape != expected_shape:
            msg = (
                f"{kind}.{f_.name} shape {arr.shape} does not match "
                f"(total_samples, *spec.shape) = {expected_shape}"
            )
            raise ValueError(msg)
        if str(arr.dtype) != f_.dtype:
            msg = f"{kind}.{f_.name} dtype {arr.dtype} does not match spec dtype {f_.dtype!r}"
            raise ValueError(msg)


def write_dataset(
    path: Path | str,
    meta: DatasetMeta,
    inputs: Mapping[str, NDArray[np.generic]],
    labels: Mapping[str, NDArray[np.generic]],
) -> None:
    """Persist ``meta`` + ``inputs`` + ``labels`` to ``path`` as HDF5.

    Validates field coverage / shape / dtype against ``meta.spec``
    before opening the file so a failed write does not leave a
    partial file on disk.

    Args:
        path: Output HDF5 path. Parent directory must already exist.
        meta: Dataset metadata; ``meta.total_samples`` is the leading
            axis of every array in ``inputs`` and ``labels``.
        inputs: ``field_name -> ndarray``; one entry per
            ``meta.spec.inputs`` field, shape ``(total_samples,
            *field.shape)``, dtype matching ``field.dtype``.
        labels: Same contract for ``meta.spec.labels``.

    Raises:
        ValueError: For missing / extra fields, wrong shape, wrong
            dtype.
    """
    _validate_arrays(meta, inputs, meta.spec.inputs, "inputs")
    _validate_arrays(meta, labels, meta.spec.labels, "labels")

    path_obj = Path(path)
    with h5py.File(path_obj, "w") as h:
        h.attrs["meta_json"] = json.dumps(_meta_to_dict(meta), sort_keys=True)
        h.attrs["schema_json"] = json.dumps(_spec_to_dict(meta.spec), sort_keys=True)
        h.attrs["variant_json"] = json.dumps(_variant_to_dict(meta.variant), sort_keys=True)

        inputs_group = h.create_group("inputs")
        for f_ in meta.spec.inputs:
            inputs_group.create_dataset(f_.name, data=inputs[f_.name])
        labels_group = h.create_group("labels")
        for f_ in meta.spec.labels:
            labels_group.create_dataset(f_.name, data=labels[f_.name])


def read_dataset(
    path: Path | str,
) -> tuple[DatasetMeta, dict[str, NDArray[np.generic]], dict[str, NDArray[np.generic]]]:
    """Read an HDF5 dataset previously written by :func:`write_dataset`.

    Args:
        path: HDF5 file path.

    Returns:
        ``(meta, inputs, labels)`` where ``inputs`` / ``labels`` are
        plain ``dict`` mappings of field name to numpy array.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If a required root attribute is missing.
    """
    path_obj = Path(path)
    with h5py.File(path_obj, "r") as h:
        try:
            meta_raw = json.loads(str(h.attrs["meta_json"]))
            schema_raw = json.loads(str(h.attrs["schema_json"]))
            variant_raw = json.loads(str(h.attrs["variant_json"]))
        except KeyError as exc:
            msg = f"{path_obj}: missing root attribute {exc}"
            raise ValueError(msg) from exc

        spec = _spec_from_dict(schema_raw)
        variant = _variant_from_dict(variant_raw)
        meta = _meta_from_dict(meta_raw, spec, variant)

        inputs: dict[str, NDArray[np.generic]] = {}
        for f_ in spec.inputs:
            inputs[f_.name] = np.asarray(h[f"inputs/{f_.name}"][...])
        labels: dict[str, NDArray[np.generic]] = {}
        for f_ in spec.labels:
            labels[f_.name] = np.asarray(h[f"labels/{f_.name}"][...])

    return meta, inputs, labels
