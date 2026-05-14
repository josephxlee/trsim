"""Editor Activity selector primitive (Phase 4.3, plan/13 section 13.2.2).

The Editor Workspace exposes five Activities (Composer / Map / Radar /
Targets / Browser) on a vertical bar at the left. This module defines:

- :class:`Activity` - StrEnum naming each activity. The string values
  double as stable keys for persistence and command ids
  (``editor.activity.composer`` etc.).
- :class:`ActivitySelector` - QObject that owns the active value and
  emits ``activity_changed`` when it transitions. The EditorWorkspace
  (and any sidecar UI) listens to this signal to swap the central
  QStackedWidget page or update the activity-bar action state.

The pattern mirrors :class:`workbench.ui.workspace_selector.WorkspaceSelector`
on purpose - both are tiny model-only objects so the visual builders
stay easy to test.
"""

from __future__ import annotations

from enum import StrEnum

from PySide6.QtCore import QObject, Signal


class Activity(StrEnum):
    """Top-level Editor activity (plan/13 section 13.2.2).

    The order matches the spec — Composer first because the Editor's
    primary purpose is *composition*; the other activities are tools
    invoked from the Composer. ``ATMOSPHERE`` joined the list in the
    2026-05-14 cycle so the AtmospherePanel widget finally has a
    visible mount point.
    """

    COMPOSER = "composer"
    MAP = "map"
    RADAR = "radar"
    TARGETS = "targets"
    ATMOSPHERE = "atmosphere"
    BROWSER = "browser"


ACTIVITY_ORDER: tuple[Activity, ...] = (
    Activity.COMPOSER,
    Activity.MAP,
    Activity.RADAR,
    Activity.TARGETS,
    Activity.ATMOSPHERE,
    Activity.BROWSER,
)
"""Activities in the order they appear on the left activity bar."""


class ActivitySelector(QObject):
    """Holds the active Editor activity and emits a Qt signal on change.

    Idempotent: setting the same activity does not re-emit.
    """

    activity_changed = Signal(Activity)

    def __init__(
        self,
        initial: Activity = Activity.COMPOSER,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._current = initial

    @property
    def current(self) -> Activity:
        return self._current

    def set_activity(self, activity: Activity) -> bool:
        """Set the active activity. Returns True iff a change occurred."""
        if activity == self._current:
            return False
        self._current = activity
        self.activity_changed.emit(activity)
        return True

    def cycle_next(self) -> Activity:
        """Cycle to the next Activity in :data:`ACTIVITY_ORDER`."""
        idx = ACTIVITY_ORDER.index(self._current)
        nxt = ACTIVITY_ORDER[(idx + 1) % len(ACTIVITY_ORDER)]
        self.set_activity(nxt)
        return nxt
