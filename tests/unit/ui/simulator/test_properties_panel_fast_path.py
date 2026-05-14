"""PropertiesPanel.show_object fast-path tests (P5b polish).

L6 SimulatorPrimaryTargetController calls show_object at 30 Hz with the
same label + key set every tick. The slow path (full form rebuild)
caused visible text flicker + amplified resize reflow cost. The fast
path mutates existing value QLabels in place.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel

from workbench.ui.simulator.panels import PropertiesPanel

pytestmark = pytest.mark.qt


def _panel(qtbot) -> PropertiesPanel:  # type: ignore[no-untyped-def]
    p = PropertiesPanel()
    qtbot.addWidget(p)
    return p


def test_show_object_creates_initial_form(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.show_object("Primary Target", {"Range": "100 m", "Lock": "searching"})
    assert p.context_label().text() == "Primary Target"
    assert p.form_layout().rowCount() == 2


def test_show_object_same_label_same_keys_reuses_widgets(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Same shape -> value QLabel widgets must be reused (no rebuild)."""
    p = _panel(qtbot)
    p.show_object("Primary Target", {"Range": "100 m", "Lock": "searching"})
    # Capture the QLabel instances created on first call.
    first_range_label = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()
    first_lock_label = p.form_layout().itemAt(1, p.form_layout().ItemRole.FieldRole).widget()

    p.show_object("Primary Target", {"Range": "150 m", "Lock": "LOCKED"})
    second_range_label = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()
    second_lock_label = p.form_layout().itemAt(1, p.form_layout().ItemRole.FieldRole).widget()

    # Same QLabel instances (fast path).
    assert first_range_label is second_range_label
    assert first_lock_label is second_lock_label
    # Texts updated.
    assert first_range_label.text() == "150 m"  # type: ignore[attr-defined]
    assert first_lock_label.text() == "LOCKED"  # type: ignore[attr-defined]
    # Still 2 rows — no rebuild.
    assert p.form_layout().rowCount() == 2


def test_show_object_different_label_triggers_rebuild(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Different context label -> full rebuild, new QLabel instances."""
    p = _panel(qtbot)
    p.show_object("Target A", {"x": "1"})
    first = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()

    p.show_object("Target B", {"x": "2"})
    second = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()

    assert first is not second  # Slow path -> new widget.
    assert p.context_label().text() == "Target B"


def test_show_object_different_keys_triggers_rebuild(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Same label but different key set -> full rebuild."""
    p = _panel(qtbot)
    p.show_object("Primary Target", {"Range": "100 m"})
    first = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()

    p.show_object("Primary Target", {"Range": "100 m", "Azimuth": "0 deg"})
    second = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()

    assert first is not second
    assert p.form_layout().rowCount() == 2


def test_clear_resets_cache(qtbot) -> None:  # type: ignore[no-untyped-def]
    """clear() must reset the cache so the next show_object goes through the slow path."""
    p = _panel(qtbot)
    p.show_object("X", {"a": "1"})
    first = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()

    p.clear()
    assert p.context_label().text() == "(nothing selected)"
    assert p.form_layout().rowCount() == 0

    p.show_object("X", {"a": "1"})
    second = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()
    assert first is not second  # New widget after clear.


def test_value_label_is_qlabel_instance(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The value column must be a QLabel so the fast path can call setText."""
    p = _panel(qtbot)
    p.show_object("X", {"a": "1"})
    field = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()
    assert isinstance(field, QLabel)


def test_show_object_60hz_loop_no_grow_in_rowcount(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Simulates the L6 controller's per-tick call — row count stays at 6."""
    p = _panel(qtbot)
    keys = ("Range", "Azimuth", "Elevation", "RCS", "Speed", "Lock")
    for tick in range(60):
        p.show_object(
            "Primary Target",
            {k: f"{k}={tick}" for k in keys},
        )
    assert p.form_layout().rowCount() == 6
    # Final values reflect the last tick.
    range_label = p.form_layout().itemAt(0, p.form_layout().ItemRole.FieldRole).widget()
    assert range_label.text() == "Range=59"  # type: ignore[attr-defined]
