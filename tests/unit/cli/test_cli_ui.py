"""CLI ``ui`` subcommand parser + build tests (MVP wrap-up)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.cli.main import build_parser, build_ui_window
from workbench.ui.main_window import MainWindow
from workbench.ui.workspace_selector import Workspace

pytestmark = pytest.mark.qt


def test_ui_parser_defaults_workspace_to_editor() -> None:
    args = build_parser().parse_args(["ui"])
    assert args.command == "ui"
    assert args.workspace == "editor"
    assert args.no_dlc is False


def test_ui_parser_simulator_workspace() -> None:
    args = build_parser().parse_args(["ui", "--workspace", "simulator"])
    assert args.workspace == "simulator"


def test_ui_parser_no_dlc_flag() -> None:
    args = build_parser().parse_args(["ui", "--no-dlc"])
    assert args.no_dlc is True


def test_build_ui_window_returns_main_window_with_dlc_runtime(qtbot) -> None:  # type: ignore[no-untyped-def]
    args = build_parser().parse_args(["ui", "--no-dlc"])
    win = build_ui_window(args)
    qtbot.addWidget(win)  # type: ignore[arg-type]
    assert isinstance(win, MainWindow)
    assert win.selector.current is Workspace.EDITOR
    # --no-dlc must skip the runtime build.
    assert win.dlc_runtime() is None


def test_build_ui_window_with_dlc_runtime(qtbot, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Point default_dlc_paths at a clean tmp_path so the test never
    # touches the real ~/.trsim/.
    from workbench.app import dlc_runtime as dlc_runtime_mod

    monkeypatch.setattr(
        dlc_runtime_mod,
        "default_dlc_paths",
        lambda: dlc_runtime_mod.DLCPaths(
            packages_root=tmp_path / "packages",
            user_root=None,
            builtin_root=None,
        ),
    )

    args = build_parser().parse_args(["ui", "--workspace", "simulator"])
    win = build_ui_window(args)
    qtbot.addWidget(win)  # type: ignore[arg-type]
    assert isinstance(win, MainWindow)
    assert win.selector.current is Workspace.SIMULATOR
    runtime = win.dlc_runtime()
    assert runtime is not None
    assert runtime.app.package_manager.installed_ids() == ()
