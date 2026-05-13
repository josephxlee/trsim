"""PluginLoader tests (Phase 7.3, plan/17 § 17.4.2)."""

from __future__ import annotations

from pathlib import Path

from workbench.app.dlc import PackageManager, PluginLoader

_MANIFEST_TEMPLATE = """
[package]
id = "{pkg_id}"
name = "Demo"
version = "1.0.0"
license = "MIT"

[compatibility]
trsim_min_version = "0.35.0"

[entry_points]
{entry_points}
"""


def _write_package(
    root: Path, pkg_id: str, *, entry_points: dict[str, str], files: dict[str, str]
) -> Path:
    pkg_dir = root / pkg_id
    pkg_dir.mkdir(parents=True)
    ep_text = "\n".join(f'"{slot}" = "{target}"' for slot, target in entry_points.items())
    (pkg_dir / "manifest.toml").write_text(
        _MANIFEST_TEMPLATE.format(pkg_id=pkg_id, entry_points=ep_text),
        encoding="utf-8",
    )
    for relpath, body in files.items():
        f = pkg_dir / relpath
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    return pkg_dir


def _scanned_loader(packages_root: Path) -> PluginLoader:
    mgr = PackageManager(packages_root)
    mgr.scan()
    return PluginLoader(mgr)


# ---------------------------------------------------------------------
# Python import slots
# ---------------------------------------------------------------------


def test_python_entry_point_resolves_to_class(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "demo-tracker",
        entry_points={"trsim.plugins.tracker": "tracker:DemoTracker"},
        files={
            "tracker.py": ("class DemoTracker:\n    name = 'demo-tracker'\n"),
        },
    )
    loader = _scanned_loader(tmp_path)
    result = loader.load_all()

    plugins = result["trsim.plugins.tracker"]
    assert len(plugins) == 1
    cls = plugins[0].attribute
    assert cls is not None
    assert cls.name == "demo-tracker"


def test_ui_panel_slot_uses_python_import(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "demo-ui",
        entry_points={"trsim.ui.panels": "panel:DemoPanel"},
        files={"panel.py": "class DemoPanel:\n    pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.plugins_for_slot("trsim.ui.panels")[0].attribute is not None


def test_python_entry_point_with_slash_path_resolves(tmp_path: Path) -> None:
    """plan/17 § 17.2.4 manifest examples use slash separators —
    ``"ui/diagnostic_panel:Panel"`` — and the loader must accept them
    as readily as ``"ui.diagnostic_panel:Panel"``. Reported during MVP
    verification: a sample DLC built per MVP_GUIDE § 4.1 silently failed
    to mount because the loader only split on dots.
    """
    _write_package(
        tmp_path,
        "demo-panel",
        entry_points={"trsim.ui.panels": "ui/diagnostic_panel:DiagnosticPanel"},
        files={
            "ui/diagnostic_panel.py": "class DiagnosticPanel:\n    pass\n",
        },
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    plugins = loader.plugins_for_slot("trsim.ui.panels")
    assert len(plugins) == 1
    assert plugins[0].attribute is not None
    assert plugins[0].attribute.__name__ == "DiagnosticPanel"
    assert loader.load_errors == ()


def test_python_entry_point_with_backslash_path_resolves(tmp_path: Path) -> None:
    """Windows-authored manifests with ``ui\\panel`` separators load too."""
    _write_package(
        tmp_path,
        "win-author",
        entry_points={"trsim.ui.panels": "ui\\\\panel:Panel"},
        files={
            "ui/panel.py": "class Panel:\n    pass\n",
        },
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    plugins = loader.plugins_for_slot("trsim.ui.panels")
    assert len(plugins) == 1
    assert plugins[0].attribute is not None


def test_python_target_without_colon_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "bad",
        entry_points={"trsim.plugins.tracker": "no_colon_target"},
        files={},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.plugins_for_slot("trsim.plugins.tracker") == ()
    assert any("module:attribute" in e.message for e in loader.load_errors)


def test_missing_module_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "bad",
        entry_points={"trsim.plugins.tracker": "nonexistent:Klass"},
        files={},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.plugins_for_slot("trsim.plugins.tracker") == ()
    assert any("import failed" in e.message for e in loader.load_errors)


def test_missing_attribute_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "bad",
        entry_points={"trsim.plugins.tracker": "mod:Missing"},
        files={"mod.py": "class OtherKlass:\n    pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert any("has no attribute" in e.message for e in loader.load_errors)


# ---------------------------------------------------------------------
# Path slots
# ---------------------------------------------------------------------


def test_resource_directory_slot_resolves_to_absolute_path(tmp_path: Path) -> None:
    pkg_dir = _write_package(
        tmp_path,
        "demo-resources",
        entry_points={"trsim.resources.radars": "resources/radars/"},
        files={"resources/radars/dummy.toml": "# placeholder\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    plugin = loader.plugins_for_slot("trsim.resources.radars")[0]
    assert plugin.resource_dir == (pkg_dir / "resources" / "radars").resolve()
    assert plugin.attribute is None  # path slot has no Python attribute


def test_resource_directory_missing_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "bad-resources",
        entry_points={"trsim.resources.maps": "resources/nonexistent/"},
        files={},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert any("not a directory" in e.message for e in loader.load_errors)


# ---------------------------------------------------------------------
# Unknown slot prefix
# ---------------------------------------------------------------------


def test_unknown_slot_prefix_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "demo",
        entry_points={"unknown.slot": "mod:Klass"},
        files={"mod.py": "class Klass: pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert any("unknown slot" in e.message for e in loader.load_errors)


# ---------------------------------------------------------------------
# Phase 9 I1 — singleton Python-import slots (trsim.physics_model etc.)
# ---------------------------------------------------------------------


def test_trsim_physics_model_slot_loads_as_python_import(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "physics-pkg",
        entry_points={"trsim.physics_model": "my_model:Model"},
        files={
            "my_model.py": (
                "class Model:\n"
                "    name = 'plug_model'\n"
                "    category = 'other'\n"
                "    parameters = ()\n"
                "    time_mode = 'static'\n"
                "    visualization = '2d'\n"
                "    def compute(self, state, params, dt_s):\n"
                "        return dict(state)\n"
            )
        },
    )
    loader = _scanned_loader(tmp_path)
    plugins = loader.load_all()
    assert "trsim.physics_model" in plugins
    (plugin,) = plugins["trsim.physics_model"]
    assert plugin.package_id == "physics-pkg"
    assert plugin.attribute is not None
    # The resolved attribute is the class itself — instantiating gives
    # a runtime_checkable PhysicsModelProtocol instance (verified via the
    # consumer in Phase 9 H2's discovery; here we just confirm it loaded).
    instance = plugin.attribute()  # type: ignore[operator]
    assert instance.name == "plug_model"


def test_trsim_physics_model_slot_missing_attribute_records_error(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "broken-pkg",
        entry_points={"trsim.physics_model": "my_model:Missing"},
        files={"my_model.py": "class Other: pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert any(e.slot == "trsim.physics_model" for e in loader.load_errors)


def test_trsim_physics_model_slot_in_known_singleton_slots() -> None:
    """Sanity — the slot is wired into the same singleton-set the validator
    relies on (test guards against accidental rename / typo)."""
    from workbench.app.dlc.plugin_loader import _PYTHON_IMPORT_EXACT_SLOTS

    assert "trsim.physics_model" in _PYTHON_IMPORT_EXACT_SLOTS


def test_existing_singleton_slots_still_load(tmp_path: Path) -> None:
    """Tracker / Pairing / etc. were listed by the SDK validator as known
    slots but the loader previously rejected them with "unknown slot
    prefix". I1 fixes that — verify tracker round-trips."""
    _write_package(
        tmp_path,
        "tracker-pkg",
        entry_points={"trsim.tracker": "my_tracker:Tracker"},
        files={"my_tracker.py": "class Tracker:\n    name = 'tk'\n"},
    )
    loader = _scanned_loader(tmp_path)
    plugins = loader.load_all()
    assert "trsim.tracker" in plugins
    assert loader.load_errors == ()


# ---------------------------------------------------------------------
# Multi-package + query helpers
# ---------------------------------------------------------------------


def test_load_all_aggregates_plugins_across_packages(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "pkg-a",
        entry_points={"trsim.plugins.tracker": "tracker_a:TrackerA"},
        files={"tracker_a.py": "class TrackerA: pass\n"},
    )
    _write_package(
        tmp_path,
        "pkg-b",
        entry_points={"trsim.plugins.tracker": "tracker_b:TrackerB"},
        files={"tracker_b.py": "class TrackerB: pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    plugins = loader.plugins_for_slot("trsim.plugins.tracker")
    assert len(plugins) == 2
    package_ids = {p.package_id for p in plugins}
    assert package_ids == {"pkg-a", "pkg-b"}


def test_all_slots_returns_sorted(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "demo",
        entry_points={
            "trsim.plugins.tracker": "mod:Tracker",
            "trsim.ui.panels": "mod:Panel",
        },
        files={"mod.py": "class Tracker: pass\nclass Panel: pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.all_slots() == ("trsim.plugins.tracker", "trsim.ui.panels")


def test_plugins_for_unknown_slot_returns_empty(tmp_path: Path) -> None:
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.plugins_for_slot("trsim.plugins.tracker") == ()


def test_rerun_load_all_replaces_state(tmp_path: Path) -> None:
    _write_package(
        tmp_path,
        "first",
        entry_points={"trsim.plugins.tracker": "mod:Klass"},
        files={"mod.py": "class Klass: pass\n"},
    )
    loader = _scanned_loader(tmp_path)
    loader.load_all()
    assert loader.all_slots() == ("trsim.plugins.tracker",)

    # Re-run on the same loader -> same result, not duplicated.
    loader.load_all()
    plugins = loader.plugins_for_slot("trsim.plugins.tracker")
    assert len(plugins) == 1


# ---------------------------------------------------------------------
# Empty manager
# ---------------------------------------------------------------------


def test_load_all_with_empty_manager_is_empty(tmp_path: Path) -> None:
    loader = _scanned_loader(tmp_path)
    assert loader.load_all() == {}
    assert loader.load_errors == ()
