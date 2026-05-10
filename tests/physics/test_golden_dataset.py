"""Unit tests for the golden-dataset loader (Phase 5.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.physics.golden_dataset import (
    GoldenDataset,
    GoldenDatasetMeta,
    GoldenSample,
)

_GOLDEN_DIR = Path(__file__).parent / "golden"


def test_meta_rejects_empty_dataset_id() -> None:
    with pytest.raises(ValueError, match=r"dataset_id"):
        GoldenDatasetMeta(dataset_id="")


def test_sample_rejects_empty_case_id() -> None:
    with pytest.raises(ValueError, match=r"case_id"):
        GoldenSample(case_id="", inputs={}, expected={})


def test_meta_default_tolerances_are_strict() -> None:
    meta = GoldenDatasetMeta(dataset_id="x.y.z")
    assert meta.rtol == 1e-9
    assert meta.atol == 0.0


def test_load_existing_radar_equation_sample() -> None:
    ds = GoldenDataset.load(_GOLDEN_DIR / "radar_equation_snr.json")
    assert ds.meta.dataset_id == "radar.equation.snr.sample"
    assert ds.meta.units["snr_linear"] == "linear"
    assert len(ds.samples) == 2
    baseline = ds.case("baseline")
    assert baseline.inputs["range_m"] == 10000.0
    assert baseline.expected["snr_linear"] == pytest.approx(41.95107293247016)


def test_case_lookup_missing_id_raises_keyerror() -> None:
    ds = GoldenDataset.load(_GOLDEN_DIR / "radar_equation_snr.json")
    with pytest.raises(KeyError, match=r"missing"):
        ds.case("missing")


def test_save_and_load_round_trip(tmp_path: Path) -> None:
    original = GoldenDataset(
        meta=GoldenDatasetMeta(
            dataset_id="alpha.beta",
            source="paper.X eq 7",
            units={"x": "m"},
            rtol=1e-6,
            atol=1e-12,
            notes="round-trip",
        ),
        samples=(
            GoldenSample(
                case_id="case_one",
                inputs={"x": 1.0, "label": "a"},
                expected={"y": 2.5},
            ),
            GoldenSample(
                case_id="case_two",
                inputs={"x": 2.0},
                expected={"y": 5.0, "z": -1.0},
            ),
        ),
    )
    out_path = tmp_path / "round.json"
    original.save(out_path)
    reloaded = GoldenDataset.load(out_path)
    assert reloaded.meta == original.meta
    assert reloaded.samples == original.samples


def test_load_rejects_missing_meta(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text('{"samples": []}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"'meta'"):
        GoldenDataset.load(bad_path)


def test_load_rejects_non_list_samples(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text('{"meta": {"dataset_id": "x"}, "samples": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match=r"'samples'"):
        GoldenDataset.load(bad_path)


def test_save_uses_sorted_keys_for_reproducible_diffs(tmp_path: Path) -> None:
    ds = GoldenDataset(
        meta=GoldenDatasetMeta(dataset_id="x", source="src"),
        samples=(GoldenSample(case_id="c", inputs={"b": 1, "a": 2}, expected={"d": 0}),),
    )
    out_path = tmp_path / "sorted.json"
    ds.save(out_path)
    content = out_path.read_text(encoding="utf-8")
    # keys sorted -> "atol" appears before "dataset_id" alphabetically.
    assert content.index('"atol"') < content.index('"dataset_id"')
    # Sample input keys also sorted alphabetically when JSON round-trips.
    assert content.index('"a"') < content.index('"b"')
