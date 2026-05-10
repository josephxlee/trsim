"""Workspace selector — Editor ↔ Simulator switching primitive (Phase 4.1).

The selector owns the current :class:`Workspace` enum value and emits
``workspace_changed`` whenever it transitions. The MainWindow (and any
sidecar UI) listens to this signal to swap the central QStackedWidget
page or update toolbar state.

Stays in :mod:`workbench.ui` (not under ``ui.editor`` or ``ui.simulator``)
so it does not violate Contract 2 (workspace-isolation) when both peers
import it.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QObject, Signal


class Workspace(StrEnum):
    """Top-level UI workspace.

    The string value doubles as a stable serialization key for
    persistence (recent workspace, layout dock state).
    """

    EDITOR = "editor"
    SIMULATOR = "simulator"


class WorkspaceSelector(QObject):
    """Holds the active workspace and emits a Qt signal on change.

    Idempotent: setting the same workspace value does not re-emit.
    """

    workspace_changed = Signal(Workspace)

    def __init__(
        self, initial: Workspace = Workspace.EDITOR, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._current = initial

    @property
    def current(self) -> Workspace:
        return self._current

    def set_workspace(self, workspace: Workspace) -> bool:
        """Set active workspace. Returns True if a change occurred."""
        if workspace == self._current:
            return False
        self._current = workspace
        self.workspace_changed.emit(workspace)
        return True

    def toggle(self) -> Workspace:
        """Cycle Editor ↔ Simulator. Returns the new active workspace."""
        nxt = Workspace.SIMULATOR if self._current == Workspace.EDITOR else Workspace.EDITOR
        self.set_workspace(nxt)
        return nxt
