"""Python code editor with autocomplete (PL-9.3a, plan/19 § 19.5.3).

Subclass of :class:`QTextEdit` that wires a :class:`QCompleter`
populated with Python keywords + common builtins + the Bouncing Ball
simulator API. The highlighter installed by :class:`CodePreview` on
the same document continues to work — the editor only adds key-event
plumbing on top.

Popup behaviour:

- Triggered automatically while typing identifiers (>= 1 character).
- Manual trigger via Ctrl+Space.
- Arrow keys + Enter / Tab inside the popup pick a completion;
  Escape hides it.
- ``activated`` slot replaces the prefix under the cursor with the
  selected completion.

The completion word list is a static set built once at class load.
Phase 9.3+ may extend the list by walking the user's edited buffer
with :mod:`ast` and harvesting the symbols they declare; the
interface (a flat ``list[str]``) keeps that future change small.
"""

from __future__ import annotations

import keyword

from PySide6.QtCore import QStringListModel, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor
from PySide6.QtWidgets import QCompleter, QTextEdit, QWidget
from typing_extensions import override

# Bouncing Ball simulator + state API names that the user's
# ``step(simulator, dt_s)`` function commonly references.
_BOUNCING_BALL_API: frozenset[str] = frozenset(
    {
        "simulator",
        "dt_s",
        "state",
        "time_s",
        "position_m",
        "velocity_m_s",
        "bounces",
        "gravity_m_s2",
        "restitution",
        "drag_coefficient_k",
        "initial_height_m",
        "initial_velocity_m_s",
        "update_state",
        "set_restitution",
        "set_drag_coefficient",
        "set_step_override",
        "BouncingBallState",
        "BouncingBallSimulator",
    }
)

_PYTHON_BUILTINS: frozenset[str] = frozenset(
    {
        "abs",
        "all",
        "any",
        "bool",
        "dict",
        "enumerate",
        "float",
        "int",
        "isinstance",
        "issubclass",
        "len",
        "list",
        "max",
        "min",
        "pow",
        "print",
        "range",
        "round",
        "set",
        "str",
        "sum",
        "tuple",
        "type",
        "zip",
        "True",
        "False",
        "None",
    }
)


def default_completion_words() -> list[str]:
    """Sorted union of Python keywords / builtins / Bouncing Ball API.

    Plain function so tests + the autocomplete dropdown share one
    source of truth.
    """
    words: set[str] = set()
    words.update(keyword.kwlist)
    words.update(_PYTHON_BUILTINS)
    words.update(_BOUNCING_BALL_API)
    return sorted(words)


class PythonCodeEditor(QTextEdit):
    """QTextEdit + QCompleter for Python keywords + Bouncing Ball API.

    Drop-in replacement for the bare ``QTextEdit`` used by
    :class:`CodePreview`. The completer is exposed via
    :meth:`completer` so tests can inspect the word list without
    simulating key events.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PhysicsLab_CodeEditor")
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        words = default_completion_words()
        self._completer = QCompleter(words, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.activated.connect(self._insert_completion)

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------

    def completer(self) -> QCompleter:
        return self._completer

    def completion_words(self) -> tuple[str, ...]:
        """Snapshot of the word list backing the completer popup."""
        model = self._completer.model()
        if isinstance(model, QStringListModel):
            return tuple(model.stringList())
        # Fallback: re-derive from the helper (should never trigger
        # in practice, but keeps the API safe).
        return tuple(default_completion_words())

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _text_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def _insert_completion(self, completion: str) -> None:
        if self._completer.widget() is not self:
            return
        cursor = self.textCursor()
        prefix_len = len(self._completer.completionPrefix())
        if prefix_len > 0:
            cursor.movePosition(
                QTextCursor.MoveOperation.Left,
                QTextCursor.MoveMode.KeepAnchor,
                prefix_len,
            )
            cursor.removeSelectedText()
        cursor.insertText(completion)
        self.setTextCursor(cursor)

    @override
    def keyPressEvent(self, e: QKeyEvent) -> None:
        # When the popup is visible let it eat the navigation keys —
        # otherwise the user's Enter / Tab / arrow key picks the
        # current completion instead of inserting a newline.
        popup = self._completer.popup()
        if (
            popup is not None
            and popup.isVisible()
            and e.key()
            in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            )
        ):
            e.ignore()
            return

        # Manual trigger: Ctrl+Space.
        ctrl_space = (
            e.modifiers() == Qt.KeyboardModifier.ControlModifier and e.key() == Qt.Key.Key_Space
        )
        if not ctrl_space:
            super().keyPressEvent(e)

        prefix = self._text_under_cursor()
        if not prefix and not ctrl_space:
            if popup is not None:
                popup.hide()
            return

        if prefix != self._completer.completionPrefix():
            self._completer.setCompletionPrefix(prefix)
            model = self._completer.completionModel()
            if model.rowCount() > 0 and popup is not None:
                popup.setCurrentIndex(model.index(0, 0))

        if popup is None:
            return
        if self._completer.completionCount() == 0:
            popup.hide()
            return
        rect = self.cursorRect()
        scrollbar = popup.verticalScrollBar()
        rect.setWidth(popup.sizeHintForColumn(0) + scrollbar.sizeHint().width())
        self._completer.complete(rect)
