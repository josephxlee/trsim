"""CLI ``--profile-mode`` flag tests (Phase 3 Q4)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workbench.cli.main import build_parser, main


def _build_resources(root: Path) -> None:
    (root / "maps").mkdir()
    (root / "radars").mkdir()
    (root / "targets").mkdir()
    (root / "maps" / "test_map.toml").write_text(
        'id = "test_map"\nkind = "map"\n', encoding="utf-8"
    )
    (root / "radars" / "test_radar.toml").write_text(
        'id = "test_radar"\nkind = "radar"\n', encoding="utf-8"
    )


def test_run_parser_default_profile_mode_is_off() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--scenario",
            "S",
            "--resources",
            "/tmp/r",
            "--map",
            "M",
            "--radar",
            "R",
        ]
    )
    assert args.profile_mode == "off"


def test_run_parser_accepts_explicit_and_live() -> None:
    parser = build_parser()
    for value in ("off", "explicit", "live"):
        args = parser.parse_args(
            [
                "run",
                "--scenario",
                "S",
                "--resources",
                "/tmp/r",
                "--map",
                "M",
                "--radar",
                "R",
                "--profile-mode",
                value,
            ]
        )
        assert args.profile_mode == value


def test_run_parser_rejects_unknown_profile_mode() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "run",
                "--scenario",
                "S",
                "--resources",
                "/tmp/r",
                "--map",
                "M",
                "--radar",
                "R",
                "--profile-mode",
                "super",
            ]
        )


def test_run_command_records_profile_mode_in_manifest_metadata(tmp_path: Path) -> None:
    """``trsim run`` propagates ``--profile-mode`` into the manifest
    metadata so users can audit what mode a stored run executed in."""
    resources = tmp_path / "resources"
    resources.mkdir()
    _build_resources(resources)
    out = tmp_path / "run_out"
    rc = main(
        [
            "run",
            "--scenario",
            "smoke",
            "--resources",
            str(resources),
            "--out",
            str(out),
            "--map",
            "test_map",
            "--radar",
            "test_radar",
            "--profile-mode",
            "live",
        ]
    )
    assert rc == 0
    data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert data["metadata"]["profile_mode"] == "live"


def test_run_command_default_metadata_records_off(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    _build_resources(resources)
    out = tmp_path / "run_out"
    main(
        [
            "run",
            "--scenario",
            "smoke",
            "--resources",
            str(resources),
            "--out",
            str(out),
            "--map",
            "test_map",
            "--radar",
            "test_radar",
        ]
    )
    data = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert data["metadata"]["profile_mode"] == "off"


def test_profile_parser_defaults_to_explicit() -> None:
    parser = build_parser()
    args = parser.parse_args(["profile", "--scenario", "S", "--frames", "5"])
    assert args.profile_mode == "explicit"


def test_profile_parser_rejects_off() -> None:
    """``trsim profile`` does not allow ``off`` (the whole command's
    purpose is to profile - off would be a no-op)."""
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "profile",
                "--scenario",
                "S",
                "--frames",
                "5",
                "--profile-mode",
                "off",
            ]
        )
