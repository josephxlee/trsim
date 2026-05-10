"""Resource Browser sidebar widget (Phase 4.4).

Always-visible left-of-center panel inside the Editor Workspace.
Layout (plan/13 section 13.2.3):

::

    +-- Resource Browser ------+
    | [Search ____________]    |
    | v Scenarios (3)          |
    |   [active] B_Conflict    |
    |   A_Base                 |
    | v Maps (2)               |
    |   ...                    |
    | [+ New Resource v]       |
    +--------------------------+

Public surface (Phase 4.4 - Phase 5+ replaces add_item with a feed
from app.resource_library):

- :meth:`add_item` / :meth:`clear` / :meth:`clear_category`
- :meth:`set_filter_text` (the QLineEdit's clear button drives this).
- ``item_double_clicked`` signal: emits ``(category, name)`` when the
  user double-clicks a leaf row. The MainWindow / Editor binds this to
  switch to the matching Activity tab.

The widget intentionally has no notion of where the data comes from -
that's the App layer's job. Status badges use ASCII prefixes
(``[active] ``, ``[stale] ``, ``[builtin] ``) so RUF002 passes
without per-line ignores.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLineEdit,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from workbench.ui.editor.resource_browser.types import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
    ResourceCategory,
    ResourceItem,
)

_CATEGORY_ROLE = Qt.ItemDataRole.UserRole
_NAME_ROLE = Qt.ItemDataRole.UserRole + 1


class ResourceBrowserSidebar(QWidget):
    """Filterable tree of registered resources, grouped by category."""

    item_double_clicked = Signal(ResourceCategory, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResourceBrowserSidebar")
        self.setMinimumWidth(220)

        self._search = QLineEdit(self)
        self._search.setPlaceholderText("Search resources...")
        self._search.setClearButtonEnabled(True)
        self._search.setObjectName("ResourceBrowserSearch")

        self._tree = QTreeWidget(self)
        self._tree.setObjectName("ResourceBrowserTree")
        self._tree.setHeaderHidden(True)
        self._tree.setUniformRowHeights(True)
        self._tree.setRootIsDecorated(True)

        self._new_button = QToolButton(self)
        self._new_button.setText("+ New Resource")
        self._new_button.setObjectName("ResourceBrowserNewBtn")
        self._new_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        self._category_nodes: dict[ResourceCategory, QTreeWidgetItem] = {}
        for cat in CATEGORY_ORDER:
            node = QTreeWidgetItem([f"{CATEGORY_LABELS[cat]} (0)"])
            node.setExpanded(True)
            node.setData(0, _CATEGORY_ROLE, cat.value)
            self._tree.addTopLevelItem(node)
            node.setExpanded(True)
            self._category_nodes[cat] = node

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        layout.addWidget(self._search)
        layout.addWidget(self._tree, 1)
        layout.addWidget(self._new_button)

        self._search.textChanged.connect(self._apply_filter)
        self._tree.itemDoubleClicked.connect(self._on_item_double_clicked)

    # ------------------------------------------------------------------
    # Mutators (Phase 5+ ResourceLibrary feeds these)
    # ------------------------------------------------------------------
    def add_item(self, item: ResourceItem) -> QTreeWidgetItem:
        """Append ``item`` under its category. Returns the leaf row."""
        parent = self._category_nodes[item.category]
        leaf = QTreeWidgetItem([item.display_text()])
        leaf.setData(0, _CATEGORY_ROLE, item.category.value)
        leaf.setData(0, _NAME_ROLE, item.name)
        parent.addChild(leaf)
        self._refresh_category_count(item.category)
        return leaf

    def clear_category(self, category: ResourceCategory) -> None:
        """Remove every leaf under ``category``."""
        node = self._category_nodes[category]
        node.takeChildren()
        self._refresh_category_count(category)

    def clear(self) -> None:
        """Remove every leaf in every category."""
        for cat in CATEGORY_ORDER:
            self.clear_category(cat)

    def set_filter_text(self, text: str) -> None:
        """Programmatic mirror of typing into the search box."""
        self._search.setText(text)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------
    def search_box(self) -> QLineEdit:
        """Return the search QLineEdit (test helper)."""
        return self._search

    def tree(self) -> QTreeWidget:
        """Return the underlying QTreeWidget (test helper)."""
        return self._tree

    def new_button(self) -> QToolButton:
        """Return the [+ New Resource] QToolButton (test helper)."""
        return self._new_button

    def category_node(self, category: ResourceCategory) -> QTreeWidgetItem:
        """Return the top-level item for ``category`` (test helper)."""
        return self._category_nodes[category]

    def visible_items(self, category: ResourceCategory) -> tuple[str, ...]:
        """Names of the leaves currently visible under ``category``."""
        node = self._category_nodes[category]
        return tuple(
            str(node.child(i).data(0, _NAME_ROLE))
            for i in range(node.childCount())
            if not node.child(i).isHidden()
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _refresh_category_count(self, category: ResourceCategory) -> None:
        node = self._category_nodes[category]
        count = node.childCount()
        node.setText(0, f"{CATEGORY_LABELS[category]} ({count})")

    def _apply_filter(self, query: str) -> None:
        q = query.strip().lower()
        for cat in CATEGORY_ORDER:
            node = self._category_nodes[cat]
            visible = 0
            for i in range(node.childCount()):
                child = node.child(i)
                name = str(child.data(0, _NAME_ROLE))
                hit = (q == "") or (q in name.lower())
                child.setHidden(not hit)
                if hit:
                    visible += 1
            node.setText(0, f"{CATEGORY_LABELS[cat]} ({visible})")
            node.setHidden(visible == 0 and q != "")

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        # Top-level rows have no NAME_ROLE - ignore them.
        name = item.data(0, _NAME_ROLE)
        category = item.data(0, _CATEGORY_ROLE)
        if not isinstance(name, str) or not isinstance(category, str):
            return
        # Discard items that no longer round-trip through the enum.
        try:
            cat_enum = ResourceCategory(category)
        except ValueError:
            return
        self.item_double_clicked.emit(cat_enum, name)
