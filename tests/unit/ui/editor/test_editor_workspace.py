"""Unit tests for the Editor Workspace shell (Phase 4.3)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtGui import QKeySequence

from workbench.ui.editor.activities import ACTIVITY_ORDER, Activity
from workbench.ui.editor.activity_pages import (
    MapEditorPage,
    RadarEditorPage,
    ResourceBrowserPage,
    ScenarioComposerPage,
    TargetsEditorPage,
)
from workbench.ui.editor.workspace import EditorWorkspace

pytestmark = pytest.mark.qt


def test_workspace_default_activity_is_composer(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    assert ws.selector.current is Activity.COMPOSER
    assert ws.activity_action(Activity.COMPOSER).isChecked()


def test_workspace_mounts_one_page_per_activity(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    assert isinstance(ws.page(Activity.COMPOSER), ScenarioComposerPage)
    assert isinstance(ws.page(Activity.MAP), MapEditorPage)
    assert isinstance(ws.page(Activity.RADAR), RadarEditorPage)
    assert isinstance(ws.page(Activity.TARGETS), TargetsEditorPage)
    assert isinstance(ws.page(Activity.BROWSER), ResourceBrowserPage)


def test_set_activity_swaps_central_page_and_action_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    ws.selector.set_activity(Activity.RADAR)
    assert ws.activity_action(Activity.RADAR).isChecked()
    assert not ws.activity_action(Activity.COMPOSER).isChecked()


def test_triggering_action_updates_selector(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    with qtbot.waitSignal(ws.selector.activity_changed, timeout=500) as blocker:
        ws.activity_action(Activity.TARGETS).trigger()
    assert blocker.args == [Activity.TARGETS]
    assert ws.selector.current is Activity.TARGETS


def test_activity_actions_have_expected_shortcuts(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    expected = {
        Activity.COMPOSER: "Ctrl+1",
        Activity.MAP: "Ctrl+2",
        Activity.RADAR: "Ctrl+3",
        Activity.TARGETS: "Ctrl+4",
        Activity.BROWSER: "Ctrl+5",
    }
    for activity, key in expected.items():
        assert ws.activity_action(activity).shortcut() == QKeySequence(key)


def test_activity_bar_has_one_action_per_activity_in_order(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    bar = ws.activity_bar()
    bar_action_names = [a.objectName() for a in bar.actions()]
    expected_names = [f"EditorActivity_{a.value}" for a in ACTIVITY_ORDER]
    assert bar_action_names == expected_names


# ---------- Phase 4.4 — Resource Browser sidebar ----------


def test_workspace_mounts_resource_browser_sidebar(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.resource_browser import ResourceBrowserSidebar

    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    sb = ws.resource_browser()
    assert isinstance(sb, ResourceBrowserSidebar)
    # Sidebar lives on the splitter alongside the central stack.
    splitter = ws.splitter()
    assert splitter.widget(0) is sb
    assert splitter.count() == 2


def test_double_click_on_resource_switches_activity(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.resource_browser import ResourceCategory, ResourceItem

    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    ws.resource_browser().add_item(
        ResourceItem(name="fmcw_corvette", category=ResourceCategory.RADAR)
    )
    leaf = ws.resource_browser().category_node(ResourceCategory.RADAR).child(0)
    ws.resource_browser().tree().itemDoubleClicked.emit(leaf, 0)
    assert ws.selector.current is Activity.RADAR


@pytest.mark.parametrize(
    ("category", "expected_activity"),
    [
        ("scenario", Activity.COMPOSER),
        ("map", Activity.MAP),
        ("radar", Activity.RADAR),
        ("targets", Activity.TARGETS),
    ],
)
def test_each_category_routes_to_its_activity(qtbot, category, expected_activity) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.resource_browser import ResourceCategory, ResourceItem

    ws = EditorWorkspace()
    qtbot.addWidget(ws)
    cat = ResourceCategory(category)
    ws.resource_browser().add_item(ResourceItem(name=f"x_{category}", category=cat))
    leaf = ws.resource_browser().category_node(cat).child(0)
    ws.resource_browser().tree().itemDoubleClicked.emit(leaf, 0)
    assert ws.selector.current is expected_activity
