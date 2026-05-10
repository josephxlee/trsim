"""Golden Dataset format + loader (Phase 5.1, plan/04 § 4.3 / plan/05).

Every analytical or literature-based regression check stores its
expected values in a small JSON file under ``tests/physics/golden/``.
This module defines:

- :class:`GoldenDatasetMeta` - top-level header (id, source, units,
  tolerance defaults).
- :class:`GoldenSample` - one (input, expected_output) record.
- :class:`GoldenDataset` - container of meta + samples with a
  ``load(path)`` / ``save(path)`` round-trip.

The on-disk schema is intentionally minimal. Real per-category
references (Skolnik radar equation tables, ITU-R P.838 rain attenuation
coefficients, NIMA TR8350.2 ECEF, etc.) ship as separate JSON files
under ``tests/physics/golden/<category>.json`` and load through this
module.

Design notes:

- Frozen + slots dataclasses so a parametrised pytest case can pass
  samples by reference without aliasing surprises.
- ``tolerance`` is *advisory*; individual tests pick whichever of
  ``rtol``/``atol`` they need. The dataclass holds both so a single
  golden file can be reused by tests with different precision needs.
- :meth:`GoldenDataset.save` writes UTF-8 JSON with sorted keys for
  reproducible diffs (CLAUDE.md § 5 - signed commits, no churn).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class GoldenDatasetMeta:
    """Top-level header of a golden dataset file.

    Attributes:
        dataset_id: Stable dot-namespaced id (``"radar.equation.snr"``).
        source: Free-form citation
            (``"Skolnik Introduction to Radar Systems 3rd ed., Eq 1.6"``).
        units: Per-field unit hints (``{"range_m": "m", "snr_db": "dB"}``).
        rtol: Default relative tolerance for ``math.isclose`` users.
        atol: Default absolute tolerance.
        notes: Free-form remarks (test author hints, derivation steps).

    Raises:
        ValueError: If ``dataset_id`` is empty.
    """

    dataset_id: str
    source: str = ""
    units: Mapping[str, str] = field(default_factory=dict)
    rtol: float = 1e-9
    atol: float = 0.0
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.dataset_id:
            msg = "GoldenDatasetMeta.dataset_id must be a non-empty string"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class GoldenSample:
    """One (inputs, expected) record inside a golden dataset.

    Attributes:
        case_id: Optional human label (``"baseline_2km"``, ``"edge_horizon"``).
        inputs: Dict of arbitrary scalars / strings the test feeds to
            its function under test.
        expected: Dict of expected outputs the test compares against.

    Raises:
        ValueError: If ``case_id`` is empty.
    """

    case_id: str
    inputs: Mapping[str, Any]
    expected: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.case_id:
            msg = "GoldenSample.case_id must be a non-empty string"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class GoldenDataset:
    """Header + ordered tuple of samples.

    Use :meth:`load` to read a JSON file from
    ``tests/physics/golden/<category>.json`` and :meth:`save` to write
    one back during reference regeneration.
    """

    meta: GoldenDatasetMeta
    samples: tuple[GoldenSample, ...] = ()

    @classmethod
    def load(cls, path: Path | str) -> GoldenDataset:
        """Read a golden dataset JSON file from disk."""
        path_obj = Path(path)
        with path_obj.open("r", encoding="utf-8") as handle:
            blob: Mapping[str, Any] = json.load(handle)

        meta_blob = blob.get("meta")
        if not isinstance(meta_blob, Mapping):
            msg = f"{path_obj}: 'meta' is missing or not an object"
            raise ValueError(msg)
        meta = GoldenDatasetMeta(
            dataset_id=str(meta_blob["dataset_id"]),
            source=str(meta_blob.get("source", "")),
            units=dict(meta_blob.get("units", {})),
            rtol=float(meta_blob.get("rtol", 1e-9)),
            atol=float(meta_blob.get("atol", 0.0)),
            notes=str(meta_blob.get("notes", "")),
        )

        samples_blob = blob.get("samples", [])
        if not isinstance(samples_blob, list):
            msg = f"{path_obj}: 'samples' must be a JSON array"
            raise ValueError(msg)
        samples = tuple(
            GoldenSample(
                case_id=str(s["case_id"]),
                inputs=dict(s.get("inputs", {})),
                expected=dict(s.get("expected", {})),
            )
            for s in samples_blob
        )
        return cls(meta=meta, samples=samples)

    def save(self, path: Path | str) -> None:
        """Write this dataset to ``path`` as UTF-8 JSON, sorted keys."""
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        blob: dict[str, Any] = {
            "meta": {
                "dataset_id": self.meta.dataset_id,
                "source": self.meta.source,
                "units": dict(self.meta.units),
                "rtol": self.meta.rtol,
                "atol": self.meta.atol,
                "notes": self.meta.notes,
            },
            "samples": [
                {
                    "case_id": s.case_id,
                    "inputs": dict(s.inputs),
                    "expected": dict(s.expected),
                }
                for s in self.samples
            ],
        }
        with path_obj.open("w", encoding="utf-8") as handle:
            json.dump(blob, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")

    def case(self, case_id: str) -> GoldenSample:
        """Return the sample whose ``case_id`` matches ``case_id``."""
        for sample in self.samples:
            if sample.case_id == case_id:
                return sample
        msg = f"no sample with case_id={case_id!r} in dataset {self.meta.dataset_id!r}"
        raise KeyError(msg)
