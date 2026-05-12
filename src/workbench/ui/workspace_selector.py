"""Workspace selector — Editor / Simulator / Physics Lab (Phase 4.1 + PL-A).

The selector owns the current :class:`Workspace` enum value and emits
``workspace_changed`` whenever it transitions. The MainWindow (and any
sidecar UI) listens to this signal to swap the central QStackedWidget
page or update toolbar state.

The third workspace — Physics Lab — was added in PL-A. plan/19 places
it as TRsim's 5th differentiator (now the user's 1st priority per the
ranking "physics_lab > simulator > editor"): an interactive 3-pane
environment where the physics formulas backing the simulator are
proven, visually verified, and (eventually) user-extended.

Stays in :mod:`workbench.ui` (not under ``ui.editor`` or
``ui.simulator``) so it does not violate Contract 2
(workspace-isolation) when both peers import it.
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
    PHYSICS_LAB = "physics_lab"


# Declarative order used by the toolbar / menu / cycle helper so the
# three workspaces always appear in the same sequence: Editor first
# (the authoring start point), Simulator next (the runtime view),
# Physics Lab last (the validation / proof environment).
WORKSPACE_ORDER: tuple[Workspace, ...] = (
    Workspace.EDITOR,
    Workspace.SIMULATOR,
    Workspace.PHYSICS_LAB,
)


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
        """Cycle through :data:`WORKSPACE_ORDER`. Returns the new active workspace.

        Editor -> Simulator -> Physics Lab -> Editor.
        """
        idx = WORKSPACE_ORDER.index(self._current)
        nxt = WORKSPACE_ORDER[(idx + 1) % len(WORKSPACE_ORDER)]
        self.set_workspace(nxt)
        return nxt
