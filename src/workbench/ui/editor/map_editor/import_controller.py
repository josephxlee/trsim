"""DEM Import wiring (Phase 4 dem_import_wizard E4).

`DEMImportController` glues three pieces together:

- :class:`workbench.ui.editor.map_editor.MapEditor`'s
  ``import_dem_requested`` button-click signal.
- :class:`workbench.ui.editor.map_editor.DEMImportWizard` modal that
  collects user inputs.
- :func:`workbench.io.dem_import.run_dem_import` orchestrator that
  actually reads + writes files.

It is the only place that touches the filesystem in the wizard's
import flow; the wizard widget is presentation-only and emits a
:class:`DEMImportRequest`, while the controller catches it, runs the
pipeline, and reports the outcome back onto the wizard's summary
page.

The controller is wired from :class:`workbench.ui.main_window.MainWindow`
as part of the MainWindow boot sequence, but is fully testable in
isolation: pass any ``map_editor`` + ``parent`` widget and (optionally)
override ``wizard_factory`` or ``runner`` to substitute mocks.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QWidget

from workbench.io.dem_import import (
    DEMImportRequest,
    DEMImportSummary,
    run_dem_import,
)
from workbench.ui.editor.map_editor.dem_import_wizard import DEMImportWizard
from workbench.ui.editor.map_editor.widget import MapEditor

WizardFactory = Callable[[QWidget | None], DEMImportWizard]
ImportRunner = Callable[[DEMImportRequest], DEMImportSummary]


def _default_wizard_factory(parent: QWidget | None) -> DEMImportWizard:
    return DEMImportWizard(parent)


class DEMImportController(QObject):
    """Open the wizard on demand and forward its results to the backend.

    Args:
        map_editor: The :class:`MapEditor` whose
            ``import_dem_requested`` signal should open the wizard.
        parent: The QWidget that will own the wizard dialog (usually
            the MainWindow). The controller itself is parented to
            this widget too so it dies with the application.
        wizard_factory: Optional override for testability. Defaults
            to :class:`DEMImportWizard`.
        runner: Optional override for the orchestrator. Defaults to
            :func:`run_dem_import`. Useful for tests to capture the
            request without writing files.
    """

    def __init__(
        self,
        *,
        map_editor: MapEditor,
        parent: QWidget,
        wizard_factory: WizardFactory = _default_wizard_factory,
        runner: ImportRunner = run_dem_import,
    ) -> None:
        super().__init__(parent)
        self._parent = parent
        self._wizard_factory = wizard_factory
        self._runner = runner
        self._active_wizard: DEMImportWizard | None = None
        map_editor.import_dem_requested.connect(self.open_wizard)

    def open_wizard(self) -> DEMImportWizard:
        """Return the active wizard (creating + showing it on first call)."""
        if self._active_wizard is not None:
            self._active_wizard.show()
            self._active_wizard.raise_()
            return self._active_wizard
        wiz = self._wizard_factory(self._parent)
        wiz.import_requested.connect(self._on_import)
        wiz.finished.connect(self._on_finished)
        self._active_wizard = wiz
        wiz.show()
        return wiz

    def active_wizard(self) -> DEMImportWizard | None:
        """Return the currently open wizard, or ``None``."""
        return self._active_wizard

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------
    def _on_import(self, request: DEMImportRequest) -> None:
        if self._active_wizard is None:
            return
        try:
            summary = self._runner(request)
        except (FileNotFoundError, ValueError, OSError) as exc:
            self._active_wizard.report_import_error(str(exc))
            return
        self._active_wizard.report_import_result(summary)

    def _on_finished(self, _result: int) -> None:
        # Drop the reference so the next button click opens a fresh
        # wizard with empty fields rather than re-showing the closed
        # one (which would still hold the previous import's status).
        self._active_wizard = None
