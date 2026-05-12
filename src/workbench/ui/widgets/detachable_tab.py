"""Detachable QTabWidget — right-click a tab to float it (option D).

Floating dock MVP. plan/05 § 5.2 + plan/13 § 13.2 keep the workspace
layout as a fixed QSplitter chain, but users still want to pop a busy
panel (FFT spectrum, Step 1 log, Profiler chart) into a separate
top-level window so it can sit alongside the simulator workspace.

Option D from the MVP-plus design discussion: a single-direction detach
button + automatic re-attach when the floating window is closed.

Lifecycle:

1. Right-click a tab on the :class:`DetachableTabWidget` tab bar.
2. Pick "Detach tab" from the context menu.
3. The tab is removed from the QTabWidget and re-parented into a
   :class:`FloatingPanel` top-level window.
4. Closing the floating window re-inserts the tab at its original
   index with the original label.

The detached widget keeps its own internal state (signals stay
connected, controllers keep their references). Re-parenting is the
only Qt-level change.

References:

- plan/02 § 2.6 — DockManager covers the bigger dock layout problem;
  this widget covers the per-tab float case that does not require
  saving / restoring an entire workspace layout.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QMainWindow,
    QMenu,
    QTabWidget,
    QWidget,
)


class FloatingPanel(QMainWindow):
    """Top-level window that hosts one detached tab.

    Carries the original tab title + index so the host
    :class:`DetachableTabWidget` can re-insert at the same spot when
    the user closes the window.

    Attributes:
        content: The detached widget (parent of this floating window).
        origin_title: Tab label at detach time.
        origin_index: Position in the source QTabWidget at detach time.
    """

    closed = Signal()

    def __init__(
        self,
        content: QWidget,
        *,
        origin_title: str,
        origin_index: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.content = content
        self.origin_title = origin_title
        self.origin_index = origin_index
        self.setObjectName(f"FloatingPanel_{origin_title}")
        self.setWindowTitle(f"TRsim — {origin_title}")
        self.setCentralWidget(content)
        # Resize once to a sensible default so the floating window is
        # not collapsed to zero. The content widget's own size hint
        # drives the actual layout; this is just a starting frame.
        self.resize(640, 480)

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 — Qt API
        """Detach the content widget before destruction so the host can
        re-insert it. Signals self.closed so the host knows to act.
        """
        # Re-parent to None so removing this QMainWindow does not also
        # delete the content widget. The host's slot will then call
        # setParent(<tab_widget>) to re-attach.
        self.takeCentralWidget()
        self.content.setParent(None)
        self.closed.emit()
        super().closeEvent(event)


class DetachableTabWidget(QTabWidget):
    """QTabWidget with a right-click "Detach tab" context menu.

    Each detached tab becomes a :class:`FloatingPanel` whose close
    event re-inserts the widget at its original index.

    Signals:
        tab_detached(int, str): Emitted after detach with the (former)
            tab index + label. Tests use this to assert the side effect.
        tab_reattached(int, str): Emitted after a floating window closes
            and the widget is re-inserted with the (new) index + label.
    """

    tab_detached = Signal(int, str)
    tab_reattached = Signal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        bar = self.tabBar()
        bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        bar.customContextMenuRequested.connect(self._on_tab_context_menu)
        # Track active floating panels so test code (and future
        # multi-workspace save/restore) can enumerate them.
        self._floating_panels: list[FloatingPanel] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detach_tab(self, index: int) -> FloatingPanel | None:
        """Promote tab ``index`` into a floating top-level window.

        Returns the :class:`FloatingPanel` so callers can resize /
        reposition it; ``None`` when the index is out of range.
        """
        if index < 0 or index >= self.count():
            return None
        widget = self.widget(index)
        if widget is None:
            return None
        title = self.tabText(index)
        self.removeTab(index)

        floating = FloatingPanel(
            widget,
            origin_title=title,
            origin_index=index,
            parent=self.window(),
        )
        floating.closed.connect(lambda f=floating: self._on_floating_closed(f))
        self._floating_panels.append(floating)
        floating.show()
        self.tab_detached.emit(index, title)
        return floating

    def floating_panels(self) -> tuple[FloatingPanel, ...]:
        """Currently-active :class:`FloatingPanel` windows."""
        return tuple(self._floating_panels)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _on_tab_context_menu(self, pos: QPoint) -> None:
        bar = self.tabBar()
        index = bar.tabAt(pos)
        if index < 0:
            return
        menu = QMenu(self)
        detach_action = menu.addAction("Detach tab")
        chosen = menu.exec(bar.mapToGlobal(pos))
        if chosen is detach_action:
            self.detach_tab(index)

    def _on_floating_closed(self, floating: FloatingPanel) -> None:
        """Re-insert ``floating.content`` back into this tab widget."""
        if floating in self._floating_panels:
            self._floating_panels.remove(floating)
        widget = floating.content
        # Clamp the re-insert index to the current tab count — the
        # user may have rearranged or removed tabs while this one was
        # detached.
        target_index = min(floating.origin_index, self.count())
        self.insertTab(target_index, widget, floating.origin_title)
        self.setCurrentIndex(target_index)
        self.tab_reattached.emit(target_index, floating.origin_title)
