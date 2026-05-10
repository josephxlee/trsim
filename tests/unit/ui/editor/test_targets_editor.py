"""Unit tests for the Targets Editor widget (Phase 4.8)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.targets_editor import MOTION_KINDS, TargetsEditor

pytestmark = pytest.mark.qt


def test_default_motion_kind_is_first_entry(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    assert te.current_motion_kind() == MOTION_KINDS[0]
    assert te.motion_combo().count() == len(MOTION_KINDS)


def test_set_motion_kind_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    received: list[str] = []
    te.motion_kind_changed.connect(received.append)
    te.set_motion_kind("AIRCRAFT")
    assert received == ["AIRCRAFT"]
    assert te.current_motion_kind() == "AIRCRAFT"


def test_set_motion_kind_rejects_unknown(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    with pytest.raises(ValueError, match=r"unknown motion kind"):
        te.set_motion_kind("WIZARDING")


def test_set_waypoint_count_pluralises_correctly(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    te.set_waypoint_count(0)
    assert te.waypoint_label().text() == "0 waypoints"
    te.set_waypoint_count(1)
    assert te.waypoint_label().text() == "1 waypoint"
    te.set_waypoint_count(7)
    assert te.waypoint_label().text() == "7 waypoints"


def test_csv_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    saw = {"import": 0, "export": 0}
    te.csv_import_requested.connect(lambda: saw.__setitem__("import", saw["import"] + 1))
    te.csv_export_requested.connect(lambda: saw.__setitem__("export", saw["export"] + 1))
    for object_name in ("TargetsImportBtn", "TargetsExportBtn"):
        btn = te.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert saw == {"import": 1, "export": 1}


def test_set_validation_status_updates_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    te = TargetsEditor()
    qtbot.addWidget(te)
    te.set_validation_status("OK")
    assert te.validation_label().text() == "Status: OK"


def test_targets_editor_page_hosts_real_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activity_pages import TargetsEditorPage

    page = TargetsEditorPage()
    qtbot.addWidget(page)
    assert isinstance(page.targets_editor(), TargetsEditor)
