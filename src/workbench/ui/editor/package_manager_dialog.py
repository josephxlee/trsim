"""DLC Package Manager dialog + controller (Phase 7 remainder F2).

Wraps the existing :class:`PackageManagerPanel` in a modal
:class:`QDialog` and glues its three button signals to the
:mod:`workbench.app.dlc.installer` service:

- ``install_requested`` → file picker → :func:`install_package` →
  refresh list.
- ``uninstall_requested(package_id)`` → :func:`uninstall_package` →
  refresh list.
- ``refresh_requested`` → re-scan via :class:`PackageManager`.

The panel itself stays I/O-free (plan/17 § 17.5 separation). The
controller owns the filesystem orchestration so unit tests can drive
the panel directly without dialogs, and can mock the runner functions
to verify wiring.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from workbench.app.dlc import (
    InstallResult,
    PackageAlreadyInstalledError,
    PackageEscapedRootError,
    PackageManager,
    PackageNotInstalledError,
    UninstallResult,
    install_package,
    uninstall_package,
)
from workbench.ui.editor.package_manager_panel import (
    InstalledPackageRow,
    PackageManagerPanel,
)

InstallRunner = Callable[..., InstallResult]
UninstallRunner = Callable[..., UninstallResult]


class PackageManagerDialog(QDialog):
    """Modal dialog hosting a :class:`PackageManagerPanel`.

    Exists so the panel can be opened on demand from the Plugins
    menu without needing a permanent QDockWidget slot in the
    MainWindow layout.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PackageManagerDialog")
        self.setWindowTitle("DLC Package Manager")
        self.setModal(True)
        self.resize(560, 420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._panel = PackageManagerPanel(self)
        layout.addWidget(self._panel)

    def panel(self) -> PackageManagerPanel:
        """Return the embedded :class:`PackageManagerPanel`."""
        return self._panel


class PackageManagerController(QObject):
    """Wire :class:`PackageManagerDialog` signals to the installer service.

    Args:
        packages_root: Install location (``~/.trsim/packages`` by
            default). The controller writes here and asks
            :class:`PackageManager` to scan it.
        parent: Owner widget — usually the MainWindow.
        installer: Optional override for the install runner (defaults
            to :func:`install_package`). Tests inject fakes.
        uninstaller: Optional override for the uninstall runner.
        dialog_factory: Optional override for the dialog constructor.
        file_picker: Optional override returning the user-selected
            archive Path, or ``None`` if cancelled. Tests inject a
            constant to skip QFileDialog.

    The controller is single-window — calling :meth:`open_dialog`
    a second time while the dialog is open just re-shows the existing
    instance. The dialog's ``finished`` signal clears the reference so
    a fresh dialog opens next time.
    """

    install_completed = Signal(InstallResult)
    uninstall_completed = Signal(UninstallResult)
    install_failed = Signal(str)
    uninstall_failed = Signal(str)

    def __init__(
        self,
        *,
        packages_root: Path,
        parent: QWidget,
        installer: InstallRunner = install_package,
        uninstaller: UninstallRunner = uninstall_package,
        dialog_factory: Callable[[QWidget], PackageManagerDialog] | None = None,
        file_picker: Callable[[QWidget], Path | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._packages_root = Path(packages_root)
        self._parent = parent
        self._installer = installer
        self._uninstaller = uninstaller
        self._dialog_factory = dialog_factory or (lambda p: PackageManagerDialog(p))
        self._file_picker = file_picker or self._default_file_picker
        self._active_dialog: PackageManagerDialog | None = None

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------
    def open_dialog(self) -> PackageManagerDialog:
        """Show + populate the dialog (creating it on first call)."""
        if self._active_dialog is not None:
            self._active_dialog.show()
            self._active_dialog.raise_()
            return self._active_dialog
        dlg = self._dialog_factory(self._parent)
        panel = dlg.panel()
        panel.install_requested.connect(self._on_install_requested)
        panel.uninstall_requested.connect(self._on_uninstall_requested)
        panel.refresh_requested.connect(self.refresh)
        dlg.finished.connect(self._on_dialog_finished)
        self._active_dialog = dlg
        self.refresh()
        dlg.show()
        return dlg

    def active_dialog(self) -> PackageManagerDialog | None:
        return self._active_dialog

    def packages_root(self) -> Path:
        return self._packages_root

    def refresh(self) -> None:
        """Re-scan ``packages_root`` and repopulate the panel."""
        if self._active_dialog is None:
            return
        mgr = PackageManager(self._packages_root)
        loaded = mgr.scan()
        rows = [
            InstalledPackageRow(
                package_id=pkg.manifest.package.package_id,
                name=pkg.manifest.package.name,
                version=pkg.manifest.package.version,
            )
            for pkg in loaded
        ]
        self._active_dialog.panel().set_installed_packages(rows)

    # ------------------------------------------------------------------
    # Quick install — used by the new "Install Package..." menu entry
    # (F3) when the user wants to skip opening the full manager.
    # ------------------------------------------------------------------
    def install_via_file_picker(self) -> InstallResult | None:
        """Prompt the user for a ``.trsim-pkg`` + run install.

        Returns ``None`` on cancel or failure (errors emit
        ``install_failed``). On success the active dialog (if any) is
        refreshed and ``install_completed`` fires.
        """
        chosen = self._file_picker(self._parent)
        if chosen is None:
            return None
        return self._run_install(chosen)

    # ------------------------------------------------------------------
    # Internal slots
    # ------------------------------------------------------------------
    def _on_install_requested(self) -> None:
        self.install_via_file_picker()

    def _on_uninstall_requested(self, package_id: str) -> None:
        try:
            result = self._uninstaller(package_id, self._packages_root)
        except (PackageNotInstalledError, PackageEscapedRootError) as exc:
            self.uninstall_failed.emit(str(exc))
            return
        self.uninstall_completed.emit(result)
        self.refresh()

    def _on_dialog_finished(self, _result: int) -> None:
        self._active_dialog = None

    def _run_install(self, pkg_path: Path) -> InstallResult | None:
        try:
            result = self._installer(pkg_path, self._packages_root)
        except (
            FileNotFoundError,
            ValueError,
            PackageAlreadyInstalledError,
        ) as exc:
            self.install_failed.emit(str(exc))
            return None
        self.install_completed.emit(result)
        self.refresh()
        return result

    def _default_file_picker(self, parent: QWidget) -> Path | None:
        path_str, _ = QFileDialog.getOpenFileName(
            parent,
            "Select DLC package",
            "",
            "TRsim DLC packages (*.trsim-pkg);;Zip archives (*.zip);;All files (*)",
        )
        if not path_str:
            return None
        return Path(path_str)


def show_failure_message(parent: QWidget, title: str, message: str) -> None:
    """Convenience helper for callers that want a default error dialog."""
    QMessageBox.warning(parent, title, message)
