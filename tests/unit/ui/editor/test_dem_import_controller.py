"""Unit tests for the DEM Import controller (Phase 4 dem_import_wizard E4)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMainWindow

from workbench.io.dem_import import (
    DEMImportRequest,
    DEMImportSummary,
    LandSeaMode,
    run_dem_import,
)
from workbench.ui.editor.map_editor import (
    DEMImportController,
    DEMImportWizard,
    MapEditor,
)

pytestmark = pytest.mark.qt


def _write_asc(path: Path) -> Path:
    path.write_text(
        "ncols 2\nnrows 1\nxllcorner 0\nyllcorner 0\ncellsize 1\nNODATA_value -9999\n10 20\n",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------
# Controller wiring
# ---------------------------------------------------------------------


def test_controller_starts_with_no_active_wizard(qtbot) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    assert controller.active_wizard() is None


def test_signal_from_map_editor_opens_wizard(qtbot) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    assert isinstance(wiz, DEMImportWizard)
    qtbot.addWidget(wiz)


def test_second_emit_reuses_wizard(qtbot) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    first = controller.active_wizard()
    editor.import_dem_requested.emit()
    second = controller.active_wizard()
    assert first is second


def test_finishing_wizard_clears_active_reference(qtbot) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)
    wiz.reject()
    assert controller.active_wizard() is None


# ---------------------------------------------------------------------
# Import runner wiring
# ---------------------------------------------------------------------


def test_controller_runs_import_on_request_signal(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)

    asc = _write_asc(tmp_path / "demo.asc")
    out = tmp_path / "out.npz"
    wiz.set_source_path(asc)
    wiz.set_output_path(out)
    req = DEMImportRequest(
        source_asc_path=asc,
        output_npz_path=out,
        land_sea_mode=LandSeaMode.NODATA,
    )
    wiz.import_requested.emit(req)
    assert out.is_file()
    result_label = wiz.findChild(object, "DEMWizardResultLabel")
    assert "Imported OK" in result_label.text()  # type: ignore[union-attr]


def test_controller_reports_failure_on_missing_source(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)

    req = DEMImportRequest(
        source_asc_path=tmp_path / "ghost.asc",
        output_npz_path=tmp_path / "out.npz",
        land_sea_mode=LandSeaMode.NODATA,
    )
    wiz.import_requested.emit(req)
    label = wiz.findChild(object, "DEMWizardResultLabel")
    assert "Import failed" in label.text()  # type: ignore[union-attr]


def test_custom_runner_is_invoked(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Runner override lets tests capture the request without I/O."""
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    captured: list[DEMImportRequest] = []

    def fake_runner(req: DEMImportRequest) -> DEMImportSummary:
        captured.append(req)
        return DEMImportSummary(
            request=req,
            output_path=req.output_npz_path,
            grid_shape=(1, 2),
            cell_size_m=1.0,
            land_cell_count=2,
            sea_cell_count=0,
            nodata_cell_count=0,
        )

    controller = DEMImportController(map_editor=editor, parent=host, runner=fake_runner)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)
    req = DEMImportRequest(
        source_asc_path=tmp_path / "demo.asc",
        output_npz_path=tmp_path / "out.npz",
        land_sea_mode=LandSeaMode.NODATA,
    )
    wiz.import_requested.emit(req)
    assert captured == [req]
    label = wiz.findChild(object, "DEMWizardResultLabel")
    assert "Imported OK" in label.text()  # type: ignore[union-attr]


def test_custom_wizard_factory_is_used(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Factory override lets tests substitute a stub wizard."""
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    factory_calls: list[None] = []

    def custom_factory(parent: object) -> DEMImportWizard:
        factory_calls.append(None)
        return DEMImportWizard()

    controller = DEMImportController(
        map_editor=editor,
        parent=host,
        wizard_factory=custom_factory,  # type: ignore[arg-type]
    )
    editor.import_dem_requested.emit()
    assert len(factory_calls) == 1
    assert isinstance(controller.active_wizard(), DEMImportWizard)


# ---------------------------------------------------------------------
# MainWindow integration
# ---------------------------------------------------------------------


def test_main_window_wires_dem_import_controller(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activities import Activity
    from workbench.ui.editor.activity_pages import MapEditorPage
    from workbench.ui.editor.workspace import EditorWorkspace
    from workbench.ui.main_window import MainWindow
    from workbench.ui.workspace_selector import Workspace

    win = MainWindow(enable_3d_viewer=False)
    qtbot.addWidget(win)
    controller = win.dem_import_controller()
    assert isinstance(controller, DEMImportController)

    editor_page = win.page(Workspace.EDITOR)
    assert isinstance(editor_page, EditorWorkspace)
    map_page = editor_page.page(Activity.MAP)
    assert isinstance(map_page, MapEditorPage)
    map_page.map_editor().import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)


# ---------------------------------------------------------------------
# Smoke: end-to-end via the real run_dem_import default
# ---------------------------------------------------------------------


def test_default_runner_is_run_dem_import(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """When no runner is injected the controller uses the real backend."""
    host = QMainWindow()
    qtbot.addWidget(host)
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = DEMImportController(map_editor=editor, parent=host)
    editor.import_dem_requested.emit()
    wiz = controller.active_wizard()
    assert wiz is not None
    qtbot.addWidget(wiz)
    asc = _write_asc(tmp_path / "demo.asc")
    out = tmp_path / "out.npz"
    summary = run_dem_import(
        DEMImportRequest(
            source_asc_path=asc,
            output_npz_path=out,
            land_sea_mode=LandSeaMode.NODATA,
        )
    )
    # Direct call verifies the default runner is well-formed (the
    # other tests verify the controller routes to it).
    assert summary.output_path.is_file()
