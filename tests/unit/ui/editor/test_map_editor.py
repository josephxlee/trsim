"""Unit tests for the Map Editor widget (Phase 4.6)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.map_editor import MapEditor, MapTool

pytestmark = pytest.mark.qt


def test_map_editor_default_tool_is_pan(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    assert me.current_tool() is MapTool.PAN
    assert me.tool_button(MapTool.PAN).isChecked() is True


def test_each_tool_button_exists_with_stable_object_name(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    for tool in MapTool:
        btn = me.tool_button(tool)
        assert btn.objectName() == f"MapTool_{tool.value}"


def test_select_tool_emits_signal_and_updates_current(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    received: list[MapTool] = []
    me.tool_changed.connect(received.append)
    me.select_tool(MapTool.FLATTEN)
    assert received == [MapTool.FLATTEN]
    assert me.current_tool() is MapTool.FLATTEN


def test_tool_buttons_form_exclusive_group(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.select_tool(MapTool.SPOT_EDIT)
    me.select_tool(MapTool.ADD_BUILDING)
    checked = [tool for tool in MapTool if me.tool_button(tool).isChecked()]
    assert checked == [MapTool.ADD_BUILDING]


def test_default_layer_visibility_matches_plan_13(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    expected_on = {"Terrain heightmap", "Land/Sea mask", "Buildings"}
    expected_off = {"Coastline polygon", "Source DEM (reference)"}
    for name in expected_on:
        assert me.layer_check(name).isChecked() is True
    for name in expected_off:
        assert me.layer_check(name).isChecked() is False


def test_layer_toggle_emits_signal_with_name_and_state(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    received: list[tuple[str, bool]] = []
    me.layer_visibility_changed.connect(lambda n, s: received.append((n, s)))
    me.layer_check("Coastline polygon").setChecked(True)
    me.layer_check("Buildings").setChecked(False)
    assert received == [("Coastline polygon", True), ("Buildings", False)]


def test_set_history_replaces_list_contents(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.set_history(["10:30 land_paint", "10:32 spot_edit", "10:35 flatten"])
    lst = me.history_list()
    assert lst.count() == 3
    assert lst.item(0).text() == "10:30 land_paint"


def test_action_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    saw: dict[str, int] = {"save": 0, "import": 0, "validate": 0, "reset": 0}
    me.save_requested.connect(lambda: saw.__setitem__("save", saw["save"] + 1))
    me.import_dem_requested.connect(lambda: saw.__setitem__("import", saw["import"] + 1))
    me.validate_requested.connect(lambda: saw.__setitem__("validate", saw["validate"] + 1))
    me.reset_to_source_requested.connect(lambda: saw.__setitem__("reset", saw["reset"] + 1))
    for object_name, key in (
        ("MapEditorSaveBtn", "save"),
        ("MapEditorImportBtn", "import"),
        ("MapEditorValidateBtn", "validate"),
        ("MapEditorResetBtn", "reset"),
    ):
        btn = me.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
        assert saw[key] == 1


def test_set_origin_updates_header_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    me = MapEditor()
    qtbot.addWidget(me)
    me.set_origin("37.5665N, 126.9780E", "egm96")
    label = me.findChild(object, "MapEditorOrigin")
    assert label is not None
    assert "37.5665N" in label.text()  # type: ignore[attr-defined]
    assert "egm96" in label.text()  # type: ignore[attr-defined]


def test_map_editor_page_hosts_real_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.editor.activity_pages import MapEditorPage

    page = MapEditorPage()
    qtbot.addWidget(page)
    assert isinstance(page.map_editor(), MapEditor)
