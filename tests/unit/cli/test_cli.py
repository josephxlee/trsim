"""Unit tests for workbench.cli.main (Phase 3.7)."""

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
    (root / "targets" / "t1.toml").write_text('id = "t1"\nkind = "target"\n', encoding="utf-8")


def test_parser_recognises_run_and_profile() -> None:
    parser = build_parser()
    # run subcommand
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
    assert args.command == "run"
    assert args.scenario == "S"

    args = parser.parse_args(["profile", "--scenario", "S", "--frames", "5"])
    assert args.command == "profile"
    assert args.frames == 5


def test_parser_no_command_prints_help_and_returns_zero(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main([])
    assert rc == 0
    captured = capsys.readouterr()
    assert "usage:" in captured.out.lower()


def test_run_command_writes_manifest_and_traces(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    _build_resources(resources)
    out = tmp_path / "run_out"

    rc = main(
        [
            "run",
            "--scenario",
            "smoke_test",
            "--resources",
            str(resources),
            "--out",
            str(out),
            "--map",
            "test_map",
            "--radar",
            "test_radar",
            "--target",
            "t1",
        ]
    )
    assert rc == 0
    manifest_path = out / "manifest.json"
    traces_path = out / "traces.npz"
    assert manifest_path.exists()
    assert traces_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["scenario_id"] == "smoke_test"
    assert data["resource_refs"]["map"].startswith("sha256:")
    assert data["resource_refs"]["radar"].startswith("sha256:")
    assert data["resource_refs"]["targets"][0].startswith("sha256:")
    assert data["termination_reason"] == "completed"


def test_run_command_missing_resource_raises(tmp_path: Path) -> None:
    resources = tmp_path / "resources"
    resources.mkdir()
    _build_resources(resources)
    with pytest.raises(KeyError, match=r"radars"):
        main(
            [
                "run",
                "--scenario",
                "S",
                "--resources",
                str(resources),
                "--out",
                str(tmp_path / "x"),
                "--map",
                "test_map",
                "--radar",
                "missing_radar",
            ]
        )


def test_profile_command_writes_json_when_output_path(
    tmp_path: Path,
) -> None:
    out = tmp_path / "profile.json"
    rc = main(
        [
            "profile",
            "--scenario",
            "S",
            "--frames",
            "3",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["scenario"] == "S"
    assert payload["frames"] == 3
    # Two stages exercised in _cmd_profile.
    stage_names = {r["stage_name"] for r in payload["reports"]}
    assert stage_names == {"detector", "tracker"}


def test_profile_command_to_stdout(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    rc = main(["profile", "--scenario", "S", "--frames", "1"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "detector" in out
    assert "tracker" in out


def test_profile_command_zero_frames_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(["profile", "--scenario", "S", "--frames", "0"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "frames" in err


# ---------------------------------------------------------------------
# Phase 3 Q4 — Profile mode toggle
# ---------------------------------------------------------------------


def test_profile_command_default_mode_is_live(tmp_path: Path) -> None:
    """When --mode is omitted the payload records 'live' + every frame."""
    out = tmp_path / "p.json"
    rc = main(["profile", "--scenario", "S", "--frames", "5", "--output", str(out)])
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "live"
    assert payload["recorded_frames"] == 5


def test_profile_command_mode_off_records_zero_frames(tmp_path: Path) -> None:
    out = tmp_path / "p.json"
    rc = main(
        [
            "profile",
            "--scenario",
            "S",
            "--frames",
            "10",
            "--mode",
            "off",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "off"
    assert payload["recorded_frames"] == 0
    # No probe ever ran -> no stage reports.
    assert payload["reports"] == []


def test_profile_command_mode_explicit_records_every_nth_frame(
    tmp_path: Path,
) -> None:
    out = tmp_path / "p.json"
    rc = main(
        [
            "profile",
            "--scenario",
            "S",
            "--frames",
            "20",
            "--mode",
            "explicit",
            "--explicit-every",
            "5",
            "--output",
            str(out),
        ]
    )
    assert rc == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["mode"] == "explicit"
    # Frames 0, 5, 10, 15 -> 4 recorded.
    assert payload["recorded_frames"] == 4


def test_profile_command_explicit_every_zero_rejected(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main(
        [
            "profile",
            "--scenario",
            "S",
            "--frames",
            "5",
            "--mode",
            "explicit",
            "--explicit-every",
            "0",
        ]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "explicit-every" in err


def test_profile_command_rejects_unknown_mode(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """argparse choices= raises SystemExit on a bad value."""
    with pytest.raises(SystemExit):
        main(["profile", "--scenario", "S", "--frames", "1", "--mode", "verbose"])
