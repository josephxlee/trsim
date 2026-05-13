"""DEM Import Wizard (Phase 4 dem_import_wizard E3, plan/13 § 13.4.5).

A modal :class:`QDialog` that walks the user through importing an
external DEM into the workbench's native ``terrain.npz``. The MVP
distils plan/11 § 11.5.2's 7-step pipeline into **four pages**:

1. **Source** — pick an ESRI ASCII grid (``.asc``).
2. **Land/Sea** — choose a :class:`LandSeaMode` strategy + optional
   threshold (for :attr:`LandSeaMode.AUTO_THRESHOLD`).
3. **Output** — pick a destination ``terrain.npz`` path.
4. **Summary** — confirm and run.

Steps 2/3/5/6 of plan/11 § 11.5.2 (vertical-reference dialog, area
crop, coordinate transform, regridding) are deferred: the workbench
backend currently accepts the source grid in its native CRS as
direct ENU metres, and the wizard saves whatever grid spacing the
source file declared.

The wizard widget is **I/O-free** in test mode — it exposes signals
for browse buttons and an ``import_requested(request)`` signal that
the host (MainWindow) wires to :func:`workbench.io.dem_import.run_dem_import`.
The actual file-picker dialogs only open when the user clicks
"Browse" *and* the wizard is shown — tests can drive the wizard
without opening a real QFileDialog by setting paths directly via
:meth:`set_source_path` / :meth:`set_output_path`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from workbench.io.dem_import import (
    DEMImportRequest,
    DEMImportSummary,
    LandSeaMode,
)

_MODE_LABEL: dict[LandSeaMode, str] = {
    LandSeaMode.AUTO_THRESHOLD: "Auto threshold (z > threshold → land)",
    LandSeaMode.NODATA: "NODATA = sea (finite cells = land)",
    LandSeaMode.ALL_LAND: "All land (no sea cells)",
}

# The wizard exposes pages in this fixed order. The summary page only
# becomes navigable when both source and output paths are valid.
_PAGE_SOURCE = 0
_PAGE_LAND_SEA = 1
_PAGE_OUTPUT = 2
_PAGE_SUMMARY = 3


class DEMImportWizard(QDialog):
    """Four-page DEM import wizard (Source → Land/Sea → Output → Summary).

    Signals:
        import_requested: Emitted once the user clicks **Import** on
            the summary page with a valid :class:`DEMImportRequest`.
            The host runs the request and may call
            :meth:`report_import_result` to fill the summary log.
        browse_source_requested: Emitted when the user clicks the
            **Browse...** button on the Source page. The host may
            override the file picker if needed; otherwise the
            wizard's built-in :func:`QFileDialog.getOpenFileName`
            handles it.
    """

    import_requested = Signal(DEMImportRequest)
    browse_source_requested = Signal()
    browse_output_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DEMImportWizard")
        self.setWindowTitle("Import DEM")
        self.setModal(True)
        self.setMinimumWidth(480)

        self._source_path: Path | None = None
        self._output_path: Path | None = None
        self._land_sea_mode: LandSeaMode = LandSeaMode.NODATA
        self._threshold_m: float = 0.5

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._step_label = QLabel("Step 1 / 4 — Source DEM", self)
        self._step_label.setObjectName("DEMWizardStepLabel")
        self._step_label.setStyleSheet("font-weight: 600;")
        layout.addWidget(self._step_label)

        self._pages = QStackedWidget(self)
        self._pages.addWidget(self._build_source_page())
        self._pages.addWidget(self._build_land_sea_page())
        self._pages.addWidget(self._build_output_page())
        self._pages.addWidget(self._build_summary_page())
        layout.addWidget(self._pages, 1)

        layout.addLayout(self._build_nav_row())

        # Wire mode radios + select default. Done here (after the nav
        # row exists) so the `toggled` handler can safely read every
        # widget the wizard owns.
        for mode, rb in self._mode_radios.items():
            rb.toggled.connect(lambda checked, m=mode: self._on_mode_toggled(checked, m))
        self._mode_radios[LandSeaMode.NODATA].setChecked(True)

        self._refresh_nav_state()

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------
    def _build_source_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("DEMWizardSourcePage")
        form = QFormLayout(page)
        intro = QLabel(
            "Select the source DEM file (ESRI ASCII grid, .asc).",
            page,
        )
        intro.setWordWrap(True)
        form.addRow(intro)

        self._source_line = QLineEdit(page)
        self._source_line.setObjectName("DEMWizardSourceLine")
        self._source_line.setReadOnly(True)
        self._source_line.setPlaceholderText("(no file selected)")

        browse_btn = QPushButton("Browse...", page)
        browse_btn.setObjectName("DEMWizardSourceBrowse")
        browse_btn.clicked.connect(self._on_browse_source)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._source_line, 1)
        row.addWidget(browse_btn, 0)
        form.addRow("Source:", row)

        self._source_status = QLabel("", page)
        self._source_status.setObjectName("DEMWizardSourceStatus")
        self._source_status.setStyleSheet("color: #c33;")
        form.addRow(self._source_status)

        return page

    def _build_land_sea_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("DEMWizardLandSeaPage")
        layout = QVBoxLayout(page)
        intro = QLabel(
            "Choose how cells become land vs. sea. The mask is saved alongside the elevation grid.",
            page,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._mode_group = QButtonGroup(page)
        self._mode_radios: dict[LandSeaMode, QRadioButton] = {}
        for mode in LandSeaMode:
            rb = QRadioButton(_MODE_LABEL[mode], page)
            rb.setObjectName(f"DEMWizardMode_{mode.value}")
            self._mode_group.addButton(rb)
            self._mode_radios[mode] = rb
            layout.addWidget(rb)

        threshold_row = QFormLayout()
        threshold_row.setContentsMargins(24, 4, 0, 0)
        self._threshold_spin = QDoubleSpinBox(page)
        self._threshold_spin.setObjectName("DEMWizardThresholdSpin")
        self._threshold_spin.setRange(-1000.0, 10000.0)
        self._threshold_spin.setDecimals(2)
        self._threshold_spin.setSingleStep(0.1)
        self._threshold_spin.setValue(self._threshold_m)
        self._threshold_spin.setEnabled(False)
        self._threshold_spin.valueChanged.connect(self._on_threshold_changed)
        threshold_row.addRow("Threshold (m):", self._threshold_spin)
        layout.addLayout(threshold_row)

        # Wiring happens after the nav row is built — see __init__.
        layout.addStretch(1)
        return page

    def _build_output_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("DEMWizardOutputPage")
        form = QFormLayout(page)
        intro = QLabel(
            "Choose the destination terrain.npz path. The parent folder is created if missing.",
            page,
        )
        intro.setWordWrap(True)
        form.addRow(intro)

        self._output_line = QLineEdit(page)
        self._output_line.setObjectName("DEMWizardOutputLine")
        self._output_line.setReadOnly(True)
        self._output_line.setPlaceholderText("(no output path selected)")

        browse_btn = QPushButton("Browse...", page)
        browse_btn.setObjectName("DEMWizardOutputBrowse")
        browse_btn.clicked.connect(self._on_browse_output)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self._output_line, 1)
        row.addWidget(browse_btn, 0)
        form.addRow("Output:", row)

        self._output_status = QLabel("", page)
        self._output_status.setObjectName("DEMWizardOutputStatus")
        self._output_status.setStyleSheet("color: #c33;")
        form.addRow(self._output_status)

        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget(self)
        page.setObjectName("DEMWizardSummaryPage")
        layout = QVBoxLayout(page)
        intro = QLabel("Review and click Import to run the pipeline.", page)
        layout.addWidget(intro)

        self._summary_label = QLabel("", page)
        self._summary_label.setObjectName("DEMWizardSummaryLabel")
        self._summary_label.setTextFormat(Qt.TextFormat.PlainText)
        self._summary_label.setWordWrap(True)
        layout.addWidget(self._summary_label, 1)

        self._result_label = QLabel("", page)
        self._result_label.setObjectName("DEMWizardResultLabel")
        self._result_label.setStyleSheet("color: #270;")
        self._result_label.setWordWrap(True)
        layout.addWidget(self._result_label, 0)

        return page

    def _build_nav_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        self._back_btn = QPushButton("Back", self)
        self._back_btn.setObjectName("DEMWizardBackBtn")
        self._next_btn = QPushButton("Next", self)
        self._next_btn.setObjectName("DEMWizardNextBtn")
        self._import_btn = QPushButton("Import", self)
        self._import_btn.setObjectName("DEMWizardImportBtn")
        self._import_btn.setVisible(False)
        self._cancel_btn = QPushButton("Cancel", self)
        self._cancel_btn.setObjectName("DEMWizardCancelBtn")

        self._back_btn.clicked.connect(self._on_back)
        self._next_btn.clicked.connect(self._on_next)
        self._import_btn.clicked.connect(self._on_import)
        self._cancel_btn.clicked.connect(self.reject)

        row.addWidget(self._cancel_btn)
        row.addStretch(1)
        row.addWidget(self._back_btn)
        row.addWidget(self._next_btn)
        row.addWidget(self._import_btn)
        return row

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _on_back(self) -> None:
        current = self._pages.currentIndex()
        if current > 0:
            self._pages.setCurrentIndex(current - 1)
        self._refresh_nav_state()

    def _on_next(self) -> None:
        current = self._pages.currentIndex()
        if current < self._pages.count() - 1:
            self._pages.setCurrentIndex(current + 1)
        self._refresh_nav_state()

    def _refresh_nav_state(self) -> None:
        idx = self._pages.currentIndex()
        self._step_label.setText(self._step_text_for(idx))

        self._back_btn.setEnabled(idx > 0)

        on_summary = idx == _PAGE_SUMMARY
        self._next_btn.setVisible(not on_summary)
        self._import_btn.setVisible(on_summary)

        if idx == _PAGE_SOURCE:
            self._next_btn.setEnabled(self._source_path is not None)
        elif idx == _PAGE_OUTPUT:
            self._next_btn.setEnabled(self._output_path is not None)
        elif idx == _PAGE_LAND_SEA:
            self._next_btn.setEnabled(True)
        else:
            self._next_btn.setEnabled(False)

        if on_summary:
            req = self._build_request()
            ready = req is not None
            self._import_btn.setEnabled(ready)
            self._summary_label.setText(self._render_summary(req))

    @staticmethod
    def _step_text_for(idx: int) -> str:
        labels = {
            _PAGE_SOURCE: "Step 1 / 4 - Source DEM",
            _PAGE_LAND_SEA: "Step 2 / 4 - Land/Sea classification",
            _PAGE_OUTPUT: "Step 3 / 4 - Output path",
            _PAGE_SUMMARY: "Step 4 / 4 - Summary",
        }
        return labels.get(idx, "")

    # ------------------------------------------------------------------
    # Field change handlers
    # ------------------------------------------------------------------
    def _on_mode_toggled(self, checked: bool, mode: LandSeaMode) -> None:
        if not checked:
            return
        self._land_sea_mode = mode
        self._threshold_spin.setEnabled(mode is LandSeaMode.AUTO_THRESHOLD)
        self._refresh_nav_state()

    def _on_threshold_changed(self, value: float) -> None:
        self._threshold_m = float(value)
        self._refresh_nav_state()

    def _on_browse_source(self) -> None:
        self.browse_source_requested.emit()
        if self._source_path is not None:
            # Host already set the path through set_source_path — done.
            return
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select source DEM",
            "",
            "ESRI ASCII grid (*.asc);;All files (*)",
        )
        if path_str:
            self.set_source_path(Path(path_str))

    def _on_browse_output(self) -> None:
        self.browse_output_requested.emit()
        if self._output_path is not None:
            return
        path_str, _ = QFileDialog.getSaveFileName(
            self,
            "Save terrain.npz as",
            "terrain.npz",
            "Workbench terrain (*.npz);;All files (*)",
        )
        if path_str:
            self.set_output_path(Path(path_str))

    def _on_import(self) -> None:
        req = self._build_request()
        if req is None:
            return
        self.import_requested.emit(req)

    def _build_request(self) -> DEMImportRequest | None:
        if self._source_path is None or self._output_path is None:
            return None
        return DEMImportRequest(
            source_asc_path=self._source_path,
            output_npz_path=self._output_path,
            land_sea_mode=self._land_sea_mode,
            threshold_m=self._threshold_m,
        )

    def _render_summary(self, req: DEMImportRequest | None) -> str:
        if req is None:
            return "Source or output path is missing — go back and pick them."
        threshold_str = (
            f"  threshold = {req.threshold_m:g} m\n"
            if req.land_sea_mode is LandSeaMode.AUTO_THRESHOLD
            else ""
        )
        return (
            f"Source: {req.source_asc_path}\n"
            f"Output: {req.output_npz_path}\n"
            f"Mode  : {_MODE_LABEL[req.land_sea_mode]}\n"
            f"{threshold_str}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_source_path(self, path: Path) -> None:
        """Programmatically pick the source DEM (used by tests + host)."""
        self._source_path = Path(path)
        self._source_line.setText(str(self._source_path))
        self._source_status.setText("")
        self._refresh_nav_state()

    def set_output_path(self, path: Path) -> None:
        """Programmatically pick the output ``terrain.npz`` path."""
        self._output_path = Path(path)
        self._output_line.setText(str(self._output_path))
        self._output_status.setText("")
        self._refresh_nav_state()

    def set_land_sea_mode(self, mode: LandSeaMode) -> None:
        """Programmatic mirror of clicking a mode radio."""
        self._mode_radios[mode].setChecked(True)

    def set_threshold_m(self, value: float) -> None:
        """Programmatic mirror of the threshold spin box."""
        self._threshold_spin.setValue(float(value))

    def source_path(self) -> Path | None:
        return self._source_path

    def output_path(self) -> Path | None:
        return self._output_path

    def land_sea_mode(self) -> LandSeaMode:
        return self._land_sea_mode

    def threshold_m(self) -> float:
        return self._threshold_m

    def current_page_index(self) -> int:
        return self._pages.currentIndex()

    def go_to_page(self, index: int) -> None:
        """Test helper — jump straight to a page without firing nav state."""
        clamped = max(0, min(index, self._pages.count() - 1))
        self._pages.setCurrentIndex(clamped)
        self._refresh_nav_state()

    def report_import_result(self, summary: DEMImportSummary) -> None:
        """Host calls this after :func:`run_dem_import` completes.

        Renders a green status line on the summary page so the user
        knows the import landed without having to alt-tab to a
        terminal.
        """
        self._result_label.setText(
            f"Imported OK -> {summary.output_path}\n"
            f"  grid     = {summary.grid_shape[0]} x {summary.grid_shape[1]}\n"
            f"  cell     = {summary.cell_size_m:g} m\n"
            f"  land     = {summary.land_cell_count} cells\n"
            f"  sea      = {summary.sea_cell_count} cells\n"
            f"  nodata   = {summary.nodata_cell_count} cells"
        )

    def report_import_error(self, message: str) -> None:
        """Host calls this when :func:`run_dem_import` raised."""
        self._result_label.setStyleSheet("color: #c33;")
        self._result_label.setText(f"Import failed: {message}")
