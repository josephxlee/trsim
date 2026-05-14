"""Unit tests for workbench.ui.editor.activities (Phase 4.3)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.activities import (
    ACTIVITY_ORDER,
    Activity,
    ActivitySelector,
)

pytestmark = pytest.mark.qt


def test_activity_enum_values_are_stable_strings() -> None:
    assert Activity.COMPOSER.value == "composer"
    assert Activity.MAP.value == "map"
    assert Activity.RADAR.value == "radar"
    assert Activity.TARGETS.value == "targets"
    assert Activity.BROWSER.value == "browser"


def test_activity_order_starts_with_composer() -> None:
    # Plan/13 § 13.2.2 puts Composer first because composition is the
    # Editor's primary purpose. The 2026-05-14 cycle promoted the
    # Atmosphere panel to a 5th Activity (Ctrl+5) so the order is now
    # 6 entries.
    assert ACTIVITY_ORDER[0] is Activity.COMPOSER
    assert set(ACTIVITY_ORDER) == set(Activity)
    assert len(ACTIVITY_ORDER) == 6


def test_default_initial_activity_is_composer(qtbot: object) -> None:
    sel = ActivitySelector()
    assert sel.current is Activity.COMPOSER


def test_explicit_initial_activity_is_honoured(qtbot: object) -> None:
    sel = ActivitySelector(initial=Activity.RADAR)
    assert sel.current is Activity.RADAR


def test_set_activity_emits_signal_on_change(qtbot) -> None:  # type: ignore[no-untyped-def]
    sel = ActivitySelector()
    with qtbot.waitSignal(sel.activity_changed, timeout=500) as blocker:
        changed = sel.set_activity(Activity.MAP)
    assert changed is True
    assert blocker.args == [Activity.MAP]
    assert sel.current is Activity.MAP


def test_set_same_activity_is_idempotent(qtbot) -> None:  # type: ignore[no-untyped-def]
    sel = ActivitySelector(initial=Activity.RADAR)
    received: list[Activity] = []
    sel.activity_changed.connect(received.append)
    changed = sel.set_activity(Activity.RADAR)
    assert changed is False
    assert received == []


def test_cycle_next_walks_in_activity_order(qtbot: object) -> None:
    sel = ActivitySelector(initial=Activity.COMPOSER)
    seen = [sel.cycle_next() for _ in range(len(ACTIVITY_ORDER))]
    # Cycling through every activity returns to Composer.
    assert seen[-1] is Activity.COMPOSER
    assert seen == [
        Activity.MAP,
        Activity.RADAR,
        Activity.TARGETS,
        Activity.ATMOSPHERE,
        Activity.BROWSER,
        Activity.COMPOSER,
    ]
