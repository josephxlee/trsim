"""Unit tests for the Map Editor page + DEM Import Wizard wiring (Phase 4 E3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.activity_pages import MapEditorPage
from workbench.ui.editor.map_editor import DEMImportWizard

pytestmark = pytest.mark.qt

_VALID_ASC_BODY = """\
ncols        3
nrows        2
xllcorner    0.0
yllcorner    0.0
cellsize     10.0
NODATA_value -9999
30.0 40.0 50.0
10.0 20.0 30.0
"""


def _write_asc(path: Path) -> Path:
    path.write_text(_VALID_ASC_BODY, encoding="utf-8")
    return path


def test_default_state_no_active_wizard(qtbot) -> None:  # type: ignore[no-untyped-def]
    page = MapEditorPage()
    qtbot.addWidget(page)
    assert page.active_wizard() is None
    assert page.last_imported_path() is None


def test_import_dem_signal_opens_wizard(qtbot) -> None:  # type: ignore[no-untyped-def]
    page = MapEditorPage()
    qtbot.addWidget(page)
    page.map_editor().import_dem_requested.emit()
    wiz = page.active_wizard()
    assert wiz is not None
    assert isinstance(wiz, DEMImportWizard)
    assert wiz.isModal() is True


def test_wizard_completed_records_path_and_history(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    page = MapEditorPage()
    qtbot.addWidget(page)
    src = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "terrain.npz"

    page.map_editor().import_dem_requested.emit()
    wiz = page.active_wizard()
    assert wiz is not None
    wiz.source_page().set_source_path(src)
    wiz.save_page().set_output_path(out)
    wiz.accept()

    assert page.last_imported_path() == out
    history = page.map_editor().history_list()
    assert history.count() == 1
    assert "Imported DEM" in history.item(0).text()
    assert str(out) in history.item(0).text()
    # accept() closes the wizard; finished slot clears the reference.
    assert page.active_wizard() is None
    # And the file actually got written by execute().
    assert out.is_file()
    with np.load(out) as data:
        assert data["elevation"].shape == (2, 3)


def test_wizard_failure_appends_failure_entry(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    page = MapEditorPage()
    qtbot.addWidget(page)

    page.map_editor().import_dem_requested.emit()
    wiz = page.active_wizard()
    assert wiz is not None
    # Trigger build_config() ValueError -> import_failed -> early return,
    # so the wizard is NOT closed (super().accept() is not reached).
    wiz.accept()

    history = page.map_editor().history_list()
    assert history.count() == 1
    assert history.item(0).text().startswith("Import failed:")
    assert page.last_imported_path() is None
    # Wizard stays alive after a failure (user can fix inputs and retry).
    assert page.active_wizard() is wiz


def test_multiple_imports_accumulate_history_newest_first(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    page = MapEditorPage()
    qtbot.addWidget(page)
    src = _write_asc(tmp_path / "src.asc")
    out_a = tmp_path / "a.npz"
    out_b = tmp_path / "b.npz"

    # First import.
    page.map_editor().import_dem_requested.emit()
    wiz = page.active_wizard()
    assert wiz is not None
    wiz.source_page().set_source_path(src)
    wiz.save_page().set_output_path(out_a)
    wiz.accept()

    # Second import via the same signal.
    page.map_editor().import_dem_requested.emit()
    wiz2 = page.active_wizard()
    assert wiz2 is not None
    assert wiz2 is not wiz
    wiz2.source_page().set_source_path(src)
    wiz2.save_page().set_output_path(out_b)
    wiz2.accept()

    history = page.map_editor().history_list()
    assert history.count() == 2
    assert str(out_b) in history.item(0).text()  # newest first
    assert str(out_a) in history.item(1).text()
    assert page.last_imported_path() == out_b


def test_wizard_signals_disconnect_after_close(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """After the wizard closes, the page should not hold a stale reference."""
    page = MapEditorPage()
    qtbot.addWidget(page)
    src = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "terrain.npz"

    page.map_editor().import_dem_requested.emit()
    wiz = page.active_wizard()
    assert wiz is not None
    wiz.source_page().set_source_path(src)
    wiz.save_page().set_output_path(out)
    wiz.accept()
    # active_wizard() drops back to None after successful Finish.
    assert page.active_wizard() is None
