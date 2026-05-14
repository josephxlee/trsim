"""ScopePOVPanel L6 cross-hair canvas tests."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")
pytest.importorskip("pyqtgraph")

import pyqtgraph as pg

from workbench.ui.simulator.panels import ScopePOVPanel

pytestmark = pytest.mark.qt


def _panel(qtbot) -> ScopePOVPanel:  # type: ignore[no-untyped-def]
    p = ScopePOVPanel()
    qtbot.addWidget(p)
    return p


def test_panel_mounts_pyqtgraph_plot_widget(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert isinstance(p.plot_widget(), pg.PlotWidget)
    assert p.plot_widget().objectName() == "ScopePOVPlot"


def test_target_marker_starts_empty(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    xs, ys = p.target_marker().getData()
    assert len(xs) == 0
    assert len(ys) == 0
    assert p.is_target_visible() is False
    assert p.hint_label().isVisibleTo(p) is True


def test_set_target_norm_moves_marker(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_target_norm(0.25, -0.5)
    xs, ys = p.target_marker().getData()
    assert list(xs) == pytest.approx([0.25])
    assert list(ys) == pytest.approx([-0.5])
    assert p.is_target_visible() is True


def test_set_target_norm_clamps_to_unit_box(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_target_norm(2.0, -3.0)
    xs, ys = p.target_marker().getData()
    assert list(xs) == pytest.approx([1.0])
    assert list(ys) == pytest.approx([-1.0])


def test_first_set_target_hides_hint_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert p.hint_label().isHidden() is False
    p.set_target_norm(0.0, 0.0)
    assert p.hint_label().isHidden() is True


def test_clear_target_restores_hint_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_target_norm(0.0, 0.0)
    p.clear_target()
    xs, _ys = p.target_marker().getData()
    assert len(xs) == 0
    assert p.is_target_visible() is False
    assert p.hint_label().isHidden() is False


def test_set_pointing_still_updates_az_readout(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Pre-L6 AZ readout API still works."""
    p = _panel(qtbot)
    p.set_pointing(actual_az_deg=12.3, commanded_az_deg=12.0)
    txt = p.az_label().text()
    assert "12.30" in txt
    assert "12.00" in txt
    assert "+0.30" in txt
