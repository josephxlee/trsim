"""Unit tests for workbench.app.event_bus (Phase 3.1)."""

from __future__ import annotations

import pytest

from workbench.app.event_bus import EventBus


def test_subscribe_and_publish_invokes_handler() -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []
    bus.subscribe("sim.started", received.append)
    n = bus.publish("sim.started", {"speed": 1})
    assert n == 1
    assert received == [{"speed": 1}]


def test_publish_with_no_payload_passes_empty_dict() -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []
    bus.subscribe("x", received.append)
    bus.publish("x")
    assert received == [{}]


def test_publish_unknown_event_returns_zero() -> None:
    bus = EventBus()
    assert bus.publish("nobody.listens") == 0


def test_multiple_handlers_invoked_in_registration_order() -> None:
    bus = EventBus()
    log: list[str] = []
    bus.subscribe("e", lambda _: log.append("a"))
    bus.subscribe("e", lambda _: log.append("b"))
    bus.subscribe("e", lambda _: log.append("c"))
    bus.publish("e")
    assert log == ["a", "b", "c"]


def test_unsubscribe_removes_handler() -> None:
    bus = EventBus()
    received: list[dict[str, object]] = []
    bus.subscribe("e", received.append)
    bus.unsubscribe("e", received.append)
    bus.publish("e", {"x": 1})
    assert received == []


def test_unsubscribe_unknown_handler_no_op() -> None:
    bus = EventBus()
    bus.unsubscribe("e", lambda _: None)  # must not raise


def test_subscriber_can_unsubscribe_during_dispatch() -> None:
    bus = EventBus()
    log: list[str] = []

    def first(_: dict[str, object]) -> None:
        log.append("first")
        bus.unsubscribe("e", first)

    def second(_: dict[str, object]) -> None:
        log.append("second")

    bus.subscribe("e", first)
    bus.subscribe("e", second)
    bus.publish("e")
    bus.publish("e")
    assert log == ["first", "second", "second"]


def test_subscribers_count() -> None:
    bus = EventBus()
    assert bus.subscribers_count("e") == 0
    bus.subscribe("e", lambda _: None)
    bus.subscribe("e", lambda _: None)
    assert bus.subscribers_count("e") == 2


def test_clear_drops_all_subscriptions() -> None:
    bus = EventBus()
    bus.subscribe("a", lambda _: None)
    bus.subscribe("b", lambda _: None)
    bus.clear()
    assert bus.subscribers_count("a") == 0
    assert bus.subscribers_count("b") == 0


def test_subscribe_empty_event_name_rejected() -> None:
    bus = EventBus()
    with pytest.raises(ValueError, match=r"event_name"):
        bus.subscribe("", lambda _: None)


def test_publish_empty_event_name_rejected() -> None:
    bus = EventBus()
    with pytest.raises(ValueError, match=r"event_name"):
        bus.publish("")
