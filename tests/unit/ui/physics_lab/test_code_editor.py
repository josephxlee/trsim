"""Code Pane autocomplete + multi-function tests (PL-9.3a)."""

from __future__ import annotations

import keyword

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from PySide6.QtWidgets import QCompleter

from workbench.ui.physics_lab import (
    BouncingBallController,
    CodePreview,
    PhysicsLabWorkspace,
)
from workbench.ui.physics_lab.code_editor import (
    PythonCodeEditor,
    default_completion_words,
)

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# default_completion_words (pure)
# ---------------------------------------------------------------------


def test_word_list_includes_python_keywords() -> None:
    words = set(default_completion_words())
    for kw in keyword.kwlist:
        assert kw in words


def test_word_list_includes_simulator_api() -> None:
    words = set(default_completion_words())
    assert {
        "simulator",
        "dt_s",
        "state",
        "position_m",
        "velocity_m_s",
        "gravity_m_s2",
        "restitution",
        "drag_coefficient_k",
        "update_state",
        "BouncingBallState",
    } <= words


def test_word_list_sorted_no_duplicates() -> None:
    words = default_completion_words()
    assert words == sorted(words)
    assert len(words) == len(set(words))


# ---------------------------------------------------------------------
# PythonCodeEditor — completer wiring
# ---------------------------------------------------------------------


def test_python_code_editor_has_completer(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    assert isinstance(editor.completer(), QCompleter)
    assert editor.completer().widget() is editor


def test_completion_words_matches_default_list(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    assert editor.completion_words() == tuple(default_completion_words())


def test_completer_prefix_match_def_returns_def(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Set the completer prefix programmatically + check the first
    completion. Avoids dealing with key-event simulation in pytest.
    """
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    c = editor.completer()
    c.setCompletionPrefix("de")
    completions = {c.completionModel().index(i, 0).data() for i in range(c.completionCount())}
    assert "def" in completions
    assert "del" in completions


def test_completer_prefix_simu_returns_simulator(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    c = editor.completer()
    c.setCompletionPrefix("simu")
    completions = {c.completionModel().index(i, 0).data() for i in range(c.completionCount())}
    assert "simulator" in completions


def test_completer_case_insensitive(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    c = editor.completer()
    c.setCompletionPrefix("SIMU")
    completions = {c.completionModel().index(i, 0).data() for i in range(c.completionCount())}
    assert "simulator" in completions


def test_completer_prefix_no_match_returns_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = PythonCodeEditor()
    qtbot.addWidget(editor)  # type: ignore[attr-defined]
    c = editor.completer()
    c.setCompletionPrefix("zzz-not-a-real-prefix")
    assert c.completionCount() == 0


# ---------------------------------------------------------------------
# CodePreview integration
# ---------------------------------------------------------------------


def test_code_preview_editor_is_python_code_editor(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    assert isinstance(cp.editor(), PythonCodeEditor)


def test_code_preview_completer_present(qtbot) -> None:  # type: ignore[no-untyped-def]
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    editor = cp.editor()
    assert isinstance(editor, PythonCodeEditor)
    assert isinstance(editor.completer(), QCompleter)


def test_code_preview_highlighter_still_attached(qtbot) -> None:  # type: ignore[no-untyped-def]
    """PL-9.1a regression — the syntax highlighter must still attach
    to the new editor's document.
    """
    cp = CodePreview()
    qtbot.addWidget(cp)  # type: ignore[attr-defined]
    assert cp.highlighter().document() is cp.editor().document()


# ---------------------------------------------------------------------
# Multi-function user step (regression for 9.3a)
# ---------------------------------------------------------------------


def test_user_step_can_define_helper_function(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The user's edit-mode source may define helper functions before
    ``step``. ``apply_user_step_code`` exec's the whole module so the
    helper ends up in the same namespace.
    """
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller: BouncingBallController = ws.bouncing_ball_controller()
    source = """
def _no_op(s):
    return s

def step(simulator, dt_s):
    from workbench.app.physics_lab import BouncingBallState
    s = _no_op(simulator.state)
    simulator.update_state(BouncingBallState(
        time_s=s.time_s + dt_s,
        position_m=s.position_m,
        velocity_m_s=0.0,
        bounces=s.bounces,
    ))
"""
    ok = controller.apply_user_step_code(source)
    assert ok is True
    initial_y = controller.simulator.state.position_m
    controller.step_once()
    # Ball is frozen because helper passes state through unmodified.
    assert controller.simulator.state.position_m == pytest.approx(initial_y)


def test_user_step_can_use_import(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The user can import standard-library modules (math) inside the
    Edit-mode source — the exec'd namespace honours imports.
    """
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller: BouncingBallController = ws.bouncing_ball_controller()
    source = """
import math

def step(simulator, dt_s):
    from workbench.app.physics_lab import BouncingBallState
    s = simulator.state
    # Use math.cos to produce a deterministic damped velocity.
    new_v = math.cos(s.time_s) * 0.0  # always zero -> frozen
    simulator.update_state(BouncingBallState(
        time_s=s.time_s + dt_s,
        position_m=s.position_m,
        velocity_m_s=new_v,
        bounces=s.bounces,
    ))
"""
    ok = controller.apply_user_step_code(source)
    assert ok is True
    initial_y = controller.simulator.state.position_m
    controller.step_once()
    assert controller.simulator.state.position_m == pytest.approx(initial_y)


def test_user_step_helper_with_state_outside_step_is_recovered(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Module-level constants survive into ``step``'s closure."""
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    controller = ws.bouncing_ball_controller()
    source = """
HOLD_VELOCITY = 0.0

def step(simulator, dt_s):
    from workbench.app.physics_lab import BouncingBallState
    s = simulator.state
    simulator.update_state(BouncingBallState(
        time_s=s.time_s + dt_s,
        position_m=s.position_m,
        velocity_m_s=HOLD_VELOCITY,
        bounces=s.bounces,
    ))
"""
    assert controller.apply_user_step_code(source) is True
    initial_y = controller.simulator.state.position_m
    controller.step_once()
    assert controller.simulator.state.position_m == pytest.approx(initial_y)
