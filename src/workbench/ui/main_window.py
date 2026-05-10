"""TRsim MainWindow — thin assembler (Phase 4.1).

Owns:

- A :class:`WorkspaceSelector` (model state).
- A central :class:`QStackedWidget` with one page per workspace.
- A workspace-toggle toolbar (Editor / Simulator radio actions).
- Ctrl+Shift+E / Ctrl+Shift+S shortcuts for switching.

Subsequent Phase 4 sub-phases bolt on:

- Phase 4.2: DockManager, CommandPalette, Toolbar (Sim/Target), Menu.
- Phase 4.3+: real Editor activities and Simulator panels.

Strict ≤ 200 lines (CLAUDE.md § 3.1 — thin assembler).
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QWidget

from workbench import __version__
from workbench.ui.editor.workspace import EditorWorkspace
from workbench.ui.simulator.workspace import SimulatorWorkspace
from workbench.ui.workspace_selector import Workspace, WorkspaceSelector


class MainWindow(QMainWindow):
    """Thin shell that swaps Workspace pages in a QStackedWidget."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"TRsim {__version__}")
        self.resize(1280, 800)

        self.selector = WorkspaceSelector()

        self._stack = QStackedWidget(self)
        self._pages: dict[Workspace, QWidget] = {
            Workspace.EDITOR: EditorWorkspace(),
            Workspace.SIMULATOR: SimulatorWorkspace(),
        }
        for ws in (Workspace.EDITOR, Workspace.SIMULATOR):
            self._stack.addWidget(self._pages[ws])
        self.setCentralWidget(self._stack)

        self._actions = self._build_workspace_actions()
        self._toolbar = self._build_toolbar(self._actions)

        self.selector.workspace_changed.connect(self._on_workspace_changed)
        self._sync_to_selector()

    # ------------------------------------------------------------------
    # Toolbar / actions
    # ------------------------------------------------------------------
    def _build_workspace_actions(self) -> dict[Workspace, QAction]:
        group = QActionGroup(self)
        group.setExclusive(True)

        actions: dict[Workspace, QAction] = {}
        for ws, label, shortcut in (
            (Workspace.EDITOR, "Editor", "Ctrl+Shift+E"),
            (Workspace.SIMULATOR, "Simulator", "Ctrl+Shift+S"),
        ):
            act = QAction(label, self)
            act.setCheckable(True)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda _checked, w=ws: self.selector.set_workspace(w))
            group.addAction(act)
            actions[ws] = act

        self._action_group = group
        return actions

    def _build_toolbar(self, actions: dict[Workspace, QAction]) -> QToolBar:
        toolbar = QToolBar("Workspace", self)
        toolbar.setObjectName("WorkspaceToolBar")
        toolbar.setMovable(False)
        for ws in (Workspace.EDITOR, Workspace.SIMULATOR):
            toolbar.addAction(actions[ws])
        self.addToolBar(toolbar)
        return toolbar

    # ------------------------------------------------------------------
    # Workspace sync
    # ------------------------------------------------------------------
    def _on_workspace_changed(self, workspace: Workspace) -> None:
        self._stack.setCurrentWidget(self._pages[workspace])
        self._actions[workspace].setChecked(True)

    def _sync_to_selector(self) -> None:
        ws = self.selector.current
        self._stack.setCurrentWidget(self._pages[ws])
        self._actions[ws].setChecked(True)

    # ------------------------------------------------------------------
    # Test-only accessors
    # ------------------------------------------------------------------
    def page(self, workspace: Workspace) -> QWidget:
        """Return the QWidget mounted for *workspace* (test helper)."""
        return self._pages[workspace]

    def workspace_action(self, workspace: Workspace) -> QAction:
        """Return the toolbar QAction for *workspace* (test helper)."""
        return self._actions[workspace]
