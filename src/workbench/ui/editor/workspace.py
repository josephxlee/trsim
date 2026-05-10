"""Editor Workspace shell (Phase 4.3, plan/13 section 13.2).

Layout (Phase 4.3 - Resource Browser sidebar arrives in Phase 4.4):

::

    +-------+----------------------------+
    | [icon]|                            |
    | [icon]|                            |
    | [icon]|     central activity page  |
    | [icon]|                            |
    | [icon]|                            |
    +-------+----------------------------+

The vertical icon bar on the left is the
:class:`ActivitySelector` - five exclusive radio QActions, one per
:class:`Activity` value. Clicking one (or pressing Ctrl+1..5 once
:class:`workbench.ui.main_window.MainWindow` wires the shortcuts) swaps
the central :class:`QStackedWidget` page.

Phase 4.5+ replaces the placeholder pages with real Composer / Map /
Radar / Targets / Browser widgets.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QHBoxLayout,
    QStackedWidget,
    QToolBar,
    QWidget,
)

from workbench.ui.editor.activities import (
    ACTIVITY_ORDER,
    Activity,
    ActivitySelector,
)
from workbench.ui.editor.activity_pages import (
    MapEditorPage,
    RadarEditorPage,
    ResourceBrowserPage,
    ScenarioComposerPage,
    TargetsEditorPage,
)

# Plan/13 section 13.2.2 lists each activity's emoji glyph; we use
# short prefix labels so the activity bar reads even when the system
# font lacks the glyphs.
_ACTIVITY_LABEL: dict[Activity, str] = {
    Activity.COMPOSER: "Composer",
    Activity.MAP: "Map",
    Activity.RADAR: "Radar",
    Activity.TARGETS: "Targets",
    Activity.BROWSER: "Browser",
}

_ACTIVITY_SHORTCUT: dict[Activity, str] = {
    Activity.COMPOSER: "Ctrl+1",
    Activity.MAP: "Ctrl+2",
    Activity.RADAR: "Ctrl+3",
    Activity.TARGETS: "Ctrl+4",
    Activity.BROWSER: "Ctrl+5",
}


class EditorWorkspace(QWidget):
    """Editor Workspace shell with Activity bar + central page stack."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("EditorWorkspace")

        self.selector = ActivitySelector()
        self._pages = self._build_pages()
        self._stack = self._build_stack()
        self._actions, self._activity_bar = self._build_activity_bar()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._activity_bar)
        layout.addWidget(self._stack, 1)

        self.selector.activity_changed.connect(self._on_activity_changed)
        self._sync_to_selector()

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------
    def _build_pages(self) -> dict[Activity, QWidget]:
        return {
            Activity.COMPOSER: ScenarioComposerPage(self),
            Activity.MAP: MapEditorPage(self),
            Activity.RADAR: RadarEditorPage(self),
            Activity.TARGETS: TargetsEditorPage(self),
            Activity.BROWSER: ResourceBrowserPage(self),
        }

    def _build_stack(self) -> QStackedWidget:
        stack = QStackedWidget(self)
        for activity in ACTIVITY_ORDER:
            stack.addWidget(self._pages[activity])
        return stack

    def _build_activity_bar(self) -> tuple[dict[Activity, QAction], QToolBar]:
        bar = QToolBar("EditorActivities", self)
        bar.setObjectName("EditorActivityBar")
        bar.setOrientation(Qt.Orientation.Vertical)
        bar.setMovable(False)

        group = QActionGroup(self)
        group.setExclusive(True)
        actions: dict[Activity, QAction] = {}
        for activity in ACTIVITY_ORDER:
            act = QAction(_ACTIVITY_LABEL[activity], self)
            act.setObjectName(f"EditorActivity_{activity.value}")
            act.setCheckable(True)
            act.setShortcut(QKeySequence(_ACTIVITY_SHORTCUT[activity]))
            act.triggered.connect(lambda _checked, a=activity: self.selector.set_activity(a))
            group.addAction(act)
            bar.addAction(act)
            actions[activity] = act
        self._action_group = group
        return actions, bar

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------
    def _on_activity_changed(self, activity: Activity) -> None:
        self._stack.setCurrentWidget(self._pages[activity])
        self._actions[activity].setChecked(True)

    def _sync_to_selector(self) -> None:
        activity = self.selector.current
        self._stack.setCurrentWidget(self._pages[activity])
        self._actions[activity].setChecked(True)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def page(self, activity: Activity) -> QWidget:
        """Return the placeholder QWidget mounted for ``activity``."""
        return self._pages[activity]

    def activity_action(self, activity: Activity) -> QAction:
        """Return the QAction for ``activity`` on the activity bar."""
        return self._actions[activity]

    def activity_bar(self) -> QToolBar:
        """Return the vertical activity QToolBar (test helper)."""
        return self._activity_bar
