"""Unit tests for app.dem_wizard (Phase 4 DEM Import Wizard E1)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.app.dem_wizard import (
    CropBounds,
    InterpolationMode,
    LandSeaMethod,
    VerticalReference,
    WizardConfig,
    crop_grid,
    derive_land_mask,
    execute,
)
from workbench.io.dem_import import DEMGrid

_VALID_ASC_BODY = """\
ncols        4
nrows        3
xllcorner    1000.0
yllcorner    2000.0
cellsize     10.0
NODATA_value -9999
70.0 80.0 90.0 100.0
40.0 50.0 60.0 -9999
10.0 20.0 30.0 -9999
"""


def _write_asc(path: Path) -> Path:
    path.write_text(_VALID_ASC_BODY, encoding="utf-8")
    return path


def _grid(elev: list[list[float]], *, cell: float = 10.0) -> DEMGrid:
    return DEMGrid(
        elevation=np.asarray(elev, dtype=np.float64),
        x_origin_m=0.0,
        y_origin_m=0.0,
        cell_size_m=cell,
    )


# ---------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------


def test_vertical_reference_values_match_plan_11_5_3() -> None:
    assert VerticalReference.EGM96.value == "egm96"
    assert VerticalReference.ELLIPSOID_WGS84.value == "ellipsoid_wgs84"
    assert VerticalReference.MSL_LOCAL.value == "msl_local"
    assert VerticalReference.NONE.value == "none"


def test_land_sea_method_values_match_plan_11_5_5() -> None:
    assert LandSeaMethod.AUTO_THRESHOLD.value == "auto_threshold"
    assert LandSeaMethod.NODATA.value == "nodata"
    assert LandSeaMethod.COASTLINE_FILE.value == "coastline_file"
    assert LandSeaMethod.ALL_LAND.value == "all_land"


def test_interpolation_mode_values_match_plan_11_6_1() -> None:
    assert InterpolationMode.BILINEAR.value == "bilinear"
    assert InterpolationMode.NEAREST.value == "nearest"
    assert InterpolationMode.BICUBIC.value == "bicubic"


# ---------------------------------------------------------------------
# CropBounds
# ---------------------------------------------------------------------


def test_crop_bounds_accept_valid_window() -> None:
    b = CropBounds(0.0, 100.0, -10.0, 90.0)
    assert b.east_min_m == 0.0
    assert b.east_max_m == 100.0


def test_crop_bounds_reject_inverted_east() -> None:
    with pytest.raises(ValueError, match=r"east_min_m \(10\.0\) must be"):
        CropBounds(10.0, 5.0, 0.0, 100.0)


def test_crop_bounds_reject_inverted_north() -> None:
    with pytest.raises(ValueError, match=r"north_min_m \(50\.0\) must be"):
        CropBounds(0.0, 10.0, 50.0, 50.0)


# ---------------------------------------------------------------------
# WizardConfig
# ---------------------------------------------------------------------


def test_wizard_config_defaults_match_plan_recommendations() -> None:
    cfg = WizardConfig(source_path=Path("a.asc"), output_path=Path("b.npz"))
    assert cfg.vertical_reference == VerticalReference.EGM96
    assert cfg.land_sea_method == LandSeaMethod.AUTO_THRESHOLD
    assert cfg.interpolation == InterpolationMode.BILINEAR
    assert cfg.crop_bounds is None
    assert cfg.land_sea_threshold_m == 0.5


def test_wizard_config_reject_coastline_without_path() -> None:
    with pytest.raises(ValueError, match=r"coastline_path required"):
        WizardConfig(
            source_path=Path("a.asc"),
            output_path=Path("b.npz"),
            land_sea_method=LandSeaMethod.COASTLINE_FILE,
        )


def test_wizard_config_reject_negative_threshold() -> None:
    with pytest.raises(ValueError, match=r"threshold_m must be >= 0"):
        WizardConfig(
            source_path=Path("a.asc"),
            output_path=Path("b.npz"),
            land_sea_threshold_m=-0.1,
        )


def test_wizard_config_accepts_coastline_with_path() -> None:
    cfg = WizardConfig(
        source_path=Path("a.asc"),
        output_path=Path("b.npz"),
        land_sea_method=LandSeaMethod.COASTLINE_FILE,
        coastline_path=Path("coast.geojson"),
    )
    assert cfg.coastline_path == Path("coast.geojson")


# ---------------------------------------------------------------------
# derive_land_mask
# ---------------------------------------------------------------------


def test_derive_land_mask_auto_threshold_excludes_below_threshold() -> None:
    grid = _grid([[0.0, 0.4, 0.5, 0.6], [1.0, 2.0, np.nan, 3.0]])
    mask = derive_land_mask(grid, LandSeaMethod.AUTO_THRESHOLD, threshold_m=0.5)
    # row 0: 0.0 not > 0.5, 0.4 not > 0.5, 0.5 not > 0.5, 0.6 > 0.5
    assert mask[0].tolist() == [False, False, False, True]
    # row 1: 1.0/2.0 land, NaN sea, 3.0 land
    assert mask[1].tolist() == [True, True, False, True]
    assert mask.dtype == np.bool_


def test_derive_land_mask_nodata_treats_finite_as_land() -> None:
    grid = _grid([[0.1, np.nan, -10.0], [5.0, 5.0, np.nan]])
    mask = derive_land_mask(grid, LandSeaMethod.NODATA)
    assert mask.tolist() == [[True, False, True], [True, True, False]]


def test_derive_land_mask_all_land_returns_full_true() -> None:
    grid = _grid([[np.nan, -100.0], [0.0, 5.0]])
    mask = derive_land_mask(grid, LandSeaMethod.ALL_LAND)
    assert mask.all()
    assert mask.shape == grid.elevation.shape


def test_derive_land_mask_coastline_file_not_implemented() -> None:
    grid = _grid([[1.0]])
    with pytest.raises(NotImplementedError, match=r"COASTLINE_FILE is deferred"):
        derive_land_mask(grid, LandSeaMethod.COASTLINE_FILE)


def test_derive_land_mask_custom_threshold() -> None:
    grid = _grid([[5.0, 9.99, 10.0, 10.01]])
    mask = derive_land_mask(grid, LandSeaMethod.AUTO_THRESHOLD, threshold_m=10.0)
    # only > 10.0 strictly is land
    assert mask[0].tolist() == [False, False, False, True]


# ---------------------------------------------------------------------
# crop_grid
# ---------------------------------------------------------------------


def test_crop_grid_full_window_returns_equivalent_grid() -> None:
    grid = _grid([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]], cell=10.0)
    out = crop_grid(grid, CropBounds(0.0, 30.0, 0.0, 20.0))
    assert out.elevation.shape == (2, 3)
    assert np.array_equal(out.elevation, grid.elevation)
    assert out.x_origin_m == 0.0
    assert out.y_origin_m == 0.0


def test_crop_grid_subwindow_snaps_to_cell_corners() -> None:
    # 4-col, 3-row grid, cell=10m, x=0..40, y=0..30
    grid = _grid(
        [
            [1.0, 2.0, 3.0, 4.0],
            [5.0, 6.0, 7.0, 8.0],
            [9.0, 10.0, 11.0, 12.0],
        ],
        cell=10.0,
    )
    # Request east 5..25, north 5..15 -> snap to col 0..3, row 0..2
    out = crop_grid(grid, CropBounds(5.0, 25.0, 5.0, 15.0))
    # col_start=floor(5/10)=0, col_stop=ceil(25/10)=3 -> cols 0..2 (3 cells)
    # row_start=floor(5/10)=0, row_stop=ceil(15/10)=2 -> rows 0..1 (2 cells)
    assert out.elevation.shape == (2, 3)
    assert out.x_origin_m == 0.0
    assert out.y_origin_m == 0.0
    assert out.cell_size_m == 10.0
    assert np.array_equal(out.elevation, grid.elevation[0:2, 0:3])


def test_crop_grid_rejects_non_overlapping_bounds() -> None:
    grid = _grid([[1.0]], cell=10.0)
    with pytest.raises(ValueError, match=r"do not overlap grid extent"):
        crop_grid(grid, CropBounds(100.0, 200.0, 100.0, 200.0))


def test_crop_grid_clamps_bounds_to_grid_extent() -> None:
    # _grid stores the array as-is (no ESRI flip); row 0 col 0 -> elevation[0,0]
    grid = _grid([[1.0, 2.0], [3.0, 4.0]], cell=10.0)
    out = crop_grid(grid, CropBounds(-50.0, 5.0, -50.0, 5.0))
    # snap window to cells 0..0 (col), rows 0..0 -> single cell
    assert out.elevation.shape == (1, 1)
    assert out.elevation[0, 0] == 1.0


# ---------------------------------------------------------------------
# execute (end-to-end)
# ---------------------------------------------------------------------


def test_execute_full_roundtrip(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "terrain.npz"

    written = execute(
        WizardConfig(
            source_path=asc,
            output_path=out,
            vertical_reference=VerticalReference.EGM96,
            land_sea_method=LandSeaMethod.AUTO_THRESHOLD,
            land_sea_threshold_m=0.5,
        )
    )
    assert written.resolve() == out.resolve()
    assert out.is_file()

    with np.load(out) as data:
        # rows: 3 rows x 4 cols, flipped so row 0 = south = "10.0 20.0 30.0 -9999"
        elev = data["elevation"]
        mask = data["land_mask"]
        cell = data["cell_size_m"]
    assert elev.shape == (3, 4)
    # south row first
    np.testing.assert_array_equal(
        np.isnan(elev[0]),
        [False, False, False, True],
    )
    # Auto-threshold > 0.5: all listed positive values are > 0.5, NaN -> sea
    assert mask[0].tolist() == [True, True, True, False]
    assert float(cell) == 10.0


def test_execute_with_crop_writes_smaller_grid(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "cropped.npz"

    # Grid is 4 cols (1000..1040) x 3 rows (2000..2030); ask for col 0..1
    crop = CropBounds(
        east_min_m=1000.0,
        east_max_m=1020.0,
        north_min_m=2000.0,
        north_max_m=2030.0,
    )
    execute(
        WizardConfig(
            source_path=asc,
            output_path=out,
            crop_bounds=crop,
            land_sea_method=LandSeaMethod.NODATA,
        )
    )
    with np.load(out) as data:
        elev = data["elevation"]
        x0 = float(data["x_origin_m"])
    assert elev.shape == (3, 2)
    assert x0 == 1000.0


def test_execute_default_threshold_and_method_match_wizard_config(
    tmp_path: Path,
) -> None:
    """Default config (no overrides) matches plan-recommended defaults."""
    asc = _write_asc(tmp_path / "src.asc")
    out = tmp_path / "default.npz"
    execute(WizardConfig(source_path=asc, output_path=out))
    with np.load(out) as data:
        # NODATA -> NaN -> not land (default threshold 0.5 > NaN is False)
        mask = data["land_mask"]
    # After ESRI flip, row 0 = south = "10 20 30 -9999"; NODATA cells live
    # in (row 0, col 3) and (row 1, col 3). Both must be sea under
    # AUTO_THRESHOLD default. Row 2 col 3 = 100.0 -> land.
    assert not bool(mask[0, 3])
    assert not bool(mask[1, 3])
    assert bool(mask[2, 3])
