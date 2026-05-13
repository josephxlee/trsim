"""Unit tests for io.package_io (Phase 7 DLC C1, plan/17 § 17.2.4)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from workbench.io.package_io import (
    MANIFEST_FILENAME,
    PACKAGE_SUFFIX,
    pack_package,
    read_manifest_from_package,
    unpack_package,
)

# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


_VALID_MANIFEST_TOML = """\
[package]
id = "demo-tracker"
name = "Demo Tracker"
version = "0.1.0"
license = "Apache-2.0"

[compatibility]
trsim_min_version = "0.40.0"

[python]
extra_requires = []

[entry_points]
"""


def _write_valid_source_dir(root: Path) -> Path:
    """Build a minimal source directory: manifest.toml + dummy resource."""
    root.mkdir(parents=True, exist_ok=True)
    (root / MANIFEST_FILENAME).write_text(_VALID_MANIFEST_TOML, encoding="utf-8")
    (root / "resources").mkdir()
    (root / "resources" / "maps").mkdir()
    (root / "resources" / "maps" / "demo.toml").write_text('id = "demo_map"\n', encoding="utf-8")
    return root


# ---------------------------------------------------------------------
# pack_package
# ---------------------------------------------------------------------


def test_pack_package_writes_trsim_pkg_archive(tmp_path: Path) -> None:
    src = _write_valid_source_dir(tmp_path / "demo")
    out = tmp_path / "demo.trsim-pkg"
    written = pack_package(src, out)
    assert written == out.resolve()
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        names = set(zf.namelist())
    assert MANIFEST_FILENAME in names
    assert "resources/maps/demo.toml" in names


def test_pack_package_rejects_wrong_suffix(tmp_path: Path) -> None:
    src = _write_valid_source_dir(tmp_path / "demo")
    bad_out = tmp_path / "demo.zip"
    with pytest.raises(ValueError, match=PACKAGE_SUFFIX):
        pack_package(src, bad_out)


def test_pack_package_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"source_dir does not exist"):
        pack_package(tmp_path / "ghost", tmp_path / "x.trsim-pkg")


def test_pack_package_rejects_source_without_manifest(tmp_path: Path) -> None:
    src = tmp_path / "no_manifest"
    src.mkdir()
    (src / "junk.txt").write_text("hi", encoding="utf-8")
    with pytest.raises(FileNotFoundError, match=r"manifest\.toml"):
        pack_package(src, tmp_path / "out.trsim-pkg")


def test_pack_package_rejects_invalid_manifest(tmp_path: Path) -> None:
    """A manifest TOML that doesn't validate must abort the pack
    *before* any zip bytes are written.
    """
    src = tmp_path / "bad"
    src.mkdir()
    (src / MANIFEST_FILENAME).write_text(
        # Missing required [package] block -> validation fails.
        '[wrong_section]\nkey = "x"\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        pack_package(src, tmp_path / "out.trsim-pkg")
    assert not (tmp_path / "out.trsim-pkg").exists()


def test_pack_package_rejects_source_that_is_a_file(tmp_path: Path) -> None:
    f = tmp_path / "file.txt"
    f.write_text("not a dir", encoding="utf-8")
    with pytest.raises(NotADirectoryError):
        pack_package(f, tmp_path / "out.trsim-pkg")


# ---------------------------------------------------------------------
# unpack_package
# ---------------------------------------------------------------------


def test_pack_then_unpack_round_trip(tmp_path: Path) -> None:
    """Build a source -> pack -> unpack -> compare files exists."""
    src = _write_valid_source_dir(tmp_path / "demo")
    pkg = tmp_path / "demo.trsim-pkg"
    pack_package(src, pkg)
    target = tmp_path / "unpacked"
    out = unpack_package(pkg, target)
    assert out == target.resolve()
    assert (target / MANIFEST_FILENAME).is_file()
    assert (target / "resources" / "maps" / "demo.toml").is_file()


def test_unpack_package_rejects_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"package archive not found"):
        unpack_package(tmp_path / "ghost.trsim-pkg", tmp_path / "target")


def test_unpack_package_refuses_existing_target(tmp_path: Path) -> None:
    src = _write_valid_source_dir(tmp_path / "demo")
    pkg = pack_package(src, tmp_path / "demo.trsim-pkg")
    existing = tmp_path / "already_there"
    existing.mkdir()
    with pytest.raises(FileExistsError, match=r"already exists"):
        unpack_package(pkg, existing)


def test_unpack_package_rejects_archive_without_manifest(tmp_path: Path) -> None:
    """A zip with no root manifest.toml is not a valid .trsim-pkg."""
    bad = tmp_path / "no_manifest.trsim-pkg"
    with zipfile.ZipFile(bad, mode="w") as zf:
        zf.writestr("junk.txt", b"hi")
    with pytest.raises(ValueError, match=r"missing root manifest\.toml"):
        unpack_package(bad, tmp_path / "target")


def test_unpack_package_rejects_zip_slip_entry(tmp_path: Path) -> None:
    """An entry named ../escape.txt would land outside target_dir;
    the loader must reject it before extracting anything.
    """
    bad = tmp_path / "evil.trsim-pkg"
    with zipfile.ZipFile(bad, mode="w") as zf:
        zf.writestr(MANIFEST_FILENAME, _VALID_MANIFEST_TOML)
        zf.writestr("../escape.txt", b"pwned")
    with pytest.raises(ValueError, match=r"zip-slip"):
        unpack_package(bad, tmp_path / "target")
    # Nothing got written outside (target dir was never created).
    assert not (tmp_path / "target").exists()


# ---------------------------------------------------------------------
# read_manifest_from_package
# ---------------------------------------------------------------------


def test_read_manifest_from_package_returns_valid_manifest(tmp_path: Path) -> None:
    src = _write_valid_source_dir(tmp_path / "demo")
    pkg = pack_package(src, tmp_path / "demo.trsim-pkg")
    manifest = read_manifest_from_package(pkg)
    assert manifest.package.package_id == "demo-tracker"
    assert manifest.package.version == "0.1.0"


def test_read_manifest_from_package_missing_archive(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        read_manifest_from_package(tmp_path / "ghost.trsim-pkg")


def test_read_manifest_from_package_missing_manifest(tmp_path: Path) -> None:
    bad = tmp_path / "no_manifest.trsim-pkg"
    with zipfile.ZipFile(bad, mode="w") as zf:
        zf.writestr("junk.txt", b"hi")
    with pytest.raises(ValueError, match=r"missing root manifest\.toml"):
        read_manifest_from_package(bad)


def test_read_manifest_from_package_strips_bom(tmp_path: Path) -> None:
    """PowerShell 5.1 BOM defence — same as the on-disk
    load_manifest_from_toml.
    """
    bad = tmp_path / "with_bom.trsim-pkg"
    body = _VALID_MANIFEST_TOML.encode("utf-8")
    with zipfile.ZipFile(bad, mode="w") as zf:
        zf.writestr(MANIFEST_FILENAME, b"\xef\xbb\xbf" + body)
    manifest = read_manifest_from_package(bad)
    assert manifest.package.package_id == "demo-tracker"
