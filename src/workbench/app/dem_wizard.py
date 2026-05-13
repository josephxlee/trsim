"""DEM Import Wizard model (Phase 4 + plan/11 § 11.5).

The Editor's "Import DEM..." action opens a 7-step wizard
(plan/11 § 11.5.2 + plan/13 § 13.4) that turns an external DEM file
into the workbench's native ``terrain.npz``. The UI layer (PySide6
QWizard, :mod:`workbench.ui.editor.map_editor.dem_import_wizard`)
collects user choices into :class:`WizardConfig` and calls
:func:`execute`.

This module is the App-layer orchestrator: pure Python (no Qt),
side-effects limited to delegating into :mod:`workbench.io.dem_import`.

7 step layout (plan/11 § 11.5.2)::

    [Step 1] Source select + format detect       -> source_path
    [Step 2] Vertical reference dialog           -> vertical_reference
    [Step 3] Region select                       -> crop_bounds | None
    [Step 4] Land/Sea derivation                 -> land_sea_method
    [Step 5] Coordinate/altitude conversion      -> (MVP no-op, CRS=ENU)
    [Step 6] Grid interpolation                  -> interpolation
    [Step 7] Workbench Native save               -> output_path

Step 5 + 6 are placeholder records in the MVP - the only supported
external format is **ESRI ASCII grid** (.asc) and the only output
format is terrain.npz with the same cell size + CRS. The wizard
keeps the fields so that a future GeoTIFF / SRTM importer can
populate them without changing the public surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from workbench.io.dem_import import (
    DEMGrid,
    read_esri_ascii_grid,
    write_terrain_npz,
)


class VerticalReference(StrEnum):
    """Vertical datum choice per plan/11 § 11.5.3."""

    ELLIPSOID_WGS84 = "ellipsoid_wgs84"
    EGM96 = "egm96"
    MSL_LOCAL = "msl_local"
    NONE = "none"


class LandSeaMethod(StrEnum):
    """Land/sea derivation choice per plan/11 § 11.5.5."""

    AUTO_THRESHOLD = "auto_threshold"
    NODATA = "nodata"
    COASTLINE_FILE = "coastline_file"
    ALL_LAND = "all_land"


class InterpolationMode(StrEnum):
    """Grid resampling choice per plan/11 § 11.6.1."""

    BILINEAR = "bilinear"
    NEAREST = "nearest"
    BICUBIC = "bicubic"


@dataclass(frozen=True, slots=True)
class CropBounds:
    """Cropping rectangle in source-grid metres."""

    east_min_m: float
    east_max_m: float
    north_min_m: float
    north_max_m: float

    def __post_init__(self) -> None:
        if self.east_min_m >= self.east_max_m:
            msg = f"east_min_m ({self.east_min_m}) must be < east_max_m ({self.east_max_m})"
            raise ValueError(msg)
        if self.north_min_m >= self.north_max_m:
            msg = f"north_min_m ({self.north_min_m}) must be < north_max_m ({self.north_max_m})"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class WizardConfig:
    """Collected wizard inputs across the 7 steps."""

    source_path: Path
    output_path: Path
    vertical_reference: VerticalReference = VerticalReference.EGM96
    crop_bounds: CropBounds | None = None
    land_sea_method: LandSeaMethod = LandSeaMethod.AUTO_THRESHOLD
    land_sea_threshold_m: float = 0.5
    coastline_path: Path | None = None
    interpolation: InterpolationMode = InterpolationMode.BILINEAR

    def __post_init__(self) -> None:
        if self.land_sea_method == LandSeaMethod.COASTLINE_FILE and self.coastline_path is None:
            msg = "coastline_path required when land_sea_method=coastline_file"
            raise ValueError(msg)
        if self.land_sea_threshold_m < 0.0:
            msg = f"land_sea_threshold_m must be >= 0, got {self.land_sea_threshold_m}"
            raise ValueError(msg)


def derive_land_mask(
    grid: DEMGrid,
    method: LandSeaMethod,
    *,
    threshold_m: float = 0.5,
) -> NDArray[np.bool_]:
    """Compute a boolean land mask from a parsed DEM grid.

    Args:
        grid: Source DEM (NaN = NODATA).
        method: Derivation rule.
        threshold_m: Cells with finite elevation > ``threshold_m`` are
            land when ``method == AUTO_THRESHOLD``.

    Returns:
        ``(nrows, ncols)`` boolean array; True = land.

    Raises:
        NotImplementedError: ``COASTLINE_FILE`` (parser deferred).
        ValueError: Unknown ``method``.
    """
    if method == LandSeaMethod.AUTO_THRESHOLD:
        return np.asarray(
            np.isfinite(grid.elevation) & (grid.elevation > threshold_m),
            dtype=np.bool_,
        )
    if method == LandSeaMethod.NODATA:
        return np.asarray(np.isfinite(grid.elevation), dtype=np.bool_)
    if method == LandSeaMethod.ALL_LAND:
        return np.ones(grid.elevation.shape, dtype=np.bool_)
    if method == LandSeaMethod.COASTLINE_FILE:
        msg = "LandSeaMethod.COASTLINE_FILE is deferred to a future cycle"
        raise NotImplementedError(msg)
    msg = f"unknown LandSeaMethod: {method!r}"
    raise ValueError(msg)


def crop_grid(grid: DEMGrid, bounds: CropBounds) -> DEMGrid:
    """Crop a DEM grid to ``bounds``. Cell size unchanged.

    Args:
        grid: Source grid.
        bounds: Requested east/north window in source metres.

    Returns:
        New :class:`DEMGrid` whose corner is snapped to the nearest
        whole-cell south-west corner inside ``bounds``.

    Raises:
        ValueError: ``bounds`` does not overlap the grid extent.
    """
    nrows, ncols = grid.elevation.shape
    east_min = grid.x_origin_m
    east_max = grid.x_origin_m + grid.cell_size_m * ncols
    north_min = grid.y_origin_m
    north_max = grid.y_origin_m + grid.cell_size_m * nrows

    e0 = max(bounds.east_min_m, east_min)
    e1 = min(bounds.east_max_m, east_max)
    n0 = max(bounds.north_min_m, north_min)
    n1 = min(bounds.north_max_m, north_max)
    if e0 >= e1 or n0 >= n1:
        msg = (
            f"crop bounds {bounds} do not overlap grid extent "
            f"east=[{east_min}, {east_max}] north=[{north_min}, {north_max}]"
        )
        raise ValueError(msg)

    col_start = int(np.floor((e0 - east_min) / grid.cell_size_m))
    col_stop = int(np.ceil((e1 - east_min) / grid.cell_size_m))
    row_start = int(np.floor((n0 - north_min) / grid.cell_size_m))
    row_stop = int(np.ceil((n1 - north_min) / grid.cell_size_m))

    cropped = grid.elevation[row_start:row_stop, col_start:col_stop]
    new_x = grid.x_origin_m + col_start * grid.cell_size_m
    new_y = grid.y_origin_m + row_start * grid.cell_size_m
    return DEMGrid(
        elevation=cropped,
        x_origin_m=new_x,
        y_origin_m=new_y,
        cell_size_m=grid.cell_size_m,
        nodata_value=grid.nodata_value,
    )


def execute(config: WizardConfig) -> Path:
    """Run the wizard end-to-end.

    Reads ``config.source_path`` (ESRI ASCII grid), optionally crops,
    derives the land mask, and writes ``config.output_path``
    (terrain.npz).

    ``vertical_reference`` and ``interpolation`` are recorded but the
    MVP backend does not yet transform elevation or resample the
    grid - those are deferred to the future GeoTIFF importer.

    Returns:
        Absolute path to the written terrain.npz.
    """
    grid = read_esri_ascii_grid(config.source_path)
    if config.crop_bounds is not None:
        grid = crop_grid(grid, config.crop_bounds)
    mask = derive_land_mask(
        grid,
        config.land_sea_method,
        threshold_m=config.land_sea_threshold_m,
    )
    return write_terrain_npz(config.output_path, grid, land_mask=mask)
