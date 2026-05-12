"""LibraryWidget category tests (PL-9.1f, plan/19 § 19.5.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.domain.physics_lab import (
    SavedExperiment,
    TimeMode,
    write_saved_experiment,
)
from workbench.ui.physics_lab import LibraryWidget, PhysicsLabWorkspace

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# LibraryWidget category structure
# ---------------------------------------------------------------------


def test_library_widget_has_three_top_level_categories(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    tree = lib.tree_widget()
    assert tree.topLevelItemCount() == 3
    top_texts = {tree.topLevelItem(i).text(0) for i in range(3)}
    assert top_texts == {
        LibraryWidget.CATEGORY_TESTS,
        LibraryWidget.CATEGORY_MODELS,
        LibraryWidget.CATEGORY_SAVED,
    }


def test_models_category_has_two_default_models(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.models_category().childCount() == 2


def test_saved_category_starts_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.saved_category().childCount() == 0


def test_set_saved_experiments_populates_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    experiments = (
        SavedExperiment(experiment_id="alpha"),
        SavedExperiment(experiment_id="beta", mode=TimeMode.COMPARE),
    )
    lib.set_saved_experiments(experiments)
    assert lib.saved_category().childCount() == 2
    labels = lib.leaf_labels()
    assert any("alpha" in lab for lab in labels)
    assert any("beta" in lab and "compare" in lab for lab in labels)


def test_set_saved_experiments_replaces_previous_entries(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_saved_experiments((SavedExperiment(experiment_id="old"),))
    lib.set_saved_experiments((SavedExperiment(experiment_id="new"),))
    assert lib.saved_category().childCount() == 1
    assert lib.saved_category().child(0).text(0).startswith("new")


def test_experiment_for_resolves_label_to_dataclass(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    exp = SavedExperiment(experiment_id="alpha")
    lib.set_saved_experiments((exp,))
    label = lib.saved_category().child(0).text(0)
    assert lib.experiment_for(label) == exp


def test_select_label_finds_leaves_across_categories(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    assert lib.select_label(LibraryWidget.BOUNCING_BALL_ROW) is True
    assert lib.current_label() == LibraryWidget.BOUNCING_BALL_ROW
    assert lib.select_label("not-a-row") is False


def test_demo_selected_signal_fires_on_leaf_only(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    received: list[str] = []
    lib.demo_selected.connect(received.append)
    # Click the Tests category itself (top-level) — no signal.
    lib.tree_widget().setCurrentItem(lib.tests_category())
    # Click an actual leaf.
    assert lib.select_label(LibraryWidget.BOUNCING_BALL_ROW) is True
    assert LibraryWidget.BOUNCING_BALL_ROW in received


def test_experiment_selected_signal_fires_on_saved_leaf(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    exp = SavedExperiment(experiment_id="alpha")
    lib.set_saved_experiments((exp,))
    received: list[SavedExperiment] = []
    lib.experiment_selected.connect(received.append)
    label = lib.saved_category().child(0).text(0)
    lib.select_label(label)
    assert received == [exp]


def test_save_button_emits_save_requested(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    seen: list[bool] = []
    lib.save_requested.connect(lambda: seen.append(True))
    lib.save_button().click()
    assert seen == [True]


# ---------------------------------------------------------------------
# Workspace save / load
# ---------------------------------------------------------------------


def test_workspace_save_current_experiment_writes_toml(
    tmp_path: Path,
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, experiment_root=tmp_path)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    exp = ws.save_current_experiment("my-exp")
    assert exp.experiment_id == "my-exp"
    assert (tmp_path / "my-exp.toml").is_file()
    # Library now lists it.
    assert ws.library_panel().saved_category().childCount() == 1


def test_workspace_save_without_root_raises(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    with pytest.raises(RuntimeError, match=r"experiment_root not configured"):
        ws.save_current_experiment("x")


def test_workspace_refresh_saved_experiments_picks_up_external_files(
    tmp_path: Path,
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """An experiment dropped into ``experiment_root`` by an external
    tool shows up after :meth:`refresh_saved_experiments`.
    """
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, experiment_root=tmp_path)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    write_saved_experiment(
        tmp_path / "external.toml",
        SavedExperiment(experiment_id="external"),
    )
    ws.refresh_saved_experiments()
    assert ws.library_panel().saved_category().childCount() == 1


def test_workspace_load_experiment_applies_parameters_and_mode(
    tmp_path: Path,
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, experiment_root=tmp_path)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    exp = SavedExperiment(
        experiment_id="snapshot",
        gravity_m_s2=4.0,
        restitution=0.2,
        initial_height_m=20.0,
        initial_velocity_m_s=5.0,
        mode=TimeMode.STATIC,
    )
    ws.load_experiment(exp)
    sim = ws.bouncing_ball_controller().simulator
    assert sim.gravity_m_s2 == pytest.approx(4.0)
    assert sim.restitution == pytest.approx(0.2)
    assert sim.initial_height_m == pytest.approx(20.0)
    assert sim.initial_velocity_m_s == pytest.approx(5.0)
    assert ws.bouncing_ball_controller().mode == TimeMode.STATIC


def test_workspace_construction_with_existing_experiments_loads_library(
    tmp_path: Path,
    qtbot,
) -> None:  # type: ignore[no-untyped-def]
    """Constructing a workspace with an ``experiment_root`` that already
    contains a TOML file populates the Saved Experiments sub-tree.
    """
    write_saved_experiment(
        tmp_path / "preexisting.toml",
        SavedExperiment(experiment_id="preexisting"),
    )
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, experiment_root=tmp_path)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.library_panel().saved_category().childCount() == 1
