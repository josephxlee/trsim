"""Command Palette widget (plan/05 § 5.4).

A lightweight QDialog that lets the user fuzzy-search and dispatch any
:class:`WorkbenchCommand` registered in the
:class:`WorkbenchCommandRegistry`. Bound to ``Ctrl+Shift+P`` by
:class:`workbench.ui.main_window.MainWindow`.

Behaviour:

- Live filter as the user types (substring on title, then id).
- ``Up`` / ``Down`` cycle the result list while focus stays in the
  search box (so the user keeps typing without re-aiming).
- ``Enter`` dispatches the highlighted command.
- ``Escape`` closes without dispatching (QDialog default).
- Disabled commands are shown greyed out and refuse dispatch.

The palette is **stateless** — it reads the registry on every open
and rebuilds the list from scratch. Cheap enough at MVP scale (a few
dozen commands).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.commands.registry import (
    WorkbenchCommand,
    WorkbenchCommandRegistry,
)

_ITEM_ROLE_COMMAND_ID = Qt.ItemDataRole.UserRole


class CommandPalette(QDialog):
    """Modal palette for searching + dispatching workbench commands."""

    def __init__(
        self,
        registry: WorkbenchCommandRegistry,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self.setWindowTitle("Command Palette")
        self.setModal(True)
        self.resize(560, 360)
        self.setObjectName("CommandPalette")

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Type a command…")
        self._search.setClearButtonEnabled(True)

        self._list = QListWidget(self)
        self._list.setUniformItemSizes(True)
        self._list.setObjectName("CommandPaletteList")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(self._search)
        layout.addWidget(self._list, 1)

        self._search.textChanged.connect(self._refresh)
        self._list.itemActivated.connect(self._on_item_activated)
        self._search.installEventFilter(self)

        self._refresh("")

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def _refresh(self, query: str) -> None:
        self._list.clear()
        for cmd in self._registry.find(query):
            self._list.addItem(self._build_item(cmd))
        if self._list.count() > 0:
            self._list.setCurrentRow(0)

    @staticmethod
    def _build_item(cmd: WorkbenchCommand) -> QListWidgetItem:
        suffix = f" — {cmd.shortcut}" if cmd.shortcut else ""
        label = f"{cmd.category}: {cmd.title}{suffix}"
        item = QListWidgetItem(label)
        item.setData(_ITEM_ROLE_COMMAND_ID, cmd.id)
        if cmd.description:
            item.setToolTip(cmd.description)
        if not cmd.is_enabled():
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        return item

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def _on_item_activated(self, item: QListWidgetItem) -> None:
        command_id = item.data(_ITEM_ROLE_COMMAND_ID)
        if not isinstance(command_id, str):
            return
        cmd = self._registry.get(command_id)
        if not cmd.is_enabled():
            return
        self._registry.dispatch(command_id)
        self.accept()

    def _activate_current(self) -> None:
        item = self._list.currentItem()
        if item is None or not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            return
        self._on_item_activated(item)

    # ------------------------------------------------------------------
    # Forward Up / Down / Enter from the search box to the list
    # ------------------------------------------------------------------
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802 (Qt override)
        if watched is self._search and event.type() == QEvent.Type.KeyPress:
            assert isinstance(event, QKeyEvent)
            key = event.key()
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
                self._step_selection(+1 if key == Qt.Key.Key_Down else -1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self._activate_current()
                return True
        return super().eventFilter(watched, event)

    def _step_selection(self, delta: int) -> None:
        count = self._list.count()
        if count == 0:
            return
        row = (self._list.currentRow() + delta) % count
        self._list.setCurrentRow(row)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------
    def search_box(self) -> QLineEdit:
        """Return the internal search QLineEdit (test helper)."""
        return self._search

    def result_list(self) -> QListWidget:
        """Return the internal result QListWidget (test helper)."""
        return self._list

    def open_fresh(self) -> None:
        """Clear the search and re-open the palette."""
        self._search.clear()
        self._refresh("")
        self._search.setFocus()
        self.show()
