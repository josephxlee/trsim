"""TRsim MainWindow — thin assembler (Phase 4.1 + 4.2 complete).

Owns:

- A :class:`WorkspaceSelector` (model state).
- A central :class:`QStackedWidget` with one page per workspace.
- A workspace-toggle toolbar (Editor / Simulator radio actions).
- Ctrl+Shift+E / Ctrl+Shift+S shortcuts for switching.
- A :class:`WorkbenchCommandRegistry` seeded by
  :func:`register_builtin_commands` + a :class:`CommandPalette` bound
  to ``Ctrl+Shift+P`` (4.2a).
- A :class:`MainMenuBar` covering File / Edit / View / Run / Plugins /
  Tools / Help (4.2c).
- A :class:`SimulationToolbar` (outer layer) and
  :class:`TargetRunToolbar` (inner layer), separated by a toolbar
  break (4.2b).
- A :class:`DockManager` ready to host Phase 4.3+ panels (4.2d).

Subsequent Phase 4 sub-phases bolt on:

- Phase 4.3+: real Editor activities and Simulator panels mount as
  QDockWidgets through :class:`DockManager`.

Strict ≤ 200 lines (CLAUDE.md § 3.1 — thin assembler).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QToolBar, QWidget

from workbench import __version__
from workbench.app.dlc_runtime import default_dlc_paths
from workbench.app.physics_lab import (
    PHYSICS_MODEL_SLOT,
    register_discovered_physics_models,
)
from workbench.ui.commands import (
    CommandHooks,
    CommandPalette,
    WorkbenchCommandRegistry,
    register_builtin_commands,
)
from workbench.ui.dlc_bootstrap import (
    DLCRuntime,
    populate_composer_options_from_library,
    populate_resource_browser_from_library,
)
from workbench.ui.dock_manager import DockManager
from workbench.ui.editor.activities import Activity
from workbench.ui.editor.activity_pages import (
    MapEditorPage,
    RadarEditorPage,
    ScenarioComposerPage,
    TargetsEditorPage,
)
from workbench.ui.editor.composer import ScenarioComposerController
from workbench.ui.editor.map_editor import DEMImportController
from workbench.ui.editor.package_manager_dialog import PackageManagerController
from workbench.ui.editor.radar_editor import RadarEditorController
from workbench.ui.editor.targets_editor import TargetsEditorController
from workbench.ui.editor.workspace import EditorWorkspace
from workbench.ui.main_menu import MainMenuBar
from workbench.ui.physics_lab import PhysicsLabWorkspace
from workbench.ui.simulator.workspace import SimulatorWorkspace
from workbench.ui.toolbars import SimulationToolbar, TargetRunToolbar
from workbench.ui.workspace_selector import WORKSPACE_ORDER, Workspace, WorkspaceSelector


class MainWindow(QMainWindow):
    """Thin shell that swaps Workspace pages in a QStackedWidget."""

    def __init__(self, *, dlc_runtime: DLCRuntime | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"TRsim {__version__}")
        self.resize(1280, 800)

        self.selector = WorkspaceSelector()
        self.commands = WorkbenchCommandRegistry()
        self.docks = DockManager(host=self)
        self._dlc_runtime = dlc_runtime

        # Phase 9 J1 — pull every ``trsim.physics_model`` plugin from the
        # DLC runtime (if any) into the global registry *before* we build
        # PhysicsLabWorkspace, so its None-default :func:`default_physics_
        # models` picks them up alongside the three built-ins. Returns the
        # DiscoveryResult so the workspace surface (later cycles) can show
        # any non-fatal errors.
        self._physics_discovery = _register_dlc_physics_models(dlc_runtime)

        self._stack = QStackedWidget(self)
        sim_panel_registry = dlc_runtime.panel_registry if dlc_runtime is not None else None
        self._pages: dict[Workspace, QWidget] = {
            Workspace.EDITOR: EditorWorkspace(),
            Workspace.SIMULATOR: SimulatorWorkspace(panel_registry=sim_panel_registry),
            Workspace.PHYSICS_LAB: PhysicsLabWorkspace(),
        }
        for ws in WORKSPACE_ORDER:
            self._stack.addWidget(self._pages[ws])
        self.setCentralWidget(self._stack)

        self._actions = self._build_workspace_actions()
        self._toolbar = self._build_toolbar(self._actions)

        self.selector.workspace_changed.connect(self._on_workspace_changed)
        self._sync_to_selector()

        register_builtin_commands(self.commands, self._build_command_hooks())
        self._palette = CommandPalette(self.commands, self)

        # MainMenuBar owns Ctrl+Shift+E / S / P shortcuts (plan/05 § 5.1
        # — "All actions are Command"). We avoid registering the same
        # shortcut on a QToolBar QAction or a free-standing QShortcut
        # so Qt does not flag them as ambiguous and silently disable
        # both bindings. The toolbar QAction below is click-only.
        self._menu_bar = MainMenuBar(self, self.commands)
        self.setMenuBar(self._menu_bar)

        self.addToolBarBreak()
        self._sim_toolbar = SimulationToolbar(self.commands, self)
        self.addToolBar(self._sim_toolbar)
        self.addToolBarBreak()
        self._target_toolbar = TargetRunToolbar(self.commands, self)
        self.addToolBar(self._target_toolbar)

        # Sim + Target toolbars only make sense inside the Simulator
        # workspace; Editor / Physics Lab don't drive a running
        # simulation. The toolbars stay built but hide themselves
        # outside Simulator (option A from the toolbar-visibility
        # discussion). The selector signal landed earlier in __init__
        # so the connect goes after the toolbars exist.
        self._refresh_sim_toolbars_visibility(self.selector.current)
        self.selector.workspace_changed.connect(self._refresh_sim_toolbars_visibility)

        if self._dlc_runtime is not None:
            populate_resource_browser_from_library(
                self._editor_page().resource_browser(),
                self._dlc_runtime.app.resource_library,
            )
            # Phase 9 cycle — also feed the ScenarioComposer dropdowns
            # so the Map / Radar / Targets references show real ids
            # the moment the user lands on the Composer page. The
            # helper is on the same dlc_bootstrap module the resource
            # browser uses, so the two surfaces stay in sync.
            composer_page = self._editor_page().page(Activity.COMPOSER)
            assert isinstance(composer_page, ScenarioComposerPage)
            populate_composer_options_from_library(
                composer_page.composer(),
                self._dlc_runtime.app.resource_library,
            )

        # Phase 9 cycle — Composer Validate button now produces real
        # status feedback via the new controller (combo shape check).
        # Wired unconditionally so tests / users without a dlc_runtime
        # still see validation status when clicking Validate.
        composer_page = self._editor_page().page(Activity.COMPOSER)
        assert isinstance(composer_page, ScenarioComposerPage)
        self._composer_controller = ScenarioComposerController(
            composer=composer_page.composer(),
            parent=self,
        )
        # Same pattern for the Targets Activity Validate button.
        targets_page = self._editor_page().page(Activity.TARGETS)
        assert isinstance(targets_page, TargetsEditorPage)
        self._targets_controller = TargetsEditorController(
            editor=targets_page.targets_editor(),
            parent=self,
        )
        # Radar Activity live computed-values strip (beamwidth + peak
        # gain). Refreshes on every relevant field edit.
        radar_page = self._editor_page().page(Activity.RADAR)
        assert isinstance(radar_page, RadarEditorPage)
        self._radar_controller = RadarEditorController(
            editor=radar_page.radar_editor(),
            parent=self,
        )

        # Wire the DEM Import wizard so the MapEditor's "Import DEM..."
        # button opens it (Phase 4 dem_import_wizard E4).
        editor_page = self._editor_page()
        map_page = editor_page.page(Activity.MAP)
        assert isinstance(map_page, MapEditorPage)
        self._dem_import_controller = DEMImportController(
            map_editor=map_page.map_editor(),
            parent=self,
        )

        # Wire the DLC Package Manager (Phase 7 remainder F3). If a
        # DLC runtime is mounted, reuse its packages_root so install /
        # uninstall actions are visible to the rest of the app on
        # restart. Otherwise default to ``~/.trsim/packages``.
        packages_root: Path = (
            self._dlc_runtime.app.paths.packages_root
            if self._dlc_runtime is not None
            else default_dlc_paths().packages_root
        )
        self._dlc_manager_controller = PackageManagerController(
            packages_root=packages_root,
            parent=self,
        )

    # ------------------------------------------------------------------
    # Toolbar / actions
    # ------------------------------------------------------------------
    def _build_workspace_actions(self) -> dict[Workspace, QAction]:
        group = QActionGroup(self)
        group.setExclusive(True)

        # Toolbar QActions are click-only — MainMenuBar owns the
        # Ctrl+Shift+E / S / L shortcuts to avoid Qt's ambiguous-shortcut
        # suppression that fires when two QActions share a key.
        actions: dict[Workspace, QAction] = {}
        for ws, label in (
            (Workspace.EDITOR, "Editor"),
            (Workspace.SIMULATOR, "Simulator"),
            (Workspace.PHYSICS_LAB, "Physics Lab"),
        ):
            act = QAction(label, self)
            act.setCheckable(True)
            act.triggered.connect(lambda _checked, w=ws: self.selector.set_workspace(w))
            group.addAction(act)
            actions[ws] = act

        self._action_group = group
        return actions

    def _build_toolbar(self, actions: dict[Workspace, QAction]) -> QToolBar:
        toolbar = QToolBar("Workspace", self)
        toolbar.setObjectName("WorkspaceToolBar")
        toolbar.setMovable(False)
        for ws in WORKSPACE_ORDER:
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
        # Phase 4 L1 wires the Simulator workspace's run-controller into
        # the SIM toolbar (play / pause / stop / speed) — Run panel now
        # shows live sim_t_s / frame_id / state / speed.
        editor = self._editor_page()
        sim = self._simulator_page()
        return CommandHooks(
            on_workspace_editor=self._activate_editor,
            on_workspace_simulator=self._activate_simulator,
            on_workspace_physics_lab=self._activate_physics_lab,
            on_palette_open=self.open_command_palette,
            on_file_exit=self._exit_app,
            on_view_toggle_fullscreen=self._toggle_fullscreen,
            on_activity_composer=lambda: self._show_activity(editor, Activity.COMPOSER),
            on_activity_map=lambda: self._show_activity(editor, Activity.MAP),
            on_activity_radar=lambda: self._show_activity(editor, Activity.RADAR),
            on_activity_targets=lambda: self._show_activity(editor, Activity.TARGETS),
            on_activity_browser=lambda: self._show_activity(editor, Activity.BROWSER),
            on_plugins_manage=self._open_dlc_manager,
            on_plugins_install_package=self._install_dlc_package,
            on_sim_start=sim.sim_play,
            on_sim_pause=sim.sim_pause,
            on_sim_stop=sim.sim_stop,
            on_sim_speed=sim.sim_set_speed,
        )

    def _simulator_page(self) -> SimulatorWorkspace:
        page = self._pages[Workspace.SIMULATOR]
        assert isinstance(page, SimulatorWorkspace)
        return page

    def _open_dlc_manager(self) -> None:
        """Hook for the ``plugins.manage`` command — open the dialog."""
        self._dlc_manager_controller.open_dialog()

    def _install_dlc_package(self) -> None:
        """Hook for the ``plugins.install_package`` command — direct
        file picker without opening the full Package Manager dialog.
        """
        self._dlc_manager_controller.install_via_file_picker()

    def _editor_page(self) -> EditorWorkspace:
        page = self._pages[Workspace.EDITOR]
        assert isinstance(page, EditorWorkspace)
        return page

    def _show_activity(self, editor: EditorWorkspace, activity: Activity) -> None:
        # Switch to the Editor workspace first so the activity becomes
        # visible even when the user dispatched the command from the
        # palette while sitting in the Simulator workspace.
        self.selector.set_workspace(Workspace.EDITOR)
        editor.selector.set_activity(activity)

    def _exit_app(self) -> None:
        self.close()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _activate_editor(self) -> None:
        self.selector.set_workspace(Workspace.EDITOR)

    def _activate_simulator(self) -> None:
        self.selector.set_workspace(Workspace.SIMULATOR)

    def _activate_physics_lab(self) -> None:
        self.selector.set_workspace(Workspace.PHYSICS_LAB)

    def _refresh_sim_toolbars_visibility(self, workspace: Workspace) -> None:
        """Show Sim + Target toolbars only on the Simulator workspace."""
        show = workspace is Workspace.SIMULATOR
        self._sim_toolbar.setVisible(show)
        self._target_toolbar.setVisible(show)

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

    def main_menu_bar(self) -> MainMenuBar:
        """Return the MainWindow's QMenuBar (test helper)."""
        return self._menu_bar

    def dock_manager(self) -> DockManager:
        """Return the DockManager (test helper)."""
        return self.docks

    def dlc_runtime(self) -> DLCRuntime | None:
        """Return the bound :class:`DLCRuntime`, or ``None``."""
        return self._dlc_runtime

    def dem_import_controller(self) -> DEMImportController:
        """Return the wired :class:`DEMImportController` (test helper)."""
        return self._dem_import_controller

    def dlc_manager_controller(self) -> PackageManagerController:
        """Return the wired :class:`PackageManagerController` (test helper)."""
        return self._dlc_manager_controller

    def physics_discovery_result(self) -> object:
        """Return the J1 :class:`DiscoveryResult` (or ``None`` when no DLC)."""
        return self._physics_discovery


def _register_dlc_physics_models(dlc_runtime: DLCRuntime | None) -> object:
    """Push the DLC's ``trsim.physics_model`` plugins into the registry.

    Returns the :class:`DiscoveryResult` for the caller to inspect; or
    ``None`` if no DLC is mounted (the typical headless-test path).
    """
    if dlc_runtime is None:
        return None
    plugins = dlc_runtime.app.plugin_loader.plugins_for_slot(PHYSICS_MODEL_SLOT)
    return register_discovered_physics_models({PHYSICS_MODEL_SLOT: plugins})
