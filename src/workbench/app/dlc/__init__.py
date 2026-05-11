"""DLC App layer (plan/17 § 17.4.2).

Phase 7.2 — :class:`PackageManager` scans ``~/.trsim/packages/`` (or a
caller-supplied root) and exposes the installed
:class:`workbench.domain.dlc.PackageManifest` records to the
workbench. Plugin loading / entry-point resolution lives in the
Phase 7.3+ PluginLoader, layered on top of this.
"""

from __future__ import annotations

from workbench.app.dlc.package_manager import (
    LoadedPackage,
    PackageLoadError,
    PackageManager,
)

__all__ = ["LoadedPackage", "PackageLoadError", "PackageManager"]
