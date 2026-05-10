"""Resource Browser sidebar (Phase 4.4, plan/13 section 13.2.3).

The sidebar is always visible in the Editor Workspace - it lists every
known resource grouped by category (Scenarios / Maps / Radars /
Targets) so the user can search, double-click into the matching
Activity, and see at a glance whether referenced hashes still match.

Phase 4.4 ships the **widget shell**: the data types it consumes plus
a sidebar widget that filters, displays status, and emits a
double-click signal. Phase 5+ will populate it from the app-layer
ResourceLibrary; right now any caller can ``add_item`` directly to
seed sample content.

Activity 5 (Resource Browser full-screen view, plan/13 section 13.7)
remains a placeholder for now - same data, future tabular layout with
bulk actions. Phase 4.5+ replaces the placeholder.
"""

from __future__ import annotations

from workbench.ui.editor.resource_browser.sidebar import ResourceBrowserSidebar
from workbench.ui.editor.resource_browser.types import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    ResourceCategory,
    ResourceItem,
    ResourceStatus,
)

__all__ = [
    "CATEGORY_LABELS",
    "CATEGORY_ORDER",
    "ResourceBrowserSidebar",
    "ResourceCategory",
    "ResourceItem",
    "ResourceStatus",
]
