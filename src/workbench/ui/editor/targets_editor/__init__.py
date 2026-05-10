"""Targets Editor widget (Phase 4.8, plan/13 § 13.6).

Editor Activity 4 - metadata edit + trajectory preview only at MVP.
Trajectory editing through GUI is explicitly excluded (plan/13
§ 13.6.3); the user imports / exports CSV instead.

Phase 4.8 ships the widget shell: metadata form (name / motion_kind
dropdown / RCS / scatterer count), CSV Import / Export buttons, a
Trajectory Preview placeholder, and a validation status banner. The
real preview canvas mounts under Phase 4.8.x once pyqtgraph is wired.
"""

from __future__ import annotations

from workbench.ui.editor.targets_editor.widget import (
    MOTION_KINDS,
    TargetsEditor,
)

__all__ = ["MOTION_KINDS", "TargetsEditor"]
