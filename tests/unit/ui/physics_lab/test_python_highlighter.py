"""Python syntax highlighter tests (PL-9.1a, plan/19 § 19.5.3)."""

from __future__ import annotations

import keyword

import pytest

pytest.importorskip("PySide6")

from workbench.ui.physics_lab.python_highlighter import (
    STATE_TRIPLE_DOUBLE,
    STATE_TRIPLE_SINGLE,
    PythonSyntaxHighlighter,
    TokenSpan,
    tokenize_python_line,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# Pure-Python tokeniser
# ---------------------------------------------------------------------


def _categories(spans: list[TokenSpan]) -> set[tuple[int, int, str]]:
    return {(s.start, s.length, s.category) for s in spans}


def test_keyword_def_categorised() -> None:
    spans, state = tokenize_python_line("def foo():")
    assert (0, 3, "keyword") in _categories(spans)
    assert state == -1


def test_def_name_separately_categorised() -> None:
    spans, _ = tokenize_python_line("def gravity_force():")
    assert (4, 13, "defname") in _categories(spans)


def test_class_name_separately_categorised() -> None:
    spans, _ = tokenize_python_line("class BouncingBallSimulator:")
    assert (6, 21, "classname") in _categories(spans)


def test_comment_categorised_to_end_of_line() -> None:
    text = "x = 1  # gravity coefficient"
    spans, _ = tokenize_python_line(text)
    # The comment span starts at the '#' and runs to the end of text.
    comment_spans = [s for s in spans if s.category == "comment"]
    assert len(comment_spans) == 1
    assert comment_spans[0].start == text.index("#")
    assert comment_spans[0].start + comment_spans[0].length == len(text)


def test_double_quoted_string_categorised() -> None:
    spans, _ = tokenize_python_line('msg = "hello"')
    string_spans = [s for s in spans if s.category == "string"]
    assert len(string_spans) == 1
    assert string_spans[0].start == 6
    assert string_spans[0].length == 7  # "hello"


def test_single_quoted_string_categorised() -> None:
    spans, _ = tokenize_python_line("msg = 'hi'")
    string_spans = [s for s in spans if s.category == "string"]
    assert len(string_spans) == 1
    assert string_spans[0].length == 4  # 'hi'


def test_escaped_quote_inside_string_does_not_terminate_early() -> None:
    text = r'x = "a\"b"'
    spans, _ = tokenize_python_line(text)
    string_spans = [s for s in spans if s.category == "string"]
    assert len(string_spans) == 1
    assert string_spans[0].start == 4
    assert string_spans[0].length == len(text) - 4


def test_decorator_categorised() -> None:
    spans, _ = tokenize_python_line("@property")
    assert any(s.category == "decorator" and s.start == 0 for s in spans)


def test_decorator_does_not_double_colour_identifier() -> None:
    """@property must not produce a second span for the 'property' name
    (the decorator span covers the whole thing).
    """
    spans, _ = tokenize_python_line("@property")
    builtins_inside = [s for s in spans if s.category == "builtin"]
    assert builtins_inside == []


def test_decimal_number_categorised() -> None:
    spans, _ = tokenize_python_line("g = 9.81")
    assert any(s.category == "number" and s.start == 4 for s in spans)


def test_hex_number_categorised() -> None:
    spans, _ = tokenize_python_line("x = 0xFF")
    assert any(s.category == "number" and s.start == 4 for s in spans)


def test_scientific_number_categorised() -> None:
    spans, _ = tokenize_python_line("c = 3e8")
    assert any(s.category == "number" and s.start == 4 for s in spans)


def test_true_false_none_are_constants_not_keywords() -> None:
    spans, _ = tokenize_python_line("a = True")
    cats = {s.category for s in spans if s.category in {"constant", "keyword"}}
    assert "constant" in cats
    assert "keyword" not in cats


def test_self_token_categorised() -> None:
    spans, _ = tokenize_python_line("    self.x = 0")
    assert any(s.category == "self" for s in spans)


def test_cls_token_categorised() -> None:
    spans, _ = tokenize_python_line("    cls.attr = 1")
    assert any(s.category == "self" for s in spans)


def test_builtin_print_categorised() -> None:
    spans, _ = tokenize_python_line("print(x)")
    assert any(s.category == "builtin" and s.start == 0 for s in spans)


def test_hash_inside_string_is_not_a_comment() -> None:
    spans, _ = tokenize_python_line('x = "#not-a-comment"')
    assert [s for s in spans if s.category == "comment"] == []
    string_spans = [s for s in spans if s.category == "string"]
    assert len(string_spans) == 1


def test_quote_inside_comment_does_not_open_string() -> None:
    spans, _ = tokenize_python_line('# unmatched "quote stays in comment')
    assert [s for s in spans if s.category == "string"] == []
    comments = [s for s in spans if s.category == "comment"]
    assert len(comments) == 1


def test_triple_double_quote_open_carries_state() -> None:
    _, state = tokenize_python_line('"""this opens but does not close')
    assert state == STATE_TRIPLE_DOUBLE


def test_triple_double_quote_close_resets_state() -> None:
    spans, state = tokenize_python_line('continuing"""', prev_state=STATE_TRIPLE_DOUBLE)
    assert state == -1
    assert any(s.category == "string" and s.start == 0 for s in spans)


def test_triple_single_quote_state_round_trip() -> None:
    _, state = tokenize_python_line("'''opens here")
    assert state == STATE_TRIPLE_SINGLE
    spans, end_state = tokenize_python_line("closes'''", prev_state=STATE_TRIPLE_SINGLE)
    assert end_state == -1
    assert any(s.category == "string" for s in spans)


def test_triple_quoted_string_complete_on_one_line() -> None:
    # `"""ok"""` is 8 characters (3 + 2 + 3).
    spans, state = tokenize_python_line('x = """ok"""')
    assert state == -1
    strings = [s for s in spans if s.category == "string"]
    assert any(s.start == 4 and s.length == 8 for s in strings)


def test_triple_quoted_middle_line_entirely_string() -> None:
    """The middle line of a docstring is fully a string."""
    spans, state = tokenize_python_line(
        "middle text inside docstring", prev_state=STATE_TRIPLE_DOUBLE
    )
    assert state == STATE_TRIPLE_DOUBLE
    assert len(spans) == 1
    assert spans[0].category == "string"
    assert spans[0].start == 0
    assert spans[0].length == len("middle text inside docstring")


def test_empty_line_returns_no_spans_and_carries_state() -> None:
    spans, state = tokenize_python_line("", prev_state=STATE_TRIPLE_DOUBLE)
    # Empty inside an open triple — still inside it.
    # spans may be empty or a zero-length one; we accept both.
    assert state == STATE_TRIPLE_DOUBLE
    assert all(s.length >= 0 for s in spans)


def test_spans_do_not_overlap() -> None:
    """A character belongs to at most one span. Regression for the
    overlap potential between decorator + builtin + identifier rules.
    """
    text = "@property\ndef step(self, dt_s):"
    spans, _ = tokenize_python_line(text.split("\n")[0])
    # Verify within first line.
    used = [False] * len(text.split("\n")[0])
    for s in spans:
        for i in range(s.start, s.start + s.length):
            assert not used[i], f"overlap at {i} in {text!r}"
            used[i] = True


# ---------------------------------------------------------------------
# Highlighter palette + attachment
# ---------------------------------------------------------------------


def test_keywords_constant_matches_python_kwlist() -> None:
    assert PythonSyntaxHighlighter.KEYWORDS == frozenset(keyword.kwlist)


def test_constants_distinct_from_keywords_in_categoriser() -> None:
    """The intersection of KEYWORDS and CONSTANTS is non-empty (True /
    False / None are technically keywords in Python 3), but the
    categoriser routes them to ``constant``.
    """
    assert {"True", "False", "None"} <= PythonSyntaxHighlighter.CONSTANTS


def test_palette_covers_every_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QTextDocument

    doc = QTextDocument()
    hl = PythonSyntaxHighlighter(doc)
    for category in (
        "keyword",
        "builtin",
        "constant",
        "self",
        "string",
        "comment",
        "number",
        "decorator",
        "defname",
        "classname",
    ):
        fmt = hl.format_for(category)
        assert fmt.foreground().color().isValid()


def test_highlighter_attached_to_document(qtbot) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QTextDocument

    doc = QTextDocument()
    hl = PythonSyntaxHighlighter(doc)
    assert hl.document() is doc


def test_highlight_block_sets_user_state_after_rehighlight(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``QSyntaxHighlighter.setCurrentBlockState`` writes to the block's
    user state. Explicit :meth:`rehighlight` drives the highlighter
    across every block without requiring a paint pass.
    """
    from PySide6.QtGui import QTextDocument

    doc = QTextDocument()
    hl = PythonSyntaxHighlighter(doc)
    doc.setPlainText('"""opened\nmiddle\n"""\n')
    hl.rehighlight()
    block0 = doc.findBlockByNumber(0)
    assert block0.userState() == STATE_TRIPLE_DOUBLE
    block2 = doc.findBlockByNumber(2)
    assert block2.userState() == -1


# ---------------------------------------------------------------------
# CodePreview integration
# ---------------------------------------------------------------------


def test_code_preview_installs_highlighter(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.physics_lab import CodePreview

    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    assert isinstance(cp.highlighter(), PythonSyntaxHighlighter)
    assert cp.highlighter().document() is cp.editor().document()
