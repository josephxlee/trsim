"""DLC App layer (plan/17 § 17.4.2).

Phase 7.2 — :class:`PackageManager` scans ``~/.trsim/packages/`` (or a
caller-supplied root) and exposes the installed
:class:`workbench.sdk.manifest.PackageManifest` records to the
workbench. Plugin loading / entry-point resolution lives in the
Phase 7.3+ PluginLoader, layered on top of this.
"""

from __future__ import annotations

from workbench.app.dlc.installer import (
    InstallResult,
    PackageAlreadyInstalledError,
    PackageEscapedRootError,
    PackageNotInstalledError,
    UninstallResult,
    install_package,
    uninstall_package,
)
from workbench.app.dlc.package_manager import (
    LoadedPackage,
    PackageLoadError,
    PackageManager,
)
from workbench.app.dlc.plugin_loader import (
    LoadedPlugin,
    PluginLoader,
    PluginLoadError,
)

__all__ = [
    "InstallResult",
    "LoadedPackage",
    "LoadedPlugin",
    "PackageAlreadyInstalledError",
    "PackageEscapedRootError",
    "PackageLoadError",
    "PackageManager",
    "PackageNotInstalledError",
    "PluginLoadError",
    "PluginLoader",
    "UninstallResult",
    "install_package",
    "uninstall_package",
]
