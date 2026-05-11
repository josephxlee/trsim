"""DatasetBuilder tests (Phase 6.4a)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import DatasetBuilder, read_dataset
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec


def _pairing_spec() -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (4,), "complex64", "Up-sweep beats"),
            FieldSpec("down_beats", (4,), "complex64", "Down-sweep beats"),
        ),
        labels=(FieldSpec("pair_indices", (4,), "int32", "GT pair indices"),),
    )


def _builder(
    tmp_path: Path,
    *,
    target: int | None = None,
    progress_cb: object = None,
) -> DatasetBuilder:
    return DatasetBuilder(
        spec=_pairing_spec(),
        variant=DatasetVariant(variant_id="A"),
        dataset_id="pairing_variant_A",
        output_path=tmp_path / "pairing.h5",
        target_samples=target,
        progress_callback=progress_cb,  # type: ignore[arg-type]
    )


def _record(rng: np.random.Generator) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    inputs = {
        "up_beats": rng.standard_normal(4).astype(np.complex64),
        "down_beats": rng.standard_normal(4).astype(np.complex64),
    }
    labels = {"pair_indices": rng.integers(0, 4, size=4).astype(np.int32)}
    return inputs, labels


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


def test_append_then_finalize_round_trips_through_hdf5(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    builder = _builder(tmp_path)
    records = [_record(rng) for _ in range(6)]
    for inputs, labels in records:
        builder.append(inputs, labels)
    meta = builder.finalize(scenarios=("baseline",), extra={"job_id": "job_99"})

    assert meta.total_samples == 6
    assert builder.n_appended == 6
    assert builder.is_finalised is True

    # Cross-check by reading the file back.
    meta_back, inputs_back, labels_back = read_dataset(tmp_path / "pairing.h5")
    assert meta_back.total_samples == 6
    assert meta_back.scenarios == ("baseline",)
    assert dict(meta_back.extra) == {"job_id": "job_99"}
    # Last appended sample matches the last array on disk.
    np.testing.assert_array_equal(inputs_back["up_beats"][-1], records[-1][0]["up_beats"])
    np.testing.assert_array_equal(labels_back["pair_indices"][-1], records[-1][1]["pair_indices"])


def test_finalize_zero_samples_writes_empty_dataset(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    meta = builder.finalize()
    assert meta.total_samples == 0
    meta_back, inputs_back, labels_back = read_dataset(tmp_path / "pairing.h5")
    assert meta_back.total_samples == 0
    assert inputs_back["up_beats"].shape == (0, 4)
    assert labels_back["pair_indices"].shape == (0, 4)


def test_progress_callback_called_per_append(tmp_path: Path) -> None:
    calls: list[tuple[int, int | None]] = []

    def cb(n: int, target: int | None) -> None:
        calls.append((n, target))

    rng = np.random.default_rng(seed=1)
    builder = _builder(tmp_path, target=10, progress_cb=cb)
    for _ in range(3):
        inputs, labels = _record(rng)
        builder.append(inputs, labels)
    assert calls == [(1, 10), (2, 10), (3, 10)]


# ---------------------------------------------------------------------
# Cancel / finalize twice
# ---------------------------------------------------------------------


def test_cancel_then_finalize_writes_partial(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=7)
    builder = _builder(tmp_path)
    for _ in range(2):
        inputs, labels = _record(rng)
        builder.append(inputs, labels)
    builder.cancel()
    assert builder.is_cancelled is True
    meta = builder.finalize()
    assert meta.total_samples == 2
    # Subsequent append must reject.
    with pytest.raises(RuntimeError, match=r"after cancel|after finalize"):
        builder.append(*_record(rng))


def test_append_after_finalize_rejects(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=8)
    builder = _builder(tmp_path)
    builder.append(*_record(rng))
    builder.finalize()
    with pytest.raises(RuntimeError, match=r"after finalize"):
        builder.append(*_record(rng))


def test_finalize_twice_rejects(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    builder.finalize()
    with pytest.raises(RuntimeError, match=r"twice"):
        builder.finalize()


# ---------------------------------------------------------------------
# Per-record validation
# ---------------------------------------------------------------------


def test_append_rejects_missing_input_field(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=9)
    builder = _builder(tmp_path)
    inputs, labels = _record(rng)
    del inputs["down_beats"]
    with pytest.raises(ValueError, match=r"inputs missing fields"):
        builder.append(inputs, labels)


def test_append_rejects_wrong_shape(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=9)
    builder = _builder(tmp_path)
    inputs, labels = _record(rng)
    inputs["up_beats"] = np.zeros(8, dtype=np.complex64)  # wrong shape (8,) vs (4,)
    with pytest.raises(ValueError, match=r"shape"):
        builder.append(inputs, labels)


def test_append_rejects_wrong_dtype(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=9)
    builder = _builder(tmp_path)
    inputs, labels = _record(rng)
    inputs["up_beats"] = inputs["up_beats"].astype(np.complex128)
    with pytest.raises(ValueError, match=r"dtype"):
        builder.append(inputs, labels)


# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_constructor_rejects_empty_dataset_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"dataset_id"):
        DatasetBuilder(
            spec=_pairing_spec(),
            variant=DatasetVariant(variant_id="A"),
            dataset_id="",
            output_path=tmp_path / "x.h5",
        )


def test_constructor_rejects_negative_target_samples(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"target_samples"):
        DatasetBuilder(
            spec=_pairing_spec(),
            variant=DatasetVariant(variant_id="A"),
            dataset_id="x",
            output_path=tmp_path / "x.h5",
            target_samples=-1,
        )
