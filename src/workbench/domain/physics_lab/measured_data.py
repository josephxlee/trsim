"""Measured Data references + I/O (PL-9.2a, plan/19 § 19.9.1).

The Physics Lab Library's "Measured Data" category points at CSV or
HDF5 files the user has dropped into a known root directory (typically
``~/.trsim/physics_lab/measured/``). The domain layer holds the
metadata (header columns, row count, free-form description); the App
or UI layer loads the actual numerical arrays via
:func:`load_measured_csv` / :func:`load_measured_hdf5` when needed.

CSV format (plan/19 § 19.9.1):

::

    aspect_angle_deg,rcs_m2
    0.0, 25.4
    1.0, 18.7
    ...

The first row is the header. Column names map to the
:attr:`MeasuredDataset.columns` tuple.

HDF5 format: a flat container with one dataset per column. Column
names are the HDF5 dataset names.

A small companion TOML sidecar (``<file>.toml``) is optional and
carries human-readable metadata: ``description``, ``source``,
``license``, optional per-column unit table. Files without the sidecar
get a minimal :class:`MeasuredDataset` derived from the header alone.
"""

from __future__ import annotations

import csv
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import h5py
import numpy as np
from numpy.typing import NDArray

MeasuredFormat = Literal["csv", "hdf5"]


@dataclass(frozen=True, slots=True)
class MeasuredDataset:
    """One measurement file the Library can offer to the user.

    Attributes:
        dataset_id: Library label. Defaults to the file stem when the
            factory helpers populate it.
        file_path: Absolute path to the CSV or HDF5 file.
        file_format: ``"csv"`` or ``"hdf5"``.
        columns: Ordered tuple of column names (CSV header or HDF5
            dataset names).
        n_rows: Number of data rows. ``-1`` when unknown (HDF5 files
            with ragged column lengths).
        description: Free-form text.
        source: Original publication / measurement source.
        license: License text.
        units: Optional per-column unit mapping.

    Raises:
        ValueError: Empty dataset_id / columns / file_format invalid.
    """

    dataset_id: str
    file_path: Path
    file_format: MeasuredFormat
    columns: tuple[str, ...]
    n_rows: int = -1
    description: str = ""
    source: str = ""
    license: str = ""
    units: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dataset_id:
            msg = "MeasuredDataset.dataset_id must be non-empty"
            raise ValueError(msg)
        if self.file_format not in ("csv", "hdf5"):
            msg = f"MeasuredDataset.file_format must be 'csv' or 'hdf5', got {self.file_format!r}"
            raise ValueError(msg)
        if not self.columns:
            msg = "MeasuredDataset.columns must not be empty"
            raise ValueError(msg)


# ---------------------------------------------------------------------
# CSV inspection + load
# ---------------------------------------------------------------------


def _read_csv_header(path: Path) -> tuple[str, ...]:
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration as exc:
            msg = f"MeasuredDataset CSV {path.name}: empty file"
            raise ValueError(msg) from exc
    return tuple(col.strip() for col in header)


def _count_csv_rows(path: Path) -> int:
    """Count data rows (excludes the header)."""
    with path.open(encoding="utf-8", newline="") as f:
        return sum(1 for _ in f) - 1


def inspect_csv(
    path: Path | str,
    *,
    dataset_id: str | None = None,
) -> MeasuredDataset:
    """Read CSV header + row count, build a :class:`MeasuredDataset`.

    Reads the sibling ``<file>.toml`` sidecar for description / source
    / license / units when present.
    """
    p = Path(path)
    columns = _read_csv_header(p)
    n_rows = _count_csv_rows(p)
    meta = _read_sidecar_metadata(p)
    return MeasuredDataset(
        dataset_id=dataset_id or str(meta.get("dataset_id", p.stem)),
        file_path=p,
        file_format="csv",
        columns=columns,
        n_rows=n_rows,
        description=str(meta.get("description", "")),
        source=str(meta.get("source", "")),
        license=str(meta.get("license", "")),
        units=_coerce_units(meta.get("units", {})),
    )


def load_measured_csv(dataset: MeasuredDataset) -> NDArray[np.float64]:
    """Load the full CSV into an ``(n_rows, n_cols)`` float64 array.

    Skips the header row + loads every column as ``float64``. Columns
    that fail to parse become ``NaN`` (numpy default).
    """
    if dataset.file_format != "csv":
        msg = f"load_measured_csv: dataset is {dataset.file_format!r}, not 'csv'"
        raise ValueError(msg)
    arr = np.genfromtxt(
        dataset.file_path,
        delimiter=",",
        skip_header=1,
        dtype=np.float64,
    )
    if arr.ndim == 1:
        # Single-row file -> reshape to (1, n_cols).
        arr = arr.reshape(1, -1)
    return arr


# ---------------------------------------------------------------------
# HDF5 inspection + load
# ---------------------------------------------------------------------


def inspect_hdf5(
    path: Path | str,
    *,
    dataset_id: str | None = None,
) -> MeasuredDataset:
    """Read HDF5 root-level dataset names + sizes."""
    p = Path(path)
    with h5py.File(p, "r") as f:
        cols: list[str] = []
        sizes: list[int] = []
        for name in f:
            obj = f[name]
            if isinstance(obj, h5py.Dataset):
                cols.append(name)
                sizes.append(int(obj.shape[0]) if obj.ndim >= 1 else 1)
    n_rows = sizes[0] if sizes and all(s == sizes[0] for s in sizes) else -1
    meta = _read_sidecar_metadata(p)
    return MeasuredDataset(
        dataset_id=dataset_id or str(meta.get("dataset_id", p.stem)),
        file_path=p,
        file_format="hdf5",
        columns=tuple(cols),
        n_rows=n_rows,
        description=str(meta.get("description", "")),
        source=str(meta.get("source", "")),
        license=str(meta.get("license", "")),
        units=_coerce_units(meta.get("units", {})),
    )


def _coerce_units(raw: object) -> dict[str, str]:
    """Best-effort conversion of a TOML-loaded units map to dict[str,str]."""
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items()}


def load_measured_hdf5(
    dataset: MeasuredDataset,
    column: str,
) -> NDArray[np.float64]:
    """Load one named column from an HDF5 dataset."""
    if dataset.file_format != "hdf5":
        msg = f"load_measured_hdf5: dataset is {dataset.file_format!r}, not 'hdf5'"
        raise ValueError(msg)
    if column not in dataset.columns:
        msg = f"load_measured_hdf5: column {column!r} not in {dataset.columns}"
        raise ValueError(msg)
    with h5py.File(dataset.file_path, "r") as f:
        return np.asarray(f[column][...], dtype=np.float64)


# ---------------------------------------------------------------------
# Sidecar TOML
# ---------------------------------------------------------------------


def _read_sidecar_metadata(file_path: Path) -> dict[str, object]:
    """Read ``<file>.toml`` next to a CSV/HDF5; return ``{}`` if absent."""
    sidecar = file_path.with_suffix(file_path.suffix + ".toml")
    if not sidecar.is_file():
        return {}
    raw = sidecar.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError):
        return {}


# ---------------------------------------------------------------------
# Directory scan
# ---------------------------------------------------------------------


def list_measured_datasets(root: Path | str) -> tuple[MeasuredDataset, ...]:
    """Scan ``root`` for ``*.csv`` / ``*.h5`` / ``*.hdf5`` files.

    Sorted by ``dataset_id``. Missing root + files that fail to parse
    are silently skipped — the UI surfaces parse failures via a status
    banner (not implemented in MVP).
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return ()
    out: list[MeasuredDataset] = []
    for csv_path in sorted(root_path.glob("*.csv")):
        try:
            out.append(inspect_csv(csv_path))
        except (OSError, ValueError):
            continue
    for h5_path in sorted(list(root_path.glob("*.h5")) + list(root_path.glob("*.hdf5"))):
        try:
            out.append(inspect_hdf5(h5_path))
        except (OSError, ValueError):
            continue
    return tuple(sorted(out, key=lambda d: d.dataset_id))
