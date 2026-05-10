"""Unit tests for workbench.ui.dock_manager (Phase 4.2d)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QMainWindow

from workbench.ui.dock_manager import DockManager

pytestmark = pytest.mark.qt


@pytest.fixture
def host(qtbot):  # type: ignore[no-untyped-def]
    win = QMainWindow()
    qtbot.addWidget(win)
    return win


def test_register_mounts_dock_widget_on_host(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    panel = QLabel("Scenario Explorer")
    dock = mgr.register("scenario_explorer", "Scenario Explorer", panel)
    assert mgr.is_registered("scenario_explorer") is True
    assert dock.objectName() == "Dock_scenario_explorer"
    assert dock.widget() is panel
    # Host has the dock as a child.
    assert dock.parent() is host


def test_register_rejects_duplicate_name(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("a", "A", QLabel())
    with pytest.raises(ValueError, match=r"already registered"):
        mgr.register("a", "Other", QLabel())


def test_register_rejects_empty_name(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    with pytest.raises(ValueError, match=r"non-empty"):
        mgr.register("", "Title", QLabel())


def test_register_honours_explicit_dock_area(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    panel = QLabel("Right side")
    dock = mgr.register("props", "Properties", panel, area=Qt.DockWidgetArea.RightDockWidgetArea)
    assert host.dockWidgetArea(dock) == Qt.DockWidgetArea.RightDockWidgetArea


def test_toggle_visibility_flips_show_hide(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("p", "Panel", QLabel())
    host.show()
    assert mgr.get("p").dock.isVisible() is True
    new_state = mgr.toggle_visibility("p")
    assert new_state is False
    assert mgr.get("p").dock.isVisible() is False
    new_state = mgr.toggle_visibility("p")
    assert new_state is True


def test_set_visible_forces_state(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("p", "Panel", QLabel())
    host.show()
    mgr.set_visible("p", False)
    assert mgr.get("p").dock.isVisible() is False
    mgr.set_visible("p", True)
    assert mgr.get("p").dock.isVisible() is True


def test_unregister_removes_dock_from_host(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("a", "A", QLabel())
    mgr.unregister("a")
    assert mgr.is_registered("a") is False
    with pytest.raises(KeyError):
        mgr.unregister("a")


def test_iter_and_names_preserve_registration_order(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("first", "First", QLabel())
    mgr.register("second", "Second", QLabel())
    mgr.register("third", "Third", QLabel())
    assert mgr.names() == ("first", "second", "third")
    assert [e.name for e in mgr] == ["first", "second", "third"]
    assert len(mgr) == 3


def test_save_and_restore_state_roundtrip(host) -> None:  # type: ignore[no-untyped-def]
    mgr = DockManager(host=host)
    mgr.register("a", "A", QLabel(), area=Qt.DockWidgetArea.LeftDockWidgetArea)
    mgr.register("b", "B", QLabel(), area=Qt.DockWidgetArea.RightDockWidgetArea)
    blob = mgr.save_state()
    # Move 'a' to the right and verify restore brings it back left.
    host.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, mgr.get("a").dock)
    assert host.dockWidgetArea(mgr.get("a").dock) == Qt.DockWidgetArea.RightDockWidgetArea
    ok = mgr.restore_state(blob)
    assert ok is True
    assert host.dockWidgetArea(mgr.get("a").dock) == Qt.DockWidgetArea.LeftDockWidgetArea
