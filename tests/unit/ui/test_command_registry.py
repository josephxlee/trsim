"""Unit tests for workbench.ui.commands.registry (Phase 4.2a)."""

from __future__ import annotations

import pytest

from workbench.ui.commands.registry import (
    WorkbenchCommand,
    WorkbenchCommandRegistry,
)


def _make_command(
    cid: str = "scenario.open",
    *,
    title: str = "Open Scenario",
    category: str = "Scenario",
    enabled: bool | None = None,
) -> tuple[WorkbenchCommand, list[str]]:
    calls: list[str] = []
    return (
        WorkbenchCommand(
            id=cid,
            title=title,
            category=category,
            execute=lambda: calls.append(cid),
            enabled_when=None if enabled is None else (lambda v=enabled: v),
        ),
        calls,
    )


def test_command_rejects_empty_id_title_category() -> None:
    with pytest.raises(ValueError, match=r"id"):
        WorkbenchCommand(id="", title="x", category="y", execute=lambda: None)
    with pytest.raises(ValueError, match=r"title"):
        WorkbenchCommand(id="x", title="", category="y", execute=lambda: None)
    with pytest.raises(ValueError, match=r"category"):
        WorkbenchCommand(id="x", title="y", category="", execute=lambda: None)


def test_command_is_enabled_default_true_and_predicate_respected() -> None:
    cmd_default, _ = _make_command()
    cmd_off, _ = _make_command(enabled=False)
    assert cmd_default.is_enabled() is True
    assert cmd_off.is_enabled() is False


def test_registry_register_get_dispatch_roundtrip() -> None:
    reg = WorkbenchCommandRegistry()
    cmd, calls = _make_command()
    reg.register(cmd)
    assert reg.is_registered("scenario.open") is True
    assert reg.get("scenario.open") is cmd
    reg.dispatch("scenario.open")
    assert calls == ["scenario.open"]


def test_registry_rejects_duplicate_id() -> None:
    reg = WorkbenchCommandRegistry()
    cmd, _ = _make_command()
    reg.register(cmd)
    cmd2, _ = _make_command(title="Open Scenario v2")
    with pytest.raises(ValueError, match=r"already registered"):
        reg.register(cmd2)


def test_registry_dispatch_missing_raises_keyerror() -> None:
    reg = WorkbenchCommandRegistry()
    with pytest.raises(KeyError):
        reg.dispatch("does.not.exist")


def test_registry_dispatch_disabled_raises_runtime_error() -> None:
    reg = WorkbenchCommandRegistry()
    cmd, calls = _make_command(enabled=False)
    reg.register(cmd)
    with pytest.raises(RuntimeError, match=r"disabled"):
        reg.dispatch("scenario.open")
    assert calls == []


def test_registry_unregister_removes_command() -> None:
    reg = WorkbenchCommandRegistry()
    cmd, _ = _make_command()
    reg.register(cmd)
    reg.unregister("scenario.open")
    assert reg.is_registered("scenario.open") is False
    with pytest.raises(KeyError):
        reg.unregister("scenario.open")


def test_registry_find_empty_query_returns_all_in_order() -> None:
    reg = WorkbenchCommandRegistry()
    cmd_a, _ = _make_command("a.x", title="Alpha")
    cmd_b, _ = _make_command("b.x", title="Beta")
    reg.register(cmd_a)
    reg.register(cmd_b)
    assert reg.find("") == (cmd_a, cmd_b)


def test_registry_find_ranks_title_hits_above_id_only_hits() -> None:
    reg = WorkbenchCommandRegistry()
    only_id, _ = _make_command("alpha.run", title="Execute Now")  # 'alpha' only in id
    only_title, _ = _make_command("z.cmd", title="Alpha Test")  # 'alpha' only in title
    reg.register(only_id)
    reg.register(only_title)
    # title-hit ranks above id-only hit even though id-only registered first.
    found = reg.find("alpha")
    assert found == (only_title, only_id)


def test_registry_find_is_case_insensitive() -> None:
    reg = WorkbenchCommandRegistry()
    cmd, _ = _make_command(title="Open Scenario")
    reg.register(cmd)
    assert reg.find("OPEN") == (cmd,)
    assert reg.find("open") == (cmd,)
