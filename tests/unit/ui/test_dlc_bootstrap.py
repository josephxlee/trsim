"""UI-layer DLC bootstrap tests (Phase 7.6, plan/17 § 17.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from workbench.app.dlc_runtime import (
    DLCPaths,
    build_dlc_app_runtime,
    default_dlc_paths,
)
from workbench.app.resources import ResourceLibrary
from workbench.ui.dlc_bootstrap import (
    DLCRuntime,
    build_dlc_runtime,
    populate_composer_options_from_library,
    populate_resource_browser_from_library,
)
from workbench.ui.editor.resource_browser import (
    ResourceBrowserSidebar,
    ResourceStatus,
)
from workbench.ui.editor.resource_browser import (
    ResourceCategory as UICategory,
)
from workbench.ui.panel_registry import PanelRegistry

pytestmark = pytest.mark.qt

_PANEL_MANIFEST = """
[package]
id = "{pkg_id}"
name = "Demo Panel Package"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
"trsim.ui.panels" = "demo_panel:DemoPanel"
"""

_PANEL_MODULE = """
class DemoPanel:
    pass
"""


def _make_panel_package(packages_root: Path, pkg_id: str) -> None:
    pkg_dir = packages_root / pkg_id
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(_PANEL_MANIFEST.format(pkg_id=pkg_id), encoding="utf-8")
    (pkg_dir / "demo_panel.py").write_text(_PANEL_MODULE, encoding="utf-8")


# ---------------------------------------------------------------------
# build_dlc_runtime — defaults + path injection
# ---------------------------------------------------------------------


def test_build_runtime_from_paths_no_packages(tmp_path: Path) -> None:
    paths = default_dlc_paths(home=tmp_path)
    runtime = build_dlc_runtime(paths=paths)
    assert isinstance(runtime, DLCRuntime)
    assert isinstance(runtime.panel_registry, PanelRegistry)
    assert len(runtime.panel_registry) == 0
    assert runtime.app.package_manager.installed_ids() == ()


def test_build_runtime_from_app_runtime_reuses_it(tmp_path: Path) -> None:
    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=None, builtin_root=None)
    app_runtime = build_dlc_app_runtime(paths)
    runtime = build_dlc_runtime(app_runtime=app_runtime)
    assert runtime.app is app_runtime


def test_build_runtime_registers_ui_panel_plugins(tmp_path: Path) -> None:
    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    _make_panel_package(pkgs, "demo-panel-pack")

    paths = DLCPaths(packages_root=pkgs, user_root=None, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    panels = runtime.panel_registry.get_panels_for_workspace("simulator")
    assert len(panels) == 1
    assert panels[0].source_package_id == "demo-panel-pack"
    assert panels[0].panel_class.__name__ == "DemoPanel"


def test_build_runtime_accepts_existing_registry(tmp_path: Path) -> None:
    paths = default_dlc_paths(home=tmp_path)
    registry = PanelRegistry()

    class _Builtin:
        pass

    registry.register(_Builtin, workspace="editor", dock_area="left")
    runtime = build_dlc_runtime(paths=paths, panel_registry=registry)
    # The builtin registration must survive.
    assert runtime.panel_registry is registry
    editor_panels = runtime.panel_registry.get_panels_for_workspace("editor")
    assert any(p.panel_class is _Builtin for p in editor_panels)


# ---------------------------------------------------------------------
# populate_resource_browser_from_library
# ---------------------------------------------------------------------


def test_populate_sidebar_with_empty_library(qtbot) -> None:  # type: ignore[no-untyped-def]
    library = ResourceLibrary(user_root=None, packages=(), builtin_root=None)
    sidebar = ResourceBrowserSidebar()
    qtbot.addWidget(sidebar)
    added = populate_resource_browser_from_library(sidebar, library)
    assert added == 0
    for cat in UICategory:
        assert sidebar.category_node(cat).childCount() == 0


def test_populate_sidebar_user_resources_mapped_to_ui_categories(
    qtbot,  # type: ignore[no-untyped-def]
    tmp_path: Path,
) -> None:
    user_root = tmp_path / "user"
    res_root = user_root / "resources"
    for cat_name, leaf in (
        ("maps", "east_coast"),
        ("radars", "kuband"),
        ("targets", "fighter_a"),
        ("scenarios", "intercept_01"),
    ):
        cat_dir = res_root / cat_name
        cat_dir.mkdir(parents=True)
        (cat_dir / f"{leaf}.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    sidebar = ResourceBrowserSidebar()
    qtbot.addWidget(sidebar)
    added = populate_resource_browser_from_library(sidebar, runtime.app.resource_library)
    assert added == 4

    # One leaf per UI category, with the correct app->ui mapping.
    assert sidebar.category_node(UICategory.MAP).childCount() == 1
    assert sidebar.category_node(UICategory.RADAR).childCount() == 1
    assert sidebar.category_node(UICategory.TARGETS).childCount() == 1
    assert sidebar.category_node(UICategory.SCENARIO).childCount() == 1


def test_populate_sidebar_builtin_carries_builtin_status(
    qtbot,  # type: ignore[no-untyped-def]
    tmp_path: Path,
) -> None:
    builtin = tmp_path / "builtin"
    radars_dir = builtin / "radars"
    radars_dir.mkdir(parents=True)
    (radars_dir / "kuband.toml").write_text("# preset", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=None, builtin_root=builtin)
    runtime = build_dlc_runtime(paths=paths)

    sidebar = ResourceBrowserSidebar()
    qtbot.addWidget(sidebar)
    populate_resource_browser_from_library(sidebar, runtime.app.resource_library)

    node = sidebar.category_node(UICategory.RADAR)
    assert node.childCount() == 1
    # ResourceStatus.BUILTIN renders the "[builtin] " prefix.
    assert node.child(0).text(0).startswith(f"[{ResourceStatus.BUILTIN.value}]")


def test_populate_sidebar_clears_previous_entries(
    qtbot,  # type: ignore[no-untyped-def]
    tmp_path: Path,
) -> None:
    user_root = tmp_path / "user"
    radars = user_root / "resources" / "radars"
    radars.mkdir(parents=True)
    (radars / "first.toml").write_text("# v1", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    sidebar = ResourceBrowserSidebar()
    qtbot.addWidget(sidebar)
    populate_resource_browser_from_library(sidebar, runtime.app.resource_library)
    assert sidebar.category_node(UICategory.RADAR).childCount() == 1

    # Swap the on-disk resource and refresh — the library re-scans
    # every call, and populate clears before adding.
    (radars / "first.toml").unlink()
    (radars / "second.toml").write_text("# v2", encoding="utf-8")
    populate_resource_browser_from_library(sidebar, runtime.app.resource_library)

    node = sidebar.category_node(UICategory.RADAR)
    assert node.childCount() == 1
    assert "second" in node.child(0).text(0)


# ---------------------------------------------------------------------
# populate_composer_options_from_library
# ---------------------------------------------------------------------


class _ComposerStub:
    """Minimal duck-typed ScenarioComposer surface used by the helper."""

    def __init__(self) -> None:
        self.maps: list[str] = []
        self.radars: list[str] = []
        self.targets: list[str] = []

    def set_map_options(self, names: list[str]) -> None:
        self.maps = list(names)

    def set_radar_options(self, names: list[str]) -> None:
        self.radars = list(names)

    def set_targets_options(self, names: list[str]) -> None:
        self.targets = list(names)


def test_populate_composer_empty_library(tmp_path: Path) -> None:
    library = ResourceLibrary(user_root=None, packages=(), builtin_root=None)
    stub = _ComposerStub()
    n_maps, n_radars, n_targets = populate_composer_options_from_library(stub, library)
    assert (n_maps, n_radars, n_targets) == (0, 0, 0)
    assert stub.maps == []
    assert stub.radars == []
    assert stub.targets == []


def test_populate_composer_three_categories_round_trip(tmp_path: Path) -> None:
    user_root = tmp_path / "user"
    res_root = user_root / "resources"
    for cat_name, leaves in (
        ("maps", ["east_coast", "north_sea"]),
        ("radars", ["kuband"]),
        ("targets", ["fighter_a", "drone_x", "missile_q"]),
    ):
        cat_dir = res_root / cat_name
        cat_dir.mkdir(parents=True)
        for leaf in leaves:
            (cat_dir / f"{leaf}.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)

    stub = _ComposerStub()
    counts = populate_composer_options_from_library(stub, runtime.app.resource_library)
    assert counts == (2, 1, 3)
    assert sorted(stub.maps) == ["east_coast", "north_sea"]
    assert stub.radars == ["kuband"]
    assert sorted(stub.targets) == ["drone_x", "fighter_a", "missile_q"]


def test_populate_composer_skips_scenarios_category(tmp_path: Path) -> None:
    """The Composer's three dropdowns are Map / Radar / Targets only —
    scenarios are addressed by the Composer's own save mechanism."""
    user_root = tmp_path / "user"
    res_root = user_root / "resources"
    cat_dir = res_root / "scenarios"
    cat_dir.mkdir(parents=True)
    (cat_dir / "intercept_01.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_runtime(paths=paths)
    stub = _ComposerStub()
    counts = populate_composer_options_from_library(stub, runtime.app.resource_library)
    # Scenarios live in the library but the Composer dropdowns do not
    # consume them — the three counts are all zero.
    assert counts == (0, 0, 0)
