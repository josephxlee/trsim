"""Unit tests for the six Simulator panels (Phase 4.9)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.panels import (
    FFTPanel,
    PluginManagerPanel,
    PropertiesPanel,
    RangeDopplerPanel,
    RunPanel,
    StageIOPanel,
)
from workbench.ui.simulator.panels.plugin_manager_panel import PIPELINE_STAGES
from workbench.ui.simulator.panels.stage_io_panel import PIPELINE_STAGE_BOXES

pytestmark = pytest.mark.qt


# ---------- FFT panel ----------


def test_fft_panel_set_frame_and_peak_counts(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = FFTPanel()
    qtbot.addWidget(p)
    p.set_frame(127)
    p.set_peak_counts(4, 3)
    assert "127" in p.frame_label().text()
    assert "4 up / 3 down" in p.peaks_label().text()


# ---------- Range-Doppler panel ----------


def test_range_doppler_panel_set_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = RangeDopplerPanel()
    qtbot.addWidget(p)
    p.set_frame(42)
    assert "42" in p.frame_label().text()


# ---------- Run panel ----------


def test_run_panel_set_history_and_metrics(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = RunPanel()
    qtbot.addWidget(p)
    p.set_history(["run_0042", "run_0041", "run_0040"])
    assert p.history_list().count() == 3
    p.set_primary_metrics(
        lock="locked since frame 18",
        continuity=0.94,
        id_switches=0,
        range_rmse_m=3.2,
        az_rmse_deg=0.12,
        positioner_lag_deg=0.4,
    )
    assert "0.94" in p.continuity_label().text()
    assert "locked since frame 18" in p.lock_label().text()


# ---------- Properties panel ----------


def test_properties_panel_show_object_then_clear(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PropertiesPanel()
    qtbot.addWidget(p)
    p.show_object("Target #1", {"Range": "12.4 km", "RCS": "-8.2 dBsm"})
    assert p.context_label().text() == "Target #1"
    assert p.form_layout().rowCount() == 2
    p.clear()
    assert p.context_label().text() == "(nothing selected)"
    assert p.form_layout().rowCount() == 0


# ---------- Plugin Manager panel ----------


def test_plugin_manager_panel_lists_every_pipeline_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PluginManagerPanel()
    qtbot.addWidget(p)
    for stage in PIPELINE_STAGES:
        section = p.stage_section(stage)
        assert section.objectName() == f"PluginStage_{stage}"


def test_plugin_manager_set_stage_plugins(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PluginManagerPanel()
    qtbot.addWidget(p)
    p.set_stage_plugins("Detector", ["default_cfar", "my_cfar_v2"])
    assert p.stage_section("Detector").list_widget().count() == 2


def test_plugin_manager_set_stage_plugins_rejects_unknown_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PluginManagerPanel()
    qtbot.addWidget(p)
    with pytest.raises(ValueError, match=r"unknown pipeline stage"):
        p.set_stage_plugins("Sorcerer", [])


def test_plugin_manager_action_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = PluginManagerPanel()
    qtbot.addWidget(p)
    saw = {"add": 0, "reload": 0}
    p.add_plugin_requested.connect(lambda: saw.__setitem__("add", saw["add"] + 1))
    p.reload_all_requested.connect(lambda: saw.__setitem__("reload", saw["reload"] + 1))
    for object_name in ("PluginManagerAddBtn", "PluginManagerReloadBtn"):
        btn = p.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert saw == {"add": 1, "reload": 1}


# ---------- Stage I/O panel ----------


def test_stage_io_panel_has_one_box_per_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = StageIOPanel()
    qtbot.addWidget(p)
    for stage in PIPELINE_STAGE_BOXES:
        box = p.stage_box(stage)
        assert box.objectName() == f"StageIOBox_{stage}"


def test_stage_io_set_io_updates_in_and_out_labels(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = StageIOPanel()
    qtbot.addWidget(p)
    p.set_stage_io("Receiver", "3 reflections", "FFTSpectrum")
    box = p.stage_box("Receiver")
    assert "3 reflections" in box.in_label().text()
    assert "FFTSpectrum" in box.out_label().text()


def test_stage_io_record_button_toggles_text_and_emits_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = StageIOPanel()
    qtbot.addWidget(p)
    received: list[bool] = []
    p.record_toggled.connect(received.append)
    p.record_button().setChecked(True)
    assert received == [True]
    assert "ON" in p.record_button().text()
    p.record_button().setChecked(False)
    assert received == [True, False]
    assert "OFF" in p.record_button().text()


def test_stage_io_set_stage_io_rejects_unknown_stage(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = StageIOPanel()
    qtbot.addWidget(p)
    with pytest.raises(ValueError, match=r"unknown stage"):
        p.set_stage_io("Wizard", "x", "y")
