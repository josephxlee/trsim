"""Unit tests for app.dlc.installer (Phase 7 remainder F1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import sdk
from workbench.app.dlc import (
    InstallResult,
    PackageAlreadyInstalledError,
    PackageEscapedRootError,
    PackageNotInstalledError,
    UninstallResult,
    install_package,
    uninstall_package,
)
from workbench.io.package_io import MANIFEST_FILENAME

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


def _write_source_dir(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / MANIFEST_FILENAME).write_text(_VALID_MANIFEST_TOML, encoding="utf-8")
    (root / "resources").mkdir()
    (root / "resources" / "demo.toml").write_text('id = "x"\n', encoding="utf-8")
    return root


def _build_pkg(tmp_path: Path) -> Path:
    src = _write_source_dir(tmp_path / "src")
    return sdk.build_package(src, tmp_path / "demo.trsim-pkg")


# ---------------------------------------------------------------------
# install_package
# ---------------------------------------------------------------------


def test_install_creates_target_dir_from_archive(tmp_path: Path) -> None:
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    result = install_package(pkg, root)
    assert isinstance(result, InstallResult)
    assert result.manifest.package.package_id == "demo-tracker"
    assert result.target_dir == root / "demo-tracker"
    assert result.target_dir.is_dir()
    assert (result.target_dir / MANIFEST_FILENAME).is_file()
    assert (result.target_dir / "resources" / "demo.toml").is_file()
    assert result.force is False


def test_install_creates_packages_root_if_missing(tmp_path: Path) -> None:
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "deep" / "nested" / "packages"
    assert not root.exists()
    result = install_package(pkg, root)
    assert result.target_dir.is_dir()
    assert root.is_dir()


def test_install_rejects_existing_target_without_force(tmp_path: Path) -> None:
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    install_package(pkg, root)
    with pytest.raises(PackageAlreadyInstalledError, match=r"already exists"):
        install_package(pkg, root)


def test_install_force_overwrites_existing(tmp_path: Path) -> None:
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    first = install_package(pkg, root)
    sentinel = first.target_dir / "extra-file"
    sentinel.write_text("hello", encoding="utf-8")
    assert sentinel.is_file()

    second = install_package(pkg, root, force=True)
    # Existing dir wiped + recreated → sentinel must be gone.
    assert not sentinel.exists()
    assert second.force is True
    assert second.manifest.package.package_id == "demo-tracker"


def test_install_missing_archive_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        install_package(tmp_path / "ghost.trsim-pkg", tmp_path / "packages")


def test_install_accepts_str_paths(tmp_path: Path) -> None:
    """``Path | str`` API contract — strings round-trip."""
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    result = install_package(str(pkg), str(root))
    assert result.target_dir.is_dir()


# ---------------------------------------------------------------------
# uninstall_package
# ---------------------------------------------------------------------


def test_uninstall_removes_target_dir(tmp_path: Path) -> None:
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    install_package(pkg, root)
    target = root / "demo-tracker"
    assert target.is_dir()

    result = uninstall_package("demo-tracker", root)
    assert isinstance(result, UninstallResult)
    assert result.package_id == "demo-tracker"
    assert result.removed_dir == target
    assert not target.exists()


def test_uninstall_missing_target_raises(tmp_path: Path) -> None:
    root = tmp_path / "packages"
    root.mkdir()
    with pytest.raises(PackageNotInstalledError, match=r"no package installed at"):
        uninstall_package("ghost", root)


def test_uninstall_rejects_escape_attempt(tmp_path: Path) -> None:
    """Malformed package_id (e.g. ``../etc/passwd``) must not delete
    anything outside ``packages_root``."""
    root = tmp_path / "packages"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(PackageEscapedRootError, match=r"resolves outside"):
        uninstall_package("../outside", root)
    assert outside.is_dir()  # untouched


def test_uninstall_default_root_resolves_user_home(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Passing ``packages_root=None`` falls back to ``~/.trsim/packages``."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    pkg = _build_pkg(tmp_path)
    result = install_package(pkg, packages_root=None)
    assert result.target_dir.is_relative_to(fake_home)
    uninstall_package("demo-tracker", packages_root=None)
    assert not result.target_dir.exists()


def test_install_default_root_resolves_user_home(monkeypatch, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    pkg = _build_pkg(tmp_path)
    result = install_package(pkg, packages_root=None)
    assert result.target_dir.is_relative_to(fake_home / ".trsim" / "packages")
