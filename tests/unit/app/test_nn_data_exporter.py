"""DataExporter HDF5 IO tests (Phase 6.3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import read_dataset, write_dataset
from workbench.domain.nn import (
    DatasetMeta,
    DatasetVariant,
    FieldSpec,
    SampleSpec,
)


def _pairing_meta(n: int = 8) -> DatasetMeta:
    """Build a Pairing-shaped DatasetMeta sized to N samples."""
    spec = SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (4,), "complex64", "Up-sweep beats"),
            FieldSpec("down_beats", (4,), "complex64", "Down-sweep beats"),
        ),
        labels=(FieldSpec("pair_indices", (4,), "int32", "GT pair indices"),),
    )
    variant = DatasetVariant(variant_id="A", sea_state=0)
    return DatasetMeta(
        dataset_id="pairing_variant_A_test",
        spec=spec,
        variant=variant,
        total_samples=n,
        created_at_iso="2026-05-11T13:00:00Z",
        scenarios=("baseline",),
        extra={"job_id": "job_0001"},
    )


def _matching_arrays(
    meta: DatasetMeta, rng: np.random.Generator
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """Build arrays that satisfy the meta's spec contract."""
    inputs = {
        "up_beats": rng.standard_normal((meta.total_samples, 4)).astype(np.complex64),
        "down_beats": rng.standard_normal((meta.total_samples, 4)).astype(np.complex64),
    }
    labels = {
        "pair_indices": rng.integers(0, 4, size=(meta.total_samples, 4)).astype(np.int32),
    }
    return inputs, labels


# ---------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------


def test_write_then_read_round_trip_preserves_arrays(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=8)
    inputs, labels = _matching_arrays(meta, rng)

    out = tmp_path / "pairing_A.h5"
    write_dataset(out, meta, inputs, labels)

    _meta_back, inputs_back, labels_back = read_dataset(out)

    # Arrays survive the round-trip bit-for-bit.
    np.testing.assert_array_equal(inputs_back["up_beats"], inputs["up_beats"])
    np.testing.assert_array_equal(inputs_back["down_beats"], inputs["down_beats"])
    np.testing.assert_array_equal(labels_back["pair_indices"], labels["pair_indices"])


def test_write_then_read_preserves_meta(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=8)
    inputs, labels = _matching_arrays(meta, rng)

    out = tmp_path / "pairing_A.h5"
    write_dataset(out, meta, inputs, labels)
    meta_back, _, _ = read_dataset(out)

    assert meta_back.dataset_id == meta.dataset_id
    assert meta_back.total_samples == meta.total_samples
    assert meta_back.created_at_iso == meta.created_at_iso
    assert meta_back.scenarios == meta.scenarios
    assert dict(meta_back.extra) == dict(meta.extra)


def test_write_then_read_preserves_spec(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)

    out = tmp_path / "pairing_A.h5"
    write_dataset(out, meta, inputs, labels)
    meta_back, _, _ = read_dataset(out)

    assert meta_back.spec.spec_id == "pairing"
    assert meta_back.spec.probe_stage == "pairing"
    assert tuple(f.name for f in meta_back.spec.inputs) == ("up_beats", "down_beats")
    assert tuple(f.dtype for f in meta_back.spec.inputs) == ("complex64", "complex64")
    assert meta_back.spec.inputs[0].shape == (4,)
    assert meta_back.spec.labels[0].name == "pair_indices"
    assert meta_back.spec.labels[0].dtype == "int32"


def test_write_then_read_preserves_variant(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    # Tweak variant to non-defaults so we exercise serialisation.
    meta = DatasetMeta(
        dataset_id=meta.dataset_id,
        spec=meta.spec,
        variant=DatasetVariant(variant_id="D", sea_state=3, attitude_on=True, sidelobe_on=True),
        total_samples=meta.total_samples,
    )
    inputs, labels = _matching_arrays(meta, rng)

    out = tmp_path / "pairing_D.h5"
    write_dataset(out, meta, inputs, labels)
    meta_back, _, _ = read_dataset(out)

    assert meta_back.variant.variant_id == "D"
    assert meta_back.variant.sea_state == 3
    assert meta_back.variant.attitude_on is True
    assert meta_back.variant.sidelobe_on is True


def test_zero_samples_round_trip(tmp_path: Path) -> None:
    """Empty datasets (from cancelled builds) must still round-trip."""
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=0)
    inputs, labels = _matching_arrays(meta, rng)
    out = tmp_path / "empty.h5"
    write_dataset(out, meta, inputs, labels)
    meta_back, inputs_back, labels_back = read_dataset(out)
    assert meta_back.total_samples == 0
    assert inputs_back["up_beats"].shape == (0, 4)
    assert labels_back["pair_indices"].shape == (0, 4)


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_write_rejects_missing_input_field(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)
    del inputs["down_beats"]
    with pytest.raises(ValueError, match=r"inputs missing fields"):
        write_dataset(tmp_path / "bad.h5", meta, inputs, labels)


def test_write_rejects_extra_input_field(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)
    inputs["surprise"] = np.zeros((4, 4), dtype=np.complex64)
    with pytest.raises(ValueError, match=r"undeclared fields"):
        write_dataset(tmp_path / "bad.h5", meta, inputs, labels)


def test_write_rejects_wrong_shape(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)
    inputs["up_beats"] = np.zeros((4, 8), dtype=np.complex64)  # wrong inner shape
    with pytest.raises(ValueError, match=r"shape"):
        write_dataset(tmp_path / "bad.h5", meta, inputs, labels)


def test_write_rejects_wrong_dtype(tmp_path: Path) -> None:
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)
    # complex128 instead of complex64
    inputs["up_beats"] = inputs["up_beats"].astype(np.complex128)
    with pytest.raises(ValueError, match=r"dtype"):
        write_dataset(tmp_path / "bad.h5", meta, inputs, labels)


def test_write_does_not_create_file_on_validation_failure(tmp_path: Path) -> None:
    """Validation runs before the HDF5 file is opened — no partial
    file remains if the call raises.
    """
    rng = np.random.default_rng(seed=42)
    meta = _pairing_meta(n=4)
    inputs, labels = _matching_arrays(meta, rng)
    inputs["up_beats"] = np.zeros((4, 8), dtype=np.complex64)  # wrong shape
    out = tmp_path / "no_partial.h5"
    with pytest.raises(ValueError):
        write_dataset(out, meta, inputs, labels)
    assert not out.exists()
