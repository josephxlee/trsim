"""Unit tests for `trsim train` (A1-b — Phase 6 NN augmentation)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from workbench.app.nn import TrainingJob, write_dataset
from workbench.app.nn.trainer import (
    load_training_job_from_toml,
    resolve_backend_from_optimizer,
)
from workbench.cli.main import build_parser, main
from workbench.domain.nn import DatasetMeta, DatasetVariant, FieldSpec, SampleSpec


def _spec(buffer: int = 4) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (buffer,), "complex64"),
            FieldSpec("down_beats", (buffer,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (buffer,), "int32"),),
    )


def _write_dataset(path: Path, *, n: int = 32, buffer: int = 4, seed: int = 0) -> None:
    rng = np.random.default_rng(seed)
    spec = _spec(buffer)
    up = (rng.standard_normal((n, buffer)) + 1j * rng.standard_normal((n, buffer))).astype(
        np.complex64
    )
    down = (rng.standard_normal((n, buffer)) + 1j * rng.standard_normal((n, buffer))).astype(
        np.complex64
    )
    label = np.clip(np.floor(np.abs(up) + np.abs(down)), 0, buffer - 1).astype(np.int32)
    meta = DatasetMeta(
        dataset_id="synthetic",
        spec=spec,
        variant=DatasetVariant(variant_id="A"),
        total_samples=n,
    )
    write_dataset(path, meta, {"up_beats": up, "down_beats": down}, {"pair_indices": label})


def _write_job_toml(
    toml_path: Path,
    *,
    dataset_path: Path,
    weights_path: Path,
    epochs: int = 3,
    optimizer: str = "adam",
    learning_rate: float = 1e-2,
) -> None:
    """Hand-rolled TOML so we don't depend on tomli_w."""
    body = (
        f'job_id = "cli_train_demo"\n'
        f'task = "pairing"\n'
        f'dataset_path = "{dataset_path.as_posix()}"\n'
        f'weights_path = "{weights_path.as_posix()}"\n'
        f"layer_sizes = [4, 16, 4]\n"
        f"epochs = {epochs}\n"
        f"learning_rate = {learning_rate}\n"
        f"batch_size = 8\n"
        f"train_fraction = 0.6\n"
        f"val_fraction = 0.2\n"
        f'optimizer = "{optimizer}"\n'
    )
    toml_path.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------
# load_training_job_from_toml
# ---------------------------------------------------------------------


def test_load_training_job_from_toml_round_trip(tmp_path: Path) -> None:
    """Hand-rolled TOML round-trips through the loader into a valid
    :class:`TrainingJob`.
    """
    toml = tmp_path / "job.toml"
    dataset = tmp_path / "ds.h5"
    weights = tmp_path / "weights.npz"
    _write_job_toml(toml, dataset_path=dataset, weights_path=weights, epochs=5, optimizer="adam")
    job = load_training_job_from_toml(toml)
    assert isinstance(job, TrainingJob)
    assert job.job_id == "cli_train_demo"
    assert job.task == "pairing"
    assert job.epochs == 5
    assert job.optimizer == "adam"
    assert job.dataset_path == dataset.resolve()
    assert job.weights_path == weights.resolve()


def test_load_training_job_from_toml_resolves_relative_paths(tmp_path: Path) -> None:
    """Relative paths in the TOML resolve against the TOML's directory."""
    toml = tmp_path / "job.toml"
    body = (
        'job_id = "rel"\n'
        'task = "pairing"\n'
        'dataset_path = "./datasets/x.h5"\n'
        'weights_path = "./weights/v1.npz"\n'
    )
    toml.write_text(body, encoding="utf-8")
    job = load_training_job_from_toml(toml)
    assert job.dataset_path == (tmp_path / "datasets" / "x.h5").resolve()
    assert job.weights_path == (tmp_path / "weights" / "v1.npz").resolve()


def test_load_training_job_from_toml_missing_required_key(tmp_path: Path) -> None:
    """Omitting a required key surfaces a clear ValueError."""
    toml = tmp_path / "job.toml"
    toml.write_text('job_id = "x"\ntask = "pairing"\nweights_path = "w.npz"\n', encoding="utf-8")
    with pytest.raises(ValueError, match=r"missing required keys.*dataset_path"):
        load_training_job_from_toml(toml)


def test_load_training_job_from_toml_strips_bom(tmp_path: Path) -> None:
    """PowerShell 5.1 ``Out-File -Encoding utf8`` writes a UTF-8 BOM;
    loader must strip it before tomllib parses.
    """
    toml = tmp_path / "job_bom.toml"
    body = b'job_id = "bom"\ntask = "pairing"\ndataset_path = "ds.h5"\nweights_path = "w.npz"\n'
    toml.write_bytes(b"\xef\xbb\xbf" + body)
    job = load_training_job_from_toml(toml)
    assert job.job_id == "bom"


def test_load_training_job_from_toml_rejects_invalid_utf8(tmp_path: Path) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_bytes(b'\xff\xfe\x00job_id = "x"\n')
    with pytest.raises(ValueError, match=r"not valid UTF-8"):
        load_training_job_from_toml(toml)


# ---------------------------------------------------------------------
# resolve_backend_from_optimizer
# ---------------------------------------------------------------------


def test_resolve_backend_adam() -> None:
    assert resolve_backend_from_optimizer("adam") == "numpy_mlp_adam"


def test_resolve_backend_sgd() -> None:
    assert resolve_backend_from_optimizer("sgd") == "numpy_mlp"


def test_resolve_backend_unknown_falls_back_to_numpy_mlp() -> None:
    """Unknown optimiser name -> plain numpy_mlp (SGD), no exception."""
    assert resolve_backend_from_optimizer("rmsprop") == "numpy_mlp"


# ---------------------------------------------------------------------
# build_parser registers the train subcommand
# ---------------------------------------------------------------------


def test_parser_recognises_train_subcommand(tmp_path: Path) -> None:
    parser = build_parser()
    args = parser.parse_args(["train", "--job", str(tmp_path / "job.toml")])
    assert args.command == "train"
    assert args.backend == "auto"
    assert args.seed == 0


def test_parser_train_accepts_explicit_backend() -> None:
    parser = build_parser()
    args = parser.parse_args(
        ["train", "--job", "j.toml", "--backend", "numpy_mlp_adam", "--seed", "7"]
    )
    assert args.backend == "numpy_mlp_adam"
    assert args.seed == 7


# ---------------------------------------------------------------------
# End-to-end: trsim train --job <toml>
# ---------------------------------------------------------------------


def test_train_command_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`trsim train --job <toml> --output report.json` reads the TOML,
    runs the trainer, writes a weights file and a JSON summary report.
    """
    dataset = tmp_path / "ds.h5"
    _write_dataset(dataset, n=24, buffer=4, seed=0)
    weights = tmp_path / "weights.npz"
    toml = tmp_path / "job.toml"
    _write_job_toml(toml, dataset_path=dataset, weights_path=weights, epochs=3)
    report = tmp_path / "report.json"

    rc = main(["train", "--job", str(toml), "--output", str(report)])
    assert rc == 0
    assert weights.is_file()
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["job_id"] == "cli_train_demo"
    assert payload["backend"] == "numpy_mlp_adam"  # optimizer="adam" in TOML
    assert payload["completed_epochs"] == 3
    assert "epochs" in payload
    assert len(payload["epochs"]) == 3
    # Per-epoch records stream to stdout as one JSON document per line
    # alongside the "training report written" notice.
    captured = capsys.readouterr()
    stdout_lines = [ln for ln in captured.out.splitlines() if ln.strip().startswith("{")]
    assert len(stdout_lines) == 3
    first_epoch_record = json.loads(stdout_lines[0])
    assert first_epoch_record["epoch"] == 1


def test_train_command_writes_output_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    dataset = tmp_path / "ds.h5"
    _write_dataset(dataset, n=24, buffer=4, seed=1)
    weights = tmp_path / "weights.npz"
    toml = tmp_path / "job.toml"
    _write_job_toml(toml, dataset_path=dataset, weights_path=weights, epochs=2)
    report = tmp_path / "report.json"

    rc = main(["train", "--job", str(toml), "--output", str(report)])
    assert rc == 0
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["completed_epochs"] == 2
    captured = capsys.readouterr()
    assert "training report written" in captured.out


def test_train_command_explicit_backend_overrides_auto(tmp_path: Path) -> None:
    """Explicit --backend overrides the optimiser-derived default."""
    dataset = tmp_path / "ds.h5"
    _write_dataset(dataset, n=24, buffer=4, seed=2)
    weights = tmp_path / "weights.npz"
    toml = tmp_path / "job.toml"
    _write_job_toml(toml, dataset_path=dataset, weights_path=weights, optimizer="adam")
    report = tmp_path / "report.json"

    # Force the SGD backend even though TOML says adam.
    rc = main(["train", "--job", str(toml), "--backend", "numpy_mlp", "--output", str(report)])
    assert rc == 0
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["backend"] == "numpy_mlp"


def test_train_command_missing_toml_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rc = main(["train", "--job", str(tmp_path / "nope.toml")])
    assert rc == 2
    captured = capsys.readouterr()
    assert "error" in captured.err.lower()


def test_train_command_invalid_toml_returns_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    toml = tmp_path / "bad.toml"
    toml.write_text('job_id = "x"\n', encoding="utf-8")  # missing required keys
    rc = main(["train", "--job", str(toml)])
    assert rc == 2
    captured = capsys.readouterr()
    assert "missing required keys" in captured.err
