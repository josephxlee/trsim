"""MeasuredDataset domain tests (PL-9.2a, plan/19 § 19.9.1)."""

from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np
import pytest

from workbench.domain.physics_lab import (
    MeasuredDataset,
    inspect_csv,
    inspect_hdf5,
    list_measured_datasets,
    load_measured_csv,
    load_measured_hdf5,
)


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _write_hdf5(path: Path, columns: dict[str, np.ndarray]) -> None:
    with h5py.File(path, "w") as f:
        for name, data in columns.items():
            f.create_dataset(name, data=data)


# ---------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------


def test_dataclass_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match=r"dataset_id must be non-empty"):
        MeasuredDataset(
            dataset_id="",
            file_path=Path("x.csv"),
            file_format="csv",
            columns=("a",),
        )


def test_dataclass_rejects_invalid_format() -> None:
    with pytest.raises(ValueError, match=r"file_format must be 'csv' or 'hdf5'"):
        MeasuredDataset(
            dataset_id="x",
            file_path=Path("x.bin"),
            file_format="bin",  # type: ignore[arg-type]
            columns=("a",),
        )


def test_dataclass_rejects_empty_columns() -> None:
    with pytest.raises(ValueError, match=r"columns must not be empty"):
        MeasuredDataset(
            dataset_id="x",
            file_path=Path("x.csv"),
            file_format="csv",
            columns=(),
        )


# ---------------------------------------------------------------------
# CSV
# ---------------------------------------------------------------------


def test_inspect_csv_reads_header_and_row_count(tmp_path: Path) -> None:
    path = tmp_path / "rcs.csv"
    _write_csv(
        path,
        "aspect_angle_deg,rcs_m2",
        ["0.0,25.4", "1.0,18.7", "2.0,12.3"],
    )
    ds = inspect_csv(path)
    assert ds.dataset_id == "rcs"
    assert ds.columns == ("aspect_angle_deg", "rcs_m2")
    assert ds.n_rows == 3
    assert ds.file_format == "csv"


def test_inspect_csv_overrides_dataset_id(tmp_path: Path) -> None:
    path = tmp_path / "rcs.csv"
    _write_csv(path, "a,b", ["1,2"])
    ds = inspect_csv(path, dataset_id="custom-id")
    assert ds.dataset_id == "custom-id"


def test_inspect_csv_reads_sidecar_metadata(tmp_path: Path) -> None:
    path = tmp_path / "rcs.csv"
    _write_csv(path, "a,b", ["1,2"])
    sidecar = tmp_path / "rcs.csv.toml"
    sidecar.write_text(
        'description = "Boeing 737 measurements"\n'
        'source = "Knott 1993 p.245"\n'
        'license = "Public domain"\n'
        '[units]\na = "deg"\nb = "m^2"\n',
        encoding="utf-8",
    )
    ds = inspect_csv(path)
    assert ds.description == "Boeing 737 measurements"
    assert ds.source == "Knott 1993 p.245"
    assert ds.license == "Public domain"
    assert ds.units == {"a": "deg", "b": "m^2"}


def test_inspect_csv_empty_file_raises(tmp_path: Path) -> None:
    path = tmp_path / "empty.csv"
    path.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match=r"empty file"):
        inspect_csv(path)


def test_load_measured_csv_returns_float_array(tmp_path: Path) -> None:
    path = tmp_path / "rcs.csv"
    _write_csv(path, "a,b", ["1.0,2.0", "3.0,4.0"])
    ds = inspect_csv(path)
    arr = load_measured_csv(ds)
    assert arr.shape == (2, 2)
    assert arr.dtype == np.float64
    assert arr[1, 1] == pytest.approx(4.0)


def test_load_measured_csv_rejects_hdf5_dataset(tmp_path: Path) -> None:
    path = tmp_path / "x.h5"
    _write_hdf5(path, {"a": np.array([1.0])})
    ds = inspect_hdf5(path)
    with pytest.raises(ValueError, match=r"not 'csv'"):
        load_measured_csv(ds)


# ---------------------------------------------------------------------
# HDF5
# ---------------------------------------------------------------------


def test_inspect_hdf5_reads_dataset_names(tmp_path: Path) -> None:
    path = tmp_path / "rcs.h5"
    _write_hdf5(
        path,
        {
            "angle": np.linspace(0.0, 360.0, 361),
            "rcs": np.zeros(361),
        },
    )
    ds = inspect_hdf5(path)
    assert ds.dataset_id == "rcs"
    assert set(ds.columns) == {"angle", "rcs"}
    assert ds.n_rows == 361
    assert ds.file_format == "hdf5"


def test_load_measured_hdf5_returns_column(tmp_path: Path) -> None:
    path = tmp_path / "x.h5"
    _write_hdf5(path, {"angle": np.array([0.0, 1.0, 2.0]), "rcs": np.array([10.0, 20.0, 30.0])})
    ds = inspect_hdf5(path)
    angle = load_measured_hdf5(ds, "angle")
    assert angle.shape == (3,)
    assert angle[2] == pytest.approx(2.0)


def test_load_measured_hdf5_rejects_unknown_column(tmp_path: Path) -> None:
    path = tmp_path / "x.h5"
    _write_hdf5(path, {"angle": np.array([0.0])})
    ds = inspect_hdf5(path)
    with pytest.raises(ValueError, match=r"column 'unknown' not in"):
        load_measured_hdf5(ds, "unknown")


def test_load_measured_hdf5_rejects_csv_dataset(tmp_path: Path) -> None:
    path = tmp_path / "x.csv"
    _write_csv(path, "a,b", ["1,2"])
    ds = inspect_csv(path)
    with pytest.raises(ValueError, match=r"not 'hdf5'"):
        load_measured_hdf5(ds, "a")


# ---------------------------------------------------------------------
# list_measured_datasets
# ---------------------------------------------------------------------


def test_list_returns_empty_when_root_missing(tmp_path: Path) -> None:
    assert list_measured_datasets(tmp_path / "no-such") == ()


def test_list_returns_empty_for_empty_dir(tmp_path: Path) -> None:
    assert list_measured_datasets(tmp_path) == ()


def test_list_returns_sorted_csv_and_hdf5(tmp_path: Path) -> None:
    _write_csv(tmp_path / "zulu.csv", "a,b", ["1,2"])
    _write_csv(tmp_path / "alpha.csv", "a,b", ["3,4"])
    _write_hdf5(tmp_path / "bravo.h5", {"a": np.array([1.0])})
    datasets = list_measured_datasets(tmp_path)
    ids = [d.dataset_id for d in datasets]
    assert ids == ["alpha", "bravo", "zulu"]


def test_list_skips_invalid_csv(tmp_path: Path) -> None:
    _write_csv(tmp_path / "good.csv", "a,b", ["1,2"])
    (tmp_path / "empty.csv").write_text("", encoding="utf-8")
    datasets = list_measured_datasets(tmp_path)
    assert [d.dataset_id for d in datasets] == ["good"]
