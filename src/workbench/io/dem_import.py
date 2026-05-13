"""DEM Import — ESRI ASCII grid → terrain.npz (Phase 3 D4, plan/04 § 4.3).

The Editor's "Import DEM" wizard (plan/22 § 22.5, Phase 4 future
work) needs a backend that turns external DEM files into the
workbench's native ``terrain.npz`` representation. The MVP supports
**ESRI ASCII grid** (``.asc``) only — the simplest open format that
QGIS, GDAL, gdal_translate, and most government DEM portals can
emit. Adding GeoTIFF (``.tif``) is a future cycle that brings in
``rasterio`` or ``GDAL`` as an optional dependency.

Public API:

- :func:`read_esri_ascii_grid(path)` — parse an ESRI ASCII grid
  file into a :class:`DEMGrid` (elevation 2D + corner + cellsize +
  NODATA mask).
- :func:`write_terrain_npz(path, grid, land_mask)` — write the
  workbench-native ``terrain.npz`` from a :class:`DEMGrid` and a
  land mask. Layout matches
  :class:`workbench.domain.terrain.WorkbenchTerrain` (plan/11).
- :func:`import_dem_to_terrain_npz(asc_path, npz_path, ...)` —
  end-to-end convenience for the Import Wizard.

ESRI ASCII grid format (briefly):

::

    ncols        <int>
    nrows        <int>
    xllcorner    <float>
    yllcorner    <float>
    cellsize     <float>
    NODATA_value <float>          # optional
    <row 0 elevations, space-separated>
    <row 1 elevations>
    ...

Row 0 is the **top** of the grid (max y); rows go top-to-bottom.
The reader flips this so the returned ``elevation`` is north-up
indexable (``elevation[0, 0]`` = south-west corner). NODATA cells
become NaN; the caller pairs this with a land mask (default: all
finite values are land).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

import numpy as np
from numpy.typing import NDArray


class LandSeaMode(StrEnum):
    """Land/Sea classification strategies for the Import Wizard (plan/11
    § 11.5.5).

    The MVP supports three modes; the wizard's "external coastline
    file" option is deferred to a later cycle because it requires
    GeoJSON/Shapefile parsing.

    - :attr:`AUTO_THRESHOLD` — every cell with finite elevation
      *above* the configured threshold is land. Cells at or below
      the threshold are sea. NaN (NODATA) cells are sea.
    - :attr:`NODATA` — every finite-elevation cell is land. NaN
      (NODATA) cells are sea. This matches SRTM-style DEMs that
      sentinel out the ocean surface.
    - :attr:`ALL_LAND` — every cell is land regardless of elevation.
      Use for inland scenarios with no coastline. Note: NODATA
      cells stay NaN in the elevation array — downstream sampling
      will return NaN. The wizard surfaces a warning when a DEM
      with NODATA cells is imported in ALL_LAND mode.
    """

    AUTO_THRESHOLD = "auto_threshold"
    NODATA = "nodata"
    ALL_LAND = "all_land"


def compute_land_mask(
    grid: DEMGrid,
    mode: LandSeaMode,
    *,
    threshold_m: float = 0.5,
) -> NDArray[np.bool_]:
    """Derive a 2D ``land_mask`` from ``grid`` per the wizard's mode.

    Args:
        grid: Parsed DEM. NODATA cells are NaN.
        mode: Classification strategy. See :class:`LandSeaMode`.
        threshold_m: Sea-level threshold for
            :attr:`LandSeaMode.AUTO_THRESHOLD`. Cells with elevation
            ``> threshold_m`` become land. Ignored for the other
            modes. Defaults to ``0.5`` m (plan/11 § 11.5.5 default).

    Returns:
        ``(nrows, ncols)`` bool array; ``True`` = land, ``False`` = sea.

    Raises:
        ValueError: ``mode`` is unrecognised or ``threshold_m`` is
            non-finite when AUTO_THRESHOLD is requested.
    """
    finite = np.isfinite(grid.elevation)
    if mode is LandSeaMode.AUTO_THRESHOLD:
        if not np.isfinite(threshold_m):
            msg = f"threshold_m must be finite for AUTO_THRESHOLD, got {threshold_m!r}"
            raise ValueError(msg)
        # NaN comparisons return False — sea automatically.
        return np.asarray((grid.elevation > threshold_m) & finite, dtype=np.bool_)
    if mode is LandSeaMode.NODATA:
        return np.asarray(finite, dtype=np.bool_)
    if mode is LandSeaMode.ALL_LAND:
        return np.ones(grid.elevation.shape, dtype=np.bool_)
    msg = f"unknown LandSeaMode {mode!r}"  # defensive — StrEnum exhausted above
    raise ValueError(msg)


_HEADER_RE: Final = re.compile(
    r"^\s*(ncols|nrows|xllcorner|yllcorner|cellsize|NODATA_value)\s+(\S+)\s*$",
    re.IGNORECASE,
)

REQUIRED_HEADERS: Final = ("ncols", "nrows", "xllcorner", "yllcorner", "cellsize")


@dataclass(frozen=True, slots=True)
class DEMGrid:
    """Parsed ESRI ASCII grid.

    Attributes:
        elevation: ``(nrows, ncols)`` float64 array. ``elevation[0, 0]``
            is the south-west corner (row 0 = south, col 0 = west).
            NODATA cells are NaN.
        x_origin_m: x-coordinate (east) of the SW corner (``xllcorner``).
        y_origin_m: y-coordinate (north) of the SW corner
            (``yllcorner``).
        cell_size_m: Grid spacing in metres (assumed isotropic).
        nodata_value: Raw NODATA sentinel from the file header. Used
            to identify NODATA cells before they were converted to NaN.
    """

    elevation: NDArray[np.float64]
    x_origin_m: float
    y_origin_m: float
    cell_size_m: float
    nodata_value: float = -9999.0


def read_esri_ascii_grid(path: Path | str) -> DEMGrid:
    """Parse an ESRI ASCII grid file into a :class:`DEMGrid`.

    Args:
        path: ``.asc`` file path.

    Returns:
        :class:`DEMGrid` with NODATA cells converted to NaN.

    Raises:
        FileNotFoundError: ``path`` does not exist.
        ValueError: Header is missing a required key, ncols/nrows
            does not match the row data, or a row has the wrong
            number of cells.
    """
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        msg = f"DEM file not found: {p}"
        raise FileNotFoundError(msg)

    header: dict[str, float] = {}
    body_rows: list[list[float]] = []

    with p.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            match = _HEADER_RE.match(line)
            if match:
                key = match.group(1).lower()
                value_str = match.group(2)
                try:
                    header[key] = float(value_str)
                except ValueError as exc:
                    msg = f"{p}: header {key!r} value {value_str!r} is not a number"
                    raise ValueError(msg) from exc
            else:
                # Body row.
                try:
                    body_rows.append([float(x) for x in line.split()])
                except ValueError as exc:
                    msg = f"{p}: non-numeric body row: {line!r}"
                    raise ValueError(msg) from exc

    for key in REQUIRED_HEADERS:
        if key not in header:
            msg = f"{p}: missing required header {key!r}"
            raise ValueError(msg)

    ncols = int(header["ncols"])
    nrows = int(header["nrows"])
    nodata = header.get("nodata_value", -9999.0)

    if len(body_rows) != nrows:
        msg = f"{p}: expected {nrows} body rows from nrows header, got {len(body_rows)}"
        raise ValueError(msg)
    for r, row in enumerate(body_rows):
        if len(row) != ncols:
            msg = f"{p}: row {r} has {len(row)} cells, expected {ncols}"
            raise ValueError(msg)

    elevation = np.asarray(body_rows, dtype=np.float64)
    # ESRI rows go top-to-bottom; flip so row 0 = south (north-up).
    elevation = elevation[::-1, :]
    # NODATA -> NaN so downstream callers can mask with np.isfinite.
    elevation = np.where(elevation == nodata, np.nan, elevation)

    return DEMGrid(
        elevation=elevation,
        x_origin_m=float(header["xllcorner"]),
        y_origin_m=float(header["yllcorner"]),
        cell_size_m=float(header["cellsize"]),
        nodata_value=float(nodata),
    )


def write_terrain_npz(
    path: Path | str,
    grid: DEMGrid,
    *,
    land_mask: NDArray[np.bool_] | None = None,
) -> Path:
    """Persist ``grid`` as a workbench-native ``terrain.npz`` archive.

    Args:
        path: Destination ``.npz``.
        grid: Parsed DEM.
        land_mask: ``(nrows, ncols)`` bool array; ``True`` = land cell,
            ``False`` = sea (use ``sea_surface.z`` instead of DEM).
            ``None`` (default) treats every finite-elevation cell as
            land; NaN (NODATA) cells default to sea.

    Returns:
        Absolute :class:`Path` to the written archive.

    Raises:
        ValueError: ``land_mask`` shape mismatch.
    """
    out = Path(path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    if land_mask is None:
        mask = np.isfinite(grid.elevation)
    else:
        if land_mask.shape != grid.elevation.shape:
            msg = (
                f"land_mask shape {land_mask.shape} does not match "
                f"elevation shape {grid.elevation.shape}"
            )
            raise ValueError(msg)
        mask = land_mask.astype(np.bool_, copy=False)

    np.savez(
        out,
        elevation=grid.elevation.astype(np.float64, copy=False),
        land_mask=mask,
        x_origin_m=np.float64(grid.x_origin_m),
        y_origin_m=np.float64(grid.y_origin_m),
        cell_size_m=np.float64(grid.cell_size_m),
    )
    return out


def import_dem_to_terrain_npz(
    asc_path: Path | str,
    npz_path: Path | str,
    *,
    land_mask: NDArray[np.bool_] | None = None,
) -> Path:
    """End-to-end helper: read ASCII DEM + write terrain.npz."""
    grid = read_esri_ascii_grid(asc_path)
    return write_terrain_npz(npz_path, grid, land_mask=land_mask)


# ---------------------------------------------------------------------
# Import Wizard orchestrator (Phase 4 dem_import_wizard E2)
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DEMImportRequest:
    """User-facing input for :func:`run_dem_import`.

    Captures the three knobs the Import Wizard exposes (plan/13
    § 13.4.5): source DEM file, output ``terrain.npz`` path, and the
    Land/Sea classification mode + optional threshold.

    Attributes:
        source_asc_path: Path to the source ``.asc`` file.
        output_npz_path: Destination ``terrain.npz`` path.
        land_sea_mode: Which :class:`LandSeaMode` strategy to use.
        threshold_m: Threshold for :attr:`LandSeaMode.AUTO_THRESHOLD`
            in metres. Ignored for the other modes. Defaults to
            ``0.5`` m (plan/11 § 11.5.5).
    """

    source_asc_path: Path
    output_npz_path: Path
    land_sea_mode: LandSeaMode
    threshold_m: float = 0.5

    def __post_init__(self) -> None:
        if self.land_sea_mode is LandSeaMode.AUTO_THRESHOLD and not np.isfinite(self.threshold_m):
            msg = f"threshold_m must be finite, got {self.threshold_m!r}"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class DEMImportSummary:
    """Result of a successful :func:`run_dem_import` call.

    Reported to the wizard's summary page so the user can see what
    actually happened (cell counts, output path).
    """

    request: DEMImportRequest
    output_path: Path
    grid_shape: tuple[int, int]
    cell_size_m: float
    land_cell_count: int
    sea_cell_count: int
    nodata_cell_count: int


def run_dem_import(request: DEMImportRequest) -> DEMImportSummary:
    """Run the full Import Wizard pipeline (read + classify + write).

    The pipeline (plan/11 § 11.5.2 distilled for MVP):

    1. Parse the ESRI ASCII DEM (:func:`read_esri_ascii_grid`).
    2. Compute the ``land_mask`` per
       :attr:`DEMImportRequest.land_sea_mode`
       (:func:`compute_land_mask`).
    3. Write the workbench-native ``terrain.npz``
       (:func:`write_terrain_npz`).

    Args:
        request: User-supplied wizard inputs.

    Returns:
        :class:`DEMImportSummary` with cell counts + output path.

    Raises:
        FileNotFoundError: Source DEM does not exist.
        ValueError: Source DEM is malformed (re-raised from
            :func:`read_esri_ascii_grid`).
    """
    grid = read_esri_ascii_grid(request.source_asc_path)
    mask = compute_land_mask(
        grid,
        request.land_sea_mode,
        threshold_m=request.threshold_m,
    )
    out = write_terrain_npz(request.output_npz_path, grid, land_mask=mask)

    land_count = int(mask.sum())
    sea_count = int(mask.size - land_count)
    nodata_count = int(np.isnan(grid.elevation).sum())

    return DEMImportSummary(
        request=request,
        output_path=out,
        grid_shape=(int(grid.elevation.shape[0]), int(grid.elevation.shape[1])),
        cell_size_m=float(grid.cell_size_m),
        land_cell_count=land_count,
        sea_cell_count=sea_count,
        nodata_cell_count=nodata_count,
    )
