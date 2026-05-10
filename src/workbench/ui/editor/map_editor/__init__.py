"""Map Editor widget (Phase 4.6, plan/13 section 13.4).

Editor Activity 2 - lightweight DEM + terrain.npz + building edit.
plan/12 § 12.11 caps the MVP toolset to:

- Pan / Zoom on a top-down map canvas.
- Land/Sea Brush (toggle land_mask per pixel).
- Spot Edit (single-pixel z override).
- Flatten Area (rectangular z fill, v0.33).
- Add Building (with anchor mode).

Phase 4.6 ships the **widget shell**: a tool palette on the left,
a placeholder canvas in the centre, layer toggles, an edit-history
list, and the action row (Save / Import DEM... / Validate). The
real DEM rendering, brush painting, and the 7-step DEM Import wizard
land in Phase 4.6.x as the canvas gains pyqtgraph backing.
"""

from __future__ import annotations

from workbench.ui.editor.map_editor.widget import MapEditor, MapTool

__all__ = ["MapEditor", "MapTool"]
