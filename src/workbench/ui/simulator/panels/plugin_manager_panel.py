"""Plugin Manager panel (Phase 4.9, plan/05 § 5.3.3)."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

PIPELINE_STAGES: tuple[str, ...] = (
    "Detector",
    "Pairing",
    "Tracker",
    "Predictor",
    "Classifier",
)


class _StageSection(QGroupBox):
    """One pipeline-stage section with its plugin list."""

    def __init__(self, stage: str, parent: QWidget | None = None) -> None:
        super().__init__(stage, parent)
        self.setObjectName(f"PluginStage_{stage}")
        layout = QVBoxLayout(self)
        self._list = QListWidget(self)
        self._list.setObjectName(f"PluginStageList_{stage}")
        layout.addWidget(self._list)

    def set_plugins(self, names: list[str]) -> None:
        self._list.clear()
        for name in names:
            self._list.addItem(name)

    def list_widget(self) -> QListWidget:
        return self._list


class PluginManagerPanel(QWidget):
    """Active plugin per pipeline stage + add/reload actions."""

    add_plugin_requested = Signal()
    reload_all_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PluginManagerPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel("Plugin Manager")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        self._sections: dict[str, _StageSection] = {}
        for stage in PIPELINE_STAGES:
            section = _StageSection(stage, self)
            self._sections[stage] = section
            layout.addWidget(section)

        action_row = QHBoxLayout()
        action_row.addStretch(1)
        add_btn = QPushButton("+ Add Plugin", self)
        add_btn.setObjectName("PluginManagerAddBtn")
        add_btn.clicked.connect(self.add_plugin_requested)
        reload_btn = QPushButton("Reload All", self)
        reload_btn.setObjectName("PluginManagerReloadBtn")
        reload_btn.clicked.connect(self.reload_all_requested)
        action_row.addWidget(add_btn)
        action_row.addWidget(reload_btn)
        layout.addLayout(action_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_stage_plugins(self, stage: str, plugins: list[str]) -> None:
        """Replace the plugin list for ``stage``."""
        if stage not in self._sections:
            msg = f"unknown pipeline stage {stage!r}; expected one of {PIPELINE_STAGES}"
            raise ValueError(msg)
        self._sections[stage].set_plugins(plugins)

    def stage_section(self, stage: str) -> _StageSection:
        """Return the section for ``stage`` (test helper)."""
        return self._sections[stage]
