"""Saved Experiments — TOML schema + I/O (PL-9.1f, plan/19 § 19.5.2).

The Physics Lab Library's "Saved Experiments" category surfaces user-
saved snapshots of the active simulator's parameters + time mode.
Each entry round-trips through a TOML file using the same hand-rolled
serialiser pattern as :mod:`workbench.domain.nn.variant_manifest`
because the project does not ship a runtime TOML writer (tomllib is
read-only on Python 3.11+).

TOML schema::

    [experiment]
    id = "drop-from-10m"
    description = "Lossless drop from 10 m to test analytic peak."
    mode = "compare"

    [parameters]
    gravity_m_s2 = 9.81
    restitution = 1.0
    initial_height_m = 10.0
    initial_velocity_m_s = 0.0

The user-facing UI (LibraryWidget Save button + Saved Experiments
sub-tree) lives in the UI layer; this module stays pure data.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from workbench.domain.physics_lab.time_modes import TimeMode


@dataclass(frozen=True, slots=True)
class SavedExperiment:
    """One persisted Bouncing Ball experiment.

    Attributes:
        experiment_id: User-supplied identifier (kebab-case is the
            recommended convention; the validation rejects empty).
        description: Free-form free-text.
        gravity_m_s2: Mirrors :attr:`BouncingBallSimulator.gravity_m_s2`.
        restitution: Mirrors :attr:`BouncingBallSimulator.restitution`.
        initial_height_m: Mirrors initial conditions.
        initial_velocity_m_s: Mirrors initial conditions.
        mode: The :class:`TimeMode` to restore on load.

    Raises:
        ValueError: For empty ``experiment_id``, non-positive gravity,
            restitution outside ``[0, 1]``, negative initial height.
    """

    experiment_id: str
    description: str = ""
    gravity_m_s2: float = 9.81
    restitution: float = 0.7
    initial_height_m: float = 5.0
    initial_velocity_m_s: float = 0.0
    drag_coefficient_k: float = 0.0
    mode: TimeMode = TimeMode.RUN

    def __post_init__(self) -> None:
        if not self.experiment_id:
            msg = "SavedExperiment.experiment_id must be non-empty"
            raise ValueError(msg)
        if self.gravity_m_s2 <= 0.0:
            msg = f"gravity_m_s2 must be > 0, got {self.gravity_m_s2}"
            raise ValueError(msg)
        if not 0.0 <= self.restitution <= 1.0:
            msg = f"restitution must be in [0, 1], got {self.restitution}"
            raise ValueError(msg)
        if self.initial_height_m < 0.0:
            msg = f"initial_height_m must be >= 0, got {self.initial_height_m}"
            raise ValueError(msg)
        if self.drag_coefficient_k < 0.0:
            msg = f"drag_coefficient_k must be >= 0, got {self.drag_coefficient_k}"
            raise ValueError(msg)


# ---------------------------------------------------------------------
# TOML write
# ---------------------------------------------------------------------


def _toml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def write_saved_experiment(path: Path | str, experiment: SavedExperiment) -> None:
    """Write ``experiment`` to ``path`` as TOML.

    The parent directory is created if it does not exist (typical use
    is the user's ``~/.trsim/physics_lab/experiments`` root). UTF-8
    encoding, no BOM — matches the rest of the codebase.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "[experiment]",
        f"id = {_toml_quote(experiment.experiment_id)}",
        f"description = {_toml_quote(experiment.description)}",
        f"mode = {_toml_quote(experiment.mode.value)}",
        "",
        "[parameters]",
        f"gravity_m_s2 = {experiment.gravity_m_s2}",
        f"restitution = {experiment.restitution}",
        f"initial_height_m = {experiment.initial_height_m}",
        f"initial_velocity_m_s = {experiment.initial_velocity_m_s}",
        f"drag_coefficient_k = {experiment.drag_coefficient_k}",
        "",
    ]
    path_obj.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------
# TOML read
# ---------------------------------------------------------------------


def read_saved_experiment(path: Path | str) -> SavedExperiment:
    """Read + validate a Saved Experiment TOML file."""
    path_obj = Path(path)
    raw = path_obj.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = f"SavedExperiment {path_obj.name}: not valid UTF-8 ({exc})"
        raise ValueError(msg) from exc
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        msg = f"SavedExperiment {path_obj.name}: invalid TOML ({exc})"
        raise ValueError(msg) from exc
    if "experiment" not in data:
        msg = f"SavedExperiment {path_obj.name}: missing [experiment] section"
        raise ValueError(msg)
    if "parameters" not in data:
        msg = f"SavedExperiment {path_obj.name}: missing [parameters] section"
        raise ValueError(msg)
    exp_section = data["experiment"]
    params = data["parameters"]
    if "id" not in exp_section:
        msg = f"SavedExperiment {path_obj.name}: missing experiment.id"
        raise ValueError(msg)
    mode_raw = exp_section.get("mode", TimeMode.RUN.value)
    try:
        mode = TimeMode(mode_raw)
    except ValueError as exc:
        msg = f"SavedExperiment {path_obj.name}: unknown mode {mode_raw!r}"
        raise ValueError(msg) from exc
    return SavedExperiment(
        experiment_id=str(exp_section["id"]),
        description=str(exp_section.get("description", "")),
        gravity_m_s2=float(params.get("gravity_m_s2", 9.81)),
        restitution=float(params.get("restitution", 0.7)),
        initial_height_m=float(params.get("initial_height_m", 5.0)),
        initial_velocity_m_s=float(params.get("initial_velocity_m_s", 0.0)),
        drag_coefficient_k=float(params.get("drag_coefficient_k", 0.0)),
        mode=mode,
    )


def list_saved_experiments(root: Path | str) -> tuple[SavedExperiment, ...]:
    """Scan ``root`` for ``*.toml`` files and return parsed experiments.

    Sorted by ``experiment_id`` for deterministic display order. Files
    that fail to parse are silently skipped — the caller (LibraryWidget
    Save UI) reports them via a status banner. A missing root returns
    an empty tuple.
    """
    root_path = Path(root)
    if not root_path.is_dir():
        return ()
    experiments: list[SavedExperiment] = []
    for toml_path in sorted(root_path.glob("*.toml")):
        try:
            experiments.append(read_saved_experiment(toml_path))
        except (ValueError, OSError):
            continue
    return tuple(sorted(experiments, key=lambda e: e.experiment_id))
