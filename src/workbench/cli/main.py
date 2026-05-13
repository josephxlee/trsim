"""TRsim CLI dispatch (Phase 3.7 + 4.1 + MVP wrap-up + A1-b).

Subcommands:

- ``trsim run --scenario <toml> [--out <dir>]``: load resources,
  run an MVP frame loop, persist a Run manifest +
  empty trace archive.
- ``trsim profile --scenario <toml> [--frames N] [--output JSON]``:
  exercise the FrameProfiler over ``N`` synthetic frames, emit a
  per-stage avg / p50 / p95 / p99 report.
- ``trsim train --job <training_job.toml> [--backend ...] [--seed N]``:
  run a :class:`TrainerService` job from a plan/07 § 7.5.2 TOML so
  training can happen outside the GUI (A1-b — Phase 6 NN
  augmentation).
- ``trsim ui [--workspace ...] [--no-dlc]``: launch the PySide6
  MainWindow with ``~/.trsim/`` packages + resources auto-loaded
  through :class:`workbench.ui.dlc_bootstrap.DLCRuntime`. Pass
  ``--no-dlc`` to start with an empty runtime (handy for debugging).
- ``trsim --version``: print the package version.

The most common MVP launch is::

    python -m workbench ui

which opens the Editor + Simulator workspaces with ``~/.trsim/``
packages and resources auto-loaded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

from workbench import __version__
from workbench.app.resource_library import ResourceLibrary
from workbench.app.timing.frame_profiler import FrameProfiler
from workbench.app.timing.stage_timing_probe import StageTimingProbe
from workbench.domain.types import RunTerminationReason
from workbench.io.run_storage import (
    ResourceRefs,
    RunManifest,
    save_manifest,
    utc_now_iso,
)
from workbench.io.trace_storage import write_traces


def build_parser() -> argparse.ArgumentParser:
    """Build the top-level ``trsim`` argparse parser."""
    parser = argparse.ArgumentParser(
        prog="trsim",
        description="TRsim — open-source tracking-radar simulation workbench",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"trsim {__version__}",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")

    run_p = sub.add_parser("run", help="run a scenario and save a Run manifest")
    run_p.add_argument(
        "--scenario",
        required=True,
        help="scenario id (must be present in --resources/scenarios/<id>.toml)",
    )
    run_p.add_argument(
        "--resources",
        default="resources",
        help="path to the resources/ directory (default: resources)",
    )
    run_p.add_argument(
        "--out",
        default=None,
        help="output directory for the run (default: ~/.workbench/runs/<run_id>/)",
    )
    run_p.add_argument(
        "--map",
        required=True,
        help="map resource id (resources/maps/<id>.toml)",
    )
    run_p.add_argument(
        "--radar",
        required=True,
        help="radar resource id (resources/radars/<id>.toml)",
    )
    run_p.add_argument(
        "--target",
        action="append",
        default=[],
        help="target resource id; repeatable",
    )

    profile_p = sub.add_parser("profile", help="run the frame profiler")
    profile_p.add_argument("--scenario", required=True, help="scenario id (informational)")
    profile_p.add_argument("--frames", type=int, default=100, help="frames to sample (default 100)")
    profile_p.add_argument(
        "--output",
        default=None,
        help="path to write a JSON profile report (default: stdout)",
    )

    train_p = sub.add_parser(
        "train",
        help="run a TrainerService job from a training_job.toml (A1-b)",
    )
    train_p.add_argument(
        "--job",
        required=True,
        help="path to training_job.toml (plan/07 § 7.5.2 schema)",
    )
    train_p.add_argument(
        "--backend",
        choices=("auto", "fake", "numpy_mlp", "numpy_mlp_adam"),
        default="auto",
        help=(
            "trainer backend; 'auto' derives from job.optimizer "
            "(adam -> numpy_mlp_adam, else numpy_mlp). default: auto"
        ),
    )
    train_p.add_argument(
        "--seed",
        type=int,
        default=0,
        help="rng seed for init + shuffle (default 0)",
    )
    train_p.add_argument(
        "--output",
        default=None,
        help="optional path to write a per-epoch JSON metrics report",
    )

    sdk_p = sub.add_parser("sdk", help="DLC SDK utilities (build / test)")
    sdk_sub = sdk_p.add_subparsers(dest="sdk_command", metavar="sdk_command")

    sdk_build_p = sdk_sub.add_parser(
        "build", help="build a .trsim-pkg from a source directory (C2)"
    )
    sdk_build_p.add_argument(
        "--source",
        required=True,
        help="path to directory containing manifest.toml + plugin/resource trees",
    )
    sdk_build_p.add_argument(
        "--output",
        required=True,
        help="destination .trsim-pkg path (must end with .trsim-pkg)",
    )

    sdk_test_p = sdk_sub.add_parser(
        "test", help="sanity-check a .trsim-pkg (manifest validity + soft issues) (C3)"
    )
    sdk_test_p.add_argument(
        "--package",
        required=True,
        help="path to the .trsim-pkg archive to inspect",
    )

    install_p = sub.add_parser(
        "install",
        help="install a .trsim-pkg into ~/.trsim/packages/ (C4)",
    )
    install_p.add_argument(
        "--package",
        required=True,
        help="path to the .trsim-pkg archive",
    )
    install_p.add_argument(
        "--packages-root",
        default=None,
        help="override the install root (default: ~/.trsim/packages/)",
    )
    install_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing installation of the same package_id",
    )

    uninstall_p = sub.add_parser(
        "uninstall",
        help="remove an installed DLC package by id (C7)",
    )
    uninstall_p.add_argument(
        "--package-id",
        required=True,
        help="package_id of the installed DLC to remove",
    )
    uninstall_p.add_argument(
        "--packages-root",
        default=None,
        help="override the install root (default: ~/.trsim/packages/)",
    )

    ui_p = sub.add_parser("ui", help="launch the PySide6 MainWindow (Phase 4.1)")
    ui_p.add_argument(
        "--workspace",
        choices=("editor", "simulator", "physics_lab"),
        default="editor",
        help="initial workspace to show (default: editor)",
    )
    ui_p.add_argument(
        "--no-dlc",
        action="store_true",
        help="skip the ~/.trsim/ DLC auto-load (start with an empty runtime)",
    )

    return parser


# ---------------------------------------------------------------------
# Subcommand bodies
# ---------------------------------------------------------------------


def _resolve_run_dir(args: argparse.Namespace, run_id: str) -> Path:
    if args.out:
        return Path(args.out).expanduser().resolve()
    return Path.home() / ".workbench" / "runs" / run_id


def _cmd_run(args: argparse.Namespace) -> int:
    """`trsim run` — minimal manifest + empty trace archive."""
    library = ResourceLibrary.scan(args.resources)
    map_entry = library.get("maps", args.map)
    radar_entry = library.get("radars", args.radar)
    target_entries = [library.get("targets", tid) for tid in args.target]

    refs = ResourceRefs(
        map_hash=map_entry.content_hash,
        radar_hash=radar_entry.content_hash,
        target_hashes=tuple(e.content_hash for e in target_entries),
    )

    run_id = f"{args.scenario}_{int(time.time())}"
    run_dir = _resolve_run_dir(args, run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    started = utc_now_iso()
    # MVP: no real frame loop. Phase 4 wires Scenario + Pipeline.step.
    sim_t_end_s = 0.0
    ended = utc_now_iso()

    manifest = RunManifest(
        run_id=run_id,
        scenario_id=args.scenario,
        resource_refs=refs,
        termination_reason=RunTerminationReason.COMPLETED,
        sim_t_start_s=0.0,
        sim_t_end_s=sim_t_end_s,
        wall_t_start_iso=started,
        wall_t_end_iso=ended,
        n_lineage_commands=0,
        metadata={"phase": "3.7-mvp"},
    )
    save_manifest(manifest, run_dir / "manifest.json")
    write_traces(run_dir / "traces.npz", [])
    print(f"run_id   : {run_id}")
    print(f"out_dir  : {run_dir}")
    print(f"map_hash : {refs.map_hash}")
    print(f"radar    : {refs.radar_hash}")
    for h in refs.target_hashes:
        print(f"target   : {h}")
    return 0


def _cmd_profile(args: argparse.Namespace) -> int:
    """`trsim profile` — exercise FrameProfiler synthetically."""
    if args.frames < 1:
        print("error: --frames must be >= 1", file=sys.stderr)
        return 2
    profiler = FrameProfiler()
    for _ in range(args.frames):
        with StageTimingProbe(profiler, stage_name="detector"):
            # Synthetic 0.5 ms work — Python loop short-circuit so it's
            # cheap on CI but produces non-zero samples.
            sum(range(50))
        with StageTimingProbe(profiler, stage_name="tracker"):
            sum(range(20))

    reports = [asdict(r) for r in profiler.report_all()]
    payload = {
        "scenario": args.scenario,
        "frames": args.frames,
        "reports": reports,
    }
    text = json.dumps(payload, indent=2)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(f"profile written to {args.output}")
    else:
        print(text)
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    """`trsim train` — run a TrainerService job from a training_job.toml.

    Loads the job via :func:`workbench.app.nn.trainer.load_training_job_from_toml`,
    selects a backend (CLI --backend overrides; ``auto`` reads
    ``job.optimizer``), and runs the trainer synchronously. Each epoch
    is echoed to stdout; a final JSON summary is printed (and optionally
    written to ``--output``).
    """
    from workbench.app.nn.trainer import (
        TrainerService,
        load_training_job_from_toml,
        resolve_backend_from_optimizer,
    )

    job_path = Path(args.job).expanduser()
    try:
        job = load_training_job_from_toml(job_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    backend = (
        resolve_backend_from_optimizer(job.optimizer) if args.backend == "auto" else args.backend
    )

    epoch_log: list[dict[str, float | int]] = []

    def _on_epoch(epoch: int, train_loss: float, val_loss: float) -> None:
        record = {"epoch": epoch, "train_loss": train_loss, "val_loss": val_loss}
        epoch_log.append(record)
        print(json.dumps(record))

    trainer = TrainerService(epoch_callback=_on_epoch, backend=backend, rng_seed=args.seed)
    try:
        result = trainer.run(job)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    summary = {
        "job_id": result.job_id,
        "backend": backend,
        "completed_epochs": result.completed_epochs,
        "final_train_loss": result.final_train_loss,
        "final_val_loss": result.final_val_loss,
        "best_val_loss": result.best_val_loss,
        "best_epoch": result.best_epoch,
        "early_stopped": result.early_stopped,
        "weights_path": str(result.weights_path),
        "epochs": epoch_log,
    }
    text = json.dumps(summary, indent=2)
    if args.output:
        Path(args.output).expanduser().write_text(text + "\n", encoding="utf-8")
        print(f"training report written to {args.output}")
    else:
        print(text)
    return 0


def _cmd_sdk(args: argparse.Namespace) -> int:
    """`trsim sdk <action>` — DLC SDK utilities (C2 build, C3 test)."""
    if args.sdk_command == "build":
        return _cmd_sdk_build(args)
    if args.sdk_command == "test":
        return _cmd_sdk_test(args)
    print("error: trsim sdk requires a sub-command (build / test)", file=sys.stderr)
    return 2


def _cmd_sdk_build(args: argparse.Namespace) -> int:
    """`trsim sdk build --source <dir> --output <pkg>` — pack a
    ``.trsim-pkg`` from a directory.

    Forwards to :func:`workbench.sdk.build_package`; converts the
    expected exceptions into a non-zero exit code + a clear stderr
    message so CI consumers can fail the job on a bad input without
    parsing tracebacks.
    """
    from workbench.sdk import build_package

    source = Path(args.source).expanduser()
    output = Path(args.output).expanduser()
    try:
        written = build_package(source, output)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"package written to {written}")
    return 0


def _cmd_sdk_test(args: argparse.Namespace) -> int:
    """`trsim sdk test --package <pkg>` — sanity-check a ``.trsim-pkg``.

    Reads the archive's ``manifest.toml`` and reports the parsed
    package metadata + non-fatal issues (empty description, empty
    author). Non-zero exit code only on hard failures (missing file,
    invalid manifest); soft issues print to stdout but still exit 0.
    """
    from workbench.sdk import test_package

    pkg_path = Path(args.package).expanduser()
    try:
        result = test_package(pkg_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"package_id      : {result.package_id}")
    print(f"package_name    : {result.package_name}")
    print(f"package_version : {result.package_version}")
    print(f"trsim_min       : {result.trsim_min_version}")
    if result.issues:
        print("issues:")
        for issue in result.issues:
            print(f"  - {issue}")
    else:
        print("issues: none")
    return 0


def _cmd_install(args: argparse.Namespace) -> int:
    """`trsim install --package <pkg> [--packages-root <dir>] [--force]`.

    Thin wrapper around :func:`workbench.app.dlc.install_package`.
    Adds stdout / exit-code plumbing on top of the shared service so
    the Editor's Package Manager dialog and the CLI stay in lockstep.
    """
    from workbench.app.dlc import (
        PackageAlreadyInstalledError,
        install_package,
    )

    try:
        result = install_package(
            args.package,
            args.packages_root,
            force=args.force,
        )
    except (FileNotFoundError, ValueError, PackageAlreadyInstalledError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    pkg = result.manifest.package
    print(f"installed {pkg.package_id} {pkg.version} -> {result.target_dir}")
    return 0


def _cmd_uninstall(args: argparse.Namespace) -> int:
    """`trsim uninstall --package-id <id> [--packages-root <dir>]`.

    Thin wrapper around :func:`workbench.app.dlc.uninstall_package`.
    """
    from workbench.app.dlc import (
        PackageEscapedRootError,
        PackageNotInstalledError,
        uninstall_package,
    )

    try:
        result = uninstall_package(args.package_id, args.packages_root)
    except PackageEscapedRootError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except PackageNotInstalledError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(f"uninstalled {result.package_id} from {result.removed_dir.parent}")
    return 0


def build_ui_window(args: argparse.Namespace) -> object:
    """Construct (but do not show / exec) the :class:`MainWindow`.

    Splits the UI subcommand body so tests can assert window state
    without entering the Qt event loop. The return type is left as
    :class:`object` so callers that never touch the UI do not need
    to import PySide6 for type checking.

    DLC ``load_errors`` (package manifest failures, plugin import
    failures, panel mount failures) are echoed to stderr so users
    can tell *why* a sample ``.trsim-pkg`` did not light up the
    workspace. Errors are accumulated; the window is still built.
    """
    # Local imports keep the CLI usable in headless contexts that
    # never touch the UI subcommand (e.g. CI running `trsim profile`).
    from workbench.ui.dlc_bootstrap import build_dlc_runtime
    from workbench.ui.main_window import MainWindow
    from workbench.ui.workspace_selector import Workspace

    runtime = None if args.no_dlc else build_dlc_runtime()
    if runtime is not None:
        _report_dlc_load_errors(runtime)
    window = MainWindow(dlc_runtime=runtime)
    if runtime is not None:
        _report_simulator_mount_errors(window)
    window.selector.set_workspace(Workspace(args.workspace))
    return window


def _report_dlc_load_errors(runtime: object) -> None:
    """Echo PackageManager + PluginLoader errors to stderr."""
    pm_errors = getattr(getattr(runtime, "app", None), "package_manager", None)
    pm_load_errors = getattr(pm_errors, "load_errors", ()) if pm_errors is not None else ()
    for err in pm_load_errors:
        print(f"[trsim ui] package error {err.path}: {err.message}", file=sys.stderr)

    pl = getattr(getattr(runtime, "app", None), "plugin_loader", None)
    pl_load_errors = getattr(pl, "load_errors", ()) if pl is not None else ()
    for err in pl_load_errors:
        print(
            f"[trsim ui] plugin error {err.package_id}/{err.slot} -> {err.target}: {err.message}",
            file=sys.stderr,
        )


def _report_simulator_mount_errors(window: object) -> None:
    """Echo Simulator DLC panel mount errors to stderr (Task D + MVP fix)."""
    try:
        from workbench.ui.simulator.workspace import SimulatorWorkspace
        from workbench.ui.workspace_selector import Workspace
    except ImportError:  # pragma: no cover — module guaranteed in app
        return
    page_getter = getattr(window, "page", None)
    if page_getter is None:
        return
    sim = page_getter(Workspace.SIMULATOR)
    if not isinstance(sim, SimulatorWorkspace):
        return
    for err in sim.dlc_mount_errors:
        print(
            f"[trsim ui] panel mount error {err.registration.source_package_id}: {err.message}",
            file=sys.stderr,
        )


def _cmd_ui(args: argparse.Namespace) -> int:
    """`trsim ui` — launch the PySide6 MainWindow.

    By default the entry point assembles a :class:`DLCRuntime` from
    ``~/.trsim/`` (see :func:`workbench.app.dlc_runtime.default_dlc_
    paths`) so any installed ``.trsim-pkg`` packages and user
    resources show up immediately. ``--no-dlc`` opts out.
    """
    from PySide6.QtWidgets import QApplication, QWidget

    app = QApplication.instance() or QApplication(sys.argv)
    window = build_ui_window(args)
    assert isinstance(window, QWidget)
    window.show()
    return int(app.exec())


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _cmd_run(args)
    if args.command == "profile":
        return _cmd_profile(args)
    if args.command == "train":
        return _cmd_train(args)
    if args.command == "sdk":
        return _cmd_sdk(args)
    if args.command == "install":
        return _cmd_install(args)
    if args.command == "uninstall":
        return _cmd_uninstall(args)
    if args.command == "ui":  # pragma: no cover — GUI loop
        return _cmd_ui(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
