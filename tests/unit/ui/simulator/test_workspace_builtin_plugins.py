"""Built-in PluginManager population tests (Phase 4 L2)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.builtin_pipeline_plugins import BUILTIN_SIMULATOR_PLUGINS
from workbench.ui.simulator.panels.plugin_manager_panel import PIPELINE_STAGES
from workbench.ui.simulator.workspace import SimulatorWorkspace

pytestmark = pytest.mark.qt


def test_workspace_populates_plugin_manager(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The PluginManager panel ships with the curated baseline filled in."""
    ws = SimulatorWorkspace(autostart_run_timer=False)
    qtbot.addWidget(ws)
    panel = ws.plugin_manager_panel()
    for stage, expected_names in BUILTIN_SIMULATOR_PLUGINS.items():
        section = panel.stage_section(stage)
        list_widget = section.list_widget()
        rendered = [list_widget.item(i).text() for i in range(list_widget.count())]
        assert tuple(rendered) == expected_names


def test_builtin_plugins_covers_every_pipeline_stage() -> None:
    """No stage is missing from the curated registry — every section
    has a key, even if its tuple is empty (Predictor / Classifier)."""
    assert set(BUILTIN_SIMULATOR_PLUGINS) == set(PIPELINE_STAGES)


def test_builtin_plugins_no_duplicate_names_within_stage() -> None:
    """Each stage's plug-in tuple uses unique display labels."""
    for stage, names in BUILTIN_SIMULATOR_PLUGINS.items():
        assert len(names) == len(set(names)), f"duplicates in {stage}: {names!r}"


def test_workspace_detector_baseline_includes_cfar_variants(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """Smoke regression — both CA-CFAR and OS-CFAR are listed."""
    ws = SimulatorWorkspace(autostart_run_timer=False)
    qtbot.addWidget(ws)
    section = ws.plugin_manager_panel().stage_section("Detector")
    list_widget = section.list_widget()
    rendered = [list_widget.item(i).text() for i in range(list_widget.count())]
    assert any("CA-CFAR" in name for name in rendered)
    assert any("OS-CFAR" in name for name in rendered)


def test_workspace_predictor_classifier_stay_empty(
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """Predictor + Classifier ship without baseline plug-ins — the
    Library starts blank until a DLC plug-in fills them."""
    ws = SimulatorWorkspace(autostart_run_timer=False)
    qtbot.addWidget(ws)
    for stage in ("Predictor", "Classifier"):
        section = ws.plugin_manager_panel().stage_section(stage)
        assert section.list_widget().count() == 0
