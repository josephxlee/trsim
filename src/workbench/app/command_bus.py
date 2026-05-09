"""Command dispatch + Lineage record (plan/04 § 4.3 Phase 3, v0.14).

Phase 3.1 — single entry point for every state-changing operation
(Sim start/pause/stop, target run, positioner move, editor save, ...).
Each command is dispatched through one chokepoint so the Lineage log
captures *who* triggered *what*, *when*, *with what arguments* —
the v0.14 Single Command Path requirement (plan/04 / plan/14 audit).

Two layers:

- :class:`Command` — record of one dispatched command (frozen).
- :class:`CommandBus` — registers handlers and dispatches.

The Lineage log is an ordered tuple of :class:`Command` instances
held on the bus. The :class:`workbench.app.evaluator` (Phase 3.2)
consumes it later for replay-validation reports.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from workbench.app.event_bus import EventBus
from workbench.domain.types import CommandSource

CommandHandler = Callable[["Command"], object]
"""Handler signature — receives the full Command, returns any payload."""


@dataclass(frozen=True, slots=True)
class Command:
    """Single dispatched command (Lineage record).

    Attributes:
        name: Dot-namespaced identifier (``"sim.start"`` / ``"target.run"``).
        source: Who triggered the command — UI / CLI / PLUGIN / TRACKER /
            REPLAY. Drives the v0.14 source-track-id requirement.
        args: Optional argument dict (interpretation per command).
        sim_t_s: Simulation time at dispatch [s]. ``-1.0`` if dispatched
            before the SimulationClock starts (CLI bootstrap).
        wall_ns: ``time.perf_counter_ns()`` at dispatch.
        source_track_id: Originating track id when ``source ==
            CommandSource.TRACKER``. ``None`` otherwise.
        source_frame_id: Frame at which the tracker decision was made
            (paired with ``source_track_id``).

    Raises:
        ValueError: If ``source == TRACKER`` and either id is missing.
    """

    name: str
    source: CommandSource
    args: dict[str, object] = field(default_factory=dict)
    sim_t_s: float = -1.0
    wall_ns: int = 0
    source_track_id: int | None = None
    source_frame_id: int | None = None

    def __post_init__(self) -> None:
        if not self.name:
            msg = "Command.name must be a non-empty string"
            raise ValueError(msg)
        if self.source is CommandSource.TRACKER and (
            self.source_track_id is None or self.source_frame_id is None
        ):
            msg = (
                "TRACKER-sourced commands must set both source_track_id "
                "and source_frame_id (plan/04 v0.14 Single Command Path)."
            )
            raise ValueError(msg)


@dataclass(slots=True)
class CommandBus:
    """Registry + dispatch + Lineage recorder.

    Mutable by intent — handlers register at boot, Lineage grows
    with every dispatch. Single-threaded MVP.

    Attributes:
        events: Optional :class:`EventBus` to mirror dispatched
            commands as ``"command.dispatched"`` events. ``None`` to
            disable.
    """

    events: EventBus | None = None
    _handlers: dict[str, CommandHandler] = field(default_factory=dict)
    _lineage: list[Command] = field(default_factory=list)

    def register(self, name: str, handler: CommandHandler) -> None:
        """Register a single handler for ``name``.

        Re-registering with the same name overwrites the previous
        handler — useful in tests but the App boot sequence should
        register every command exactly once.

        Args:
            name: Dot-namespaced command identifier.
            handler: Callable receiving the Command, returning any
                handler-defined result.

        Raises:
            ValueError: If ``name`` is empty.
        """
        if not name:
            msg = "command name must be a non-empty string"
            raise ValueError(msg)
        self._handlers[name] = handler

    def is_registered(self, name: str) -> bool:
        """Whether a handler is currently registered for ``name``."""
        return name in self._handlers

    def dispatch(
        self,
        name: str,
        source: CommandSource,
        args: dict[str, object] | None = None,
        *,
        sim_t_s: float = -1.0,
        source_track_id: int | None = None,
        source_frame_id: int | None = None,
    ) -> object:
        """Build a :class:`Command`, run its handler, append to Lineage.

        Returns whatever the handler returns. Raises :class:`KeyError`
        if no handler is registered.

        Side effects:
            - Lineage append.
            - Event publication ``"command.dispatched"`` with the
              Command serialised to a dict (when ``events`` is set).
        """
        cmd = Command(
            name=name,
            source=source,
            args=args if args is not None else {},
            sim_t_s=sim_t_s,
            wall_ns=time.perf_counter_ns(),
            source_track_id=source_track_id,
            source_frame_id=source_frame_id,
        )
        if name not in self._handlers:
            msg = f"no handler registered for command {name!r}"
            raise KeyError(msg)

        result = self._handlers[name](cmd)
        self._lineage.append(cmd)
        if self.events is not None:
            self.events.publish(
                "command.dispatched",
                {
                    "name": cmd.name,
                    "source": cmd.source.value,
                    "args": cmd.args,
                    "sim_t_s": cmd.sim_t_s,
                    "wall_ns": cmd.wall_ns,
                },
            )
        return result

    @property
    def lineage(self) -> tuple[Command, ...]:
        """Snapshot of every dispatched command in chronological order."""
        return tuple(self._lineage)

    def clear_lineage(self) -> None:
        """Reset the Lineage log (typically when a new Run starts)."""
        self._lineage.clear()
