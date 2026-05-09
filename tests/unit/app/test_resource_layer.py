"""Unit tests for App resource layer: library + cache + scenario service (Phase 3.3)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workbench.app.resource_cache import (
    DEFAULT_CACHE_CAPACITY,
    ResourceCache,
)
from workbench.app.resource_library import (
    RESOURCE_KINDS,
    ResourceEntry,
    ResourceLibrary,
    compute_content_hash,
)
from workbench.app.scenario_service import ScenarioService, ScenarioSummary

# ---------------------------------------------------------------------
# compute_content_hash
# ---------------------------------------------------------------------


def test_compute_content_hash_format() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "x.toml"
        p.write_text("hello\n", encoding="utf-8")
        h = compute_content_hash(p)
    assert h.startswith("sha256:")
    # sha256 hex is 64 chars; with prefix -> 71.
    assert len(h) == len("sha256:") + 64


def test_compute_content_hash_changes_with_content() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        a = Path(tmp) / "a.toml"
        b = Path(tmp) / "b.toml"
        a.write_text("foo\n", encoding="utf-8")
        b.write_text("bar\n", encoding="utf-8")
        assert compute_content_hash(a) != compute_content_hash(b)


# ---------------------------------------------------------------------
# ResourceLibrary
# ---------------------------------------------------------------------


def _build_library_tree(root: Path) -> None:
    (root / "maps").mkdir()
    (root / "radars").mkdir()
    (root / "targets").mkdir()
    (root / "maps" / "east_coast.toml").write_text(
        'id = "east_coast"\nkind = "map"\n', encoding="utf-8"
    )
    (root / "radars" / "fmcw_x.toml").write_text(
        'id = "fmcw_x"\nkind = "radar"\n', encoding="utf-8"
    )
    (root / "targets" / "f16.toml").write_text('id = "f16"\nkind = "target"\n', encoding="utf-8")


def test_resource_kinds_locked() -> None:
    assert RESOURCE_KINDS == ("maps", "radars", "targets")


def test_library_scan_indexes_each_kind() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_library_tree(root)
        lib = ResourceLibrary.scan(root)
        assert len(lib) == 3
        assert lib.has("maps", "east_coast")
        assert lib.has("radars", "fmcw_x")
        assert lib.has("targets", "f16")


def test_library_scan_skips_missing_subdirs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "maps").mkdir()
        (root / "maps" / "x.toml").write_text('id = "x"\n', encoding="utf-8")
        # No radars/ or targets/ subdir.
        lib = ResourceLibrary.scan(root)
        assert len(lib) == 1


def test_library_scan_root_missing_raises() -> None:
    with pytest.raises(FileNotFoundError, match=r"resource root"):
        ResourceLibrary.scan("/no/such/path/here_we_hope")


def test_library_get_known_entry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_library_tree(root)
        lib = ResourceLibrary.scan(root)
        entry = lib.get("maps", "east_coast")
        assert entry.kind == "maps"
        assert entry.resource_id == "east_coast"
        assert entry.content_hash.startswith("sha256:")


def test_library_get_missing_raises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        lib = ResourceLibrary.scan(tmp)
        with pytest.raises(KeyError, match=r"radars"):
            lib.get("radars", "missing")


def test_library_list_filtered_by_kind() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_library_tree(root)
        lib = ResourceLibrary.scan(root)
        targets = lib.list(kind="targets")
        assert len(targets) == 1
        assert targets[0].resource_id == "f16"


def test_library_resource_id_falls_back_to_filename() -> None:
    # No 'id' key in the TOML -> use filename stem.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "maps").mkdir()
        (root / "maps" / "auto_named.toml").write_text('kind = "map"\n', encoding="utf-8")
        lib = ResourceLibrary.scan(root)
        entry = lib.get("maps", "auto_named")
        assert entry.resource_id == "auto_named"


def test_library_add_replaces_existing() -> None:
    lib = ResourceLibrary(root=Path("/tmp"))
    e = ResourceEntry(
        kind="maps", resource_id="x", path=Path("/tmp/x.toml"), content_hash="sha256:00"
    )
    lib.add(e)
    assert lib.get("maps", "x") is e
    e2 = ResourceEntry(
        kind="maps", resource_id="x", path=Path("/tmp/x.toml"), content_hash="sha256:11"
    )
    lib.add(e2)
    assert lib.get("maps", "x") is e2


# ---------------------------------------------------------------------
# ResourceCache
# ---------------------------------------------------------------------


def test_cache_default_capacity() -> None:
    assert DEFAULT_CACHE_CAPACITY == 256


def test_cache_put_get() -> None:
    c = ResourceCache()
    c.put("sha256:aa", "obj_a")
    assert c.get("sha256:aa") == "obj_a"


def test_cache_has_and_contains() -> None:
    c = ResourceCache()
    c.put("sha256:aa", 1)
    assert c.has("sha256:aa")
    assert "sha256:aa" in c
    assert "sha256:bb" not in c


def test_cache_lru_eviction() -> None:
    c = ResourceCache(max_entries=2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)  # evicts "a"
    assert not c.has("a")
    assert c.has("b")
    assert c.has("c")


def test_cache_get_refreshes_lru() -> None:
    c = ResourceCache(max_entries=2)
    c.put("a", 1)
    c.put("b", 2)
    _ = c.get("a")  # refresh — "a" is now most recent
    c.put("c", 3)  # should evict "b" (oldest), not "a"
    assert c.has("a")
    assert not c.has("b")
    assert c.has("c")


def test_cache_get_missing_raises() -> None:
    c = ResourceCache()
    with pytest.raises(KeyError, match=r"no cached value"):
        c.get("missing")


def test_cache_put_empty_hash_rejected() -> None:
    with pytest.raises(ValueError, match=r"content_hash"):
        ResourceCache().put("", "x")


def test_cache_zero_capacity_rejected() -> None:
    with pytest.raises(ValueError, match=r"max_entries"):
        ResourceCache(max_entries=0)


def test_cache_clear() -> None:
    c = ResourceCache()
    c.put("a", 1)
    c.clear()
    assert len(c) == 0


# ---------------------------------------------------------------------
# ScenarioService
# ---------------------------------------------------------------------


def test_scenario_service_describe_resolves_hashes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_library_tree(root)
        lib = ResourceLibrary.scan(root)
        svc = ScenarioService(library=lib)
        summary = svc.describe(
            "test_scenario",
            map_id="east_coast",
            radar_id="fmcw_x",
            target_ids=("f16",),
        )
        assert isinstance(summary, ScenarioSummary)
        assert summary.scenario_id == "test_scenario"
        assert summary.map_hash.startswith("sha256:")
        assert summary.radar_hash.startswith("sha256:")
        assert len(summary.target_hashes) == 1
        assert summary.target_hashes[0].startswith("sha256:")


def test_scenario_service_describe_missing_raises() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _build_library_tree(root)
        svc = ScenarioService(library=ResourceLibrary.scan(root))
        with pytest.raises(KeyError):
            svc.describe("x", map_id="nonexistent", radar_id="fmcw_x", target_ids=())


def test_scenario_service_empty_id_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        svc = ScenarioService(library=ResourceLibrary.scan(tmp))
        with pytest.raises(ValueError, match=r"scenario_id"):
            svc.describe("", map_id="", radar_id="", target_ids=())
