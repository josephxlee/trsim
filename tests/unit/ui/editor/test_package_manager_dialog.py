"""Unit tests for PackageManagerDialog + Controller (Phase 7 remainder F2)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QMainWindow

from workbench import sdk
from workbench.app.dlc import (
    InstallResult,
    PackageAlreadyInstalledError,
    PackageNotInstalledError,
    UninstallResult,
    install_package,
)
from workbench.io.package_io import MANIFEST_FILENAME
from workbench.ui.editor.package_manager_dialog import (
    PackageManagerController,
    PackageManagerDialog,
)
from workbench.ui.editor.package_manager_panel import (
    InstalledPackageRow,
    PackageManagerPanel,
)

pytestmark = pytest.mark.qt


_VALID_MANIFEST_TOML = """\
[package]
id = "demo-tracker"
name = "Demo Tracker"
version = "0.1.0"
license = "Apache-2.0"

[compatibility]
trsim_min_version = "0.40.0"

[python]
extra_requires = []

[entry_points]
"""


def _write_source_dir(root: Path, *, pkg_id: str = "demo-tracker") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = _VALID_MANIFEST_TOML.replace("demo-tracker", pkg_id)
    (root / MANIFEST_FILENAME).write_text(manifest, encoding="utf-8")
    (root / "resources").mkdir()
    (root / "resources" / "demo.toml").write_text('id = "x"\n', encoding="utf-8")
    return root


def _build_pkg(tmp_path: Path, *, pkg_id: str = "demo-tracker") -> Path:
    src = _write_source_dir(tmp_path / f"src_{pkg_id}", pkg_id=pkg_id)
    return sdk.build_package(src, tmp_path / f"{pkg_id}.trsim-pkg")


# ---------------------------------------------------------------------
# Dialog smoke
# ---------------------------------------------------------------------


def test_dialog_hosts_a_package_manager_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    dlg = PackageManagerDialog()
    qtbot.addWidget(dlg)
    assert isinstance(dlg.panel(), PackageManagerPanel)


# ---------------------------------------------------------------------
# Controller state
# ---------------------------------------------------------------------


def test_controller_starts_without_active_dialog(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(packages_root=tmp_path, parent=host)
    assert ctrl.active_dialog() is None
    assert ctrl.packages_root() == tmp_path


def test_open_dialog_creates_dialog_and_refreshes_empty(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(packages_root=tmp_path, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    assert ctrl.active_dialog() is dlg
    assert dlg.panel().installed_packages() == ()


def test_open_dialog_second_call_reuses_dialog(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(packages_root=tmp_path, parent=host)
    dlg1 = ctrl.open_dialog()
    qtbot.addWidget(dlg1)
    dlg2 = ctrl.open_dialog()
    assert dlg1 is dlg2


def test_dialog_close_clears_active_reference(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(packages_root=tmp_path, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    dlg.reject()
    assert ctrl.active_dialog() is None


# ---------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------


def test_refresh_populates_panel_from_packages_root(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    root = tmp_path / "packages"
    pkg = _build_pkg(tmp_path)
    install_package(pkg, root)

    ctrl = PackageManagerController(packages_root=root, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    rows = dlg.panel().installed_packages()
    assert len(rows) == 1
    assert rows[0].package_id == "demo-tracker"


def test_refresh_with_no_dialog_is_noop(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(packages_root=tmp_path, parent=host)
    ctrl.refresh()  # must not raise
    assert ctrl.active_dialog() is None


# ---------------------------------------------------------------------
# Install via file picker
# ---------------------------------------------------------------------


def test_install_via_file_picker_uses_chosen_path(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"

    ctrl = PackageManagerController(
        packages_root=root,
        parent=host,
        file_picker=lambda _parent: pkg,
    )
    completed: list[InstallResult] = []
    ctrl.install_completed.connect(completed.append)

    result = ctrl.install_via_file_picker()
    assert result is not None
    assert result.manifest.package.package_id == "demo-tracker"
    assert (root / "demo-tracker" / MANIFEST_FILENAME).is_file()
    assert len(completed) == 1


def test_install_via_file_picker_cancel_returns_none(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    ctrl = PackageManagerController(
        packages_root=tmp_path,
        parent=host,
        file_picker=lambda _parent: None,
    )
    completed: list[InstallResult] = []
    ctrl.install_completed.connect(completed.append)
    assert ctrl.install_via_file_picker() is None
    assert completed == []


def test_install_failure_emits_install_failed(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    install_package(pkg, root)

    # Second install (no force) → PackageAlreadyInstalledError.
    ctrl = PackageManagerController(
        packages_root=root,
        parent=host,
        file_picker=lambda _parent: pkg,
    )
    failed: list[str] = []
    ctrl.install_failed.connect(failed.append)
    result = ctrl.install_via_file_picker()
    assert result is None
    assert len(failed) == 1
    assert "already exists" in failed[0]


def test_install_failure_with_custom_installer(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)

    def raising_installer(*_args: object, **_kwargs: object) -> InstallResult:
        msg = "fake target exists"
        raise PackageAlreadyInstalledError(msg)

    ctrl = PackageManagerController(
        packages_root=tmp_path,
        parent=host,
        installer=raising_installer,
        file_picker=lambda _parent: Path("fake.trsim-pkg"),
    )
    failed: list[str] = []
    ctrl.install_failed.connect(failed.append)
    ctrl.install_via_file_picker()
    assert failed == ["fake target exists"]


# ---------------------------------------------------------------------
# Uninstall
# ---------------------------------------------------------------------


def test_uninstall_request_removes_package_and_refreshes(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    pkg = _build_pkg(tmp_path)
    root = tmp_path / "packages"
    install_package(pkg, root)
    assert (root / "demo-tracker").is_dir()

    ctrl = PackageManagerController(packages_root=root, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)

    completed: list[UninstallResult] = []
    ctrl.uninstall_completed.connect(completed.append)

    dlg.panel().uninstall_requested.emit("demo-tracker")
    assert not (root / "demo-tracker").exists()
    assert len(completed) == 1
    assert completed[0].package_id == "demo-tracker"
    assert dlg.panel().installed_packages() == ()


def test_uninstall_failure_emits_uninstall_failed(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)

    def raising_uninstaller(*_args: object, **_kwargs: object) -> UninstallResult:
        msg = "no package installed"
        raise PackageNotInstalledError(msg)

    ctrl = PackageManagerController(
        packages_root=tmp_path,
        parent=host,
        uninstaller=raising_uninstaller,
    )
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)

    failed: list[str] = []
    ctrl.uninstall_failed.connect(failed.append)
    dlg.panel().uninstall_requested.emit("ghost")
    assert failed == ["no package installed"]


# ---------------------------------------------------------------------
# Refresh button on panel
# ---------------------------------------------------------------------


def test_panel_refresh_button_triggers_rescan(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    root = tmp_path / "packages"
    ctrl = PackageManagerController(packages_root=root, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    assert dlg.panel().installed_packages() == ()

    # Install a package *outside* of the controller flow, then ask the
    # panel to refresh — controller should pick up the new entry.
    pkg = _build_pkg(tmp_path)
    install_package(pkg, root)
    dlg.panel().refresh_requested.emit()
    rows = dlg.panel().installed_packages()
    assert len(rows) == 1
    assert rows[0].package_id == "demo-tracker"


# ---------------------------------------------------------------------
# Custom dialog factory
# ---------------------------------------------------------------------


def test_custom_dialog_factory_used(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    factory_calls: list[None] = []

    def fake_factory(parent: object) -> PackageManagerDialog:
        factory_calls.append(None)
        return PackageManagerDialog()

    ctrl = PackageManagerController(
        packages_root=tmp_path,
        parent=host,
        dialog_factory=fake_factory,  # type: ignore[arg-type]
    )
    ctrl.open_dialog()
    assert len(factory_calls) == 1


# ---------------------------------------------------------------------
# Multi-package refresh ordering
# ---------------------------------------------------------------------


def test_refresh_returns_rows_sorted_by_package_id(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    host = QMainWindow()
    qtbot.addWidget(host)
    root = tmp_path / "packages"
    install_package(_build_pkg(tmp_path, pkg_id="zeta-pkg"), root)
    install_package(_build_pkg(tmp_path, pkg_id="alpha-pkg"), root)
    install_package(_build_pkg(tmp_path, pkg_id="mid-pkg"), root)
    ctrl = PackageManagerController(packages_root=root, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    ids = [row.package_id for row in dlg.panel().installed_packages()]
    assert ids == ["alpha-pkg", "mid-pkg", "zeta-pkg"]


def test_installed_row_display_format(qtbot, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """Smoke: refreshed rows render through the panel's display()."""
    host = QMainWindow()
    qtbot.addWidget(host)
    root = tmp_path / "packages"
    install_package(_build_pkg(tmp_path), root)
    ctrl = PackageManagerController(packages_root=root, parent=host)
    dlg = ctrl.open_dialog()
    qtbot.addWidget(dlg)
    rows = dlg.panel().installed_packages()
    assert isinstance(rows[0], InstalledPackageRow)
    assert "demo-tracker" in rows[0].display()
