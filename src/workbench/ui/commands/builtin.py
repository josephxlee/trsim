"""Built-in :class:`WorkbenchCommand` registration (Phase 4.2b).

The MainWindow boot sequence calls :func:`register_builtin_commands`
to seed the catalog with workspace-switching, palette, simulation,
target-run, and speed commands.

Most commands are **UI-stubs** at this phase: they accept a ``hooks``
mapping whose default values are no-ops. Phase 5 (App-layer wiring)
replaces those defaults with calls into :class:`SimulationClock` /
:class:`RunManager` via the domain :class:`CommandBus`.

Splitting registration out of :mod:`workbench.ui.main_window` keeps the
window class a thin assembler (CLAUDE.md § 3.1 ≤ 200 lines).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from workbench.ui.commands.registry import (
    ExecuteFn,
    WorkbenchCommand,
    WorkbenchCommandRegistry,
)


def _noop() -> None:
    return None


def _bind_speed(hook: Callable[[int], None], multiplier: int) -> ExecuteFn:
    """Return a zero-arg ``ExecuteFn`` that calls ``hook(multiplier)``."""

    def _execute() -> None:
        hook(multiplier)

    return _execute


@dataclass(slots=True)
class CommandHooks:
    """Concrete callbacks the MainWindow injects when registering commands.

    All hooks default to a no-op so individual sub-phases can wire
    only what they need. Defaults are zero-arg ``Callable[[], None]``.
    Speed hooks are passed the multiplier in their name (1/2/4/8) at
    *registration* time, so each ends up zero-arg here too.
    """

    # Phase 4.2a + PL-A — workspace + palette.
    on_workspace_editor: Callable[[], None] = field(default=_noop)
    on_workspace_simulator: Callable[[], None] = field(default=_noop)
    on_workspace_physics_lab: Callable[[], None] = field(default=_noop)
    on_palette_open: Callable[[], None] = field(default=_noop)

    # Phase 4.2b — simulation outer layer.
    on_sim_start: Callable[[], None] = field(default=_noop)
    on_sim_pause: Callable[[], None] = field(default=_noop)
    on_sim_stop: Callable[[], None] = field(default=_noop)
    on_sim_speed: Callable[[int], None] = field(default=lambda _m: None)

    # Phase 4.2b — target-run inner layer.
    on_target_run: Callable[[], None] = field(default=_noop)
    on_target_pause: Callable[[], None] = field(default=_noop)
    on_target_stop: Callable[[], None] = field(default=_noop)

    # Phase 4.2c — file / view / plugins / help (menu bar entries).
    on_file_new: Callable[[], None] = field(default=_noop)
    on_file_open: Callable[[], None] = field(default=_noop)
    on_file_save: Callable[[], None] = field(default=_noop)
    on_file_exit: Callable[[], None] = field(default=_noop)
    on_view_reset_layout: Callable[[], None] = field(default=_noop)
    on_view_toggle_fullscreen: Callable[[], None] = field(default=_noop)
    on_plugins_manage: Callable[[], None] = field(default=_noop)
    on_plugins_install_package: Callable[[], None] = field(default=_noop)
    on_plugins_reload_all: Callable[[], None] = field(default=_noop)
    on_help_about: Callable[[], None] = field(default=_noop)

    # Phase 4.3 — Editor Activity switching.
    on_activity_composer: Callable[[], None] = field(default=_noop)
    on_activity_map: Callable[[], None] = field(default=_noop)
    on_activity_radar: Callable[[], None] = field(default=_noop)
    on_activity_targets: Callable[[], None] = field(default=_noop)
    on_activity_atmosphere: Callable[[], None] = field(default=_noop)
    on_activity_browser: Callable[[], None] = field(default=_noop)


SIM_SPEEDS: tuple[int, ...] = (1, 2, 4, 8)


def register_builtin_commands(
    registry: WorkbenchCommandRegistry,
    hooks: CommandHooks,
) -> None:
    """Populate ``registry`` with every Phase 4.2 built-in command.

    Idempotency: this function expects a *fresh* registry — calling it
    twice raises :class:`ValueError` from the first duplicate id.
    """
    # ----- Workspace + palette (Phase 4.2a) -----
    registry.register(
        WorkbenchCommand(
            id="workspace.switch_to_editor",
            title="Switch to Editor Workspace",
            category="Workspace",
            execute=hooks.on_workspace_editor,
            shortcut="Ctrl+Shift+E",
        )
    )
    registry.register(
        WorkbenchCommand(
            id="workspace.switch_to_simulator",
            title="Switch to Simulator Workspace",
            category="Workspace",
            execute=hooks.on_workspace_simulator,
            shortcut="Ctrl+Shift+S",
        )
    )
    registry.register(
        WorkbenchCommand(
            id="workspace.switch_to_physics_lab",
            title="Switch to Physics Lab Workspace",
            category="Workspace",
            execute=hooks.on_workspace_physics_lab,
            shortcut="Ctrl+Shift+L",
        )
    )
    registry.register(
        WorkbenchCommand(
            id="palette.open",
            title="Show Command Palette",
            category="View",
            execute=hooks.on_palette_open,
            shortcut="Ctrl+Shift+P",
        )
    )

    # ----- Simulation (outer layer) -----
    registry.register(
        WorkbenchCommand(
            id="sim.start",
            title="Start Simulation",
            category="Simulation",
            execute=hooks.on_sim_start,
            shortcut="Shift+Space",
        )
    )
    registry.register(
        WorkbenchCommand(
            id="sim.pause",
            title="Pause Simulation",
            category="Simulation",
            execute=hooks.on_sim_pause,
        )
    )
    registry.register(
        WorkbenchCommand(
            id="sim.stop",
            title="Stop Simulation",
            category="Simulation",
            execute=hooks.on_sim_stop,
            shortcut="Ctrl+Space",
        )
    )
    for multiplier in SIM_SPEEDS:
        registry.register(
            WorkbenchCommand(
                id=f"sim.speed.x{multiplier}",
                title=f"Set Simulation Speed x{multiplier}",
                category="Simulation",
                execute=_bind_speed(hooks.on_sim_speed, multiplier),
                shortcut=str(multiplier),
            )
        )

    # ----- Target Run (inner layer) -----
    registry.register(
        WorkbenchCommand(
            id="target.run",
            title="Start Target Run",
            category="Target Run",
            execute=hooks.on_target_run,
            shortcut="Space",
        )
    )
    registry.register(
        WorkbenchCommand(
            id="target.pause",
            title="Pause Target Run",
            category="Target Run",
            execute=hooks.on_target_pause,
        )
    )
    registry.register(
        WorkbenchCommand(
            id="target.stop",
            title="Stop Target Run",
            category="Target Run",
            execute=hooks.on_target_stop,
            shortcut="Shift+Ctrl+Space",
        )
    )

    # ----- File / View / Plugins / Help (Phase 4.2c menu bar) -----
    for cmd in (
        WorkbenchCommand(
            id="file.new",
            title="New Resource...",
            category="File",
            execute=hooks.on_file_new,
            shortcut="Ctrl+N",
        ),
        WorkbenchCommand(
            id="file.open",
            title="Open Scenario...",
            category="File",
            execute=hooks.on_file_open,
            shortcut="Ctrl+O",
        ),
        WorkbenchCommand(
            id="file.save",
            title="Save",
            category="File",
            execute=hooks.on_file_save,
            shortcut="Ctrl+S",
        ),
        WorkbenchCommand(
            id="file.exit",
            title="Exit",
            category="File",
            execute=hooks.on_file_exit,
            shortcut="Ctrl+Q",
        ),
        WorkbenchCommand(
            id="view.reset_layout",
            title="Reset Layout",
            category="View",
            execute=hooks.on_view_reset_layout,
        ),
        WorkbenchCommand(
            id="view.toggle_fullscreen",
            title="Toggle Fullscreen",
            category="View",
            execute=hooks.on_view_toggle_fullscreen,
            shortcut="F11",
        ),
        WorkbenchCommand(
            id="plugins.manage",
            title="Manage Plugins...",
            category="Plugins",
            execute=hooks.on_plugins_manage,
        ),
        WorkbenchCommand(
            id="plugins.install_package",
            title="Install Package...",
            category="Plugins",
            execute=hooks.on_plugins_install_package,
        ),
        WorkbenchCommand(
            id="plugins.reload_all",
            title="Reload All Plugins",
            category="Plugins",
            execute=hooks.on_plugins_reload_all,
        ),
        WorkbenchCommand(
            id="help.about",
            title="About TRsim",
            category="Help",
            execute=hooks.on_help_about,
        ),
        # ----- Editor Activity (Phase 4.3) -----
        WorkbenchCommand(
            id="editor.activity.composer",
            title="Editor: Open Scenario Composer",
            category="Editor",
            execute=hooks.on_activity_composer,
            shortcut="Ctrl+1",
        ),
        WorkbenchCommand(
            id="editor.activity.map",
            title="Editor: Open Map Editor",
            category="Editor",
            execute=hooks.on_activity_map,
            shortcut="Ctrl+2",
        ),
        WorkbenchCommand(
            id="editor.activity.radar",
            title="Editor: Open Radar Editor",
            category="Editor",
            execute=hooks.on_activity_radar,
            shortcut="Ctrl+3",
        ),
        WorkbenchCommand(
            id="editor.activity.targets",
            title="Editor: Open Targets Editor",
            category="Editor",
            execute=hooks.on_activity_targets,
            shortcut="Ctrl+4",
        ),
        WorkbenchCommand(
            id="editor.activity.atmosphere",
            title="Editor: Open Atmosphere Panel",
            category="Editor",
            execute=hooks.on_activity_atmosphere,
            shortcut="Ctrl+5",
        ),
        WorkbenchCommand(
            id="editor.activity.browser",
            title="Editor: Open Resource Browser",
            category="Editor",
            execute=hooks.on_activity_browser,
            shortcut="Ctrl+6",
        ),
    ):
        registry.register(cmd)
