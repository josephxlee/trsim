"""Built-in command catalog (plan/04 § 4.3 Phase 3).

Phase 3.1 — central directory of Sim / Target / Positioner / Editor /
Workspace command names. Importing this module gives Plugin authors
a single source of truth for the strings the CommandBus accepts.

The handlers themselves are registered by the App boot sequence
(Phase 3.2 / 3.7); this module just exposes the names + a builder
that pre-registers no-op stubs for testing.
"""

from __future__ import annotations

from typing import Final

from workbench.app.command_bus import Command, CommandBus

# --- Sim commands (v0.15) --------------------------------------------

SIM_START: Final[str] = "sim.start"
SIM_PAUSE: Final[str] = "sim.pause"
SIM_STOP: Final[str] = "sim.stop"
SIM_SET_SPEED: Final[str] = "sim.set_speed"

# --- Target Run commands (v0.14) -------------------------------------

TARGET_RUN: Final[str] = "target.run"
TARGET_PAUSE: Final[str] = "target.pause"
TARGET_STOP: Final[str] = "target.stop"

# --- Positioner commands (v0.14) -------------------------------------

POSITIONER_TOGGLE_MODE: Final[str] = "positioner.toggle_mode"
POSITIONER_MANUAL_ADJUST: Final[str] = "positioner.manual_adjust"

# --- Editor / Workspace commands (v0.19~v0.20) -----------------------

EDITOR_SAVE_RESOURCE: Final[str] = "editor.save_resource"
EDITOR_VALIDATE: Final[str] = "editor.validate"
EDITOR_EXPORT_BUNDLE: Final[str] = "editor.export_bundle"

WORKSPACE_SWITCH_TO_EDITOR: Final[str] = "workspace.switch_to_editor"
WORKSPACE_SWITCH_TO_SIMULATOR: Final[str] = "workspace.switch_to_simulator"


BUILTIN_COMMAND_NAMES: Final[tuple[str, ...]] = (
    SIM_START,
    SIM_PAUSE,
    SIM_STOP,
    SIM_SET_SPEED,
    TARGET_RUN,
    TARGET_PAUSE,
    TARGET_STOP,
    POSITIONER_TOGGLE_MODE,
    POSITIONER_MANUAL_ADJUST,
    EDITOR_SAVE_RESOURCE,
    EDITOR_VALIDATE,
    EDITOR_EXPORT_BUNDLE,
    WORKSPACE_SWITCH_TO_EDITOR,
    WORKSPACE_SWITCH_TO_SIMULATOR,
)
"""Tuple of every built-in command name. Useful for sanity checks."""


def register_noop_handlers(bus: CommandBus) -> None:
    """Register a no-op handler for every built-in command.

    Useful in tests where the actual side effect doesn't matter — the
    test only needs to dispatch and verify Lineage / events. Each
    handler returns ``None``.
    """

    def _noop(_: Command) -> None:
        return None

    for name in BUILTIN_COMMAND_NAMES:
        bus.register(name, _noop)
