"""Package Manager — scan + register installed .trsim-pkg (plan/17 § 17.4.2).

Phase 7.2 — reads every ``manifest.toml`` under the configured
packages root and exposes the parsed records via :class:`LoadedPackage`.
The MVP does not import any plugin code or copy resources; the
PluginLoader / ResourceLibrary integration lives in later sub-steps.

Directory layout (plan/17 § 17.2.4):

::

    <packages_root>/
    ├── advanced-tracker/
    │   ├── manifest.toml
    │   ├── plugins/
    │   ├── resources/
    │   └── ...
    └── glint-modeling-extras/
        └── manifest.toml

Each top-level directory under ``packages_root`` is treated as one
candidate package. Subdirectories without ``manifest.toml`` are
ignored (with an error message accumulated in :attr:`PackageManager.
load_errors`).

Duplicate ``package_id`` across two directories is an error — the
first directory wins, the second is recorded in ``load_errors``.

References:

- plan/17 § 17.2.4 — DLC format.
- plan/17 § 17.4.2 — Plugin Loader (consumes this output).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.domain.dlc import PackageManifest, load_manifest_from_toml


@dataclass(frozen=True, slots=True)
class LoadedPackage:
    """One installed package on disk.

    Attributes:
        manifest: Parsed :class:`PackageManifest`.
        root: Absolute path to the package's top-level directory.
            Plugin / resource paths inside the manifest are resolved
            relative to this root.
    """

    manifest: PackageManifest
    root: Path

    @property
    def package_id(self) -> str:
        """Shortcut to ``self.manifest.package.package_id``."""
        return self.manifest.package.package_id


@dataclass(frozen=True, slots=True)
class PackageLoadError:
    """One entry in :attr:`PackageManager.load_errors`.

    Attributes:
        path: Directory or file that triggered the error.
        message: Human-readable reason (free-form English).
    """

    path: Path
    message: str


class PackageManager:
    """Lazy scanner over ``packages_root`` for installed ``.trsim-pkg``.

    Construction does not scan; the caller invokes :meth:`scan` to
    populate the registry. Re-scan replaces the previous state — the
    common pattern is "scan once at startup, re-scan after install /
    uninstall actions".

    Attributes:
        packages_root: Directory the manager scans (``~/.trsim/
            packages/`` by convention).
    """

    def __init__(self, packages_root: Path | str) -> None:
        self.packages_root = Path(packages_root)
        self._packages: dict[str, LoadedPackage] = {}
        self._load_errors: list[PackageLoadError] = []

    # ------------------------------------------------------------------
    # Scan
    # ------------------------------------------------------------------

    def scan(self) -> tuple[LoadedPackage, ...]:
        """Discover packages under :attr:`packages_root`.

        Returns:
            Tuple of newly-loaded packages, sorted by ``package_id``
            for deterministic iteration. The same data is also
            available via :meth:`installed_ids` / :meth:`get`.

        Notes:
            Missing root is *not* an error — an empty workbench install
            has nothing under ``~/.trsim/packages/``. The result is
            simply an empty tuple.
        """
        self._packages = {}
        self._load_errors = []
        if not self.packages_root.exists():
            return ()
        if not self.packages_root.is_dir():
            self._load_errors.append(
                PackageLoadError(
                    path=self.packages_root,
                    message=f"packages_root is not a directory: {self.packages_root}",
                )
            )
            return ()

        for entry in sorted(self.packages_root.iterdir()):
            if not entry.is_dir():
                continue
            manifest_path = entry / "manifest.toml"
            if not manifest_path.is_file():
                self._load_errors.append(
                    PackageLoadError(
                        path=entry,
                        message="missing manifest.toml",
                    )
                )
                continue
            try:
                manifest = load_manifest_from_toml(manifest_path)
            except (ValueError, OSError) as exc:
                self._load_errors.append(PackageLoadError(path=manifest_path, message=str(exc)))
                continue

            pkg = LoadedPackage(manifest=manifest, root=entry.resolve())
            if pkg.package_id in self._packages:
                existing = self._packages[pkg.package_id].root
                self._load_errors.append(
                    PackageLoadError(
                        path=entry,
                        message=(
                            f"duplicate package_id {pkg.package_id!r} (first claim at {existing})"
                        ),
                    )
                )
                continue
            self._packages[pkg.package_id] = pkg

        return tuple(self._packages[k] for k in sorted(self._packages))

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get(self, package_id: str) -> LoadedPackage | None:
        return self._packages.get(package_id)

    def installed_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._packages.keys()))

    @property
    def load_errors(self) -> tuple[PackageLoadError, ...]:
        return tuple(self._load_errors)
