"""ResourceLibrary 3-source tests (Phase 7.4, plan/17 § 17.4.3)."""

from __future__ import annotations

from pathlib import Path

from workbench.app.dlc import LoadedPackage, PackageManager
from workbench.app.resources import (
    ResourceCategory,
    ResourceLibrary,
    ResourceSource,
)

_MANIFEST = """
[package]
id = "{pkg_id}"
name = "Demo"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"
"""


def _make_resource_file(root: Path, *parts: str) -> Path:
    p = root.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# placeholder\n", encoding="utf-8")
    return p


def _make_package_with_resources(root: Path, pkg_id: str, resources: dict[str, list[str]]) -> Path:
    pkg_dir = root / pkg_id
    pkg_dir.mkdir(parents=True)
    (pkg_dir / "manifest.toml").write_text(_MANIFEST.format(pkg_id=pkg_id), encoding="utf-8")
    for category, names in resources.items():
        for name in names:
            _make_resource_file(pkg_dir / "resources" / category / f"{name}.toml")
    return pkg_dir


def _scanned_packages(packages_root: Path) -> tuple[LoadedPackage, ...]:
    mgr = PackageManager(packages_root)
    mgr.scan()
    return tuple(pkg for pkg in (mgr.get(pid) for pid in mgr.installed_ids()) if pkg is not None)


# ---------------------------------------------------------------------
# Empty library
# ---------------------------------------------------------------------


def test_empty_library_returns_empty_for_every_category() -> None:
    lib = ResourceLibrary()
    for category in ResourceCategory:
        assert lib.list_resources(category) == ()


# ---------------------------------------------------------------------
# Built-in only
# ---------------------------------------------------------------------


def test_builtin_root_resources_are_listed(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    _make_resource_file(builtin, "maps", "east_coast.toml")
    _make_resource_file(builtin, "maps", "west_coast.toml")
    lib = ResourceLibrary(builtin_root=builtin)
    entries = lib.list_resources(ResourceCategory.MAPS)
    assert [e.resource_id for e in entries] == ["east_coast", "west_coast"]
    assert all(e.source is ResourceSource.BUILTIN for e in entries)


def test_missing_category_dir_returns_empty(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    builtin.mkdir()
    lib = ResourceLibrary(builtin_root=builtin)
    assert lib.list_resources(ResourceCategory.MAPS) == ()


# ---------------------------------------------------------------------
# User only
# ---------------------------------------------------------------------


def test_user_root_resources_are_listed(tmp_path: Path) -> None:
    user = tmp_path / "user"
    _make_resource_file(user, "resources", "radars", "x_band.toml")
    lib = ResourceLibrary(user_root=user)
    entries = lib.list_resources(ResourceCategory.RADARS)
    assert [e.resource_id for e in entries] == ["x_band"]
    assert entries[0].source is ResourceSource.USER


# ---------------------------------------------------------------------
# Packages
# ---------------------------------------------------------------------


def test_package_resources_are_listed(tmp_path: Path) -> None:
    pkg_root = tmp_path / "packages"
    _make_package_with_resources(pkg_root, "demo-pkg", {"targets": ["stealth_aircraft"]})
    lib = ResourceLibrary(packages=_scanned_packages(pkg_root))
    entries = lib.list_resources(ResourceCategory.TARGETS)
    assert [e.resource_id for e in entries] == ["stealth_aircraft"]
    assert entries[0].source is ResourceSource.PACKAGE
    assert entries[0].package_id == "demo-pkg"


def test_multiple_packages_aggregate(tmp_path: Path) -> None:
    pkg_root = tmp_path / "packages"
    _make_package_with_resources(pkg_root, "pkg-a", {"maps": ["alpha"]})
    _make_package_with_resources(pkg_root, "pkg-b", {"maps": ["bravo"]})
    lib = ResourceLibrary(packages=_scanned_packages(pkg_root))
    entries = lib.list_resources(ResourceCategory.MAPS)
    assert [e.resource_id for e in entries] == ["alpha", "bravo"]


# ---------------------------------------------------------------------
# Three-source priority
# ---------------------------------------------------------------------


def test_user_wins_over_package_wins_over_builtin(tmp_path: Path) -> None:
    """Same resource_id 'east_coast' in all three tiers — User wins."""
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    pkg_root = tmp_path / "packages"
    _make_resource_file(builtin, "maps", "east_coast.toml")
    _make_package_with_resources(pkg_root, "demo-pkg", {"maps": ["east_coast"]})
    _make_resource_file(user, "resources", "maps", "east_coast.toml")

    lib = ResourceLibrary(
        user_root=user,
        packages=_scanned_packages(pkg_root),
        builtin_root=builtin,
    )
    entries = lib.list_resources(ResourceCategory.MAPS)
    assert len(entries) == 1
    winner = entries[0]
    assert winner.source is ResourceSource.USER
    # Both other tiers shadow this entry.
    assert ResourceSource.PACKAGE in winner.shadowed_by_source
    assert ResourceSource.BUILTIN in winner.shadowed_by_source


def test_package_wins_over_builtin_when_user_missing(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    pkg_root = tmp_path / "packages"
    _make_resource_file(builtin, "maps", "shared.toml")
    _make_package_with_resources(pkg_root, "demo-pkg", {"maps": ["shared"]})
    lib = ResourceLibrary(packages=_scanned_packages(pkg_root), builtin_root=builtin)
    entries = lib.list_resources(ResourceCategory.MAPS)
    assert entries[0].source is ResourceSource.PACKAGE
    assert entries[0].shadowed_by_source == (ResourceSource.BUILTIN,)


def test_no_shadowing_when_unique(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    _make_resource_file(builtin, "maps", "builtin_only.toml")
    _make_resource_file(user, "resources", "maps", "user_only.toml")
    lib = ResourceLibrary(user_root=user, builtin_root=builtin)
    entries = lib.list_resources(ResourceCategory.MAPS)
    for entry in entries:
        assert entry.shadowed_by_source == ()


# ---------------------------------------------------------------------
# Hidden / metadata files
# ---------------------------------------------------------------------


def test_dotfiles_skipped(tmp_path: Path) -> None:
    builtin = tmp_path / "builtin"
    _make_resource_file(builtin, "maps", "real.toml")
    _make_resource_file(builtin, "maps", ".DS_Store")
    lib = ResourceLibrary(builtin_root=builtin)
    entries = lib.list_resources(ResourceCategory.MAPS)
    assert [e.resource_id for e in entries] == ["real"]


# ---------------------------------------------------------------------
# all_categories
# ---------------------------------------------------------------------


def test_all_categories_lists_four() -> None:
    lib = ResourceLibrary()
    categories = lib.all_categories()
    assert ResourceCategory.MAPS in categories
    assert ResourceCategory.RADARS in categories
    assert ResourceCategory.TARGETS in categories
    assert ResourceCategory.SCENARIOS in categories
    assert len(categories) == 4
