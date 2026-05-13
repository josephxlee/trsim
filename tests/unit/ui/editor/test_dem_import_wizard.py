"""Unit tests for the DEM Import Wizard (Phase 4 E2)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QRadioButton

from workbench.app.dem_wizard import (
    CropBounds,
    InterpolationMode,
    LandSeaMethod,
    VerticalReference,
)
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


# ---------------------------------------------------------------------
# Construction + 7 pages
# ---------------------------------------------------------------------


def test_wizard_has_seven_pages_in_plan_order(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    # IDs explicitly assigned PAGE_SOURCE..PAGE_SAVE = 0..6
    assert sorted(w.pageIds()) == [0, 1, 2, 3, 4, 5, 6]
    assert w.startId() == DEMImportWizard.PAGE_SOURCE


def test_wizard_default_choices_match_plan_recommendations(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    assert w.vertical_page().vertical_reference() == VerticalReference.EGM96
    assert w.land_sea_page().land_sea_method() == LandSeaMethod.AUTO_THRESHOLD
    assert w.land_sea_page().land_sea_threshold_m() == pytest.approx(0.5)
    assert w.interpolation_page().interpolation() == InterpolationMode.BILINEAR
    assert w.region_page().crop_bounds() is None


# ---------------------------------------------------------------------
# Page-level setter/getter round-trips
# ---------------------------------------------------------------------


def test_source_page_path_roundtrip(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    p = tmp_path / "src.asc"
    p.touch()
    w.source_page().set_source_path(p)
    assert w.source_page().source_path() == p
    assert w.source_page().isComplete() is True


def test_source_page_empty_path_is_incomplete(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    assert w.source_page().source_path() is None
    assert w.source_page().isComplete() is False


def test_vertical_reference_setter_updates_radio(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.vertical_page().set_vertical_reference(VerticalReference.MSL_LOCAL)
    assert w.vertical_page().vertical_reference() == VerticalReference.MSL_LOCAL


def test_region_page_full_extent_yields_none(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    assert w.region_page().crop_bounds() is None


def test_region_page_custom_crop_yields_bounds(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    bounds = CropBounds(0.0, 100.0, -50.0, 50.0)
    w.region_page().set_crop_bounds(bounds)
    out = w.region_page().crop_bounds()
    assert out is not None
    assert out.east_min_m == pytest.approx(0.0)
    assert out.east_max_m == pytest.approx(100.0)
    assert out.north_min_m == pytest.approx(-50.0)
    assert out.north_max_m == pytest.approx(50.0)


def test_region_page_setter_with_none_returns_to_full(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.region_page().set_crop_bounds(CropBounds(0.0, 1.0, 0.0, 1.0))
    assert w.region_page().crop_bounds() is not None
    w.region_page().set_crop_bounds(None)
    assert w.region_page().crop_bounds() is None


def test_land_sea_method_and_threshold_roundtrip(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.land_sea_page().set_land_sea(LandSeaMethod.NODATA, threshold_m=1.25)
    assert w.land_sea_page().land_sea_method() == LandSeaMethod.NODATA
    assert w.land_sea_page().land_sea_threshold_m() == pytest.approx(1.25)


def test_land_sea_coastline_radio_is_disabled(qtbot) -> None:  # type: ignore[no-untyped-def]
    """COASTLINE_FILE backend is deferred — UI must lock the radio."""
    w = DEMImportWizard()
    qtbot.addWidget(w)
    radios = w.land_sea_page().findChildren(QRadioButton)
    by_name = {r.objectName(): r for r in radios}
    assert "DEMWizardLS_coastline_file" in by_name
    assert by_name["DEMWizardLS_coastline_file"].isEnabled() is False
    # Other 3 methods remain selectable.
    for method in (
        LandSeaMethod.AUTO_THRESHOLD,
        LandSeaMethod.NODATA,
        LandSeaMethod.ALL_LAND,
    ):
        assert by_name[f"DEMWizardLS_{method.value}"].isEnabled() is True


def test_interpolation_roundtrip(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.interpolation_page().set_interpolation(InterpolationMode.NEAREST)
    assert w.interpolation_page().interpolation() == InterpolationMode.NEAREST


def test_save_page_path_roundtrip(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    p = tmp_path / "out.npz"
    w.save_page().set_output_path(p)
    assert w.save_page().output_path() == p
    assert w.save_page().isComplete() is True


# ---------------------------------------------------------------------
# build_config
# ---------------------------------------------------------------------


def test_build_config_collects_all_pages(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    src = tmp_path / "src.asc"
    src.touch()
    out = tmp_path / "out.npz"

    w.source_page().set_source_path(src)
    w.save_page().set_output_path(out)
    w.vertical_page().set_vertical_reference(VerticalReference.EGM96)
    w.region_page().set_crop_bounds(CropBounds(0.0, 50.0, 0.0, 50.0))
    w.land_sea_page().set_land_sea(LandSeaMethod.ALL_LAND, threshold_m=2.0)
    w.interpolation_page().set_interpolation(InterpolationMode.BICUBIC)

    cfg = w.build_config()
    assert cfg.source_path == src
    assert cfg.output_path == out
    assert cfg.vertical_reference == VerticalReference.EGM96
    assert cfg.crop_bounds == CropBounds(0.0, 50.0, 0.0, 50.0)
    assert cfg.land_sea_method == LandSeaMethod.ALL_LAND
    assert cfg.land_sea_threshold_m == pytest.approx(2.0)
    assert cfg.interpolation == InterpolationMode.BICUBIC


def test_build_config_rejects_missing_source(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.save_page().set_output_path(tmp_path / "out.npz")
    with pytest.raises(ValueError, match=r"source path is empty"):
        w.build_config()


def test_build_config_rejects_missing_output(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    src = tmp_path / "src.asc"
    src.touch()
    w.source_page().set_source_path(src)
    with pytest.raises(ValueError, match=r"Output path is empty"):
        w.build_config()


# ---------------------------------------------------------------------
# accept() — end-to-end happy path + failures
# ---------------------------------------------------------------------


def test_accept_runs_execute_and_emits_import_completed(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    src = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "terrain.npz"

    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.source_page().set_source_path(src)
    w.save_page().set_output_path(out)

    received: list[Path] = []
    w.import_completed.connect(received.append)
    failed: list[str] = []
    w.import_failed.connect(failed.append)

    w.accept()
    assert failed == []
    assert len(received) == 1
    assert received[0].resolve() == out.resolve()
    assert out.is_file()
    with np.load(out) as data:
        assert data["elevation"].shape == (2, 3)


def test_accept_missing_source_emits_import_failed(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    out = tmp_path / "terrain.npz"
    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.source_page().set_source_path(tmp_path / "does_not_exist.asc")
    w.save_page().set_output_path(out)

    received: list[Path] = []
    failed: list[str] = []
    w.import_completed.connect(received.append)
    w.import_failed.connect(failed.append)

    w.accept()
    assert received == []
    assert len(failed) == 1
    assert "not found" in failed[0].lower()
    assert not out.exists()


def test_accept_with_empty_paths_emits_import_failed(qtbot) -> None:  # type: ignore[no-untyped-def]
    w = DEMImportWizard()
    qtbot.addWidget(w)
    failed: list[str] = []
    received: list[Path] = []
    w.import_completed.connect(received.append)
    w.import_failed.connect(failed.append)
    w.accept()
    assert received == []
    assert len(failed) == 1
    assert "empty" in failed[0].lower()


def test_accept_with_coastline_method_emits_import_failed(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """COASTLINE_FILE radio is locked, but force-selecting yields a failure."""
    src = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "out.npz"

    w = DEMImportWizard()
    qtbot.addWidget(w)
    w.source_page().set_source_path(src)
    w.save_page().set_output_path(out)

    # Force-pick the deferred coastline radio (UI disables it by default).
    radios = w.land_sea_page().findChildren(QRadioButton)
    by_name = {r.objectName(): r for r in radios}
    coast = by_name["DEMWizardLS_coastline_file"]
    coast.setEnabled(True)
    coast.setChecked(True)
    # The wizard doesn't expose a coastline_path control yet, so
    # WizardConfig.__post_init__ rejects -> import_failed signal.

    received: list[Path] = []
    failed: list[str] = []
    w.import_completed.connect(received.append)
    w.import_failed.connect(failed.append)
    w.accept()
    assert received == []
    assert len(failed) == 1
