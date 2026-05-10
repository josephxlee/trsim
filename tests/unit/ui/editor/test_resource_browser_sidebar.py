"""Unit tests for resource_browser.sidebar (Phase 4.4)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.resource_browser import (
    ResourceBrowserSidebar,
    ResourceCategory,
    ResourceItem,
    ResourceStatus,
)

pytestmark = pytest.mark.qt


def test_sidebar_starts_empty_with_zero_counts(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    for cat in ResourceCategory:
        node = sb.category_node(cat)
        assert node.childCount() == 0
        assert "(0)" in node.text(0)


def test_add_item_increments_count_and_displays_status_prefix(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    sb.add_item(
        ResourceItem(
            name="B_Conflict",
            category=ResourceCategory.SCENARIO,
            status=ResourceStatus.ACTIVE,
        )
    )
    sb.add_item(ResourceItem(name="A_Base", category=ResourceCategory.SCENARIO))
    node = sb.category_node(ResourceCategory.SCENARIO)
    assert node.childCount() == 2
    assert "(2)" in node.text(0)
    assert node.child(0).text(0) == "[active] B_Conflict"
    assert node.child(1).text(0) == "A_Base"


def test_clear_category_removes_only_that_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    sb.add_item(ResourceItem(name="A", category=ResourceCategory.SCENARIO))
    sb.add_item(ResourceItem(name="B", category=ResourceCategory.MAP))
    sb.clear_category(ResourceCategory.SCENARIO)
    assert sb.category_node(ResourceCategory.SCENARIO).childCount() == 0
    assert sb.category_node(ResourceCategory.MAP).childCount() == 1


def test_clear_wipes_every_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    for cat in ResourceCategory:
        sb.add_item(ResourceItem(name=f"x_{cat.value}", category=cat))
    sb.clear()
    for cat in ResourceCategory:
        assert sb.category_node(cat).childCount() == 0


def test_filter_hides_non_matching_leaves_case_insensitive(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    for n in ("Alpha", "beta", "Charlie"):
        sb.add_item(ResourceItem(name=n, category=ResourceCategory.MAP))
    sb.set_filter_text("AL")
    visible = sb.visible_items(ResourceCategory.MAP)
    assert visible == ("Alpha",)
    sb.set_filter_text("")
    assert sb.visible_items(ResourceCategory.MAP) == ("Alpha", "beta", "Charlie")


def test_filter_collapses_empty_categories(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    sb.add_item(ResourceItem(name="Alpha", category=ResourceCategory.MAP))
    sb.add_item(ResourceItem(name="Bravo", category=ResourceCategory.RADAR))
    sb.set_filter_text("Alpha")
    # Map node still visible, Radar node hidden because zero matches.
    assert sb.category_node(ResourceCategory.MAP).isHidden() is False
    assert sb.category_node(ResourceCategory.RADAR).isHidden() is True


def test_double_clicking_a_leaf_emits_category_and_name(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    sb.add_item(ResourceItem(name="fmcw_corvette", category=ResourceCategory.RADAR))
    received: list[tuple[ResourceCategory, str]] = []
    sb.item_double_clicked.connect(lambda c, n: received.append((c, n)))
    leaf = sb.category_node(ResourceCategory.RADAR).child(0)
    sb.tree().itemDoubleClicked.emit(leaf, 0)
    assert received == [(ResourceCategory.RADAR, "fmcw_corvette")]


def test_double_clicking_a_category_header_does_not_emit(qtbot) -> None:  # type: ignore[no-untyped-def]
    sb = ResourceBrowserSidebar()
    qtbot.addWidget(sb)
    received: list[tuple[ResourceCategory, str]] = []
    sb.item_double_clicked.connect(lambda c, n: received.append((c, n)))
    header = sb.category_node(ResourceCategory.SCENARIO)
    sb.tree().itemDoubleClicked.emit(header, 0)
    assert received == []
