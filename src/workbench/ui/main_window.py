"""TRsim MainWindow — thin assembler (Phase 4.1 + 4.2a + 4.2b).

Owns:

- A :class:`WorkspaceSelector` (model state).
- A central :class:`QStackedWidget` with one page per workspace.
- A workspace-toggle toolbar (Editor / Simulator radio actions).
- Ctrl+Shift+E / Ctrl+Shift+S shortcuts for switching.
- A :class:`WorkbenchCommandRegistry` seeded by
  :func:`register_builtin_commands` + a :class:`CommandPalette` bound
  to ``Ctrl+Shift+P``.
- A :class:`SimulationToolbar` (outer layer) and
  :class:`TargetRunToolbar` (inner layer), separated by a toolbar break.

Subsequent Phase 4 sub-phases bolt on:

- Phase 4.2c: MenuBar (File / Edit / View / Run / Plugins / Tools / Help).
- Phase 4.2d: DockManager + workspace-state persistence.
- Phase 4.3+: real Editor activities and Simulator panels.

Strict ≤ 200 lines (CLAUDE.md § 3.1 — thin assembler).
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QActionGroup, QKeySequence, QShortcut
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QWidget

from workbench import __version__
from workbench.ui.commands import (
    CommandHooks,
    CommandPalette,
    WorkbenchCommandRegistry,
    register_builtin_commands,
)
from workbench.ui.editor.workspace import EditorWorkspace
from workbench.ui.simulator.workspace import SimulatorWorkspace
from workbench.ui.toolbars import SimulationToolbar, TargetRunToolbar
from workbench.ui.workspace_selector import Workspace, WorkspaceSelector


class MainWindow(QMainWindow):
    """Thin shell that swaps Workspace pages in a QStackedWidget."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"TRsim {__version__}")
        self.resize(1280, 800)

        self.selector = WorkspaceSelector()
        self.commands = WorkbenchCommandRegistry()

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

        register_builtin_commands(self.commands, self._build_command_hooks())
        self._palette = CommandPalette(self.commands, self)
        self._palette_shortcut = QShortcut(QKeySequence("Ctrl+Shift+P"), self)
        self._palette_shortcut.activated.connect(self.open_command_palette)

        self.addToolBarBreak()
        self._sim_toolbar = SimulationToolbar(self.commands, self)
        self.addToolBar(self._sim_toolbar)
        self.addToolBarBreak()
        self._target_toolbar = TargetRunToolbar(self.commands, self)
        self.addToolBar(self._target_toolbar)

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
    # Command catalog
    # ------------------------------------------------------------------
    def _build_command_hooks(self) -> CommandHooks:
        # Phase 5 wiring replaces the no-op defaults for sim/target hooks
        # with calls into SimulationClock / RunManager via CommandBus.
        return CommandHooks(
            on_workspace_editor=self._activate_editor,
            on_workspace_simulator=self._activate_simulator,
            on_palette_open=self.open_command_palette,
        )

    def _activate_editor(self) -> None:
        self.selector.set_workspace(Workspace.EDITOR)

    def _activate_simulator(self) -> None:
        self.selector.set_workspace(Workspace.SIMULATOR)

    def open_command_palette(self) -> None:
        """Show the Command Palette dialog (idempotent)."""
        self._palette.open_fresh()

    # ------------------------------------------------------------------
    # Test-only accessors
    # ------------------------------------------------------------------
    def page(self, workspace: Workspace) -> QWidget:
        """Return the QWidget mounted for *workspace* (test helper)."""
        return self._pages[workspace]

    def workspace_action(self, workspace: Workspace) -> QAction:
        """Return the toolbar QAction for *workspace* (test helper)."""
        return self._actions[workspace]

    def command_palette(self) -> CommandPalette:
        """Return the embedded CommandPalette (test helper)."""
        return self._palette

    def simulation_toolbar(self) -> SimulationToolbar:
        """Return the SimulationToolbar (test helper)."""
        return self._sim_toolbar

    def target_run_toolbar(self) -> TargetRunToolbar:
        """Return the TargetRunToolbar (test helper)."""
        return self._target_toolbar
