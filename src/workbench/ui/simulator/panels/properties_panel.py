"""Context-sensitive Properties panel (Phase 4.9, plan/05 § 5.3.5).

P5b (post-MVP polish, 2026-05-14) — :meth:`show_object` now incrementally
patches the form when the caller pushes the same ``label`` + key-set,
which the L6 :class:`SimulatorPrimaryTargetController` does at 60 Hz.
Previously every tick wiped 6 rows and recreated them, producing visible
text flicker and amplifying the Qt reflow cost during window resize. The
new fast path mutates existing :class:`QLabel` widgets in place.
"""

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

        # Track the most recent (label, key tuple) so subsequent calls
        # with the same shape can patch in place without thrashing
        # the layout. Mapping is field-name -> value QLabel for O(1)
        # setText() during the fast path.
        self._current_label: str | None = None
        self._current_value_labels: dict[str, QLabel] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def show_object(self, label: str, properties: dict[str, str]) -> None:
        """Replace the form contents with ``properties`` keyed values.

        Fast path: when the previous call's ``label`` matches and the
        property keys are identical, only the value text is mutated.
        Slow path (initial call, label change, key-set change): the
        form is rebuilt from scratch.
        """
        same_label = label == self._current_label
        same_keys = tuple(properties.keys()) == tuple(self._current_value_labels.keys())
        if same_label and same_keys:
            # Fast path — just update the existing value labels.
            for key, value in properties.items():
                self._current_value_labels[key].setText(value)
            return

        # Slow path — rebuild form.
        self._context_label.setText(label)
        self._clear_form()
        self._current_value_labels = {}
        for key, value in properties.items():
            value_label = QLabel(value)
            self._form_layout.addRow(QLabel(key), value_label)
            self._current_value_labels[key] = value_label
        self._current_label = label

    def clear(self) -> None:
        self._context_label.setText("(nothing selected)")
        self._clear_form()
        self._current_label = None
        self._current_value_labels = {}

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
