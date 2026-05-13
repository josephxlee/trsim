"""Unit tests for `trsim sdk build / test` (Phase 7 DLC C2 / C3)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

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
    return root


# ---------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------


def test_parser_recognises_sdk_build_subcommand(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "sdk",
            "build",
            "--source",
            str(tmp_path / "src"),
            "--output",
            str(tmp_path / "out.trsim-pkg"),
        ]
    )
    assert args.command == "sdk"
    assert args.sdk_command == "build"
    assert args.source == str(tmp_path / "src")
    assert args.output == str(tmp_path / "out.trsim-pkg")


def test_sdk_without_subcommand_returns_error(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["sdk"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "trsim sdk requires" in captured.err


# ---------------------------------------------------------------------
# sdk build end-to-end
# ---------------------------------------------------------------------


def test_sdk_build_writes_trsim_pkg(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    src = _write_source_dir(tmp_path / "demo")
    out = tmp_path / "demo.trsim-pkg"
    rc = main(["sdk", "build", "--source", str(src), "--output", str(out)])
    assert rc == 0
    assert out.is_file()
    with zipfile.ZipFile(out) as zf:
        assert MANIFEST_FILENAME in zf.namelist()
    captured = capsys.readouterr()
    assert "package written to" in captured.out


def test_sdk_build_missing_source_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(
        [
            "sdk",
            "build",
            "--source",
            str(tmp_path / "ghost"),
            "--output",
            str(tmp_path / "out.trsim-pkg"),
        ]
    )
    assert rc == 2
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


def test_sdk_build_wrong_suffix_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    src = _write_source_dir(tmp_path / "demo")
    rc = main(["sdk", "build", "--source", str(src), "--output", str(tmp_path / "out.zip")])
    assert rc == 2
    captured = capsys.readouterr()
    assert ".trsim-pkg" in captured.err


# ---------------------------------------------------------------------
# Python API (sdk.build_package)
# ---------------------------------------------------------------------


def test_sdk_build_package_python_api(tmp_path: Path) -> None:
    """``import workbench.sdk as sdk; sdk.build_package(...)`` -> archive."""
    from workbench import sdk

    src = _write_source_dir(tmp_path / "demo")
    out = tmp_path / "demo.trsim-pkg"
    written = sdk.build_package(src, out)
    assert written == out.resolve()
    assert out.is_file()


# ---------------------------------------------------------------------
# sdk test end-to-end (C3)
# ---------------------------------------------------------------------


def test_parser_recognises_sdk_test_subcommand(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["sdk", "test", "--package", str(tmp_path / "x.trsim-pkg")])
    assert args.command == "sdk"
    assert args.sdk_command == "test"
    assert args.package == str(tmp_path / "x.trsim-pkg")


def test_sdk_test_reports_manifest_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """End-to-end: build a valid package, run `sdk test`, stdout must
    surface package_id / package_name / package_version / trsim_min.
    """
    from workbench import sdk

    src = _write_source_dir(tmp_path / "demo")
    pkg = sdk.build_package(src, tmp_path / "demo.trsim-pkg")
    rc = main(["sdk", "test", "--package", str(pkg)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "demo-tracker" in captured.out
    assert "Demo Tracker" in captured.out
    assert "0.1.0" in captured.out
    assert "0.40.0" in captured.out


def test_sdk_test_reports_soft_issues_but_still_zero_exit(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A manifest missing description / author is *valid* but generates
    soft issues. Exit code stays 0; the issue list prints to stdout.
    """
    from workbench import sdk

    src = _write_source_dir(tmp_path / "demo")
    pkg = sdk.build_package(src, tmp_path / "demo.trsim-pkg")
    rc = main(["sdk", "test", "--package", str(pkg)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "issues:" in captured.out
    assert "description" in captured.out


def test_sdk_test_missing_package_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["sdk", "test", "--package", str(tmp_path / "ghost.trsim-pkg")])
    assert rc == 2
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


def test_sdk_test_python_api(tmp_path: Path) -> None:
    """``sdk.test_package`` returns a PackageTestResult."""
    from workbench import sdk

    src = _write_source_dir(tmp_path / "demo")
    pkg = sdk.build_package(src, tmp_path / "demo.trsim-pkg")
    result = sdk.test_package(pkg)
    assert result.package_id == "demo-tracker"
    assert result.package_version == "0.1.0"
    assert result.trsim_min_version == "0.40.0"
    # Description + author empty -> soft issues exist.
    assert len(result.issues) >= 1
