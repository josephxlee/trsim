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


def _patch_default_paths(
    monkeypatch: pytest.MonkeyPatch, *, packages_root, user_root=None, builtin_root=None
) -> None:
    """Replace default_dlc_paths in both the app source module *and*
    the ui.dlc_bootstrap import site (it re-exports the symbol at
    import time, so patching only the source module misses the call
    that ``build_dlc_runtime`` actually makes).
    """
    from workbench.app import dlc_runtime as app_mod
    from workbench.ui import dlc_bootstrap as ui_mod

    def _fake() -> object:
        return app_mod.DLCPaths(
            packages_root=packages_root,
            user_root=user_root,
            builtin_root=builtin_root,
        )

    monkeypatch.setattr(app_mod, "default_dlc_paths", _fake)
    monkeypatch.setattr(ui_mod, "default_dlc_paths", _fake)


def test_build_ui_window_with_dlc_runtime(qtbot, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    # Point default_dlc_paths at a clean tmp_path so the test never
    # touches the real ~/.trsim/.
    _patch_default_paths(monkeypatch, packages_root=tmp_path / "packages")

    args = build_parser().parse_args(["ui", "--workspace", "simulator"])
    win = build_ui_window(args)
    qtbot.addWidget(win)  # type: ignore[arg-type]
    assert isinstance(win, MainWindow)
    assert win.selector.current is Workspace.SIMULATOR
    runtime = win.dlc_runtime()
    assert runtime is not None
    assert runtime.app.package_manager.installed_ids() == ()


def test_build_ui_window_echoes_package_errors_to_stderr(  # type: ignore[no-untyped-def]
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A package with a bad manifest must surface its load error on stderr.

    Reported during MVP verification: a sample .trsim-pkg whose
    entry_point used slash separators silently produced no DLC tab,
    leaving the user unable to tell whether the load failed or the
    mount path was wrong.
    """
    pkgs = tmp_path / "packages"
    pkgs.mkdir(parents=True)
    (pkgs / "broken-pkg").mkdir()
    (pkgs / "broken-pkg" / "manifest.toml").write_text(
        "this is not valid toml ===",
        encoding="utf-8",
    )

    _patch_default_paths(monkeypatch, packages_root=pkgs)

    args = build_parser().parse_args(["ui"])
    win = build_ui_window(args)
    qtbot.addWidget(win)  # type: ignore[arg-type]

    err = capsys.readouterr().err
    assert "[trsim ui] package error" in err
    assert "broken-pkg" in err


def test_build_ui_window_echoes_plugin_errors_to_stderr(  # type: ignore[no-untyped-def]
    qtbot,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An entry_point whose Python target cannot be imported logs to stderr.

    Mirrors the MVP_GUIDE § 4.1 sample DLC failure mode (manifest
    points at ``ui/diagnostic_panel:DiagnosticPanel`` but the file
    does not exist).
    """
    pkgs = tmp_path / "packages"
    pkg_dir = pkgs / "demo-panel"
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(
        """
[package]
id = "demo-panel"
name = "Demo"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.ui.panels" = "ui/missing_module:Panel"
""",
        encoding="utf-8",
    )

    _patch_default_paths(monkeypatch, packages_root=pkgs)

    args = build_parser().parse_args(["ui"])
    win = build_ui_window(args)
    qtbot.addWidget(win)  # type: ignore[arg-type]

    err = capsys.readouterr().err
    assert "[trsim ui] plugin error" in err
    assert "demo-panel" in err
    assert "trsim.ui.panels" in err
