"""TargetsEditorController validation tests."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.targets_editor import TargetsEditor, TargetsEditorController

pytestmark = pytest.mark.qt


def _build(qtbot) -> tuple[TargetsEditor, TargetsEditorController]:  # type: ignore[no-untyped-def]
    editor = TargetsEditor()
    qtbot.addWidget(editor)
    controller = TargetsEditorController(editor=editor)
    return editor, controller


def _set_form(
    editor: TargetsEditor,
    *,
    name: str = "fighter_a",
    motion: str = "AIRCRAFT",
    rcs: str = "1.0",
    scatterers: str = "3",
) -> None:
    editor.name_edit().setText(name)
    editor.motion_combo().setCurrentText(motion)
    editor.rcs_edit().setText(rcs)
    editor.scatterers_edit().setText(scatterers)


def test_validation_ok_when_all_fields_valid(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor)
    status, messages = controller.run_validation()
    assert status == "OK"
    assert any("fighter_a" in m for m in messages)
    assert any("AIRCRAFT" in m for m in messages)


def test_validation_warn_when_name_is_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Empty / default '(unnamed)' is a soft warning - the rest of the
    form is numerically valid so the controller stays at WARN."""
    editor, controller = _build(qtbot)
    _set_form(editor, name="(unnamed)")
    status, _messages = controller.run_validation()
    assert status == "WARN"


def test_validation_warn_when_name_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor, name="")
    status, _messages = controller.run_validation()
    assert status == "WARN"


def test_validation_error_when_rcs_not_float(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor, rcs="not_a_number")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("RCS" in m for m in messages)


def test_validation_error_when_rcs_zero_or_negative(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor, rcs="0")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("RCS" in m for m in messages)


def test_validation_error_when_scatterers_not_int(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor, scatterers="three")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("Scatterer" in m for m in messages)


def test_validation_error_when_scatterers_zero(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_form(editor, scatterers="0")
    status, messages = controller.run_validation()
    assert status == "ERROR"
    assert any("Scatterer" in m for m in messages)


def test_validate_signal_triggers_controller_and_updates_panel(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    editor, _controller = _build(qtbot)
    _set_form(editor)
    editor.validate_requested.emit()
    assert "OK" in editor.validation_label().text()
