"""Unit tests for resource_browser.types (Phase 4.4)."""

from __future__ import annotations

import pytest

from workbench.ui.editor.resource_browser.types import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    ResourceCategory,
    ResourceItem,
    ResourceStatus,
    status_prefix,
)


def test_category_enum_values_are_stable_strings() -> None:
    assert ResourceCategory.SCENARIO.value == "scenario"
    assert ResourceCategory.MAP.value == "map"
    assert ResourceCategory.RADAR.value == "radar"
    assert ResourceCategory.TARGETS.value == "targets"


def test_category_order_is_complete_and_starts_with_scenario() -> None:
    assert CATEGORY_ORDER[0] is ResourceCategory.SCENARIO
    assert set(CATEGORY_ORDER) == set(ResourceCategory)
    assert len(CATEGORY_ORDER) == 4


def test_category_labels_use_plural_forms() -> None:
    assert CATEGORY_LABELS[ResourceCategory.SCENARIO] == "Scenarios"
    assert CATEGORY_LABELS[ResourceCategory.MAP] == "Maps"
    assert CATEGORY_LABELS[ResourceCategory.RADAR] == "Radars"
    assert CATEGORY_LABELS[ResourceCategory.TARGETS] == "Targets"


def test_status_prefix_active_and_stale_use_ascii_brackets() -> None:
    assert status_prefix(ResourceStatus.ACTIVE) == "[active] "
    assert status_prefix(ResourceStatus.STALE) == "[stale] "
    assert status_prefix(ResourceStatus.BUILTIN) == "[builtin] "
    assert status_prefix(ResourceStatus.NORMAL) == ""


def test_resource_item_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match=r"non-empty"):
        ResourceItem(name="", category=ResourceCategory.MAP)


def test_resource_item_display_text_includes_status_prefix() -> None:
    item = ResourceItem(
        name="B_Conflict",
        category=ResourceCategory.SCENARIO,
        status=ResourceStatus.ACTIVE,
    )
    assert item.display_text() == "[active] B_Conflict"


def test_resource_item_default_status_is_normal_with_no_prefix() -> None:
    item = ResourceItem(name="A_Base", category=ResourceCategory.SCENARIO)
    assert item.status is ResourceStatus.NORMAL
    assert item.display_text() == "A_Base"
