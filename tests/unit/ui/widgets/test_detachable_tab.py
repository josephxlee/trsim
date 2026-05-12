"""DetachableTabWidget + FloatingPanel tests (floating dock option D)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel, QWidget

from workbench.ui.widgets import DetachableTabWidget, FloatingPanel

pytestmark = pytest.mark.qt


def _populated(qtbot: object) -> tuple[DetachableTabWidget, list[QWidget]]:
    tabs = DetachableTabWidget()
    qtbot.addWidget(tabs)  # type: ignore[attr-defined]
    pages = [QLabel(f"page-{i}") for i in range(3)]
    for i, w in enumerate(pages):
        tabs.addTab(w, f"Tab {i}")
    return tabs, pages


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------


def test_detachable_widget_inherits_tab_behavior(qtbot: object) -> None:
    tabs, pages = _populated(qtbot)
    assert tabs.count() == 3
    assert tabs.tabText(1) == "Tab 1"
    assert tabs.widget(1) is pages[1]
    assert tabs.floating_panels() == ()


# ---------------------------------------------------------------------
# detach_tab
# ---------------------------------------------------------------------


def test_detach_tab_removes_from_widget_and_emits_signal(qtbot: object) -> None:
    tabs, pages = _populated(qtbot)
    detached_payload: list[tuple[int, str]] = []
    tabs.tab_detached.connect(lambda i, t: detached_payload.append((i, t)))

    floating = tabs.detach_tab(1)
    assert isinstance(floating, FloatingPanel)
    assert tabs.count() == 2
    # Page 1 has been pulled out — only pages[0] and pages[2] remain.
    assert tabs.widget(0) is pages[0]
    assert tabs.widget(1) is pages[2]
    assert detached_payload == [(1, "Tab 1")]
    assert tabs.floating_panels() == (floating,)
    # The FloatingPanel owns the content widget after detach.
    assert floating.content is pages[1]


def test_detach_tab_with_out_of_range_index_is_noop(qtbot: object) -> None:
    tabs, _ = _populated(qtbot)
    assert tabs.detach_tab(99) is None
    assert tabs.detach_tab(-1) is None
    assert tabs.count() == 3


def test_floating_panel_carries_origin_metadata(qtbot: object) -> None:
    tabs, _ = _populated(qtbot)
    floating = tabs.detach_tab(2)
    assert floating is not None
    assert floating.origin_title == "Tab 2"
    assert floating.origin_index == 2
    assert "Tab 2" in floating.windowTitle()


# ---------------------------------------------------------------------
# Re-attach on close
# ---------------------------------------------------------------------


def test_closing_floating_window_reinserts_tab(qtbot: object) -> None:
    tabs, pages = _populated(qtbot)
    reattach_payload: list[tuple[int, str]] = []
    tabs.tab_reattached.connect(lambda i, t: reattach_payload.append((i, t)))

    floating = tabs.detach_tab(1)
    assert floating is not None
    assert tabs.count() == 2

    floating.close()

    # Re-insert at the original index (clamped to current count).
    assert tabs.count() == 3
    assert tabs.tabText(1) == "Tab 1"
    assert tabs.widget(1) is pages[1]
    assert reattach_payload == [(1, "Tab 1")]
    assert tabs.floating_panels() == ()


def test_close_after_tab_count_shrinks_clamps_to_end(qtbot: object) -> None:
    """If the user removes other tabs while one is floating, the
    re-insert clamps to the current count instead of crashing.
    """
    tabs, _ = _populated(qtbot)
    floating = tabs.detach_tab(2)
    assert floating is not None
    # Pull tab 0 out (and immediately reattach to keep count at 2).
    inner = tabs.detach_tab(0)
    assert inner is not None
    inner.close()
    # Now remove a real tab so count = 1.
    tabs.removeTab(0)
    assert tabs.count() == 1
    # Close the originally-detached panel — should land at index 1.
    floating.close()
    assert tabs.count() == 2
    assert tabs.tabText(1) == "Tab 2"


def test_multiple_simultaneous_floating_panels(qtbot: object) -> None:
    tabs, _ = _populated(qtbot)
    f0 = tabs.detach_tab(0)
    f1 = tabs.detach_tab(0)  # was tab 1, now index 0 after the previous detach
    assert f0 is not None
    assert f1 is not None
    assert tabs.count() == 1
    assert len(tabs.floating_panels()) == 2
    # Close them in reverse order; each re-attach should succeed.
    f1.close()
    assert tabs.count() == 2
    f0.close()
    assert tabs.count() == 3
