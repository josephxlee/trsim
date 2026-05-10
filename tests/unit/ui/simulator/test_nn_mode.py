"""Unit tests for NN Mode panels (Phase 4.11)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.nn_mode import (
    ERROR_CATEGORIES,
    Step1DatasetPanel,
    Step2EvalPanel,
)

pytestmark = pytest.mark.qt


# ---------- Step 1 Dataset Builder ----------


def test_step1_default_inputs(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step1DatasetPanel()
    qtbot.addWidget(p)
    assert p.scenario_combo().count() == 1
    assert p.frames_edit().text() == "200"
    assert "dataset_v1.h5" in p.output_edit().text()


def test_step1_set_scenarios_replaces_options(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step1DatasetPanel()
    qtbot.addWidget(p)
    p.set_scenarios(["A_Base", "B_Conflict"])
    items = [p.scenario_combo().itemText(i) for i in range(p.scenario_combo().count())]
    assert items == ["(none)", "A_Base", "B_Conflict"]


def test_step1_set_status_and_log(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step1DatasetPanel()
    qtbot.addWidget(p)
    p.set_status("running")
    assert p.status_label().text() == "Status: running"
    p.append_log("frame 1/200")
    p.append_log("frame 200/200")
    assert p.log_list().count() == 2


def test_step1_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step1DatasetPanel()
    qtbot.addWidget(p)
    saw = {"build": 0, "cancel": 0}
    p.build_requested.connect(lambda: saw.__setitem__("build", saw["build"] + 1))
    p.cancel_requested.connect(lambda: saw.__setitem__("cancel", saw["cancel"] + 1))
    for object_name in ("NNStep1BuildBtn", "NNStep1CancelBtn"):
        btn = p.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert saw == {"build": 1, "cancel": 1}


# ---------- Step 2 Evaluation ----------


def test_step2_table_has_one_row_per_error_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step2EvalPanel()
    qtbot.addWidget(p)
    table = p.error_table()
    assert table.rowCount() == len(ERROR_CATEGORIES)
    for i, cat in enumerate(ERROR_CATEGORIES):
        assert table.item(i, 0).text() == cat


def test_step2_set_error_metrics_updates_row(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step2EvalPanel()
    qtbot.addWidget(p)
    p.set_error_metrics("Tracker", rmse=0.123, bias=-0.456)
    table = p.error_table()
    idx = ERROR_CATEGORIES.index("Tracker")
    assert table.item(idx, 1).text() == "0.123"
    assert "-0.456" in table.item(idx, 2).text()


def test_step2_set_error_metrics_rejects_unknown(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step2EvalPanel()
    qtbot.addWidget(p)
    with pytest.raises(ValueError, match=r"unknown error category"):
        p.set_error_metrics("Wizard", rmse=1.0, bias=0.0)


def test_step2_set_datasets_and_plugins(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step2EvalPanel()
    qtbot.addWidget(p)
    p.set_datasets(["pairing_v1.h5", "tracker_v2.h5"])
    p.set_plugins(["my_pairing_nn", "my_tracker_nn"])
    assert p.dataset_combo().count() == 3
    assert p.plugin_combo().count() == 3


def test_step2_buttons_emit_signals(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = Step2EvalPanel()
    qtbot.addWidget(p)
    saw = {"run": 0, "export": 0}
    p.run_eval_requested.connect(lambda: saw.__setitem__("run", saw["run"] + 1))
    p.export_report_requested.connect(lambda: saw.__setitem__("export", saw["export"] + 1))
    for object_name in ("NNStep2RunBtn", "NNStep2ExportBtn"):
        btn = p.findChild(object, object_name)
        assert btn is not None
        btn.click()  # type: ignore[attr-defined]
    assert saw == {"run": 1, "export": 1}
