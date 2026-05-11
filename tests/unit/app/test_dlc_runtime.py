"""App-layer DLC runtime assembly tests (Phase 7.6, plan/17 § 17.4)."""

from __future__ import annotations

from pathlib import Path

from workbench.app.dlc import PackageManager, PluginLoader
from workbench.app.dlc_runtime import (
    DLCPaths,
    build_dlc_app_runtime,
    default_dlc_paths,
)
from workbench.app.resources import ResourceCategory, ResourceLibrary, ResourceSource

_GOOD_MANIFEST = """
[package]
id = "{pkg_id}"
name = "Demo Package"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"
"""


def _make_package(root: Path, pkg_id: str) -> Path:
    pkg_dir = root / pkg_id
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(_GOOD_MANIFEST.format(pkg_id=pkg_id), encoding="utf-8")
    return pkg_dir


# ---------------------------------------------------------------------
# default_dlc_paths
# ---------------------------------------------------------------------


def test_default_paths_uses_injected_home(tmp_path: Path) -> None:
    paths = default_dlc_paths(home=tmp_path)
    assert paths.packages_root == tmp_path / ".trsim" / "packages"
    assert paths.user_root == tmp_path / ".trsim"
    assert paths.builtin_root is None


def test_default_paths_real_home_resolves_to_dot_trsim() -> None:
    paths = default_dlc_paths()
    assert paths.packages_root.name == "packages"
    assert paths.packages_root.parent.name == ".trsim"
    assert paths.user_root is not None
    assert paths.user_root.name == ".trsim"


# ---------------------------------------------------------------------
# build_dlc_app_runtime — empty
# ---------------------------------------------------------------------


def test_build_with_missing_packages_root(tmp_path: Path) -> None:
    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=None, builtin_root=None)
    runtime = build_dlc_app_runtime(paths)
    assert runtime.paths is paths
    assert isinstance(runtime.package_manager, PackageManager)
    assert isinstance(runtime.plugin_loader, PluginLoader)
    assert isinstance(runtime.resource_library, ResourceLibrary)
    assert runtime.package_manager.installed_ids() == ()
    assert runtime.plugin_loader.all_slots() == ()


def test_build_with_empty_packages_root(tmp_path: Path) -> None:
    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    paths = DLCPaths(packages_root=pkgs, user_root=None, builtin_root=None)
    runtime = build_dlc_app_runtime(paths)
    assert runtime.package_manager.installed_ids() == ()
    for cat in ResourceCategory:
        assert runtime.resource_library.list_resources(cat) == ()


# ---------------------------------------------------------------------
# build_dlc_app_runtime — populated
# ---------------------------------------------------------------------


def test_build_loads_installed_packages(tmp_path: Path) -> None:
    pkgs = tmp_path / "packages"
    pkgs.mkdir()
    _make_package(pkgs, "alpha")
    _make_package(pkgs, "beta")

    paths = DLCPaths(packages_root=pkgs, user_root=None, builtin_root=None)
    runtime = build_dlc_app_runtime(paths)

    assert runtime.package_manager.installed_ids() == ("alpha", "beta")
    # ResourceLibrary received the same scanned packages.
    assert tuple(p.package_id for p in runtime.resource_library.installed_packages()) == (
        "alpha",
        "beta",
    )


def test_build_indexes_user_resources(tmp_path: Path) -> None:
    user_root = tmp_path / "user"
    radars = user_root / "resources" / "radars"
    radars.mkdir(parents=True)
    (radars / "kuband.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=None)
    runtime = build_dlc_app_runtime(paths)

    entries = runtime.resource_library.list_resources(ResourceCategory.RADARS)
    assert len(entries) == 1
    assert entries[0].resource_id == "kuband"
    assert entries[0].source == ResourceSource.USER


def test_build_indexes_builtin_resources(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    maps_dir = builtin / "maps"
    maps_dir.mkdir(parents=True)
    (maps_dir / "east_coast.toml").write_text("# stub", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=None, builtin_root=builtin)
    runtime = build_dlc_app_runtime(paths)

    entries = runtime.resource_library.list_resources(ResourceCategory.MAPS)
    assert len(entries) == 1
    assert entries[0].resource_id == "east_coast"
    assert entries[0].source == ResourceSource.BUILTIN


def test_build_user_shadows_builtin(tmp_path: Path) -> None:
    user_root = tmp_path / "user"
    user_radars = user_root / "resources" / "radars"
    user_radars.mkdir(parents=True)
    (user_radars / "kuband.toml").write_text("# user", encoding="utf-8")

    builtin = tmp_path / "builtin"
    builtin_radars = builtin / "radars"
    builtin_radars.mkdir(parents=True)
    (builtin_radars / "kuband.toml").write_text("# builtin", encoding="utf-8")

    paths = DLCPaths(packages_root=tmp_path / "ghost", user_root=user_root, builtin_root=builtin)
    runtime = build_dlc_app_runtime(paths)

    entries = runtime.resource_library.list_resources(ResourceCategory.RADARS)
    assert len(entries) == 1
    assert entries[0].source == ResourceSource.USER
    assert entries[0].shadowed_by_source == (ResourceSource.BUILTIN,)


# ---------------------------------------------------------------------
# Round-trip with default_dlc_paths
# ---------------------------------------------------------------------


def test_runtime_from_default_paths_no_side_effects(tmp_path: Path) -> None:
    paths = default_dlc_paths(home=tmp_path)
    runtime = build_dlc_app_runtime(paths)
    # The home directory must not have been populated by the build.
    assert not (tmp_path / ".trsim").exists()
    assert runtime.package_manager.installed_ids() == ()
