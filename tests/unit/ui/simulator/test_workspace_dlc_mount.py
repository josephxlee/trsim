"""Simulator workspace DLC panel mount tests (Task D, plan/17 § 17.4.4)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QLabel, QWidget

from workbench.ui.panel_registry import PanelRegistration, PanelRegistry
from workbench.ui.simulator.workspace import DLCMountError, SimulatorWorkspace

pytestmark = pytest.mark.qt


class _GoodPanel(QWidget):
    pass


class _AnotherPanel(QWidget):
    pass


class _RaisingPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:  # type: ignore[no-untyped-def]
        del parent
        msg = "boom"
        raise RuntimeError(msg)


class _NotAWidget:
    def __init__(self, parent: QWidget | None = None) -> None:  # type: ignore[no-untyped-def]
        del parent


# ---------------------------------------------------------------------
# No registry: defaults
# ---------------------------------------------------------------------


def test_workspace_no_registry_has_no_dlc_panels(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert ws.dlc_panels == ()
    assert ws.dlc_mount_errors == ()
    # Default bottom tabs: Run / Stage I/O / Profiler.
    assert ws.bottom_tabs().count() == 6


# ---------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------


def test_registry_with_simulator_panel_mounts_as_bottom_tab(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(
        _GoodPanel,
        workspace="simulator",
        dock_area="right",
        source_package_id="demo-dlc",
    )
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)

    assert ws.bottom_tabs().count() == 7
    assert len(ws.dlc_panels) == 1
    assert isinstance(ws.dlc_panels[0], _GoodPanel)
    assert ws.bottom_tabs().tabText(6) == "[DLC] demo-dlc: _GoodPanel"


def test_two_simulator_panels_mount_in_order(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(_GoodPanel, workspace="simulator", dock_area="right", source_package_id="a")
    registry.register(
        _AnotherPanel, workspace="simulator", dock_area="right", source_package_id="b"
    )
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)

    assert ws.bottom_tabs().count() == 8
    assert ws.bottom_tabs().tabText(6) == "[DLC] a: _GoodPanel"
    assert ws.bottom_tabs().tabText(7) == "[DLC] b: _AnotherPanel"


def test_builtin_workspace_tag_skipped_when_workspace_is_editor(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(_GoodPanel, workspace="editor", dock_area="left")
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    # Editor-tagged panels must not land on the Simulator workspace.
    assert ws.bottom_tabs().count() == 6
    assert ws.dlc_panels == ()


def test_empty_package_id_uses_class_only_label(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(_GoodPanel, workspace="simulator", dock_area="right")
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert ws.bottom_tabs().tabText(6) == "[DLC] _GoodPanel"


# ---------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------


def test_raising_constructor_recorded_as_mount_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(
        _RaisingPanel, workspace="simulator", dock_area="right", source_package_id="broken"
    )
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert ws.dlc_panels == ()
    assert ws.bottom_tabs().count() == 6
    assert len(ws.dlc_mount_errors) == 1
    err = ws.dlc_mount_errors[0]
    assert isinstance(err, DLCMountError)
    assert err.registration.source_package_id == "broken"
    assert "constructor failed" in err.message


def test_non_qwidget_factory_recorded_as_mount_error(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(
        _NotAWidget, workspace="simulator", dock_area="right", source_package_id="wrong-shape"
    )
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert ws.dlc_panels == ()
    assert len(ws.dlc_mount_errors) == 1
    assert "did not return a QWidget" in ws.dlc_mount_errors[0].message


def test_mixed_good_and_bad_isolates_failure(qtbot) -> None:  # type: ignore[no-untyped-def]
    registry = PanelRegistry()
    registry.register(
        _RaisingPanel, workspace="simulator", dock_area="right", source_package_id="x"
    )
    registry.register(_GoodPanel, workspace="simulator", dock_area="right", source_package_id="y")
    ws = SimulatorWorkspace(panel_registry=registry, enable_3d_viewer=False)
    qtbot.addWidget(ws)
    assert len(ws.dlc_panels) == 1
    assert len(ws.dlc_mount_errors) == 1
    assert ws.bottom_tabs().tabText(6) == "[DLC] y: _GoodPanel"


# ---------------------------------------------------------------------
# Explicit mount_dlc_panels API (post-construction)
# ---------------------------------------------------------------------


def test_mount_dlc_panels_returns_added_count(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)
    added = ws.mount_dlc_panels(
        [
            PanelRegistration(
                panel_class=_GoodPanel,
                workspace="simulator",
                dock_area="right",
                source_package_id="late-bind",
            )
        ]
    )
    assert added == 1
    assert ws.bottom_tabs().tabText(6) == "[DLC] late-bind: _GoodPanel"


def test_mount_dlc_panels_accepts_qlabel_subclass(qtbot) -> None:  # type: ignore[no-untyped-def]
    """Sanity check: any QWidget subclass is accepted, not just QWidget itself."""

    class _LabelPanel(QLabel):
        def __init__(self, parent: QWidget | None = None) -> None:
            super().__init__("hello", parent)

    ws = SimulatorWorkspace(enable_3d_viewer=False)
    qtbot.addWidget(ws)
    added = ws.mount_dlc_panels(
        [
            PanelRegistration(
                panel_class=_LabelPanel,
                workspace="simulator",
                dock_area="right",
                source_package_id="lbl",
            )
        ]
    )
    assert added == 1
    assert isinstance(ws.dlc_panels[0], _LabelPanel)
