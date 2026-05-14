"""Unit tests for sdk.package_validator + sdk.resource_schemas (Phase 7 C8)."""

from __future__ import annotations

import pytest

from workbench.sdk.manifest import (
    CompatibilitySpec,
    PackageManifest,
    PackageMeta,
    PythonDeps,
)
from workbench.sdk.package_validator import (
    KNOWN_ENTRY_POINT_SLOTS,
    validate_entry_point_slots,
)
from workbench.sdk.resource_schemas import (
    MAP_REQUIRED_KEYS,
    RADAR_REQUIRED_KEYS,
    SCENARIO_REQUIRED_KEYS,
    TARGETS_REQUIRED_KEYS,
    known_resource_categories,
    validate_resource_toml_blob,
)


def _minimal_manifest(entry_points: dict[str, str] | None = None) -> PackageManifest:
    return PackageManifest(
        package=PackageMeta(
            package_id="demo",
            name="Demo",
            version="0.1.0",
            license="Apache-2.0",
        ),
        compatibility=CompatibilitySpec(trsim_min_version="0.40.0"),
        dependencies={},
        entry_points=entry_points or {},
        python=PythonDeps(extra_requires=()),
    )


# ---------------------------------------------------------------------
# package_validator
# ---------------------------------------------------------------------


def test_validate_entry_point_slots_passes_for_all_known_slots() -> None:
    """Manifest using every curated slot must produce zero issues."""
    eps = {slot: f"target_{i}" for i, slot in enumerate(sorted(KNOWN_ENTRY_POINT_SLOTS))}
    manifest = _minimal_manifest(eps)
    assert validate_entry_point_slots(manifest) == ()


def test_validate_entry_point_slots_flags_unknown_slot() -> None:
    """A typo'd slot ('trsim.trackers') -> one issue string."""
    manifest = _minimal_manifest({"trsim.trackers": "plugins/x.py:Wrong"})
    issues = validate_entry_point_slots(manifest)
    assert len(issues) == 1
    assert "trsim.trackers" in issues[0]
    assert "known slots" in issues[0]


def test_validate_entry_point_slots_sorts_issues() -> None:
    """Multiple unknown slots come back sorted alphabetically so the
    output is deterministic across runs.
    """
    manifest = _minimal_manifest(
        {
            "zzz.unknown": "a:A",
            "aaa.unknown": "b:B",
        }
    )
    issues = validate_entry_point_slots(manifest)
    assert len(issues) == 2
    assert "aaa.unknown" in issues[0]
    assert "zzz.unknown" in issues[1]


def test_known_entry_point_slots_includes_canonical_dlc_slots() -> None:
    """Sanity-lock: the canonical slots from plan/17 § 17.2.4 are
    all in :data:`KNOWN_ENTRY_POINT_SLOTS`.
    """
    canonical = {
        "trsim.tracker",
        "trsim.pairing",
        "trsim.ui.panels",
        "trsim.resources.maps",
        "trsim.resources.radars",
        "trsim.resources.targets",
        "trsim.resources.scenarios",
    }
    assert canonical <= KNOWN_ENTRY_POINT_SLOTS


# ---------------------------------------------------------------------
# resource_schemas
# ---------------------------------------------------------------------


def test_known_resource_categories_lists_four_canonical_buckets() -> None:
    assert set(known_resource_categories()) == {
        "maps",
        "radars",
        "targets",
        "scenarios",
    }


@pytest.mark.parametrize(
    "category",
    ["maps", "radars", "targets", "scenarios"],
)
def test_validate_resource_blob_passes_when_required_keys_present(category: str) -> None:
    """Each category accepts a blob containing every required key."""
    issues = validate_resource_toml_blob(category, {"id": "demo"})  # type: ignore[arg-type]
    assert issues == ()


def test_validate_resource_blob_reports_missing_id() -> None:
    """Empty blob fails with the canonical "missing key" message."""
    issues = validate_resource_toml_blob("maps", {})
    assert len(issues) == 1
    assert "id" in issues[0]


def test_validate_resource_blob_rejects_unknown_category() -> None:
    with pytest.raises(ValueError, match=r"unknown resource category"):
        validate_resource_toml_blob("widgets", {"id": "x"})  # type: ignore[arg-type]


def test_required_keys_constants_are_frozensets() -> None:
    """Constants are immutable so callers can't accidentally mutate them."""
    for keys in (
        MAP_REQUIRED_KEYS,
        RADAR_REQUIRED_KEYS,
        TARGETS_REQUIRED_KEYS,
        SCENARIO_REQUIRED_KEYS,
    ):
        assert isinstance(keys, frozenset)
        assert "id" in keys
