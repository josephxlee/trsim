"""UI command catalog (plan/05 § 5.4 — Workbench-level commands).

This package holds the **UI** notion of a Command (menu / toolbar /
palette action). It is distinct from :mod:`workbench.app.command_bus`,
which carries **domain** commands (sim.start / target.run /
positioner.toggle_mode) through the Single Command Path.

The two layers connect at the leaves: a UI command's ``execute``
callable typically calls ``CommandBus.dispatch(...)`` (or a service
method) — but the registries themselves stay separate so that the UI
catalog can include actions with no domain side-effect (``view.toggle_panel``,
``palette.open``).
"""

from __future__ import annotations

from workbench.ui.commands.palette import CommandPalette
from workbench.ui.commands.registry import (
    WorkbenchCommand,
    WorkbenchCommandRegistry,
)

__all__ = [
    "CommandPalette",
    "WorkbenchCommand",
    "WorkbenchCommandRegistry",
]
