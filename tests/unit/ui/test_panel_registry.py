"""Panel Registry tests (Phase 7.5, plan/17 § 17.4.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from workbench.app.dlc import LoadedPlugin
from workbench.ui.panel_registry import PanelRegistration, PanelRegistry


class _BuiltinPanel:
    """Stand-in for a real Qt panel."""


class _AnotherBuiltinPanel:
    pass


def _dlc_plugin(panel_class: type, *, package_id: str = "demo-pkg") -> LoadedPlugin:
    return LoadedPlugin(
        slot="trsim.ui.panels",
        package_id=package_id,
        target="panel:Klass",
        attribute=panel_class,
    )


# ---------------------------------------------------------------------
# Built-in registration
# ---------------------------------------------------------------------


def test_register_single_panel() -> None:
    reg = PanelRegistry()
    reg.register(_BuiltinPanel, workspace="editor", dock_area="left")
    assert len(reg) == 1
    entry = reg.all_registrations()[0]
    assert isinstance(entry, PanelRegistration)
    assert entry.panel_class is _BuiltinPanel
    assert entry.workspace == "editor"
    assert entry.dock_area == "left"
    assert entry.source_package_id == ""


def test_register_preserves_insertion_order() -> None:
    reg = PanelRegistry()
    reg.register(_BuiltinPanel, workspace="editor", dock_area="left")
    reg.register(_AnotherBuiltinPanel, workspace="simulator", dock_area="right")
    classes = [e.panel_class for e in reg.all_registrations()]
    assert classes == [_BuiltinPanel, _AnotherBuiltinPanel]


def test_register_empty_workspace_rejected() -> None:
    reg = PanelRegistry()
    with pytest.raises(ValueError, match=r"workspace"):
        reg.register(_BuiltinPanel, workspace="", dock_area="left")


def test_register_empty_dock_area_rejected() -> None:
    reg = PanelRegistry()
    with pytest.raises(ValueError, match=r"dock_area"):
        reg.register(_BuiltinPanel, workspace="editor", dock_area="")


# ---------------------------------------------------------------------
# Workspace filtering
# ---------------------------------------------------------------------


def test_get_panels_for_workspace_filters_correctly() -> None:
    reg = PanelRegistry()
    reg.register(_BuiltinPanel, workspace="editor", dock_area="left")
    reg.register(_AnotherBuiltinPanel, workspace="simulator", dock_area="right")
    editor_panels = reg.get_panels_for_workspace("editor")
    sim_panels = reg.get_panels_for_workspace("simulator")
    assert [p.panel_class for p in editor_panels] == [_BuiltinPanel]
    assert [p.panel_class for p in sim_panels] == [_AnotherBuiltinPanel]


def test_get_panels_for_unknown_workspace_returns_empty() -> None:
    reg = PanelRegistry()
    reg.register(_BuiltinPanel, workspace="editor", dock_area="left")
    assert reg.get_panels_for_workspace("nn_training") == ()


# ---------------------------------------------------------------------
# DLC plugin registration
# ---------------------------------------------------------------------


def test_register_dlc_plugin_adds_entry_with_package_id() -> None:
    reg = PanelRegistry()
    n = reg.register_dlc_plugins([_dlc_plugin(_BuiltinPanel)])
    assert n == 1
    sim_panels = reg.get_panels_for_workspace("simulator")
    assert len(sim_panels) == 1
    assert sim_panels[0].source_package_id == "demo-pkg"
    assert sim_panels[0].dock_area == "right"  # default


def test_register_dlc_plugins_honours_default_overrides() -> None:
    reg = PanelRegistry()
    reg.register_dlc_plugins(
        [_dlc_plugin(_BuiltinPanel)],
        default_workspace="editor",
        default_dock_area="bottom",
    )
    panels = reg.get_panels_for_workspace("editor")
    assert panels[0].dock_area == "bottom"


def test_register_dlc_skips_plugin_without_attribute() -> None:
    """Plugins whose attribute is None (path-slot mistakes etc.) are
    silently skipped; PluginLoader already logged the error.
    """
    bad = LoadedPlugin(
        slot="trsim.ui.panels",
        package_id="bad-pkg",
        target="panel:Missing",
        attribute=None,
    )
    reg = PanelRegistry()
    n = reg.register_dlc_plugins([bad])
    assert n == 0


def test_register_dlc_skips_non_class_attribute() -> None:
    """A plugin attribute that is a function / instance, not a class,
    is rejected silently (defer the type check to main_window).
    """

    def _factory() -> Any:
        return None

    plugin = LoadedPlugin(
        slot="trsim.ui.panels",
        package_id="bad-pkg",
        target="panel:factory",
        attribute=_factory,
    )
    reg = PanelRegistry()
    n = reg.register_dlc_plugins([plugin])
    assert n == 0


def test_register_dlc_multiple_plugins_aggregate() -> None:
    reg = PanelRegistry()
    n = reg.register_dlc_plugins(
        [
            _dlc_plugin(_BuiltinPanel, package_id="pkg-a"),
            _dlc_plugin(_AnotherBuiltinPanel, package_id="pkg-b"),
        ]
    )
    assert n == 2
    panels = reg.get_panels_for_workspace("simulator")
    assert {p.source_package_id for p in panels} == {"pkg-a", "pkg-b"}


# ---------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------


def test_clear_removes_all_entries() -> None:
    reg = PanelRegistry()
    reg.register(_BuiltinPanel, workspace="editor", dock_area="left")
    reg.register_dlc_plugins([_dlc_plugin(_AnotherBuiltinPanel)])
    assert len(reg) == 2
    reg.clear()
    assert len(reg) == 0
    assert reg.all_registrations() == ()


# ---------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------


def test_empty_registry_returns_empty(_: None = None) -> None:
    reg = PanelRegistry()
    assert reg.all_registrations() == ()
    assert reg.get_panels_for_workspace("editor") == ()
    assert len(reg) == 0


# Path import is unused; quiet the linter.
_ = Path
