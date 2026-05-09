"""Run manifest persistence (plan/10 § 10.9.3, plan/04 § 4.3 Phase 3).

Phase 3.4 — minimum viable Run Manifest. Records who ran what, with
which resource versions (content hashes), what the outcome was, and
when. Disk format is JSON for stdlib portability — TOML write would
need ``tomli_w`` (optional sdk extra), and the manifest is
machine-only data so the more rigid JSON shape is fine.

Layout (`runs/<run_id>/manifest.json`):

```
{
  "run_id": "...",
  "scenario_id": "...",
  "resource_refs": {
    "map":     "sha256:...",
    "radar":   "sha256:...",
    "targets": ["sha256:...", "sha256:..."]
  },
  "termination_reason": "completed",
  "sim_t_start_s": 0.0,
  "sim_t_end_s": 60.0,
  "wall_t_start_iso": "...",
  "wall_t_end_iso": "...",
  "n_lineage_commands": 17,
  "metadata": {...optional dict, set by caller...}
}
```
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from workbench.domain.types import RunTerminationReason


@dataclass(frozen=True, slots=True)
class ResourceRefs:
    """Content hashes pinning a Run to specific resource bytes
    (plan/10 § 10.9.3, v0.20).

    Attributes:
        map_hash: ``sha256:<hex>`` of the Map resource manifest.
        radar_hash: Radar platform manifest.
        target_hashes: Tuple of Target manifests.
    """

    map_hash: str
    radar_hash: str
    target_hashes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunManifest:
    """Top-level Run record.

    Attributes:
        run_id: Workspace-unique identifier.
        scenario_id: Source Scenario id.
        resource_refs: Content hashes of every dereferenced resource.
        termination_reason: Why the run ended.
        sim_t_start_s: Sim time at start (typically 0).
        sim_t_end_s: Sim time at end.
        wall_t_start_iso: ISO-8601 wall-clock start (UTC).
        wall_t_end_iso: ISO-8601 wall-clock end.
        n_lineage_commands: Count of CommandBus lineage entries during
            the run (the lineage payload itself goes to a separate
            file at MVP+alpha).
        metadata: Free-form dict for caller annotations.

    Raises:
        ValueError: For empty ids / negative time ranges.
    """

    run_id: str
    scenario_id: str
    resource_refs: ResourceRefs
    termination_reason: RunTerminationReason
    sim_t_start_s: float = 0.0
    sim_t_end_s: float = 0.0
    wall_t_start_iso: str = ""
    wall_t_end_iso: str = ""
    n_lineage_commands: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id:
            msg = "run_id must be a non-empty string"
            raise ValueError(msg)
        if not self.scenario_id:
            msg = "scenario_id must be a non-empty string"
            raise ValueError(msg)
        if self.sim_t_start_s < 0.0:
            msg = f"sim_t_start_s must be >= 0, got {self.sim_t_start_s}"
            raise ValueError(msg)
        if self.sim_t_end_s < self.sim_t_start_s:
            msg = (
                f"sim_t_end_s ({self.sim_t_end_s}) must be >= sim_t_start_s ({self.sim_t_start_s})"
            )
            raise ValueError(msg)
        if self.n_lineage_commands < 0:
            msg = f"n_lineage_commands must be >= 0, got {self.n_lineage_commands}"
            raise ValueError(msg)


# ---------------------------------------------------------------------
# JSON serialisation
# ---------------------------------------------------------------------


def _manifest_to_dict(manifest: RunManifest) -> dict[str, Any]:
    return {
        "run_id": manifest.run_id,
        "scenario_id": manifest.scenario_id,
        "resource_refs": {
            "map": manifest.resource_refs.map_hash,
            "radar": manifest.resource_refs.radar_hash,
            "targets": list(manifest.resource_refs.target_hashes),
        },
        "termination_reason": manifest.termination_reason.value,
        "sim_t_start_s": manifest.sim_t_start_s,
        "sim_t_end_s": manifest.sim_t_end_s,
        "wall_t_start_iso": manifest.wall_t_start_iso,
        "wall_t_end_iso": manifest.wall_t_end_iso,
        "n_lineage_commands": manifest.n_lineage_commands,
        "metadata": dict(manifest.metadata),
    }


def _dict_to_manifest(data: dict[str, Any]) -> RunManifest:
    refs_data = data["resource_refs"]
    refs = ResourceRefs(
        map_hash=refs_data["map"],
        radar_hash=refs_data["radar"],
        target_hashes=tuple(refs_data["targets"]),
    )
    return RunManifest(
        run_id=data["run_id"],
        scenario_id=data["scenario_id"],
        resource_refs=refs,
        termination_reason=RunTerminationReason(data["termination_reason"]),
        sim_t_start_s=float(data.get("sim_t_start_s", 0.0)),
        sim_t_end_s=float(data.get("sim_t_end_s", 0.0)),
        wall_t_start_iso=str(data.get("wall_t_start_iso", "")),
        wall_t_end_iso=str(data.get("wall_t_end_iso", "")),
        n_lineage_commands=int(data.get("n_lineage_commands", 0)),
        metadata=dict(data.get("metadata", {})),
    )


def save_manifest(manifest: RunManifest, path: Path | str) -> None:
    """Write ``manifest`` to ``path`` as JSON (UTF-8, indent=2)."""
    Path(path).write_text(
        json.dumps(_manifest_to_dict(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_manifest(path: Path | str) -> RunManifest:
    """Read a manifest written by :func:`save_manifest`."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return _dict_to_manifest(data)


def utc_now_iso() -> str:
    """Helper: ISO-8601 UTC timestamp with 'Z' suffix.

    Used by the App / CLI to fill ``wall_t_start_iso`` /
    ``wall_t_end_iso``. Captured here so tests can monkey-patch a
    deterministic clock.
    """
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
