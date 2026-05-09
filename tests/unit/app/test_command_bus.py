"""Unit tests for workbench.app.command_bus + command_registry (Phase 3.1)."""

from __future__ import annotations

import pytest

from workbench.app.command_bus import Command, CommandBus
from workbench.app.command_registry import (
    BUILTIN_COMMAND_NAMES,
    SIM_PAUSE,
    SIM_START,
    register_noop_handlers,
)
from workbench.app.event_bus import EventBus
from workbench.domain.types import CommandSource


def test_command_construction_minimal() -> None:
    c = Command(name="sim.start", source=CommandSource.MANUAL_USER)
    assert c.name == "sim.start"
    assert c.args == {}
    assert c.sim_t_s == -1.0
    assert c.source_track_id is None


def test_command_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match=r"name"):
        Command(name="", source=CommandSource.MANUAL_USER)


def test_tracker_command_requires_track_and_frame_id() -> None:
    with pytest.raises(ValueError, match=r"TRACKER"):
        Command(name="positioner.manual_adjust", source=CommandSource.TRACKER)


def test_tracker_command_with_full_lineage_succeeds() -> None:
    c = Command(
        name="positioner.manual_adjust",
        source=CommandSource.TRACKER,
        source_track_id=42,
        source_frame_id=7,
    )
    assert c.source_track_id == 42
    assert c.source_frame_id == 7


# ---------------------------------------------------------------------
# CommandBus dispatch + Lineage
# ---------------------------------------------------------------------


def test_dispatch_invokes_registered_handler() -> None:
    bus = CommandBus()
    received: list[Command] = []
    bus.register("x", received.append)  # type: ignore[arg-type]
    bus.dispatch("x", source=CommandSource.MANUAL_USER, args={"k": 1})
    assert len(received) == 1
    assert received[0].name == "x"
    assert received[0].args == {"k": 1}


def test_dispatch_unknown_command_raises() -> None:
    bus = CommandBus()
    with pytest.raises(KeyError, match=r"x"):
        bus.dispatch("x", source=CommandSource.MANUAL_USER)


def test_dispatch_appends_to_lineage() -> None:
    bus = CommandBus()
    bus.register("a", lambda _: None)
    bus.register("b", lambda _: None)
    bus.dispatch("a", source=CommandSource.MANUAL_USER)
    bus.dispatch("b", source=CommandSource.INITIAL_SCAN)
    names = [c.name for c in bus.lineage]
    assert names == ["a", "b"]


def test_dispatch_handler_return_propagates() -> None:
    bus = CommandBus()
    bus.register("x", lambda _: 42)
    assert bus.dispatch("x", source=CommandSource.MANUAL_USER) == 42


def test_clear_lineage() -> None:
    bus = CommandBus()
    bus.register("x", lambda _: None)
    bus.dispatch("x", source=CommandSource.MANUAL_USER)
    bus.clear_lineage()
    assert bus.lineage == ()


def test_dispatch_publishes_event_when_bus_has_event_sink() -> None:
    events = EventBus()
    received: list[dict[str, object]] = []
    events.subscribe("command.dispatched", received.append)
    bus = CommandBus(events=events)
    bus.register("x", lambda _: None)
    bus.dispatch("x", source=CommandSource.MANUAL_USER, args={"k": 1})
    assert len(received) == 1
    assert received[0]["name"] == "x"
    assert received[0]["source"] == "manual_user"


def test_register_overwrites_previous_handler() -> None:
    bus = CommandBus()
    bus.register("x", lambda _: 1)
    bus.register("x", lambda _: 2)
    assert bus.dispatch("x", source=CommandSource.MANUAL_USER) == 2


def test_register_empty_name_rejected() -> None:
    bus = CommandBus()
    with pytest.raises(ValueError, match=r"command name"):
        bus.register("", lambda _: None)


def test_is_registered() -> None:
    bus = CommandBus()
    assert not bus.is_registered("x")
    bus.register("x", lambda _: None)
    assert bus.is_registered("x")


def test_dispatch_with_tracker_source_propagates_lineage_ids() -> None:
    bus = CommandBus()
    received: list[Command] = []
    bus.register("p", received.append)  # type: ignore[arg-type]
    bus.dispatch(
        "p",
        source=CommandSource.TRACKER,
        source_track_id=3,
        source_frame_id=11,
    )
    assert received[0].source_track_id == 3
    assert received[0].source_frame_id == 11


# ---------------------------------------------------------------------
# command_registry
# ---------------------------------------------------------------------


def test_builtin_command_count_locked() -> None:
    # 14 commands as of Phase 3.1 — bumping this requires a deliberate
    # update both here and in plan/04 § 4.3.
    assert len(BUILTIN_COMMAND_NAMES) == 14


def test_builtin_includes_sim_start() -> None:
    assert SIM_START == "sim.start"
    assert SIM_PAUSE == "sim.pause"
    assert SIM_START in BUILTIN_COMMAND_NAMES


def test_register_noop_handlers_registers_all_builtins() -> None:
    bus = CommandBus()
    register_noop_handlers(bus)
    for name in BUILTIN_COMMAND_NAMES:
        assert bus.is_registered(name)
        # And dispatch returns None for the no-op.
        assert bus.dispatch(name, source=CommandSource.MANUAL_USER) is None
