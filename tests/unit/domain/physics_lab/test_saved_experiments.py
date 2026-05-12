"""Saved Experiment domain tests (PL-9.1f, plan/19 § 19.5.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.domain.physics_lab import (
    SavedExperiment,
    TimeMode,
    list_saved_experiments,
    read_saved_experiment,
    write_saved_experiment,
)

# ---------------------------------------------------------------------
# Dataclass validation
# ---------------------------------------------------------------------


def test_default_values_match_pl_d_initial_conditions() -> None:
    exp = SavedExperiment(experiment_id="x")
    assert exp.gravity_m_s2 == pytest.approx(9.81)
    assert exp.restitution == pytest.approx(0.7)
    assert exp.initial_height_m == pytest.approx(5.0)
    assert exp.initial_velocity_m_s == pytest.approx(0.0)
    assert exp.mode == TimeMode.RUN


def test_empty_experiment_id_rejected() -> None:
    with pytest.raises(ValueError, match=r"experiment_id must be non-empty"):
        SavedExperiment(experiment_id="")


def test_non_positive_gravity_rejected() -> None:
    with pytest.raises(ValueError, match=r"gravity_m_s2 must be > 0"):
        SavedExperiment(experiment_id="x", gravity_m_s2=0.0)


def test_restitution_out_of_unit_interval_rejected() -> None:
    with pytest.raises(ValueError, match=r"restitution must be in \[0, 1\]"):
        SavedExperiment(experiment_id="x", restitution=-0.1)
    with pytest.raises(ValueError, match=r"restitution must be in \[0, 1\]"):
        SavedExperiment(experiment_id="x", restitution=1.5)


def test_negative_initial_height_rejected() -> None:
    with pytest.raises(ValueError, match=r"initial_height_m must be >= 0"):
        SavedExperiment(experiment_id="x", initial_height_m=-1.0)


# ---------------------------------------------------------------------
# Write / Read round-trip
# ---------------------------------------------------------------------


def test_write_read_round_trip_preserves_all_fields(tmp_path: Path) -> None:
    exp = SavedExperiment(
        experiment_id="drop-10m",
        description="lossless drop test",
        gravity_m_s2=9.81,
        restitution=1.0,
        initial_height_m=10.0,
        initial_velocity_m_s=-2.0,
        mode=TimeMode.COMPARE,
    )
    path = tmp_path / "drop-10m.toml"
    write_saved_experiment(path, exp)
    loaded = read_saved_experiment(path)
    assert loaded == exp


def test_write_creates_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "nested" / "exp.toml"
    write_saved_experiment(nested, SavedExperiment(experiment_id="x"))
    assert nested.is_file()


def test_read_missing_experiment_section_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("[parameters]\ngravity_m_s2 = 9.81\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"missing \[experiment\]"):
        read_saved_experiment(path)


def test_read_missing_parameters_section_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text('[experiment]\nid = "x"\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"missing \[parameters\]"):
        read_saved_experiment(path)


def test_read_invalid_toml_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text("not [ valid toml at all", encoding="utf-8")
    with pytest.raises(ValueError, match=r"invalid TOML"):
        read_saved_experiment(path)


def test_read_unknown_mode_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(
        '[experiment]\nid = "x"\nmode = "warp"\n[parameters]\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"unknown mode 'warp'"):
        read_saved_experiment(path)


def test_read_strips_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "bom.toml"
    body = '[experiment]\nid = "x"\n[parameters]\n'
    path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    loaded = read_saved_experiment(path)
    assert loaded.experiment_id == "x"


# ---------------------------------------------------------------------
# list_saved_experiments
# ---------------------------------------------------------------------


def test_list_returns_empty_when_root_missing(tmp_path: Path) -> None:
    missing = tmp_path / "no-such-dir"
    assert list_saved_experiments(missing) == ()


def test_list_returns_empty_for_empty_dir(tmp_path: Path) -> None:
    assert list_saved_experiments(tmp_path) == ()


def test_list_returns_sorted_experiments(tmp_path: Path) -> None:
    for exp_id in ("zulu", "alpha", "bravo"):
        write_saved_experiment(
            tmp_path / f"{exp_id}.toml",
            SavedExperiment(experiment_id=exp_id),
        )
    loaded = list_saved_experiments(tmp_path)
    assert [e.experiment_id for e in loaded] == ["alpha", "bravo", "zulu"]


def test_list_skips_invalid_files(tmp_path: Path) -> None:
    write_saved_experiment(
        tmp_path / "good.toml",
        SavedExperiment(experiment_id="good"),
    )
    (tmp_path / "bad.toml").write_text("garbage", encoding="utf-8")
    loaded = list_saved_experiments(tmp_path)
    assert [e.experiment_id for e in loaded] == ["good"]
