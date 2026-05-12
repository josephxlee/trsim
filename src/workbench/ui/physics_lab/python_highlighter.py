"""Python syntax highlighter for the Physics Lab Code pane (PL-9.1a).

plan/19 § 19.5.3 lists syntax highlight as the minimum read-mode
affordance for the Code pane. Autocomplete and structural folding
stay in 9.3.

Two layers:

- :func:`tokenize_python_line` — pure-Python categoriser. Takes one
  text block (a single line from QSyntaxHighlighter) plus the
  previous-block state for tracking open triple-quoted strings, and
  returns the ordered list of ``(start, length, category)`` spans
  plus the new block state. Reused by the Qt highlighter and by the
  unit tests so colouring decisions can be checked without a QApp.
- :class:`PythonSyntaxHighlighter` — :class:`QSyntaxHighlighter`
  subclass that wires the categoriser into a QTextDocument and ships
  the colour palette.

Categories produced:

============= ==========================
category      what it matches
============= ==========================
``keyword``   ``def``, ``class``, ``return``, ``if``, ...
``builtin``   ``len``, ``range``, ``print``, ``isinstance``, ...
``constant``  ``True``, ``False``, ``None``
``self``      ``self``, ``cls``
``string``    ``"..."``, ``'...'``, ``\"\"\"...\"\"\"``, ``'''...'''``
``comment``   ``# ... end of line``
``number``    int / float / scientific / hex literal
``decorator`` ``@identifier``
``defname``   the identifier in ``def NAME(...)``
``classname`` the identifier in ``class NAME(...)``
============= ==========================
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass

from PySide6.QtGui import (
    QColor,
    QFont,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextDocument,
)
from typing_extensions import override

# Block-state values for triple-quoted strings carried across blocks.
# Qt's default block state is -1; we keep that as "no open string".
STATE_TRIPLE_DOUBLE: int = 0
STATE_TRIPLE_SINGLE: int = 1


# ---------------------------------------------------------------------
# Token category tables
# ---------------------------------------------------------------------


_PYTHON_BUILTINS: frozenset[str] = frozenset(
    {
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "bool",
        "breakpoint",
        "bytearray",
        "bytes",
        "callable",
        "chr",
        "classmethod",
        "compile",
        "complex",
        "delattr",
        "dict",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "float",
        "format",
        "frozenset",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "int",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "list",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "object",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "property",
        "range",
        "repr",
        "reversed",
        "round",
        "set",
        "setattr",
        "slice",
        "sorted",
        "staticmethod",
        "str",
        "sum",
        "super",
        "tuple",
        "type",
        "vars",
        "zip",
    }
)

_PYTHON_KEYWORDS: frozenset[str] = frozenset(keyword.kwlist)
_PYTHON_CONSTANTS: frozenset[str] = frozenset({"True", "False", "None"})
_SELF_TOKENS: frozenset[str] = frozenset({"self", "cls"})


# ---------------------------------------------------------------------
# Regex patterns (pure-Python tokeniser)
# ---------------------------------------------------------------------


_RE_IDENTIFIER = re.compile(r"\b[A-Za-z_]\w*\b")
_RE_DECORATOR = re.compile(r"@[A-Za-z_]\w*")
_RE_DEF_NAME = re.compile(r"\bdef\s+([A-Za-z_]\w*)")
_RE_CLASS_NAME = re.compile(r"\bclass\s+([A-Za-z_]\w*)")
_RE_NUMBER = re.compile(r"\b0[xX][0-9a-fA-F]+\b|\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b")


@dataclass(frozen=True, slots=True)
class TokenSpan:
    """One colour run inside a single text block (single line).

    Attributes:
        start: Column index where the span begins (0-based).
        length: Number of characters covered.
        category: One of the keys listed in the module docstring.
    """

    start: int
    length: int
    category: str


# ---------------------------------------------------------------------
# Pure-Python categoriser
# ---------------------------------------------------------------------


def _find_string_close(text: str, start: int, quote: str) -> int | None:
    """Return the index of the matching closing quote, or None."""
    i = start + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == quote:
            return i
        i += 1
    return None


def tokenize_python_line(
    text: str,
    prev_state: int = -1,
) -> tuple[list[TokenSpan], int]:
    """Categorise one block of source text.

    The function does not emit overlapping spans: each character maps
    to at most one category. Strings and comments are detected first so
    they shadow keyword/identifier matches inside their contents.

    Args:
        text: One block (QSyntaxHighlighter passes one line at a time).
        prev_state: ``-1`` if the previous block ended outside a
            triple-quoted string; :data:`STATE_TRIPLE_DOUBLE` or
            :data:`STATE_TRIPLE_SINGLE` if a multi-line triple-quoted
            string from the previous line was open.

    Returns:
        ``(spans, new_state)`` where ``spans`` is ordered by ``start``
        and ``new_state`` is the block state to carry forward.
    """
    spans: list[TokenSpan] = []
    n = len(text)
    masked: list[bool] = [False] * n

    def add(start: int, length: int, category: str) -> None:
        spans.append(TokenSpan(start, length, category))
        end = start + length
        for i in range(start, end):
            if 0 <= i < n:
                masked[i] = True

    new_state = -1
    cursor = 0

    # ---- Carry over a triple-quoted string from the previous block.
    if prev_state == STATE_TRIPLE_DOUBLE:
        end = text.find('"""')
        if end == -1:
            add(0, n, "string")
            return spans, STATE_TRIPLE_DOUBLE
        add(0, end + 3, "string")
        cursor = end + 3
    elif prev_state == STATE_TRIPLE_SINGLE:
        end = text.find("'''")
        if end == -1:
            add(0, n, "string")
            return spans, STATE_TRIPLE_SINGLE
        add(0, end + 3, "string")
        cursor = end + 3

    # ---- Walk left-to-right finding strings, triples and comments.
    while cursor < n:
        if text.startswith('"""', cursor):
            close = text.find('"""', cursor + 3)
            if close == -1:
                add(cursor, n - cursor, "string")
                new_state = STATE_TRIPLE_DOUBLE
                cursor = n
                break
            add(cursor, close + 3 - cursor, "string")
            cursor = close + 3
            continue
        if text.startswith("'''", cursor):
            close = text.find("'''", cursor + 3)
            if close == -1:
                add(cursor, n - cursor, "string")
                new_state = STATE_TRIPLE_SINGLE
                cursor = n
                break
            add(cursor, close + 3 - cursor, "string")
            cursor = close + 3
            continue
        ch = text[cursor]
        if ch in ('"', "'"):
            single_close = _find_string_close(text, cursor, ch)
            if single_close is None:
                add(cursor, n - cursor, "string")
                cursor = n
                break
            add(cursor, single_close + 1 - cursor, "string")
            cursor = single_close + 1
            continue
        if ch == "#":
            add(cursor, n - cursor, "comment")
            cursor = n
            break
        cursor += 1

    # ---- Decorators (skip ranges already inside strings/comments).
    for m in _RE_DECORATOR.finditer(text):
        if any(masked[m.start() : m.end()]):
            continue
        add(m.start(), m.end() - m.start(), "decorator")

    # ---- Numbers.
    for m in _RE_NUMBER.finditer(text):
        if any(masked[m.start() : m.end()]):
            continue
        add(m.start(), m.end() - m.start(), "number")

    # ---- Identifiers: keyword / builtin / constant / self / def-/class-name.
    def_starts = {m.start(1) for m in _RE_DEF_NAME.finditer(text)}
    cls_starts = {m.start(1) for m in _RE_CLASS_NAME.finditer(text)}
    for m in _RE_IDENTIFIER.finditer(text):
        if any(masked[m.start() : m.end()]):
            continue
        token = text[m.start() : m.end()]
        # Constants are checked before keywords because True/False/None
        # are technically in keyword.kwlist but want their own colour.
        category: str | None = None
        if m.start() in def_starts:
            category = "defname"
        elif m.start() in cls_starts:
            category = "classname"
        elif token in _PYTHON_CONSTANTS:
            category = "constant"
        elif token in _PYTHON_KEYWORDS:
            category = "keyword"
        elif token in _SELF_TOKENS:
            category = "self"
        elif token in _PYTHON_BUILTINS:
            category = "builtin"
        if category is None:
            continue
        add(m.start(), m.end() - m.start(), category)

    spans.sort(key=lambda s: s.start)
    return spans, new_state


# ---------------------------------------------------------------------
# Qt highlighter
# ---------------------------------------------------------------------


def _make_format(
    color: str,
    *,
    bold: bool = False,
    italic: bool = False,
) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


def _build_palette() -> dict[str, QTextCharFormat]:
    # Palette tuned for the system-default light text background.
    # PL-E's Edit-mode tint (rgba(120,180,120,32)) sits on top of these
    # foreground colours; all entries stay readable in both modes.
    return {
        "keyword": _make_format("#0033b3", bold=True),
        "builtin": _make_format("#00627a"),
        "constant": _make_format("#0033b3", italic=True),
        "self": _make_format("#871094", italic=True),
        "string": _make_format("#067d17"),
        "comment": _make_format("#6e7474", italic=True),
        "number": _make_format("#1750eb"),
        "decorator": _make_format("#9e880d"),
        "defname": _make_format("#00627a", bold=True),
        "classname": _make_format("#005180", bold=True),
    }


class PythonSyntaxHighlighter(QSyntaxHighlighter):
    """Light-theme Python syntax highlighter for the Code pane.

    Attaches to a :class:`QTextDocument` and recolours spans returned
    by :func:`tokenize_python_line`.

    Class attributes:
        KEYWORDS: ``frozenset[str]`` of Python reserved words
            (``keyword.kwlist``).
        BUILTINS: ``frozenset[str]`` of the common builtins that get
            their own colour.
        CONSTANTS: ``frozenset[str]`` (``True``/``False``/``None``).

    Methods:
        :meth:`format_for(category)` — return the
            :class:`QTextCharFormat` used for a category. Tests use this
            to confirm the palette covers every category emitted by the
            tokeniser.
    """

    KEYWORDS: frozenset[str] = _PYTHON_KEYWORDS
    BUILTINS: frozenset[str] = _PYTHON_BUILTINS
    CONSTANTS: frozenset[str] = _PYTHON_CONSTANTS

    def __init__(self, document: QTextDocument) -> None:
        super().__init__(document)
        self._palette = _build_palette()

    def format_for(self, category: str) -> QTextCharFormat:
        return self._palette[category]

    @override
    def highlightBlock(self, text: str) -> None:
        prev_state = self.previousBlockState()
        spans, new_state = tokenize_python_line(text, prev_state)
        for span in spans:
            fmt = self._palette.get(span.category)
            if fmt is None:
                continue
            self.setFormat(span.start, span.length, fmt)
        self.setCurrentBlockState(new_state)
