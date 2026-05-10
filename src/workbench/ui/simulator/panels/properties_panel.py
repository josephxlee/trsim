"""Context-sensitive Properties panel (Phase 4.9, plan/05 § 5.3.5)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PropertiesPanel(QWidget):
    """Generic key-value inspector for whatever the user selects."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PropertiesPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QHBoxLayout()
        title = QLabel("Properties")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch(1)
        self._context_label = QLabel("(nothing selected)")
        self._context_label.setObjectName("PropertiesPanelContext")
        self._context_label.setStyleSheet("color: #777;")
        header.addWidget(self._context_label)
        layout.addLayout(header)

        self._form_host = QWidget(self)
        self._form_host.setObjectName("PropertiesFormHost")
        self._form_layout = QFormLayout(self._form_host)
        layout.addWidget(self._form_host, 1)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_object(self, label: str, properties: dict[str, str]) -> None:
        """Replace the form contents with ``properties`` keyed values."""
        self._context_label.setText(label)
        self._clear_form()
        for key, value in properties.items():
            self._form_layout.addRow(QLabel(key), QLabel(value))

    def clear(self) -> None:
        self._context_label.setText("(nothing selected)")
        self._clear_form()

    def _clear_form(self) -> None:
        while self._form_layout.rowCount() > 0:
            self._form_layout.removeRow(0)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def context_label(self) -> QLabel:
        return self._context_label

    def form_layout(self) -> QFormLayout:
        return self._form_layout
