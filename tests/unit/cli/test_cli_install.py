"""Unit tests for `trsim install` (Phase 7 DLC C4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench import sdk
from workbench.cli.main import build_parser, main
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
# Parser
# ---------------------------------------------------------------------


def test_parser_recognises_install_subcommand(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["install", "--package", str(tmp_path / "x.trsim-pkg")])
    assert args.command == "install"
    assert args.package == str(tmp_path / "x.trsim-pkg")
    assert args.packages_root is None
    assert args.force is False


def test_parser_install_accepts_packages_root_and_force(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "install",
            "--package",
            str(tmp_path / "x.trsim-pkg"),
            "--packages-root",
            str(tmp_path / "pkgs"),
            "--force",
        ]
    )
    assert args.packages_root == str(tmp_path / "pkgs")
    assert args.force is True


# ---------------------------------------------------------------------
# install end-to-end
# ---------------------------------------------------------------------


def test_install_extracts_into_packages_root_under_package_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pkg = _build_pkg(tmp_path)
    pkgs_root = tmp_path / "pkgs"
    rc = main(
        [
            "install",
            "--package",
            str(pkg),
            "--packages-root",
            str(pkgs_root),
        ]
    )
    assert rc == 0
    target = pkgs_root / "demo-tracker"
    assert (target / MANIFEST_FILENAME).is_file()
    assert (target / "resources" / "demo.toml").is_file()
    captured = capsys.readouterr()
    assert "installed demo-tracker" in captured.out


def test_install_refuses_existing_target_without_force(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pkg = _build_pkg(tmp_path)
    pkgs_root = tmp_path / "pkgs"
    main(["install", "--package", str(pkg), "--packages-root", str(pkgs_root)])
    # Second install without --force should fail.
    rc = main(["install", "--package", str(pkg), "--packages-root", str(pkgs_root)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "already exists" in captured.err


def test_install_with_force_overwrites_existing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pkg = _build_pkg(tmp_path)
    pkgs_root = tmp_path / "pkgs"
    main(["install", "--package", str(pkg), "--packages-root", str(pkgs_root)])
    rc = main(
        [
            "install",
            "--package",
            str(pkg),
            "--packages-root",
            str(pkgs_root),
            "--force",
        ]
    )
    assert rc == 0
    captured = capsys.readouterr()
    assert "installed demo-tracker" in captured.out


def test_install_missing_archive_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "install",
            "--package",
            str(tmp_path / "ghost.trsim-pkg"),
            "--packages-root",
            str(tmp_path / "pkgs"),
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


# ---------------------------------------------------------------------
# uninstall (C7)
# ---------------------------------------------------------------------


def test_parser_recognises_uninstall_subcommand(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "uninstall",
            "--package-id",
            "demo-tracker",
            "--packages-root",
            str(tmp_path / "pkgs"),
        ]
    )
    assert args.command == "uninstall"
    assert args.package_id == "demo-tracker"
    assert args.packages_root == str(tmp_path / "pkgs")


def test_uninstall_removes_installed_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pkg = _build_pkg(tmp_path)
    pkgs_root = tmp_path / "pkgs"
    main(["install", "--package", str(pkg), "--packages-root", str(pkgs_root)])
    target = pkgs_root / "demo-tracker"
    assert target.exists()

    rc = main(
        [
            "uninstall",
            "--package-id",
            "demo-tracker",
            "--packages-root",
            str(pkgs_root),
        ]
    )
    assert rc == 0
    assert not target.exists()
    captured = capsys.readouterr()
    assert "uninstalled demo-tracker" in captured.out


def test_uninstall_missing_package_id_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "uninstall",
            "--package-id",
            "never-installed",
            "--packages-root",
            str(tmp_path / "pkgs"),
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "no package installed" in captured.err


def test_uninstall_rejects_path_escape(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A package_id of ``../../etc`` must not escape packages_root."""
    rc = main(
        [
            "uninstall",
            "--package-id",
            "../../etc",
            "--packages-root",
            str(tmp_path / "pkgs"),
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "outside packages_root" in captured.err
