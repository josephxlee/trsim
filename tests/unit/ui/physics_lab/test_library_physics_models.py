"""LibraryWidget physics-model registration tests (Phase 9 H1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

from workbench.app.physics_lab.models import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
)
from workbench.sdk.protocols import PhysicsModelProtocol
from workbench.ui.physics_lab import LibraryWidget

pytestmark = pytest.mark.qt


def _builtins() -> tuple[PhysicsModelProtocol, ...]:
    return (GravityOnlyModel(), BouncingBallModel(), FreeSpaceLossModel())


# ---------------------------------------------------------------------
# Default placeholder behaviour
# ---------------------------------------------------------------------


def test_default_models_show_two_placeholders(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    # Pre-H1 contract — empty registry leaves the legacy placeholders.
    assert lib.models_category().childCount() == 2
    assert lib.physics_model_for("Gravity (always on)") is None


def test_set_physics_models_empty_falls_back_to_placeholders(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models(())
    assert lib.models_category().childCount() == 2
    labels = {lib.models_category().child(i).text(0) for i in range(2)}
    assert labels == {"Gravity (always on)", "Air Drag (toggle)"}


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


def test_set_physics_models_replaces_subtree(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models(_builtins())
    assert lib.models_category().childCount() == 3
    leaves = [lib.models_category().child(i).text(0) for i in range(3)]
    # Order preserved.
    assert "Gravity Only (analytic)" in leaves[0]
    assert "Bouncing Ball" in leaves[1]
    assert "Free-Space Path Loss" in leaves[2]


def test_label_format_includes_category(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models((GravityOnlyModel(),))
    leaf = lib.models_category().child(0).text(0)
    assert "Gravity Only (analytic)" in leaf
    assert "(dynamics)" in leaf


def test_physics_model_for_round_trip(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    gravity = GravityOnlyModel()
    lib.set_physics_models((gravity,))
    label = lib.models_category().child(0).text(0)
    assert lib.physics_model_for(label) is gravity


def test_physics_model_for_returns_none_for_unknown_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models(_builtins())
    assert lib.physics_model_for("non-existent label") is None
    # Tests / Saved / Measured / Papers labels also resolve to None
    # (Models registry is independent of those four mappings).
    assert lib.physics_model_for("Bouncing Ball Demo") is None


# ---------------------------------------------------------------------
# Signal emission on selection
# ---------------------------------------------------------------------


def test_physics_model_selected_signal_fires(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    bb = BouncingBallModel()
    lib.set_physics_models((bb,))
    received: list[PhysicsModelProtocol] = []
    lib.physics_model_selected.connect(received.append)
    label = lib.models_category().child(0).text(0)
    assert lib.select_label(label) is True
    assert received == [bb]


def test_selecting_non_model_does_not_fire_physics_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models(_builtins())
    received: list[PhysicsModelProtocol] = []
    lib.physics_model_selected.connect(received.append)
    lib.select_label("Bouncing Ball Demo")
    assert received == []


# ---------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------


def test_duplicate_names_rejected(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    with pytest.raises(ValueError, match=r"Duplicate physics-model names"):
        lib.set_physics_models((GravityOnlyModel(), GravityOnlyModel()))


def test_replacing_registry_clears_previous_lookup(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    g1 = GravityOnlyModel()
    lib.set_physics_models((g1,))
    label_first = lib.models_category().child(0).text(0)
    assert lib.physics_model_for(label_first) is g1
    # Replace with a different list.
    lib.set_physics_models((BouncingBallModel(),))
    assert lib.physics_model_for(label_first) is None
    new_label = lib.models_category().child(0).text(0)
    assert "Bouncing Ball" in new_label


def test_set_physics_models_accepts_any_iterable(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    # generator
    lib.set_physics_models(m for m in _builtins())
    assert lib.models_category().childCount() == 3


def test_leaf_labels_after_set_includes_models(qtbot) -> None:  # type: ignore[no-untyped-def]
    lib = LibraryWidget()
    qtbot.addWidget(lib)  # type: ignore[attr-defined]
    lib.set_physics_models((GravityOnlyModel(),))
    labels = lib.leaf_labels()
    assert any("Gravity Only" in lab for lab in labels)
