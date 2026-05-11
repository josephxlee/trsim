"""App-layer DLC runtime assembly (plan/17 § 17.4 finale).

Phase 7.6 — collects the three App-layer DLC services into one
container so the workbench start-up (CLI entry / MainWindow) can spin
up the full DLC pipeline in two lines:

1. :class:`workbench.app.dlc.PackageManager` — scans
   ``~/.trsim/packages/`` for installed ``.trsim-pkg`` directories.
2. :class:`workbench.app.dlc.PluginLoader` — resolves each manifest's
   ``[entry_points]`` map to Python callables / resource directories.
3. :class:`workbench.app.resources.ResourceLibrary` — merges User /
   Package / Built-in resource roots into one index.

The UI-layer counterpart (:mod:`workbench.ui.dlc_bootstrap`) builds on
top of this to register DLC UI panels and feed the Editor's Resource
Browser sidebar.

Path policy (plan/17 § 17.2.4 / § 17.4.3):

- ``packages_root`` = ``~/.trsim/packages/``.
- ``user_root`` = ``~/.trsim/`` (so ResourceLibrary picks up
  ``~/.trsim/resources/<category>/``).
- ``builtin_root`` is reserved for the shipped ``data/resources/``
  directory; left ``None`` here because the MVP does not yet ship
  built-in presets (Phase 5+ ResourceLibrary feed will populate it).

References:

- plan/17 § 17.4.2 — PackageManager + PluginLoader integration.
- plan/17 § 17.4.3 — ResourceLibrary 3-source priority.
- plan/04 § 4.3 Phase 7 통합 — three integration check-boxes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.app.dlc import PackageManager, PluginLoader
from workbench.app.resources import ResourceLibrary


@dataclass(frozen=True, slots=True)
class DLCPaths:
    """Filesystem roots the runtime hands to its three layers.

    Attributes:
        packages_root: Directory scanned by :class:`PackageManager`.
            Missing directory is *not* an error — the scan simply
            returns no packages.
        user_root: Top-level user directory; the ResourceLibrary
            looks at ``user_root / "resources" / <category>``. ``None``
            disables the User tier.
        builtin_root: Shipped read-only resource root. Read as
            ``builtin_root / <category>``. ``None`` disables the
            Built-in tier (MVP default; preset shipping is a later
            sub-step).
    """

    packages_root: Path
    user_root: Path | None = None
    builtin_root: Path | None = None


def default_dlc_paths(*, home: Path | None = None) -> DLCPaths:
    """Return the standard ``~/.trsim/`` install layout.

    Args:
        home: Override for ``$HOME``; injected by tests to avoid
            touching the real user directory.

    Returns:
        ``DLCPaths(packages_root=<home>/.trsim/packages,
        user_root=<home>/.trsim, builtin_root=None)``.
    """
    base = (home if home is not None else Path.home()) / ".trsim"
    return DLCPaths(packages_root=base / "packages", user_root=base, builtin_root=None)


@dataclass(frozen=True, slots=True)
class DLCAppRuntime:
    """Three-layer App-side DLC bundle.

    Attributes:
        paths: The filesystem roots used to build the runtime.
        package_manager: Already-scanned :class:`PackageManager`.
        plugin_loader: Already-loaded :class:`PluginLoader`. Its
            :meth:`plugins_for_slot` is the only API the UI layer
            needs.
        resource_library: :class:`ResourceLibrary` initialised with
            the scanned packages plus the User / Built-in roots
            from ``paths``.
    """

    paths: DLCPaths
    package_manager: PackageManager
    plugin_loader: PluginLoader
    resource_library: ResourceLibrary


def build_dlc_app_runtime(paths: DLCPaths) -> DLCAppRuntime:
    """Assemble the three App-layer services from ``paths``.

    Sequence:

    1. Construct a :class:`PackageManager` over ``paths.packages_root``
       and call :meth:`PackageManager.scan` immediately.
    2. Construct a :class:`PluginLoader` over that manager and call
       :meth:`PluginLoader.load_all`.
    3. Build a :class:`ResourceLibrary` with the just-scanned packages
       plus the User / Built-in roots.

    Errors during scan / load are captured on the respective service
    objects (``load_errors`` properties); the runtime never raises.
    """
    package_manager = PackageManager(paths.packages_root)
    package_manager.scan()
    plugin_loader = PluginLoader(package_manager)
    plugin_loader.load_all()
    resource_library = ResourceLibrary(
        user_root=paths.user_root,
        packages=tuple(
            package_manager.get(pid)  # type: ignore[misc]
            for pid in package_manager.installed_ids()
            if package_manager.get(pid) is not None
        ),
        builtin_root=paths.builtin_root,
    )
    return DLCAppRuntime(
        paths=paths,
        package_manager=package_manager,
        plugin_loader=plugin_loader,
        resource_library=resource_library,
    )
