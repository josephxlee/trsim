"""Streaming DatasetBuilder for NN training data (plan/07 § 7.4.3).

Phase 6.4a — the App-layer orchestrator that sits between a Pipeline
probe hook (Phase 6.4b) and the on-disk HDF5 layout (Phase 6.3 /
:func:`workbench.app.nn.write_dataset`).

Lifecycle:

1. The caller instantiates :class:`DatasetBuilder` with a
   :class:`SampleSpec` + :class:`DatasetVariant` + output path.
2. The Pipeline / Step-1 wiring calls :meth:`append` once per
   captured sample (per frame, per probe). Each call validates the
   per-field record shape and dtype against the spec.
3. The optional ``progress_callback`` is invoked after every append
   with ``(n_appended, target_or_none)``. The Editor uses this to
   drive the progress bar.
4. The caller calls :meth:`finalize` when the scenario finishes (or
   :meth:`cancel` + :meth:`finalize` if the user aborts). Finalize
   stacks the per-field record lists into ``(N, *field.shape)``
   arrays and forwards to :func:`write_dataset`.

The builder lives entirely in App-layer memory until ``finalize`` —
this is fine for the MVP sample sizes (plan/07 § 7.4.3 ships
hundreds-to-thousands of samples per variant). Larger datasets can
swap the per-field lists for an HDF5 resizable-dataset path later
without changing the public API.

References:

- plan/07 § 7.4.3 — Automatic Dataset Builder.
- plan/07 § 7.4.4 — Dataset HDF5 layout (delegated to data_exporter).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from workbench.app.nn.data_exporter import write_dataset
from workbench.domain.nn.sample_spec import (
    DatasetMeta,
    DatasetVariant,
    FieldSpec,
    SampleSpec,
)

ProgressCallback = Callable[[int, int | None], None]
"""Signature ``callback(n_appended, target_or_None)`` (plan/07 § 7.4.3).

``target`` is the caller-supplied expected sample count for the
progress bar. ``None`` means "open-ended"; the Editor displays the
current count instead of a percentage.
"""


def _validate_record(
    record: Mapping[str, NDArray[np.generic]],
    fields: tuple[FieldSpec, ...],
    kind: str,
    sample_index: int,
) -> None:
    declared = {f.name for f in fields}
    supplied = set(record.keys())
    missing = declared - supplied
    if missing:
        msg = f"sample {sample_index}: {kind} missing fields declared in spec: {sorted(missing)}"
        raise ValueError(msg)
    extra = supplied - declared
    if extra:
        msg = f"sample {sample_index}: {kind} contains undeclared fields: {sorted(extra)}"
        raise ValueError(msg)
    for f_ in fields:
        arr = record[f_.name]
        if arr.shape != f_.shape:
            msg = (
                f"sample {sample_index}: {kind}.{f_.name} shape "
                f"{arr.shape} does not match spec.shape {f_.shape}"
            )
            raise ValueError(msg)
        if str(arr.dtype) != f_.dtype:
            msg = (
                f"sample {sample_index}: {kind}.{f_.name} dtype "
                f"{arr.dtype} does not match spec dtype {f_.dtype!r}"
            )
            raise ValueError(msg)


class DatasetBuilder:
    """Stream samples into per-field lists; finalize writes one HDF5.

    Attributes:
        spec: SampleSpec the builder collects against.
        variant: DatasetVariant tag persisted in the file.
        dataset_id: Stable identifier for the resulting file.
        output_path: HDF5 path the finalised dataset is written to.
        target_samples: Optional expected count fed to the progress
            callback. ``None`` for open-ended runs (e.g. "build until
            the user clicks Stop").

    Raises:
        ValueError: If ``dataset_id`` or ``output_path`` is empty.
    """

    def __init__(
        self,
        *,
        spec: SampleSpec,
        variant: DatasetVariant,
        dataset_id: str,
        output_path: Path | str,
        target_samples: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        if not dataset_id:
            msg = "DatasetBuilder.dataset_id must be a non-empty string"
            raise ValueError(msg)
        path_obj = Path(output_path)
        if path_obj == Path():
            msg = "DatasetBuilder.output_path must be a non-empty path"
            raise ValueError(msg)
        if target_samples is not None and target_samples < 0:
            msg = f"target_samples must be >= 0 or None, got {target_samples}"
            raise ValueError(msg)

        self.spec = spec
        self.variant = variant
        self.dataset_id = dataset_id
        self.output_path = path_obj
        self.target_samples = target_samples
        self._progress_callback = progress_callback

        self._inputs: dict[str, list[NDArray[np.generic]]] = {f.name: [] for f in spec.inputs}
        self._labels: dict[str, list[NDArray[np.generic]]] = {f.name: [] for f in spec.labels}
        self._cancelled = False
        self._finalised = False

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    @property
    def n_appended(self) -> int:
        """Number of samples appended so far."""
        # Every list grows in lockstep — pick any input field.
        if not self.spec.inputs:
            return 0
        return len(self._inputs[self.spec.inputs[0].name])

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    @property
    def is_finalised(self) -> bool:
        return self._finalised

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(
        self,
        inputs: Mapping[str, NDArray[np.generic]],
        labels: Mapping[str, NDArray[np.generic]],
    ) -> None:
        """Append one sample.

        Args:
            inputs: Mapping ``field_name -> ndarray`` with shape =
                ``field.shape`` (no leading sample axis) and dtype
                matching ``field.dtype``. One entry per
                ``spec.inputs`` field.
            labels: Same contract for ``spec.labels``.

        Raises:
            RuntimeError: If the builder is already finalised or
                cancelled.
            ValueError: For missing / extra fields, wrong shape,
                wrong dtype on the per-sample record.
        """
        if self._finalised:
            msg = "DatasetBuilder.append called after finalize"
            raise RuntimeError(msg)
        if self._cancelled:
            msg = "DatasetBuilder.append called after cancel"
            raise RuntimeError(msg)

        idx = self.n_appended
        _validate_record(inputs, self.spec.inputs, "inputs", idx)
        _validate_record(labels, self.spec.labels, "labels", idx)

        for f_ in self.spec.inputs:
            self._inputs[f_.name].append(inputs[f_.name])
        for f_ in self.spec.labels:
            self._labels[f_.name].append(labels[f_.name])

        if self._progress_callback is not None:
            self._progress_callback(self.n_appended, self.target_samples)

    def cancel(self) -> None:
        """Mark the builder as cancelled.

        Subsequent ``append`` calls raise; ``finalize`` still works
        and writes the partial sample set that was already appended.
        Idempotent.
        """
        self._cancelled = True

    # ------------------------------------------------------------------
    # Finalisation
    # ------------------------------------------------------------------

    def finalize(
        self,
        *,
        scenarios: tuple[str, ...] = (),
        created_at_iso: str = "",
        extra: Mapping[str, str] | None = None,
    ) -> DatasetMeta:
        """Stack the per-field lists and write the HDF5 file.

        Args:
            scenarios: Scenario IDs that contributed samples (recorded
                in DatasetMeta.scenarios).
            created_at_iso: ISO-8601 timestamp string. Empty by default.
            extra: Optional free-form string key/value extras (job_id,
                git_hash, user notes).

        Returns:
            The :class:`DatasetMeta` actually written to disk.

        Raises:
            RuntimeError: If called twice on the same instance.
        """
        if self._finalised:
            msg = "DatasetBuilder.finalize called twice"
            raise RuntimeError(msg)

        n = self.n_appended
        meta = DatasetMeta(
            dataset_id=self.dataset_id,
            spec=self.spec,
            variant=self.variant,
            total_samples=n,
            created_at_iso=created_at_iso,
            scenarios=scenarios,
            extra=dict(extra or {}),
        )

        inputs_arr: dict[str, NDArray[np.generic]] = {
            f_.name: _stack_records(self._inputs[f_.name], f_, n) for f_ in self.spec.inputs
        }
        labels_arr: dict[str, NDArray[np.generic]] = {
            f_.name: _stack_records(self._labels[f_.name], f_, n) for f_ in self.spec.labels
        }

        write_dataset(self.output_path, meta, inputs_arr, labels_arr)
        self._finalised = True
        return meta


def _stack_records(
    records: list[NDArray[np.generic]],
    field: FieldSpec,
    expected_n: int,
) -> NDArray[np.generic]:
    """Stack ``records`` into one ``(N, *field.shape)`` array.

    Empty record list returns an empty array of the right shape +
    dtype so downstream HDF5 write can size the dataset correctly.
    """
    if expected_n == 0:
        return np.empty((0, *field.shape), dtype=np.dtype(field.dtype))
    return np.stack(records, axis=0)
