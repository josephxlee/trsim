"""WorkbenchCommand + Registry (plan/05 § 5.4).

A :class:`WorkbenchCommand` is the UI-layer notion of a user-invokable
action — what menus, toolbars, and the Command Palette show. Each
command has a stable dot-namespaced ``id`` (``"scenario.open"``,
``"workspace.switch_to_editor"``), a human title, a category for
grouping in the palette, and an ``execute`` callable.

This is **not** the Single Command Path of
:mod:`workbench.app.command_bus`. UI commands typically **call into**
that bus inside their ``execute``, but the catalog here also holds
purely-UI actions with no domain side-effect (toggle a panel, open the
palette, reset the layout).

Search is intentionally simple: case-insensitive substring match on
``id`` and ``title``, with title hits ranked first. Real fuzzy ranking
(edit distance, MRU weighting) is a post-MVP follow-up.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

ExecuteFn = Callable[[], None]
EnabledFn = Callable[[], bool]


@dataclass(frozen=True, slots=True)
class WorkbenchCommand:
    """One UI-invokable action (menu / toolbar / palette entry).

    Attributes:
        id: Stable dot-namespaced identifier. Unique within a
            registry — re-registration is rejected.
        title: Human-readable label shown in menus and the palette.
        category: Group label (``"Scenario"`` / ``"View"`` /
            ``"Simulation"``). Used by the palette to group results.
        execute: Zero-arg callable invoked when the user picks the
            command. Errors propagate to the caller of ``dispatch``.
        shortcut: Optional default keyboard shortcut string
            (``"Ctrl+Shift+P"``). The shortcut is **advisory** — actual
            QShortcut wiring lives in MainWindow.
        description: Optional one-line tooltip. Empty by default.
        enabled_when: Optional predicate. ``None`` (default) means the
            command is always enabled. The palette greys out commands
            whose predicate returns ``False`` and ``dispatch`` raises
            :class:`RuntimeError` for them.
        icon: Optional theme-icon name (toolbar use). Plain string —
            resolution is the toolbar's job.

    Raises:
        ValueError: If ``id``, ``title``, or ``category`` is empty.
    """

    id: str
    title: str
    category: str
    execute: ExecuteFn
    shortcut: str | None = None
    description: str = ""
    enabled_when: EnabledFn | None = None
    icon: str | None = None

    def __post_init__(self) -> None:
        for field_name, value in (
            ("id", self.id),
            ("title", self.title),
            ("category", self.category),
        ):
            if not value:
                msg = f"WorkbenchCommand.{field_name} must be a non-empty string"
                raise ValueError(msg)

    def is_enabled(self) -> bool:
        """Return True iff ``enabled_when`` is unset or returns True."""
        return self.enabled_when is None or self.enabled_when()


@dataclass(slots=True)
class WorkbenchCommandRegistry:
    """In-memory registry of :class:`WorkbenchCommand` by ``id``.

    Mutable by intent — boot code registers commands, user-installed
    plugins may add more later. Registration is idempotent only via
    explicit :meth:`unregister`; re-registering the same id raises
    :class:`ValueError` to surface accidental shadowing.
    """

    _commands: dict[str, WorkbenchCommand] = field(default_factory=dict)

    def register(self, command: WorkbenchCommand) -> None:
        """Register ``command``. Raises if its id is already taken."""
        if command.id in self._commands:
            msg = f"command id {command.id!r} is already registered"
            raise ValueError(msg)
        self._commands[command.id] = command

    def unregister(self, command_id: str) -> None:
        """Remove ``command_id``. Raises :class:`KeyError` if absent."""
        del self._commands[command_id]

    def is_registered(self, command_id: str) -> bool:
        return command_id in self._commands

    def get(self, command_id: str) -> WorkbenchCommand:
        """Return the command registered under ``command_id``."""
        return self._commands[command_id]

    def all(self) -> tuple[WorkbenchCommand, ...]:
        """Snapshot of every registered command, insertion order."""
        return tuple(self._commands.values())

    def find(self, query: str) -> tuple[WorkbenchCommand, ...]:
        """Substring-match commands by ``title`` then ``id``.

        Empty query returns every command in registration order. Title
        matches rank above id-only matches; within a tier the original
        registration order is preserved.
        """
        q = query.strip().lower()
        if not q:
            return self.all()

        title_hits: list[WorkbenchCommand] = []
        id_only_hits: list[WorkbenchCommand] = []
        for cmd in self._commands.values():
            if q in cmd.title.lower():
                title_hits.append(cmd)
            elif q in cmd.id.lower():
                id_only_hits.append(cmd)
        return tuple(title_hits + id_only_hits)

    def dispatch(self, command_id: str) -> None:
        """Run ``command_id``'s ``execute`` after an enabled check.

        Raises:
            KeyError: If ``command_id`` is not registered.
            RuntimeError: If the command's ``enabled_when`` returns False.
        """
        cmd = self._commands[command_id]
        if not cmd.is_enabled():
            msg = f"command {command_id!r} is currently disabled"
            raise RuntimeError(msg)
        cmd.execute()
