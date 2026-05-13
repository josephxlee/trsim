"""PhysicsLabWorkspace physics_models integration (Phase 9 H2)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.physics_lab import (
    BouncingBallModel,
    GravityOnlyModel,
    unregister_all_physics_models,
)
from workbench.ui.physics_lab import PhysicsLabWorkspace

pytestmark = pytest.mark.qt


@pytest.fixture(autouse=True)
def _isolate_registry() -> None:
    unregister_all_physics_models()


def test_default_workspace_loads_three_builtins(qtbot) -> None:  # type: ignore[no-untyped-def]
    """``physics_models=None`` (default) → built-in trio populated."""
    ws = PhysicsLabWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    models = ws.physics_models()
    assert len(models) == 3
    # Library Models category mirrors the count.
    assert ws.library_panel().models_category().childCount() == 3


def test_explicit_empty_falls_back_to_placeholders(qtbot) -> None:  # type: ignore[no-untyped-def]
    """An explicit ``()`` produces the legacy 2-row placeholder."""
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, physics_models=())
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.physics_models() == ()
    assert ws.library_panel().models_category().childCount() == 2


def test_explicit_subset_populates(qtbot) -> None:  # type: ignore[no-untyped-def]
    gravity = GravityOnlyModel()
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, physics_models=(gravity,))
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.physics_models() == (gravity,)
    assert ws.library_panel().models_category().childCount() == 1
    leaf = ws.library_panel().models_category().child(0).text(0)
    assert "Gravity Only" in leaf


def test_set_physics_models_replaces_after_construct(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, physics_models=())
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    bb = BouncingBallModel()
    ws.set_physics_models((bb,))
    assert ws.physics_models() == (bb,)
    assert ws.library_panel().models_category().childCount() == 1


def test_refresh_physics_models_pulls_from_default_registry(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, physics_models=())
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    assert ws.physics_models() == ()
    ws.refresh_physics_models()
    # After refresh, the workspace pulls all built-ins (3).
    assert len(ws.physics_models()) == 3


def test_library_signal_round_trips_through_workspace(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Clicking the Models leaf fires the LibraryWidget signal even when the
    workspace owns the registry — confirms no double-wiring breakage."""
    gravity = GravityOnlyModel()
    ws = PhysicsLabWorkspace(enable_3d_viewer=False, physics_models=(gravity,))
    qtbot.addWidget(ws)  # type: ignore[attr-defined]
    received: list[object] = []
    ws.library_panel().physics_model_selected.connect(received.append)
    label = ws.library_panel().models_category().child(0).text(0)
    assert ws.library_panel().select_label(label) is True
    assert received == [gravity]
