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

    # Phase 4.2a — workspace + palette.
    on_workspace_editor: Callable[[], None] = field(default=_noop)
    on_workspace_simulator: Callable[[], None] = field(default=_noop)
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
