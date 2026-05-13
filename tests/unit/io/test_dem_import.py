"""Unit tests for io.dem_import (Phase 3 D4)."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from workbench.io.dem_import import (
    DEMGrid,
    LandSeaMode,
    compute_land_mask,
    import_dem_to_terrain_npz,
    read_esri_ascii_grid,
    write_terrain_npz,
)

_VALID_ASC_BODY = """\
ncols        3
nrows        2
xllcorner    1000.0
yllcorner    2000.0
cellsize     10.0
NODATA_value -9999
30.0 40.0 50.0
10.0 20.0 30.0
"""


def _write_asc(path: Path, body: str = _VALID_ASC_BODY) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


# ---------------------------------------------------------------------
# read_esri_ascii_grid
# ---------------------------------------------------------------------


def test_read_basic_grid_north_up_orientation(tmp_path: Path) -> None:
    """ESRI rows go top-to-bottom; reader flips so row 0 = south."""
    asc = _write_asc(tmp_path / "demo.asc")
    grid = read_esri_ascii_grid(asc)
    assert isinstance(grid, DEMGrid)
    assert grid.elevation.shape == (2, 3)
    # Row 0 (south) = the *second* ESRI row (10, 20, 30).
    np.testing.assert_array_equal(grid.elevation[0], np.array([10.0, 20.0, 30.0]))
    np.testing.assert_array_equal(grid.elevation[1], np.array([30.0, 40.0, 50.0]))


def test_read_grid_header_fields(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "demo.asc")
    grid = read_esri_ascii_grid(asc)
    assert grid.x_origin_m == 1000.0
    assert grid.y_origin_m == 2000.0
    assert grid.cell_size_m == 10.0
    assert grid.nodata_value == -9999.0


def test_read_grid_converts_nodata_to_nan(tmp_path: Path) -> None:
    body = """\
ncols        2
nrows        2
xllcorner    0.0
yllcorner    0.0
cellsize     5.0
NODATA_value -9999
-9999 30.0
10.0 -9999
"""
    asc = _write_asc(tmp_path / "with_nodata.asc", body)
    grid = read_esri_ascii_grid(asc)
    # After flip: row 0 = south = [10.0, NaN], row 1 = north = [NaN, 30.0]
    assert grid.elevation[0, 0] == 10.0
    assert np.isnan(grid.elevation[0, 1])
    assert np.isnan(grid.elevation[1, 0])
    assert grid.elevation[1, 1] == 30.0


def test_read_grid_default_nodata_when_header_missing(tmp_path: Path) -> None:
    """NODATA_value header is optional; defaults to -9999."""
    body = """\
ncols        2
nrows        1
xllcorner    0
yllcorner    0
cellsize     1
10.0 20.0
"""
    asc = _write_asc(tmp_path / "no_nodata.asc", body)
    grid = read_esri_ascii_grid(asc)
    assert grid.nodata_value == -9999.0
    np.testing.assert_array_equal(grid.elevation, np.array([[10.0, 20.0]]))


def test_read_grid_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"DEM file not found"):
        read_esri_ascii_grid(tmp_path / "ghost.asc")


def test_read_grid_missing_required_header_raises(tmp_path: Path) -> None:
    body = """\
ncols        2
nrows        1
cellsize     1
10.0 20.0
"""
    asc = _write_asc(tmp_path / "no_origin.asc", body)
    with pytest.raises(ValueError, match=r"missing required header"):
        read_esri_ascii_grid(asc)


def test_read_grid_wrong_row_count_raises(tmp_path: Path) -> None:
    body = """\
ncols        2
nrows        3
xllcorner    0
yllcorner    0
cellsize     1
1 2
3 4
"""
    asc = _write_asc(tmp_path / "short.asc", body)
    with pytest.raises(ValueError, match=r"expected 3 body rows"):
        read_esri_ascii_grid(asc)


def test_read_grid_wrong_cell_count_raises(tmp_path: Path) -> None:
    body = """\
ncols        3
nrows        1
xllcorner    0
yllcorner    0
cellsize     1
1 2
"""
    asc = _write_asc(tmp_path / "short_row.asc", body)
    with pytest.raises(ValueError, match=r"has 2 cells"):
        read_esri_ascii_grid(asc)


def test_read_grid_non_numeric_body_raises(tmp_path: Path) -> None:
    body = """\
ncols        2
nrows        1
xllcorner    0
yllcorner    0
cellsize     1
abc 2
"""
    asc = _write_asc(tmp_path / "bad.asc", body)
    with pytest.raises(ValueError, match=r"non-numeric body row"):
        read_esri_ascii_grid(asc)


# ---------------------------------------------------------------------
# write_terrain_npz
# ---------------------------------------------------------------------


def test_write_terrain_npz_round_trip(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "demo.asc")
    grid = read_esri_ascii_grid(asc)
    npz = write_terrain_npz(tmp_path / "demo.npz", grid)
    assert npz.is_file()
    loaded = np.load(npz)
    np.testing.assert_array_equal(loaded["elevation"], grid.elevation)
    assert float(loaded["x_origin_m"]) == grid.x_origin_m
    assert float(loaded["y_origin_m"]) == grid.y_origin_m
    assert float(loaded["cell_size_m"]) == grid.cell_size_m
    # Default land mask: every finite-elevation cell is land.
    np.testing.assert_array_equal(loaded["land_mask"], np.isfinite(grid.elevation))


def test_write_terrain_npz_with_explicit_land_mask(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "demo.asc")
    grid = read_esri_ascii_grid(asc)
    mask = np.array([[True, False, True], [False, True, False]], dtype=np.bool_)
    npz = write_terrain_npz(tmp_path / "demo.npz", grid, land_mask=mask)
    loaded = np.load(npz)
    np.testing.assert_array_equal(loaded["land_mask"], mask)


def test_write_terrain_npz_rejects_mask_shape_mismatch(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "demo.asc")
    grid = read_esri_ascii_grid(asc)
    bad_mask = np.zeros((4, 4), dtype=np.bool_)
    with pytest.raises(ValueError, match=r"land_mask shape"):
        write_terrain_npz(tmp_path / "demo.npz", grid, land_mask=bad_mask)


def test_write_terrain_npz_default_mask_treats_nan_as_sea(tmp_path: Path) -> None:
    """NaN (NODATA) cells default to sea (mask = False)."""
    body = """\
ncols        2
nrows        2
xllcorner    0
yllcorner    0
cellsize     1
NODATA_value -9999
-9999 30
10 20
"""
    asc = _write_asc(tmp_path / "demo.asc", body)
    grid = read_esri_ascii_grid(asc)
    npz = write_terrain_npz(tmp_path / "demo.npz", grid)
    loaded = np.load(npz)
    mask = loaded["land_mask"]
    # Row 0 (south) = [10, 20] all land. Row 1 (north) = [NaN, 30],
    # only the 30 cell is land.
    assert bool(mask[0, 0]) is True
    assert bool(mask[0, 1]) is True
    assert bool(mask[1, 0]) is False  # NODATA -> sea
    assert bool(mask[1, 1]) is True


# ---------------------------------------------------------------------
# import_dem_to_terrain_npz (end-to-end helper)
# ---------------------------------------------------------------------


def test_import_helper_writes_npz_from_asc(tmp_path: Path) -> None:
    asc = _write_asc(tmp_path / "demo.asc")
    npz = import_dem_to_terrain_npz(asc, tmp_path / "out.npz")
    assert npz.is_file()
    loaded = np.load(npz)
    assert loaded["elevation"].shape == (2, 3)


# ---------------------------------------------------------------------
# LandSeaMode + compute_land_mask (Phase 4 dem_import_wizard E1)
# ---------------------------------------------------------------------


def _grid_with_elevations(elevations: list[list[float]]) -> DEMGrid:
    arr = np.asarray(elevations, dtype=np.float64)
    return DEMGrid(
        elevation=arr,
        x_origin_m=0.0,
        y_origin_m=0.0,
        cell_size_m=1.0,
        nodata_value=-9999.0,
    )


def test_land_sea_mode_string_values() -> None:
    """StrEnum values are stable — wizard combo + TOML round-trip."""
    assert LandSeaMode.AUTO_THRESHOLD.value == "auto_threshold"
    assert LandSeaMode.NODATA.value == "nodata"
    assert LandSeaMode.ALL_LAND.value == "all_land"


def test_compute_land_mask_auto_threshold_classifies_above_threshold() -> None:
    grid = _grid_with_elevations([[-1.0, 0.0, 0.5, 0.51, 10.0]])
    mask = compute_land_mask(grid, LandSeaMode.AUTO_THRESHOLD, threshold_m=0.5)
    assert mask.dtype == np.bool_
    np.testing.assert_array_equal(mask, np.array([[False, False, False, True, True]]))


def test_compute_land_mask_auto_threshold_custom_threshold() -> None:
    grid = _grid_with_elevations([[0.0, 5.0, 10.0]])
    mask = compute_land_mask(grid, LandSeaMode.AUTO_THRESHOLD, threshold_m=5.0)
    np.testing.assert_array_equal(mask, np.array([[False, False, True]]))


def test_compute_land_mask_auto_threshold_nan_is_sea() -> None:
    grid = _grid_with_elevations([[np.nan, 1.0, 100.0]])
    mask = compute_land_mask(grid, LandSeaMode.AUTO_THRESHOLD, threshold_m=0.5)
    np.testing.assert_array_equal(mask, np.array([[False, True, True]]))


def test_compute_land_mask_nodata_treats_nan_as_sea() -> None:
    grid = _grid_with_elevations([[np.nan, -100.0, 0.0, 50.0]])
    mask = compute_land_mask(grid, LandSeaMode.NODATA)
    np.testing.assert_array_equal(mask, np.array([[False, True, True, True]]))


def test_compute_land_mask_all_land_marks_every_cell() -> None:
    grid = _grid_with_elevations([[np.nan, -100.0, 0.0, 50.0]])
    mask = compute_land_mask(grid, LandSeaMode.ALL_LAND)
    np.testing.assert_array_equal(mask, np.ones((1, 4), dtype=np.bool_))


def test_compute_land_mask_auto_threshold_rejects_nan_threshold() -> None:
    grid = _grid_with_elevations([[1.0]])
    with pytest.raises(ValueError, match=r"threshold_m must be finite"):
        compute_land_mask(grid, LandSeaMode.AUTO_THRESHOLD, threshold_m=float("nan"))


def test_compute_land_mask_shape_matches_elevation() -> None:
    grid = _grid_with_elevations([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
    for mode in LandSeaMode:
        mask = compute_land_mask(grid, mode)
        assert mask.shape == grid.elevation.shape, (mode, mask.shape)
