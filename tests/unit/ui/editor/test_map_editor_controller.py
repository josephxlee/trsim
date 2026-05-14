"""MapEditorController validation tests."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.simulation_domain import OutsideEnvironment, SimulationDomain
from workbench.ui.editor.map_editor import MapEditor, MapEditorController

pytestmark = pytest.mark.qt


def _build(qtbot) -> tuple[MapEditor, MapEditorController]:  # type: ignore[no-untyped-def]
    editor = MapEditor()
    qtbot.addWidget(editor)
    controller = MapEditorController(editor=editor, parent=editor)
    return editor, controller


def _set_valid_domain(editor: MapEditor) -> None:
    panel = editor.domain_panel()
    panel.set_domain(
        SimulationDomain(
            bounds_east=(0.0, 1000.0),
            bounds_north=(0.0, 1000.0),
            ceiling_alt_m=2000.0,
            floor_alt_m=-100.0,
        )
    )


def test_validation_warn_when_origin_unset_but_domain_valid(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    _set_valid_domain(editor)
    status, messages = controller.run_validation()
    assert status == "WARN"
    assert any("Origin" in m for m in messages)


def test_validation_ok_when_origin_and_domain_valid(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    editor.set_origin("37.5665N, 126.9780E", "egm96")
    _set_valid_domain(editor)
    status, messages = controller.run_validation()
    assert status == "OK"
    assert any("origin set" in m for m in messages)


def test_validation_status_label_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    editor = MapEditor()
    qtbot.addWidget(editor)
    assert editor.validation_status_label().text() == "Status: not yet validated"


def test_validate_signal_routes_through_controller(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    editor, _controller = _build(qtbot)
    editor.set_origin("37.5665N, 126.9780E", "egm96")
    _set_valid_domain(editor)
    editor.validate_requested.emit()
    assert "OK" in editor.validation_status_label().text()


def test_domain_change_after_ok_demotes_status_to_not_validated(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """User reaches OK, then edits the domain — the status label must
    not falsely keep the OK badge."""
    editor, controller = _build(qtbot)
    editor.set_origin("37.5N, 127.0E", "egm96")
    _set_valid_domain(editor)
    controller.run_validation()
    assert "OK" in editor.validation_status_label().text()
    # Domain edit -> demoted to "not yet validated".
    editor.domain_changed.emit(
        SimulationDomain(
            bounds_east=(0.0, 500.0),
            bounds_north=(0.0, 500.0),
            ceiling_alt_m=1500.0,
            floor_alt_m=-50.0,
        )
    )
    assert editor.validation_status_label().text() == "Status: not yet validated"


def test_outside_environment_change_demotes_status(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    editor, controller = _build(qtbot)
    editor.set_origin("37.5N, 127.0E", "egm96")
    _set_valid_domain(editor)
    controller.run_validation()
    editor.outside_environment_changed.emit(OutsideEnvironment.OPEN_SEA)
    assert editor.validation_status_label().text() == "Status: not yet validated"
