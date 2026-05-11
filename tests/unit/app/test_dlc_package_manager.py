"""PackageManager scan tests (Phase 7.2, plan/17 § 17.4.2)."""

from __future__ import annotations

from pathlib import Path

from workbench.app.dlc import PackageManager

_GOOD_MANIFEST = """
[package]
id = "{pkg_id}"
name = "Demo Package"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"
"""


def _make_package(root: Path, pkg_id: str) -> Path:
    pkg_dir = root / pkg_id
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(_GOOD_MANIFEST.format(pkg_id=pkg_id), encoding="utf-8")
    return pkg_dir


# ---------------------------------------------------------------------
# Empty / missing root
# ---------------------------------------------------------------------


def test_missing_packages_root_returns_empty(tmp_path: Path) -> None:
    mgr = PackageManager(tmp_path / "nonexistent")
    assert mgr.scan() == ()
    assert mgr.installed_ids() == ()
    assert mgr.load_errors == ()


def test_empty_packages_root_returns_empty(tmp_path: Path) -> None:
    mgr = PackageManager(tmp_path)
    assert mgr.scan() == ()
    assert mgr.installed_ids() == ()


def test_packages_root_is_file_records_error(tmp_path: Path) -> None:
    f = tmp_path / "packages-as-file"
    f.write_text("not a dir", encoding="utf-8")
    mgr = PackageManager(f)
    assert mgr.scan() == ()
    assert any("not a directory" in e.message for e in mgr.load_errors)


# ---------------------------------------------------------------------
# Single + multiple package discovery
# ---------------------------------------------------------------------


def test_single_package_is_loaded(tmp_path: Path) -> None:
    _make_package(tmp_path, "demo-package")
    mgr = PackageManager(tmp_path)
    loaded = mgr.scan()
    assert len(loaded) == 1
    assert loaded[0].package_id == "demo-package"
    assert loaded[0].root == (tmp_path / "demo-package").resolve()


def test_multiple_packages_sorted_by_id(tmp_path: Path) -> None:
    _make_package(tmp_path, "zeta")
    _make_package(tmp_path, "alpha")
    _make_package(tmp_path, "mid-pack")
    mgr = PackageManager(tmp_path)
    loaded = mgr.scan()
    assert [p.package_id for p in loaded] == ["alpha", "mid-pack", "zeta"]


def test_installed_ids_matches_scan(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")
    _make_package(tmp_path, "beta")
    mgr = PackageManager(tmp_path)
    mgr.scan()
    assert mgr.installed_ids() == ("alpha", "beta")


def test_get_returns_loaded_package(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")
    mgr = PackageManager(tmp_path)
    mgr.scan()
    pkg = mgr.get("alpha")
    assert pkg is not None
    assert pkg.package_id == "alpha"
    assert pkg.manifest.package.version == "1.0.0"


def test_get_missing_returns_none(tmp_path: Path) -> None:
    mgr = PackageManager(tmp_path)
    mgr.scan()
    assert mgr.get("ghost") is None


# ---------------------------------------------------------------------
# Error accumulation
# ---------------------------------------------------------------------


def test_directory_without_manifest_records_error(tmp_path: Path) -> None:
    (tmp_path / "broken").mkdir()  # no manifest.toml
    _make_package(tmp_path, "good")
    mgr = PackageManager(tmp_path)
    loaded = mgr.scan()
    assert [p.package_id for p in loaded] == ["good"]
    assert any("missing manifest" in e.message for e in mgr.load_errors)


def test_invalid_manifest_records_error_and_keeps_others(tmp_path: Path) -> None:
    bad = tmp_path / "bad-pkg"
    bad.mkdir()
    (bad / "manifest.toml").write_text(
        '[package]\nid = "INVALID"\nname = "x"\nversion = "1.0.0"\nlicense = "MIT"\n'
        '[compatibility]\ntrsim_min_version = "0.35.0"\n',
        encoding="utf-8",
    )
    _make_package(tmp_path, "good-pkg")
    mgr = PackageManager(tmp_path)
    loaded = mgr.scan()
    assert [p.package_id for p in loaded] == ["good-pkg"]
    assert any("package_id" in e.message for e in mgr.load_errors)


def test_duplicate_package_id_records_error(tmp_path: Path) -> None:
    """Two directories both claim package_id 'alpha' -> first wins,
    second is recorded as an error.
    """
    # dir A: alphabetically first
    (tmp_path / "first").mkdir()
    (tmp_path / "first" / "manifest.toml").write_text(
        _GOOD_MANIFEST.format(pkg_id="alpha"), encoding="utf-8"
    )
    # dir B: alphabetically second
    (tmp_path / "second").mkdir()
    (tmp_path / "second" / "manifest.toml").write_text(
        _GOOD_MANIFEST.format(pkg_id="alpha"), encoding="utf-8"
    )
    mgr = PackageManager(tmp_path)
    loaded = mgr.scan()
    assert len(loaded) == 1
    assert loaded[0].root == (tmp_path / "first").resolve()
    assert any("duplicate" in e.message for e in mgr.load_errors)


# ---------------------------------------------------------------------
# Re-scan replaces state
# ---------------------------------------------------------------------


def test_rescan_picks_up_new_package(tmp_path: Path) -> None:
    _make_package(tmp_path, "alpha")
    mgr = PackageManager(tmp_path)
    assert [p.package_id for p in mgr.scan()] == ["alpha"]
    _make_package(tmp_path, "beta")
    assert [p.package_id for p in mgr.scan()] == ["alpha", "beta"]


def test_rescan_clears_previous_errors(tmp_path: Path) -> None:
    (tmp_path / "broken").mkdir()
    mgr = PackageManager(tmp_path)
    mgr.scan()
    assert mgr.load_errors  # has at least one
    # Fix the broken dir
    (tmp_path / "broken").rmdir()
    _make_package(tmp_path, "fixed")
    mgr.scan()
    assert mgr.load_errors == ()
    assert mgr.installed_ids() == ("fixed",)
