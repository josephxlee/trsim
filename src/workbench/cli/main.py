"""TRsim CLI dispatch (Phase 3.7 + 4.1 + MVP wrap-up).

Subcommands:

- ``trsim run --scenario <toml> [--out <dir>]``: load resources,
  run an MVP frame loop, persist a Run manifest +
  empty trace archive.
- ``trsim profile --scenario <toml> [--frames N] [--output JSON]``:
  exercise the FrameProfiler over ``N`` synthetic frames, emit a
  per-stage avg / p50 / p95 / p99 report.
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

    ui_p = sub.add_parser("ui", help="launch the PySide6 MainWindow (Phase 4.1)")
    ui_p.add_argument(
        "--workspace",
        choices=("editor", "simulator"),
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
    if args.command == "ui":  # pragma: no cover — GUI loop
        return _cmd_ui(args)
    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
