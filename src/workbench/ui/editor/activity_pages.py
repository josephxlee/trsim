"""Five Editor activity placeholder pages (Phase 4.3).

Each placeholder is a QWidget that announces which Activity it stands
in for. Phase 4.5+ replaces them with the real implementations
(Scenario Composer, Map Editor, Radar Editor, Targets Editor, Resource
Browser) per plan/13 sections 13.3-13.7.

Keeping the stubs in a single file (vs. five sub-packages) at this
phase avoids premature directory churn. When a real activity arrives
(e.g. Map Editor with its DEM-import wizard) it gets its own module
and this file shrinks.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


def _make_placeholder(
    title: str,
    hint: str,
    object_name: str,
    parent: QWidget | None = None,
) -> QWidget:
    page = QWidget(parent)
    page.setObjectName(object_name)
    layout = QVBoxLayout(page)
    layout.setContentsMargins(24, 24, 24, 24)

    title_label = QLabel(title)
    title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title_label.setStyleSheet("font-size: 18px; font-weight: 600;")

    hint_label = QLabel(hint)
    hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hint_label.setStyleSheet("color: #777;")

    layout.addStretch(1)
    layout.addWidget(title_label)
    layout.addWidget(hint_label)
    layout.addStretch(1)
    return page


class ScenarioComposerPage(QWidget):
    """Activity 1 placeholder - real impl in Phase 4.5 (plan/13 § 13.3)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ScenarioComposerPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Scenario Composer",
                hint="Phase 4.5 will mount References / Installation / Composition / Validation here.",
                object_name="ScenarioComposerInner",
                parent=self,
            )
        )


class MapEditorPage(QWidget):
    """Activity 2 placeholder - real impl in Phase 4.6 (plan/13 § 13.4)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MapEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Map Editor",
                hint="Phase 4.6 mounts Pan/Zoom + Land/Sea Brush + Spot Edit + Flatten + DEM Import.",
                object_name="MapEditorInner",
                parent=self,
            )
        )


class RadarEditorPage(QWidget):
    """Activity 3 placeholder - real impl in Phase 4.7 (plan/13 § 13.5)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("RadarEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Radar Editor",
                hint="Phase 4.7 mounts Antenna type dropdown + dynamic form + Beam Pattern Preview.",
                object_name="RadarEditorInner",
                parent=self,
            )
        )


class TargetsEditorPage(QWidget):
    """Activity 4 placeholder - real impl in Phase 4.8 (plan/13 § 13.6)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("TargetsEditorPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Targets Editor",
                hint="Phase 4.8 mounts metadata edit + Trajectory Preview (CSV import only at MVP).",
                object_name="TargetsEditorInner",
                parent=self,
            )
        )


class ResourceBrowserPage(QWidget):
    """Activity 5 placeholder - real impl in Phase 4.4 (plan/13 § 13.7)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResourceBrowserPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(
            _make_placeholder(
                title="Resource Browser",
                hint="Phase 4.4 mounts the resource tree (Scenarios / Maps / Radars / Targets) with status icons.",
                object_name="ResourceBrowserInner",
                parent=self,
            )
        )
