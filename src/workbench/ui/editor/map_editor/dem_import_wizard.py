"""DEM Import Wizard (Phase 4 E2, plan/11 § 11.5 + plan/13 § 13.4).

The 7-step QWizard that turns an external DEM file into the
workbench's native ``terrain.npz``. The Map Editor's
``Import DEM...`` button opens this wizard; the wizard
collects user choices into an
:class:`workbench.app.dem_wizard.WizardConfig` and emits
:attr:`DEMImportWizard.import_completed` with the written
``terrain.npz`` path when the user clicks **Finish**.

7 page layout (one page per plan/11 § 11.5.2 step)::

    Page 0 — Source file (Step 1)
    Page 1 — Vertical reference (Step 2)
    Page 2 — Region (Step 3)
    Page 3 — Land/Sea derivation (Step 4)
    Page 4 — Coordinate conversion (Step 5, MVP no-op note)
    Page 5 — Interpolation (Step 6)
    Page 6 — Save (Step 7)

The MVP backend only supports ESRI ASCII grid (.asc) input;
:class:`workbench.app.dem_wizard.WizardConfig` records the user's
choices for the future GeoTIFF importer regardless.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QWizard,
    QWizardPage,
)

from workbench.app.dem_wizard import (
    CropBounds,
    InterpolationMode,
    LandSeaMethod,
    VerticalReference,
    WizardConfig,
    execute,
)

_VERTICAL_REF_LABELS: tuple[tuple[VerticalReference, str], ...] = (
    (VerticalReference.ELLIPSOID_WGS84, "WGS84 ellipsoid"),
    (VerticalReference.EGM96, "EGM96 geoid (recommended)"),
    (VerticalReference.MSL_LOCAL, "Local mean sea level"),
    (VerticalReference.NONE, "No correction (debug)"),
)

_LAND_SEA_LABELS: tuple[tuple[LandSeaMethod, str], ...] = (
    (LandSeaMethod.AUTO_THRESHOLD, "Auto threshold (z > threshold m)"),
    (LandSeaMethod.NODATA, "Use NODATA cells as sea"),
    (LandSeaMethod.COASTLINE_FILE, "External coastline file (deferred)"),
    (LandSeaMethod.ALL_LAND, "All land (no sea region)"),
)

_INTERPOLATION_LABELS: tuple[tuple[InterpolationMode, str], ...] = (
    (InterpolationMode.BILINEAR, "Bilinear (default)"),
    (InterpolationMode.NEAREST, "Nearest neighbour (fastest)"),
    (InterpolationMode.BICUBIC, "Bicubic (smoothest)"),
)


# ----------------------------------------------------------------------
# Page 0 — Source file
# ----------------------------------------------------------------------
class SourcePage(QWizardPage):
    """Step 1 — pick the external DEM file (.asc)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 1 - Source DEM file")
        self.setSubTitle(
            "Pick an external DEM. The MVP supports ESRI ASCII grid (.asc); "
            "GeoTIFF / SRTM is a future cycle."
        )

        layout = QFormLayout(self)
        self._path_edit = QLineEdit(self)
        self._path_edit.setObjectName("DEMWizardSourcePath")
        self._path_edit.setPlaceholderText("Path to source .asc file...")
        self._path_edit.textChanged.connect(self.completeChanged)

        browse = QPushButton("Browse...", self)
        browse.setObjectName("DEMWizardSourceBrowseBtn")
        browse.clicked.connect(self._on_browse)

        row = QHBoxLayout()
        row.addWidget(self._path_edit, 1)
        row.addWidget(browse, 0)
        layout.addRow("DEM file:", row)

    def _on_browse(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select DEM source",
            "",
            "ESRI ASCII grid (*.asc);;All files (*)",
        )
        if path_str:
            self._path_edit.setText(path_str)

    def isComplete(self) -> bool:  # noqa: N802 - QWizardPage Qt method
        return bool(self._path_edit.text().strip())

    # Public API ------------------------------------------------------
    def source_path(self) -> Path | None:
        text = self._path_edit.text().strip()
        return Path(text) if text else None

    def set_source_path(self, path: Path | str) -> None:
        self._path_edit.setText(str(path))


# ----------------------------------------------------------------------
# Page 1 — Vertical reference
# ----------------------------------------------------------------------
class VerticalReferencePage(QWizardPage):
    """Step 2 — pick the input DEM's vertical datum."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 2 - Vertical reference")
        self.setSubTitle(
            "Choose how to interpret the source DEM's elevation values. "
            "Default = EGM96 (matches SRTM / AWS Terrain Tiles)."
        )

        v = QVBoxLayout(self)
        self._group = QButtonGroup(self)
        self._buttons: dict[VerticalReference, QRadioButton] = {}
        for ref, label in _VERTICAL_REF_LABELS:
            rb = QRadioButton(label, self)
            rb.setObjectName(f"DEMWizardVRef_{ref.value}")
            self._group.addButton(rb)
            self._buttons[ref] = rb
            v.addWidget(rb)
        self._buttons[VerticalReference.EGM96].setChecked(True)

    def vertical_reference(self) -> VerticalReference:
        for ref, btn in self._buttons.items():
            if btn.isChecked():
                return ref
        return VerticalReference.EGM96

    def set_vertical_reference(self, ref: VerticalReference) -> None:
        self._buttons[ref].setChecked(True)


# ----------------------------------------------------------------------
# Page 2 — Region
# ----------------------------------------------------------------------
class RegionPage(QWizardPage):
    """Step 3 — full extent vs Map Bounds crop."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 3 - Region")
        self.setSubTitle(
            "Import the full DEM extent, or crop to a smaller window (performance + disk savings)."
        )

        v = QVBoxLayout(self)
        self._full_btn = QRadioButton("Full extent", self)
        self._full_btn.setObjectName("DEMWizardRegionFull")
        self._crop_btn = QRadioButton("Custom crop", self)
        self._crop_btn.setObjectName("DEMWizardRegionCrop")
        self._full_btn.setChecked(True)
        v.addWidget(self._full_btn)
        v.addWidget(self._crop_btn)

        self._crop_group = QGroupBox("Crop bounds (metres, source CRS)", self)
        self._crop_group.setObjectName("DEMWizardCropGroup")
        cg = QFormLayout(self._crop_group)
        self._east_min = QDoubleSpinBox(self)
        self._east_max = QDoubleSpinBox(self)
        self._north_min = QDoubleSpinBox(self)
        self._north_max = QDoubleSpinBox(self)
        for sb, name in (
            (self._east_min, "DEMWizardEastMin"),
            (self._east_max, "DEMWizardEastMax"),
            (self._north_min, "DEMWizardNorthMin"),
            (self._north_max, "DEMWizardNorthMax"),
        ):
            sb.setObjectName(name)
            sb.setRange(-1e9, 1e9)
            sb.setDecimals(2)
        self._east_max.setValue(1000.0)
        self._north_max.setValue(1000.0)
        cg.addRow("East min (m):", self._east_min)
        cg.addRow("East max (m):", self._east_max)
        cg.addRow("North min (m):", self._north_min)
        cg.addRow("North max (m):", self._north_max)
        v.addWidget(self._crop_group)
        self._crop_group.setEnabled(False)
        self._crop_btn.toggled.connect(self._crop_group.setEnabled)

    def crop_bounds(self) -> CropBounds | None:
        if not self._crop_btn.isChecked():
            return None
        return CropBounds(
            east_min_m=self._east_min.value(),
            east_max_m=self._east_max.value(),
            north_min_m=self._north_min.value(),
            north_max_m=self._north_max.value(),
        )

    def set_crop_bounds(self, bounds: CropBounds | None) -> None:
        if bounds is None:
            self._full_btn.setChecked(True)
            return
        self._crop_btn.setChecked(True)
        self._east_min.setValue(bounds.east_min_m)
        self._east_max.setValue(bounds.east_max_m)
        self._north_min.setValue(bounds.north_min_m)
        self._north_max.setValue(bounds.north_max_m)


# ----------------------------------------------------------------------
# Page 3 — Land/Sea derivation
# ----------------------------------------------------------------------
class LandSeaPage(QWizardPage):
    """Step 4 — land/sea derivation method."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 4 - Land/Sea derivation")
        self.setSubTitle(
            "Decide which cells are land and which are sea. The result is "
            "stored alongside the elevation grid in terrain.npz."
        )

        v = QVBoxLayout(self)
        self._group = QButtonGroup(self)
        self._buttons: dict[LandSeaMethod, QRadioButton] = {}
        for method, label in _LAND_SEA_LABELS:
            rb = QRadioButton(label, self)
            rb.setObjectName(f"DEMWizardLS_{method.value}")
            self._group.addButton(rb)
            self._buttons[method] = rb
            v.addWidget(rb)
        self._buttons[LandSeaMethod.AUTO_THRESHOLD].setChecked(True)
        self._buttons[LandSeaMethod.COASTLINE_FILE].setEnabled(False)

        self._threshold = QDoubleSpinBox(self)
        self._threshold.setObjectName("DEMWizardLSThreshold")
        self._threshold.setRange(0.0, 1000.0)
        self._threshold.setDecimals(3)
        self._threshold.setValue(0.5)
        thresh_row = QHBoxLayout()
        thresh_label = QLabel("Threshold (m):", self)
        thresh_label.setObjectName("DEMWizardLSThresholdLabel")
        thresh_row.addWidget(thresh_label)
        thresh_row.addWidget(self._threshold)
        thresh_row.addStretch(1)
        v.addLayout(thresh_row)

        self._editor_brush = QCheckBox(
            "Allow Map Editor brush to refine later",
            self,
        )
        self._editor_brush.setObjectName("DEMWizardLSEditorBrush")
        self._editor_brush.setChecked(True)
        v.addWidget(self._editor_brush)

    def land_sea_method(self) -> LandSeaMethod:
        for method, btn in self._buttons.items():
            if btn.isChecked():
                return method
        return LandSeaMethod.AUTO_THRESHOLD

    def land_sea_threshold_m(self) -> float:
        return float(self._threshold.value())

    def set_land_sea(
        self,
        method: LandSeaMethod,
        *,
        threshold_m: float | None = None,
    ) -> None:
        self._buttons[method].setChecked(True)
        if threshold_m is not None:
            self._threshold.setValue(threshold_m)


# ----------------------------------------------------------------------
# Page 4 — Coordinate conversion (MVP no-op)
# ----------------------------------------------------------------------
class CoordinateConversionPage(QWizardPage):
    """Step 5 — coordinate / altitude conversion (MVP no-op note)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 5 - Coordinate / altitude conversion")
        self.setSubTitle(
            "The MVP keeps the source CRS as Map ENU. CRS reprojection + "
            "geoid lookups arrive with the future GeoTIFF importer."
        )
        v = QVBoxLayout(self)
        note = QLabel(
            "<b>No conversion is performed in the MVP.</b><br>"
            "The wizard records your vertical reference choice for the "
            "import log; the workbench reads elevation values as-is.",
            self,
        )
        note.setObjectName("DEMWizardCRSNote")
        note.setWordWrap(True)
        v.addWidget(note)
        v.addStretch(1)


# ----------------------------------------------------------------------
# Page 5 — Interpolation
# ----------------------------------------------------------------------
class InterpolationPage(QWizardPage):
    """Step 6 — grid interpolation mode."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 6 - Grid interpolation")
        self.setSubTitle(
            "Choose resampling mode. MVP keeps the source resolution; the "
            "choice is recorded for the future GeoTIFF importer."
        )

        v = QVBoxLayout(self)
        self._combo = QComboBox(self)
        self._combo.setObjectName("DEMWizardInterpolation")
        # StrEnum is a str subclass; QComboBox.userData stringifies it,
        # so keep a parallel list indexed by combo position.
        self._modes: tuple[InterpolationMode, ...] = tuple(
            mode for mode, _ in _INTERPOLATION_LABELS
        )
        for _, label in _INTERPOLATION_LABELS:
            self._combo.addItem(label)
        # Default index = bilinear (index 0)
        self._combo.setCurrentIndex(0)
        v.addWidget(QLabel("Interpolation mode:", self))
        v.addWidget(self._combo)
        v.addStretch(1)

    def interpolation(self) -> InterpolationMode:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._modes):
            return self._modes[idx]
        return InterpolationMode.BILINEAR

    def set_interpolation(self, mode: InterpolationMode) -> None:
        if mode in self._modes:
            self._combo.setCurrentIndex(self._modes.index(mode))


# ----------------------------------------------------------------------
# Page 6 — Save
# ----------------------------------------------------------------------
class SavePage(QWizardPage):
    """Step 7 — terrain.npz output path."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setTitle("Step 7 - Save")
        self.setSubTitle(
            "Pick where to write terrain.npz. The Map Editor reads this file directly."
        )

        layout = QFormLayout(self)
        self._path_edit = QLineEdit(self)
        self._path_edit.setObjectName("DEMWizardOutputPath")
        self._path_edit.setPlaceholderText("Path to terrain.npz...")
        self._path_edit.textChanged.connect(self.completeChanged)

        browse = QPushButton("Browse...", self)
        browse.setObjectName("DEMWizardOutputBrowseBtn")
        browse.clicked.connect(self._on_browse)

        row = QHBoxLayout()
        row.addWidget(self._path_edit, 1)
        row.addWidget(browse, 0)
        layout.addRow("Output file:", row)

    def _on_browse(self) -> None:
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save terrain.npz",
            "terrain.npz",
            "Workbench terrain (*.npz);;All files (*)",
        )
        if path_str:
            self._path_edit.setText(path_str)

    def isComplete(self) -> bool:  # noqa: N802 - QWizardPage Qt method
        return bool(self._path_edit.text().strip())

    def output_path(self) -> Path | None:
        text = self._path_edit.text().strip()
        return Path(text) if text else None

    def set_output_path(self, path: Path | str) -> None:
        self._path_edit.setText(str(path))


# ----------------------------------------------------------------------
# Wizard container
# ----------------------------------------------------------------------
class DEMImportWizard(QWizard):
    """7-step wizard. Emits ``import_completed(Path)`` on success."""

    import_completed = Signal(Path)
    import_failed = Signal(str)

    PAGE_SOURCE = 0
    PAGE_VERTICAL = 1
    PAGE_REGION = 2
    PAGE_LAND_SEA = 3
    PAGE_CRS = 4
    PAGE_INTERPOLATION = 5
    PAGE_SAVE = 6

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DEMImportWizard")
        self.setWindowTitle("Import DEM")
        self.setOption(QWizard.WizardOption.NoBackButtonOnStartPage, True)

        self._source = SourcePage(self)
        self._vertical = VerticalReferencePage(self)
        self._region = RegionPage(self)
        self._land_sea = LandSeaPage(self)
        self._crs = CoordinateConversionPage(self)
        self._interp = InterpolationPage(self)
        self._save = SavePage(self)

        # Set explicit page IDs to keep stable ordering even if pages
        # are added in a different order in the future.
        self.setPage(self.PAGE_SOURCE, self._source)
        self.setPage(self.PAGE_VERTICAL, self._vertical)
        self.setPage(self.PAGE_REGION, self._region)
        self.setPage(self.PAGE_LAND_SEA, self._land_sea)
        self.setPage(self.PAGE_CRS, self._crs)
        self.setPage(self.PAGE_INTERPOLATION, self._interp)
        self.setPage(self.PAGE_SAVE, self._save)
        self.setStartId(self.PAGE_SOURCE)

    # ------------------------------------------------------------------
    # Public read-only accessors (for test introspection)
    # ------------------------------------------------------------------
    def source_page(self) -> SourcePage:
        return self._source

    def vertical_page(self) -> VerticalReferencePage:
        return self._vertical

    def region_page(self) -> RegionPage:
        return self._region

    def land_sea_page(self) -> LandSeaPage:
        return self._land_sea

    def interpolation_page(self) -> InterpolationPage:
        return self._interp

    def save_page(self) -> SavePage:
        return self._save

    # ------------------------------------------------------------------
    # Config assembly
    # ------------------------------------------------------------------
    def build_config(self) -> WizardConfig:
        """Collect every page's state into a :class:`WizardConfig`.

        Raises:
            ValueError: Either source or output path is missing, or the
                downstream :class:`WizardConfig` validators reject the
                combination.
        """
        src = self._source.source_path()
        if src is None:
            msg = "DEM source path is empty"
            raise ValueError(msg)
        out = self._save.output_path()
        if out is None:
            msg = "Output path is empty"
            raise ValueError(msg)
        return WizardConfig(
            source_path=src,
            output_path=out,
            vertical_reference=self._vertical.vertical_reference(),
            crop_bounds=self._region.crop_bounds(),
            land_sea_method=self._land_sea.land_sea_method(),
            land_sea_threshold_m=self._land_sea.land_sea_threshold_m(),
            interpolation=self._interp.interpolation(),
        )

    # ------------------------------------------------------------------
    # QWizard hook — runs when the user clicks Finish
    # ------------------------------------------------------------------
    def accept(self) -> None:
        try:
            config = self.build_config()
            written = execute(config)
        except (
            ValueError,
            FileNotFoundError,
            NotImplementedError,
            OSError,
        ) as exc:
            self.import_failed.emit(str(exc))
            return
        self.import_completed.emit(written)
        super().accept()
