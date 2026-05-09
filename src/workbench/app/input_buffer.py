"""InputBuffer — buffer commands while Sim is PAUSED (plan/03 § 3.5.0b, v0.15).

Phase 3.2 — when the SimulationClock is PAUSED, UI command sources
(arrow keys, Editor save, etc.) are buffered here instead of being
flushed straight to the CommandBus. Resume calls :meth:`flush` to
replay them in order.

Design choice: the buffer holds raw command tuples
``(name, source, args)`` rather than fully built :class:`Command`
records — the wall-clock + sim_t_s timestamps belong to the eventual
dispatch, not the buffering moment.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from workbench.domain.types import CommandSource

BufferedCommand = tuple[str, CommandSource, dict[str, object]]
"""``(name, source, args)`` — pending command record."""


@dataclass(slots=True)
class InputBuffer:
    """FIFO buffer for commands enqueued while Sim is PAUSED."""

    _queue: list[BufferedCommand] = field(default_factory=list)

    def enqueue(
        self,
        name: str,
        source: CommandSource,
        args: dict[str, object] | None = None,
    ) -> None:
        """Append a command to the buffer (no validation).

        Raises:
            ValueError: If ``name`` is empty.
        """
        if not name:
            msg = "command name must be a non-empty string"
            raise ValueError(msg)
        self._queue.append((name, source, args if args is not None else {}))

    def flush(
        self,
        dispatch: Callable[[str, CommandSource, dict[str, object]], object],
    ) -> int:
        """Drain the buffer in FIFO order via the supplied ``dispatch`` callable.

        ``dispatch`` is typically a thin wrapper around
        :meth:`workbench.app.command_bus.CommandBus.dispatch`. We don't
        import the CommandBus here so the buffer stays decoupled.

        Returns:
            Number of commands dispatched.
        """
        n = len(self._queue)
        for name, source, args in self._queue:
            dispatch(name, source, args)
        self._queue.clear()
        return n

    def clear(self) -> None:
        """Drop every buffered command without dispatching."""
        self._queue.clear()

    def __len__(self) -> int:
        return len(self._queue)

    @property
    def pending(self) -> tuple[BufferedCommand, ...]:
        """Snapshot of the current queue (empty tuple if no items)."""
        return tuple(self._queue)
