"""Pub/sub event bus (plan/04 § 4.3 Phase 3).

Phase 3.1 — minimal in-process event bus that App services and the
UI use to broadcast / receive named events. Synchronous dispatch:
publishing an event runs every subscribed handler in registration
order on the calling thread. The Qt-side adapter (Phase 4) marshals
events onto the GUI thread when needed.

Why synchronous + in-process: the App layer runs single-threaded
inside Sim PAUSED / RUNNING (the simulation thread is separate);
flipping to async pub/sub is MVP+alpha and costs reproducibility.

Event payload is a plain ``dict[str, object]`` to avoid a typed
event class explosion at MVP. Phase 4 will tighten this to per-event
TypedDicts as the consumer set stabilises.

References:

- plan/04 § 4.3 Phase 3 — App layer scope.
- plan/02 § 2.5 — Layering (App > Domain > Physics).
"""

from __future__ import annotations

import contextlib
from collections.abc import Callable
from dataclasses import dataclass, field

EventHandler = Callable[[dict[str, object]], None]
"""Subscriber signature: ``handler(payload) -> None``."""


@dataclass(slots=True)
class EventBus:
    """In-process pub/sub bus.

    Not frozen — handlers register / unregister at runtime. Threading
    is the caller's problem; the bus does no locking at MVP. The Qt
    adapter (Phase 4) wraps publish() in a queued connection.
    """

    _handlers: dict[str, list[EventHandler]] = field(default_factory=dict)

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Register ``handler`` for ``event_name`` events.

        Same handler can subscribe to multiple events; same event
        can have many subscribers (call order = registration order).

        Args:
            event_name: Dot-namespaced event identifier
                (``"sim.started"`` / ``"run.terminated"``).
            handler: Callable invoked with the event payload dict.

        Raises:
            ValueError: If ``event_name`` is empty.
        """
        if not event_name:
            msg = "event_name must be a non-empty string"
            raise ValueError(msg)
        self._handlers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Remove a previously registered ``handler``.

        Silently no-ops if the handler isn't registered for that event.
        """
        with contextlib.suppress(KeyError, ValueError):
            self._handlers[event_name].remove(handler)

    def publish(self, event_name: str, payload: dict[str, object] | None = None) -> int:
        """Dispatch ``event_name`` to every subscriber.

        Args:
            event_name: Event identifier.
            payload: Optional payload dict. ``None`` is normalised to ``{}``.

        Returns:
            Number of handlers invoked.

        Raises:
            ValueError: If ``event_name`` is empty.
        """
        if not event_name:
            msg = "event_name must be a non-empty string"
            raise ValueError(msg)
        handlers = self._handlers.get(event_name, ())
        data = payload if payload is not None else {}
        for h in tuple(handlers):  # snapshot — handlers may unsubscribe
            h(data)
        return len(handlers)

    def subscribers_count(self, event_name: str) -> int:
        """Number of handlers currently subscribed to ``event_name``."""
        return len(self._handlers.get(event_name, ()))

    def clear(self) -> None:
        """Drop every subscription. Useful between test cases."""
        self._handlers.clear()
