"""Editor Package Manager panel (Phase 7 C5, plan/17 § 17.2.4 + § 17.4.4).

UI front-end for the DLC install / uninstall workflow. Shows the
list of currently-installed packages (from
:class:`workbench.app.dlc.package_manager.PackageManager`) and
provides three actions:

- **Install...** — emit ``install_requested(Path)`` so the wiring
  layer (MainWindow / EditorWorkspace) can spawn a file picker
  and route the choice through :func:`workbench.io.package_io.
  unpack_package`.
- **Uninstall** — emit ``uninstall_requested(str)`` with the
  selected ``package_id`` so the wiring layer can ``shutil.rmtree``
  the install dir and trigger a PackageManager rescan.
- **Refresh** — emit ``refresh_requested()`` so the caller re-scans
  ``~/.trsim/packages/`` and calls :meth:`set_installed_packages`
  with the fresh list.

The panel is intentionally I/O-free — it never touches the
filesystem itself. This keeps the widget testable without a fake
filesystem and lets the MainWindow choose the user-resolved paths
(important for the file-picker flow).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True, slots=True)
class InstalledPackageRow:
    """One row in the Package Manager panel.

    Attributes:
        package_id: Stable identifier from manifest.toml [package].id.
        name: Display name from manifest.toml [package].name.
        version: SemVer string.
    """

    package_id: str
    name: str
    version: str

    def display(self) -> str:
        """Row label shown in the QListWidget."""
        return f"{self.name} ({self.package_id}) — v{self.version}"


class PackageManagerPanel(QWidget):
    """List of installed DLC packages + install / uninstall / refresh actions."""

    install_requested = Signal()
    """Emitted when the user clicks Install — wiring layer opens the
    file picker."""
    uninstall_requested = Signal(str)
    """Emitted with the selected ``package_id``."""
    refresh_requested = Signal()
    """Re-scan request — wiring layer re-runs PackageManager.scan()."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("PackageManagerPanel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self._header = QLabel("Installed DLC Packages", self)
        self._header.setObjectName("PackageManagerHeader")
        layout.addWidget(self._header)

        self._list = QListWidget(self)
        self._list.setObjectName("PackageManagerList")
        layout.addWidget(self._list, 1)

        self._action_row = self._build_action_row()
        layout.addWidget(self._action_row)

        self._rows: list[InstalledPackageRow] = []

    # ------------------------------------------------------------------
    # Builders
    # ------------------------------------------------------------------

    def _build_action_row(self) -> QWidget:
        row = QWidget(self)
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)

        self._install_btn = QPushButton("Install...", row)
        self._install_btn.setObjectName("PackageManagerInstallBtn")
        self._install_btn.clicked.connect(self.install_requested)
        h.addWidget(self._install_btn)

        self._uninstall_btn = QPushButton("Uninstall", row)
        self._uninstall_btn.setObjectName("PackageManagerUninstallBtn")
        self._uninstall_btn.setEnabled(False)
        self._uninstall_btn.clicked.connect(self._emit_uninstall_for_selected)
        h.addWidget(self._uninstall_btn)

        self._refresh_btn = QPushButton("Refresh", row)
        self._refresh_btn.setObjectName("PackageManagerRefreshBtn")
        self._refresh_btn.clicked.connect(self.refresh_requested)
        h.addWidget(self._refresh_btn)

        h.addStretch(1)

        self._list.currentRowChanged.connect(self._update_uninstall_button_state)
        return row

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_installed_packages(self, rows: Sequence[InstalledPackageRow]) -> None:
        """Replace the displayed list of packages.

        Idempotent — the same input replaces the same set of QListWidget
        rows. The current selection is cleared.
        """
        self._rows = list(rows)
        self._list.blockSignals(True)
        self._list.clear()
        for row in self._rows:
            item = QListWidgetItem(row.display())
            item.setData(0x0100, row.package_id)  # Qt.UserRole
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._update_uninstall_button_state()

    def installed_packages(self) -> tuple[InstalledPackageRow, ...]:
        """Snapshot of the rows currently displayed."""
        return tuple(self._rows)

    def selected_package_id(self) -> str | None:
        """``package_id`` of the highlighted row, or ``None`` if none."""
        item = self._list.currentItem()
        if item is None:
            return None
        data = item.data(0x0100)
        return str(data) if isinstance(data, str) else None

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _emit_uninstall_for_selected(self) -> None:
        pkg_id = self.selected_package_id()
        if pkg_id is not None:
            self.uninstall_requested.emit(pkg_id)

    def _update_uninstall_button_state(self) -> None:
        self._uninstall_btn.setEnabled(self.selected_package_id() is not None)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def list_widget(self) -> QListWidget:
        return self._list

    def install_button(self) -> QPushButton:
        return self._install_btn

    def uninstall_button(self) -> QPushButton:
        return self._uninstall_btn

    def refresh_button(self) -> QPushButton:
        return self._refresh_btn
