"""Unit tests for the Profiler panel + Reference Timing UI (Phase 4.12)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.profiler_panel import (
    PIPELINE_STAGES,
    PROFILE_REPORT_COLUMNS,
    ProfileReport,
    ProfilerPanel,
    ScaleIndicator,
    TimingBreakdownPanel,
)

pytestmark = pytest.mark.qt


# ---------- TimingBreakdownPanel ----------


def test_timing_breakdown_has_one_bar_per_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = TimingBreakdownPanel()
    qtbot.addWidget(p)
    for stage in PIPELINE_STAGES:
        bar = p.stage_bar(stage)
        assert bar.objectName() == f"TimingBar_{stage}"


def test_timing_breakdown_set_stage_timings_updates_values(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = TimingBreakdownPanel()
    qtbot.addWidget(p)
    timings = {stage: 50.0 + 10 * i for i, stage in enumerate(PIPELINE_STAGES)}
    p.set_stage_timings(timings)
    for stage, expected in timings.items():
        assert p.stage_bar(stage).value() == int(expected)


def test_timing_breakdown_set_stage_timings_rejects_unknown(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = TimingBreakdownPanel()
    qtbot.addWidget(p)
    with pytest.raises(ValueError, match=r"unknown pipeline stage"):
        p.set_stage_timings({"WizardStage": 1.0})


# ---------- ScaleIndicator ----------


def test_scale_indicator_default_is_dash(qtbot) -> None:  # type: ignore[no-untyped-def]
    si = ScaleIndicator()
    qtbot.addWidget(si)
    assert si.value_label().text() == "--"


def test_scale_indicator_formats_value_with_two_decimals(qtbot) -> None:  # type: ignore[no-untyped-def]
    si = ScaleIndicator()
    qtbot.addWidget(si)
    si.set_scale(1.23)
    assert si.value_label().text() == "1.23x"


@pytest.mark.parametrize(
    ("scale", "expect_color_word"),
    [
        (1.0, ""),  # default colour, no color attribute
        (0.7, "b87000"),  # yellow band
        (0.3, "b00020"),  # red band
    ],
)
def test_scale_indicator_color_bands(qtbot, scale, expect_color_word) -> None:  # type: ignore[no-untyped-def]
    si = ScaleIndicator()
    qtbot.addWidget(si)
    si.set_scale(scale)
    style = si.value_label().styleSheet()
    if expect_color_word:
        assert expect_color_word in style
    else:
        assert "color:" not in style


def test_scale_indicator_none_clears_value(qtbot) -> None:  # type: ignore[no-untyped-def]
    si = ScaleIndicator()
    qtbot.addWidget(si)
    si.set_scale(0.5)
    si.set_scale(None)
    assert si.value_label().text() == "--"


# ---------- ProfileReport ----------


def test_profile_report_columns_match_constant(qtbot) -> None:  # type: ignore[no-untyped-def]
    pr = ProfileReport()
    qtbot.addWidget(pr)
    headers = [pr.table().horizontalHeaderItem(i).text() for i in range(pr.table().columnCount())]
    assert headers == list(PROFILE_REPORT_COLUMNS)


def test_profile_report_set_rows_populates_table(qtbot) -> None:  # type: ignore[no-untyped-def]
    pr = ProfileReport()
    qtbot.addWidget(pr)
    pr.set_rows(
        [
            ("Detector", 12.3, 11.5, 18.0, 22.7),
            ("Tracker", 4.1, 4.0, 6.2, 7.8),
        ]
    )
    table = pr.table()
    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "Detector"
    assert table.item(0, 1).text() == "12.3"
    assert table.item(1, 4).text() == "7.8"


def test_profile_report_clear_resets_to_zero_rows(qtbot) -> None:  # type: ignore[no-untyped-def]
    pr = ProfileReport()
    qtbot.addWidget(pr)
    pr.set_rows([("Tracker", 4.0, 4.0, 5.0, 6.0)])
    pr.clear()
    assert pr.table().rowCount() == 0


# ---------- ProfilerPanel composite ----------


def test_profiler_panel_mounts_subwidgets(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ProfilerPanel()
    qtbot.addWidget(p)
    assert isinstance(p.timing_breakdown(), TimingBreakdownPanel)
    assert isinstance(p.profile_report(), ProfileReport)
    assert isinstance(p.scale_indicator(), ScaleIndicator)


def test_profiler_panel_action_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = ProfilerPanel()
    qtbot.addWidget(p)
    saw = {"run": 0, "ref": 0}
    p.run_profile_requested.connect(lambda: saw.__setitem__("run", saw["run"] + 1))
    p.set_reference_requested.connect(lambda: saw.__setitem__("ref", saw["ref"] + 1))
    for object_name in ("ProfilerRunBtn", "ProfilerSetReferenceBtn"):
        btn = p.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert saw == {"run": 1, "ref": 1}


def test_simulator_workspace_mounts_profiler_tab(qtbot) -> None:  # type: ignore[no-untyped-def]
    from workbench.ui.simulator.workspace import SimulatorWorkspace

    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    tabs = ws.bottom_tabs()
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    assert titles == ["Run", "Stage I/O", "Profiler"]
    assert isinstance(ws.profiler_panel(), ProfilerPanel)
