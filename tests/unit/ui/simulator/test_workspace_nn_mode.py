"""Simulator workspace NN-mode mount tests (MVP UI wire-up)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.ui.nn_training import NNTrainingController, TrainingPanel
from workbench.ui.simulator.nn_mode import Step1DatasetPanel, Step2EvalPanel
from workbench.ui.simulator.nn_mode.step1_controller import NNStep1Controller
from workbench.ui.simulator.nn_mode.step2_controller import NNStep2Controller
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def test_nn_panels_are_instantiated(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Phase 4.11 panels finally live inside the Simulator workspace."""
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    assert isinstance(ws.nn_step1_panel(), Step1DatasetPanel)
    assert isinstance(ws.nn_step2_panel(), Step2EvalPanel)
    assert isinstance(ws.nn_training_panel(), TrainingPanel)


def test_nn_controllers_are_attached_to_their_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    s1c = ws.nn_step1_controller()
    s2c = ws.nn_step2_controller()
    tc = ws.nn_training_controller()
    assert isinstance(s1c, NNStep1Controller)
    assert isinstance(s2c, NNStep2Controller)
    assert isinstance(tc, NNTrainingController)
    assert s1c.panel is ws.nn_step1_panel()
    assert s2c.panel is ws.nn_step2_panel()
    assert tc.panel is ws.nn_training_panel()


def test_nn_panels_occupy_three_bottom_tabs(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    tabs = ws.bottom_tabs()
    # Built-in 3 runtime tabs (0..2) + 3 NN-mode tabs (3..5).
    assert tabs.widget(3) is ws.nn_step1_panel()
    assert tabs.widget(4) is ws.nn_step2_panel()
    assert tabs.widget(5) is ws.nn_training_panel()


def test_nn_step1_build_signal_drives_controller(qtbot, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """End-to-end: clicking Build on the mounted Step 1 writes the HDF5.

    Proves the panel -> controller wiring survived the mount — the
    controller listens for the panel's ``build_requested`` signal and
    routes to the real :class:`DatasetBuilder` / :class:`PipelineRunner`.
    """
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    panel = ws.nn_step1_panel()
    out = tmp_path / "demo.h5"
    panel.frames_edit().setText("3")
    panel.output_edit().setText(str(out))
    panel.build_requested.emit()
    assert out.is_file()
    assert "done:" in panel.status_label().text()


def test_nn_training_panel_object_name_is_set(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Smoke check: the mounted Training panel preserves its objectName."""
    ws = SimulatorWorkspace()
    qtbot.addWidget(ws)
    tp = ws.nn_training_panel()
    assert tp.objectName() == "NNTrainingPanel"
    assert tp.layout() is not None
