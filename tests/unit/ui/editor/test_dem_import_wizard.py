"""Unit tests for the DEM Import Wizard (Phase 4 dem_import_wizard E3)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")

from workbench.io.dem_import import (
    DEMImportRequest,
    DEMImportSummary,
    LandSeaMode,
    run_dem_import,
)
from workbench.ui.editor.map_editor import DEMImportWizard

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Default state
# ---------------------------------------------------------------------


def test_wizard_starts_on_source_page(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    assert wiz.current_page_index() == 0


def test_wizard_default_mode_is_nodata(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    assert wiz.land_sea_mode() is LandSeaMode.NODATA


def test_wizard_default_threshold_is_half_metre(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    assert wiz.threshold_m() == 0.5


def test_wizard_starts_without_paths(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    assert wiz.source_path() is None
    assert wiz.output_path() is None


# ---------------------------------------------------------------------
# Path setters
# ---------------------------------------------------------------------


def test_set_source_path_updates_line_edit(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    src = tmp_path / "demo.asc"
    wiz.set_source_path(src)
    assert wiz.source_path() == src
    line = wiz.findChild(object, "DEMWizardSourceLine")
    assert line is not None
    assert line.text() == str(src)  # type: ignore[attr-defined]


def test_set_output_path_updates_line_edit(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    out = tmp_path / "terrain.npz"
    wiz.set_output_path(out)
    assert wiz.output_path() == out
    line = wiz.findChild(object, "DEMWizardOutputLine")
    assert line is not None
    assert line.text() == str(out)  # type: ignore[attr-defined]


# ---------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------


def test_next_button_disabled_without_source(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    next_btn = wiz.findChild(object, "DEMWizardNextBtn")
    assert next_btn is not None
    assert next_btn.isEnabled() is False  # type: ignore[attr-defined]


def test_next_button_enabled_after_source(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_source_path(tmp_path / "demo.asc")
    next_btn = wiz.findChild(object, "DEMWizardNextBtn")
    assert next_btn is not None
    assert next_btn.isEnabled() is True  # type: ignore[attr-defined]


def test_back_button_disabled_on_first_page(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    back_btn = wiz.findChild(object, "DEMWizardBackBtn")
    assert back_btn is not None
    assert back_btn.isEnabled() is False  # type: ignore[attr-defined]


def test_summary_page_swaps_next_for_import_button(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """On the summary page, Next is replaced by Import. We check the
    explicit visibility property (setVisible state), not isVisible(),
    because the dialog is not shown in headless tests."""
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_source_path(tmp_path / "demo.asc")
    wiz.set_output_path(tmp_path / "out.npz")
    wiz.go_to_page(3)
    next_btn = wiz.findChild(object, "DEMWizardNextBtn")
    import_btn = wiz.findChild(object, "DEMWizardImportBtn")
    assert next_btn.isHidden() is True  # type: ignore[union-attr]
    assert import_btn.isHidden() is False  # type: ignore[union-attr]


def test_step_label_reflects_current_page(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    label = wiz.findChild(object, "DEMWizardStepLabel")
    assert label is not None
    assert "Step 1 / 4" in label.text()  # type: ignore[attr-defined]
    wiz.set_source_path(tmp_path / "demo.asc")
    wiz.go_to_page(1)
    assert "Step 2 / 4" in label.text()  # type: ignore[attr-defined]


# ---------------------------------------------------------------------
# Land/Sea mode
# ---------------------------------------------------------------------


def test_threshold_spin_disabled_for_non_threshold_modes(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    spin = wiz.findChild(object, "DEMWizardThresholdSpin")
    assert spin is not None
    # Default mode = NODATA; spin should be disabled.
    assert spin.isEnabled() is False  # type: ignore[attr-defined]


def test_threshold_spin_enabled_for_auto_threshold(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_land_sea_mode(LandSeaMode.AUTO_THRESHOLD)
    spin = wiz.findChild(object, "DEMWizardThresholdSpin")
    assert spin is not None
    assert spin.isEnabled() is True  # type: ignore[attr-defined]
    assert wiz.land_sea_mode() is LandSeaMode.AUTO_THRESHOLD


def test_threshold_spin_value_round_trips(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_land_sea_mode(LandSeaMode.AUTO_THRESHOLD)
    wiz.set_threshold_m(2.5)
    assert wiz.threshold_m() == 2.5


# ---------------------------------------------------------------------
# Import signal
# ---------------------------------------------------------------------


def test_import_button_disabled_without_paths(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.go_to_page(3)
    import_btn = wiz.findChild(object, "DEMWizardImportBtn")
    assert import_btn is not None
    assert import_btn.isEnabled() is False  # type: ignore[attr-defined]


def test_import_button_emits_request(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_source_path(tmp_path / "demo.asc")
    wiz.set_output_path(tmp_path / "out.npz")
    wiz.set_land_sea_mode(LandSeaMode.AUTO_THRESHOLD)
    wiz.set_threshold_m(1.5)
    wiz.go_to_page(3)

    received: list[DEMImportRequest] = []
    wiz.import_requested.connect(received.append)
    btn = wiz.findChild(object, "DEMWizardImportBtn")
    assert btn is not None
    btn.click()  # type: ignore[attr-defined]
    assert len(received) == 1
    req = received[0]
    assert req.source_asc_path == tmp_path / "demo.asc"
    assert req.output_npz_path == tmp_path / "out.npz"
    assert req.land_sea_mode is LandSeaMode.AUTO_THRESHOLD
    assert req.threshold_m == 1.5


def test_summary_label_renders_source_output_mode(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_source_path(tmp_path / "demo.asc")
    wiz.set_output_path(tmp_path / "out.npz")
    wiz.go_to_page(3)
    label = wiz.findChild(object, "DEMWizardSummaryLabel")
    assert label is not None
    text = label.text()  # type: ignore[attr-defined]
    assert "demo.asc" in text
    assert "out.npz" in text
    assert "NODATA" in text


# ---------------------------------------------------------------------
# Cancel button
# ---------------------------------------------------------------------


def test_cancel_button_rejects_dialog(qtbot) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    rejected: list[int] = []
    wiz.rejected.connect(lambda: rejected.append(1))
    btn = wiz.findChild(object, "DEMWizardCancelBtn")
    assert btn is not None
    btn.click()  # type: ignore[attr-defined]
    assert rejected == [1]


# ---------------------------------------------------------------------
# Report helpers
# ---------------------------------------------------------------------


def _write_asc(path: Path) -> Path:
    path.write_text(
        "ncols 2\nnrows 1\nxllcorner 0\nyllcorner 0\ncellsize 1\nNODATA_value -9999\n10 20\n",
        encoding="utf-8",
    )
    return path


def test_report_import_result_renders_summary(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: wizard collects request, host calls run_dem_import,
    summary page shows actual file landed + cell counts."""
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    asc = _write_asc(tmp_path / "demo.asc")
    out = tmp_path / "out.npz"
    wiz.set_source_path(asc)
    wiz.set_output_path(out)
    wiz.go_to_page(3)

    received: list[DEMImportSummary] = []

    def host_handler(req: DEMImportRequest) -> None:
        received.append(run_dem_import(req))
        wiz.report_import_result(received[-1])

    wiz.import_requested.connect(host_handler)
    btn = wiz.findChild(object, "DEMWizardImportBtn")
    btn.click()  # type: ignore[union-attr]
    assert len(received) == 1
    assert out.is_file()
    np.load(out)  # archive is readable
    result_label = wiz.findChild(object, "DEMWizardResultLabel")
    assert result_label is not None
    text = result_label.text()  # type: ignore[attr-defined]
    assert "Imported OK" in text
    assert str(out) in text


def test_report_import_error_renders_failure(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    wiz = DEMImportWizard()
    qtbot.addWidget(wiz)
    wiz.set_source_path(tmp_path / "missing.asc")
    wiz.set_output_path(tmp_path / "out.npz")
    wiz.go_to_page(3)

    def host_handler(req: DEMImportRequest) -> None:
        try:
            run_dem_import(req)
        except FileNotFoundError as exc:
            wiz.report_import_error(str(exc))

    wiz.import_requested.connect(host_handler)
    btn = wiz.findChild(object, "DEMWizardImportBtn")
    btn.click()  # type: ignore[union-attr]
    label = wiz.findChild(object, "DEMWizardResultLabel")
    assert label is not None
    assert "Import failed" in label.text()  # type: ignore[attr-defined]
