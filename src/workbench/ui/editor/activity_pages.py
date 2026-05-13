"""Editor activity pages (Phase 4.3 + 4.5+ progressive replacement).

Activities replace their placeholder once a real implementation
arrives. Phase 4.5 has already migrated :class:`ScenarioComposerPage`
to wrap the real :class:`ScenarioComposer` widget; Map / Radar /
Targets / Browser remain placeholder stubs until Phase 4.6+.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from workbench.ui.editor.composer import ScenarioComposer
from workbench.ui.editor.map_editor import DEMImportWizard, MapEditor
from workbench.ui.editor.radar_editor import RadarEditor
from workbench.ui.editor.targets_editor import TargetsEditor


def _make_placeholder(
    title: str,
    hint: str,
    object_name: str,
    parent: QWidget | None = None,
) -> QWidget:
    page = QWidget(parent)
    page.setObjectName(object_name)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 24, 24, 24)

    title_label = QLabel(title)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("font-size: 18px; font-weight: 600;")

    hint_label = QLabel(hint)
    hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hint_label.setStyleSheet("color: #777;")

    layout.addStretch(1)
    layout.addWidget(title_label)
    layout.addWidget(hint_label)
    layout.addStretch(1)
    return page


class ScenarioComposerPage(QWidget):
    """Activity 1 - hosts the real ScenarioComposer widget (Phase 4.5)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScenarioComposerPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._composer = ScenarioComposer(self)
        layout.addWidget(self._composer)

    def composer(self) -> ScenarioComposer:
        """Return the embedded :class:`ScenarioComposer` (test helper)."""
        return self._composer


class MapEditorPage(QWidget):
    """Activity 2 - hosts the real MapEditor widget (Phase 4.6).

    Owns the DEM Import Wizard wiring (Phase 4 E3): when the user
    clicks the Map Editor's "Import DEM..." button, this page opens a
    :class:`DEMImportWizard` and pushes the result into the edit
    history.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._map_editor = MapEditor(self)
        layout.addWidget(self._map_editor)

        self._wizard: DEMImportWizard | None = None
        self._last_imported_path: Path | None = None
        self._history: list[str] = []
        self._map_editor.import_dem_requested.connect(self._on_import_requested)

    def map_editor(self) -> MapEditor:
        """Return the embedded :class:`MapEditor` (test helper)."""
        return self._map_editor

    # ------------------------------------------------------------------
    # DEM Import wiring
    # ------------------------------------------------------------------
    def active_wizard(self) -> DEMImportWizard | None:
        """Return the currently open :class:`DEMImportWizard`, if any."""
        return self._wizard

    def last_imported_path(self) -> Path | None:
        """Return the path written by the most recent successful import."""
        return self._last_imported_path

    def _on_import_requested(self) -> None:
        wiz = DEMImportWizard(self)
        wiz.setModal(True)
        wiz.import_completed.connect(self._on_wizard_completed)
        wiz.import_failed.connect(self._on_wizard_failed)
        wiz.finished.connect(self._on_wizard_finished)
        self._wizard = wiz
        wiz.show()

    def _on_wizard_completed(self, path: Path) -> None:
        self._last_imported_path = Path(path)
        self._push_history(f"Imported DEM -> {path}")

    def _on_wizard_failed(self, message: str) -> None:
        self._push_history(f"Import failed: {message}")

    def _on_wizard_finished(self, _result: int) -> None:
        self._wizard = None

    def _push_history(self, entry: str) -> None:
        self._history = [entry, *self._history]
        self._map_editor.set_history(self._history)


class RadarEditorPage(QWidget):
    """Activity 3 - hosts the real RadarEditor widget (Phase 4.7)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadarEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._radar_editor = RadarEditor(self)
        layout.addWidget(self._radar_editor)

    def radar_editor(self) -> RadarEditor:
        """Return the embedded :class:`RadarEditor` (test helper)."""
        return self._radar_editor


class TargetsEditorPage(QWidget):
    """Activity 4 - hosts the real TargetsEditor widget (Phase 4.8)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TargetsEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._targets_editor = TargetsEditor(self)
        layout.addWidget(self._targets_editor)

    def targets_editor(self) -> TargetsEditor:
        """Return the embedded :class:`TargetsEditor` (test helper)."""
        return self._targets_editor


class ResourceBrowserPage(QWidget):
    """Activity 5 placeholder - real impl in Phase 4.4 (plan/13 § 13.7)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResourceBrowserPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Resource Browser",
                hint="Phase 4.4 mounts the resource tree (Scenarios / Maps / Radars / Targets) with status icons.",
                object_name="ResourceBrowserInner",
                parent=self,
            )
        )
