"""Unit tests for app.bundle_service (Phase 3 D1, plan/10 § 10.11)."""

from __future__ import annotations

import tarfile
from pathlib import Path

import pytest

from workbench.app.bundle_service import (
    BUNDLE_MANIFEST_FILENAME,
    RUN_BUNDLE_SUFFIX,
    SCENARIO_BUNDLE_SUFFIX,
    BundleManifest,
    pack_run_bundle,
    pack_scenario_bundle,
    read_bundle_manifest,
    unpack_bundle,
)


def _write_scenario_source(root: Path) -> Path:
    """Build a minimal bundle source layout (scenario + resources)."""
    root.mkdir(parents=True, exist_ok=True)
    sc = root / "scenario" / "B_demo"
    sc.mkdir(parents=True, exist_ok=True)
    (sc / "scenario.toml").write_text('id = "B_demo"\n', encoding="utf-8")
    res = root / "resources" / "maps" / "demo_map"
    res.mkdir(parents=True, exist_ok=True)
    (res / "map.toml").write_text('id = "demo_map"\n', encoding="utf-8")
    return root


# ---------------------------------------------------------------------
# pack_scenario_bundle
# ---------------------------------------------------------------------


def test_pack_scenario_bundle_writes_targz_with_manifest(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    out = tmp_path / "demo.scnbundle"
    written = pack_scenario_bundle(src, out, creator="Test Author")
    assert written == out.resolve()
    assert out.is_file()
    with tarfile.open(out, mode="r:gz") as tf:
        names = set(tf.getnames())
    assert BUNDLE_MANIFEST_FILENAME in names
    assert "scenario/B_demo/scenario.toml" in names
    assert "resources/maps/demo_map/map.toml" in names


def test_pack_scenario_bundle_rejects_wrong_suffix(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    with pytest.raises(ValueError, match=SCENARIO_BUNDLE_SUFFIX):
        pack_scenario_bundle(src, tmp_path / "demo.zip")


def test_pack_scenario_bundle_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"source_dir does not exist"):
        pack_scenario_bundle(tmp_path / "ghost", tmp_path / "x.scnbundle")


def test_pack_scenario_bundle_rejects_file_as_source(tmp_path: Path) -> None:
    f = tmp_path / "f.txt"
    f.write_text("hi", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        pack_scenario_bundle(f, tmp_path / "x.scnbundle")


def test_pack_scenario_bundle_auto_generates_manifest_kind_scenario(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    bundle = pack_scenario_bundle(src, tmp_path / "demo.scnbundle", creator="Alice")
    manifest = read_bundle_manifest(bundle)
    assert manifest.kind == "scenario"
    assert manifest.creator == "Alice"
    assert manifest.workbench_version  # non-empty
    assert manifest.created_iso.endswith("Z")  # UTC tag


def test_pack_scenario_bundle_overrides_source_manifest(tmp_path: Path) -> None:
    """If the source dir contains a manifest.toml, our auto-generated
    one wins (plan/10 § 10.11.4)."""
    src = _write_scenario_source(tmp_path / "src")
    (src / BUNDLE_MANIFEST_FILENAME).write_text('forbidden = "yes"', encoding="utf-8")
    bundle = pack_scenario_bundle(src, tmp_path / "demo.scnbundle")
    manifest = read_bundle_manifest(bundle)
    assert manifest.kind == "scenario"
    # The user-provided manifest must not have leaked into the archive
    # — we'd see a TOMLDecodeError or an unrecognised field if it did.
    assert "forbidden" not in manifest.extra


# ---------------------------------------------------------------------
# pack_run_bundle
# ---------------------------------------------------------------------


def test_pack_run_bundle_uses_run_kind(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    (src / "run").mkdir()
    (src / "run" / "manifest.json").write_text("{}", encoding="utf-8")
    bundle = pack_run_bundle(src, tmp_path / "demo.runbundle", creator="Bob")
    manifest = read_bundle_manifest(bundle)
    assert manifest.kind == "run"
    assert manifest.creator == "Bob"


def test_pack_run_bundle_rejects_wrong_suffix(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    with pytest.raises(ValueError, match=RUN_BUNDLE_SUFFIX):
        pack_run_bundle(src, tmp_path / "demo.scnbundle")


# ---------------------------------------------------------------------
# unpack_bundle
# ---------------------------------------------------------------------


def test_pack_then_unpack_round_trip(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    bundle = pack_scenario_bundle(src, tmp_path / "demo.scnbundle")
    target = tmp_path / "unpacked"
    out = unpack_bundle(bundle, target)
    assert out == target.resolve()
    assert (target / BUNDLE_MANIFEST_FILENAME).is_file()
    assert (target / "scenario" / "B_demo" / "scenario.toml").is_file()
    assert (target / "resources" / "maps" / "demo_map" / "map.toml").is_file()


def test_unpack_bundle_rejects_existing_target(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    bundle = pack_scenario_bundle(src, tmp_path / "demo.scnbundle")
    existing = tmp_path / "already"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        unpack_bundle(bundle, existing)


def test_unpack_bundle_rejects_archive_without_manifest(tmp_path: Path) -> None:
    bad = tmp_path / "no_manifest.scnbundle"
    with tarfile.open(bad, mode="w:gz") as tf:
        info = tarfile.TarInfo(name="junk.txt")
        info.size = 2
        tf.addfile(info, fileobj=_BytesBuffer(b"hi"))
    with pytest.raises(ValueError, match=BUNDLE_MANIFEST_FILENAME):
        unpack_bundle(bad, tmp_path / "target")


def test_unpack_bundle_rejects_tar_slip_entry(tmp_path: Path) -> None:
    """An entry whose name resolves outside target_dir must be rejected
    before extraction (tar-slip defence, mirrors zip-slip in package_io).
    """
    bad = tmp_path / "evil.scnbundle"
    with tarfile.open(bad, mode="w:gz") as tf:
        # Manifest entry — required so we get past the manifest check.
        manifest_body = (
            b'kind = "scenario"\n'
            b'created_iso = "2026-05-13T00:00:00Z"\n'
            b'workbench_version = "0.0.0"\n'
            b'creator = ""\n'
        )
        info = tarfile.TarInfo(name=BUNDLE_MANIFEST_FILENAME)
        info.size = len(manifest_body)
        tf.addfile(info, fileobj=_BytesBuffer(manifest_body))
        # Tar-slip entry.
        evil = tarfile.TarInfo(name="../escape.txt")
        evil.size = 4
        tf.addfile(evil, fileobj=_BytesBuffer(b"pwnd"))
    with pytest.raises(ValueError, match=r"tar-slip"):
        unpack_bundle(bad, tmp_path / "target")
    assert not (tmp_path / "target").exists()


def test_unpack_bundle_rejects_absolute_path_entry(tmp_path: Path) -> None:
    """Tar entries starting with '/' are rejected before any resolve()."""
    bad = tmp_path / "abs.scnbundle"
    with tarfile.open(bad, mode="w:gz") as tf:
        manifest_body = (
            b'kind = "scenario"\n'
            b'created_iso = "2026-05-13T00:00:00Z"\n'
            b'workbench_version = "0.0.0"\n'
        )
        info = tarfile.TarInfo(name=BUNDLE_MANIFEST_FILENAME)
        info.size = len(manifest_body)
        tf.addfile(info, fileobj=_BytesBuffer(manifest_body))
        abs_entry = tarfile.TarInfo(name="/etc/passwd")
        abs_entry.size = 1
        tf.addfile(abs_entry, fileobj=_BytesBuffer(b"x"))
    with pytest.raises(ValueError, match=r"unsafe name"):
        unpack_bundle(bad, tmp_path / "target")


# ---------------------------------------------------------------------
# read_bundle_manifest
# ---------------------------------------------------------------------


def test_read_bundle_manifest_returns_dataclass(tmp_path: Path) -> None:
    src = _write_scenario_source(tmp_path / "src")
    bundle = pack_scenario_bundle(src, tmp_path / "demo.scnbundle", creator="C")
    manifest = read_bundle_manifest(bundle)
    assert isinstance(manifest, BundleManifest)
    assert manifest.kind == "scenario"


def test_read_bundle_manifest_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_bundle_manifest(tmp_path / "ghost.scnbundle")


def test_read_bundle_manifest_rejects_invalid_kind(tmp_path: Path) -> None:
    bad = tmp_path / "bad_kind.scnbundle"
    with tarfile.open(bad, mode="w:gz") as tf:
        body = (
            b'kind = "rocket"\ncreated_iso = "2026-05-13T00:00:00Z"\nworkbench_version = "0.0.0"\n'
        )
        info = tarfile.TarInfo(name=BUNDLE_MANIFEST_FILENAME)
        info.size = len(body)
        tf.addfile(info, fileobj=_BytesBuffer(body))
    with pytest.raises(ValueError, match=r"kind must be"):
        read_bundle_manifest(bad)


# ---------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------


class _BytesBuffer:
    """Minimal file-like wrapper for tarfile.addfile."""

    def __init__(self, data: bytes) -> None:
        self._data = data
        self._pos = 0

    def read(self, n: int = -1) -> bytes:
        if n < 0 or n > len(self._data) - self._pos:
            chunk = self._data[self._pos :]
            self._pos = len(self._data)
            return chunk
        chunk = self._data[self._pos : self._pos + n]
        self._pos += n
        return chunk
