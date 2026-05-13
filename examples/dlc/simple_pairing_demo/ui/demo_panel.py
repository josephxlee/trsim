"""Placeholder UI panel for the simple_pairing_demo DLC.

The :class:`DemoPanel` is intentionally trivial — a Qt widget with
a label — so the DLC plugin loader has a real `QWidget` subclass
to mount and so new authors see a working example without first
having to learn pyqtgraph / pyvista.

`manifest.toml` references this module via the
`trsim.ui.panels` entry point:

    [entry_points]
    "trsim.ui.panels" = "ui/demo_panel.py:DemoPanel"
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class DemoPanel(QWidget):
    """Trivial panel mounted by the DLC PluginLoader."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("DemoPanel")
        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Hello from the simple_pairing_demo DLC!\n"
                "Replace this widget with your own NN / visualization.",
                self,
            )
        )
