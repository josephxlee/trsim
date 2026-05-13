"""MainWindow QMenuBar (Phase 4.2c).

Reads :class:`WorkbenchCommandRegistry` and exposes a structured
:class:`MainMenuBar`. Every menu entry is a QAction that calls
``registry.dispatch(command_id)`` so menu, toolbar, and palette share a
single dispatch path (plan/05 section 5.1 - "All actions are Command").

Layout (plan/05 section 5.2):

    File   Edit   View   Run   Plugins   Tools   Help

At Phase 4.2c the MVP set is:

- File: New Resource, Open Scenario, Save, Exit
- View: Switch to Editor / Simulator, Show Command Palette,
  Reset Layout, Toggle Fullscreen
- Run: Sim Start / Pause / Stop, Speed submenu (x1/x2/x4/x8),
  Target Run / Pause / Stop
- Plugins: Manage..., Reload All
- Help: About TRsim

Edit and Tools are intentionally empty placeholders at this phase
(populated by Phase 4.7+ Editor activities and Phase 4.10+ Physics Lab
/ HIL Console respectively).

The class wraps QMenuBar so it can hold strong Python references to
every QMenu it builds. Without this, sub-menus reachable only through
``bar.actions()[i].menu()`` are vulnerable to PySide6's
"Internal C++ object already deleted" runtime error when the sole
Python reference falls out of scope.
"""

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from workbench.ui.commands.builtin import SIM_SPEEDS
from workbench.ui.commands.registry import WorkbenchCommandRegistry

_TOP_LEVEL_KEYS: tuple[str, ...] = (
    "file",
    "edit",
    "view",
    "run",
    "plugins",
    "tools",
    "help",
)


class MainMenuBar(QMenuBar):
    """Workbench top-level menu bar with strong refs to every QMenu."""

    def __init__(
        self,
        parent: QWidget,
        registry: WorkbenchCommandRegistry,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MainMenuBar")
        self._registry = registry
        self._menus: dict[str, QMenu] = {}
        self._submenu_speed: QMenu | None = None

        self._build_file_menu()
        self._build_edit_menu()
        self._build_view_menu()
        self._build_run_menu()
        self._build_plugins_menu()
        self._build_tools_menu()
        self._build_help_menu()

    # ------------------------------------------------------------------
    # Per-menu builders
    # ------------------------------------------------------------------
    def _build_file_menu(self) -> None:
        menu = self._add_top_level("file", "&File", "MenuFile")
        self._attach(menu, "file.new")
        self._attach(menu, "file.open")
        self._attach(menu, "file.save")
        menu.addSeparator()
        self._attach(menu, "file.exit")

    def _build_edit_menu(self) -> None:
        # Phase 4.7+ will populate this once the Editor exposes Undo/Redo.
        self._add_top_level("edit", "&Edit", "MenuEdit")

    def _build_view_menu(self) -> None:
        menu = self._add_top_level("view", "&View", "MenuView")
        self._attach(menu, "workspace.switch_to_editor")
        self._attach(menu, "workspace.switch_to_simulator")
        self._attach(menu, "workspace.switch_to_physics_lab")
        menu.addSeparator()
        self._attach(menu, "palette.open")
        self._attach(menu, "view.reset_layout")
        self._attach(menu, "view.toggle_fullscreen")

    def _build_run_menu(self) -> None:
        menu = self._add_top_level("run", "&Run", "MenuRun")
        self._attach(menu, "sim.start")
        self._attach(menu, "sim.pause")
        self._attach(menu, "sim.stop")
        speed = QMenu("Simulation Speed", menu)
        speed.setObjectName("MenuRunSpeed")
        for multiplier in SIM_SPEEDS:
            self._attach(speed, f"sim.speed.x{multiplier}")
        menu.addMenu(speed)
        self._submenu_speed = speed
        menu.addSeparator()
        self._attach(menu, "target.run")
        self._attach(menu, "target.pause")
        self._attach(menu, "target.stop")

    def _build_plugins_menu(self) -> None:
        menu = self._add_top_level("plugins", "&Plugins", "MenuPlugins")
        self._attach(menu, "plugins.manage")
        self._attach(menu, "plugins.install_package")
        self._attach(menu, "plugins.reload_all")

    def _build_tools_menu(self) -> None:
        # Phase 4.10+ adds Physics Lab / HIL Console entries here.
        self._add_top_level("tools", "&Tools", "MenuTools")

    def _build_help_menu(self) -> None:
        menu = self._add_top_level("help", "&Help", "MenuHelp")
        self._attach(menu, "help.about")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _add_top_level(self, key: str, title: str, object_name: str) -> QMenu:
        menu = QMenu(title, self)
        menu.setObjectName(object_name)
        self.addMenu(menu)
        self._menus[key] = menu
        return menu

    def _attach(self, menu: QMenu, command_id: str) -> QAction:
        cmd = self._registry.get(command_id)
        act = QAction(cmd.title, menu)
        act.setObjectName(f"MenuAction_{command_id}")
        if cmd.shortcut is not None:
            act.setShortcut(QKeySequence(cmd.shortcut))
        act.setEnabled(cmd.is_enabled())
        registry = self._registry
        act.triggered.connect(lambda _checked=False, cid=command_id: registry.dispatch(cid))
        menu.addAction(act)
        return act

    # ------------------------------------------------------------------
    # Public accessors (test + future Phase 5 wiring)
    # ------------------------------------------------------------------
    def menu_for(self, key: str) -> QMenu:
        """Return the top-level QMenu for ``key`` (one of file/edit/...)."""
        if key not in _TOP_LEVEL_KEYS:
            msg = f"unknown menu key {key!r}; expected one of {_TOP_LEVEL_KEYS}"
            raise ValueError(msg)
        return self._menus[key]

    def speed_submenu(self) -> QMenu:
        """Return the Simulation Speed submenu (Run > Simulation Speed)."""
        if self._submenu_speed is None:  # pragma: no cover - never None post __init__
            msg = "speed submenu not built; this should not happen"
            raise RuntimeError(msg)
        return self._submenu_speed

    def action_for(self, command_id: str) -> QAction:
        """Return the QAction wired to ``command_id`` anywhere in the bar."""
        target = f"MenuAction_{command_id}"
        for menu in (*self._menus.values(), self._submenu_speed):
            if menu is None:
                continue
            for action in menu.actions():
                if action.objectName() == target:
                    return action
        msg = f"no menu action found for command {command_id!r}"
        raise KeyError(msg)
