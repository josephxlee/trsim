"""DLC install / uninstall service (Phase 7 remainder F1, plan/17 § 17.5).

Pure app-layer functions shared by the ``trsim install`` /
``trsim uninstall`` CLI and the Editor's Package Manager dialog.

The CLI was the first caller (Phase 7 C4 + C7) and embedded the
filesystem orchestration inline. Adding the UI Package Manager
dialog (this cycle's F2) needed the same logic — so we extract it
here and the CLI becomes a thin wrapper that adds stdout / exit-code
plumbing.

Public API:

- :func:`install_package(pkg_path, packages_root, force=False) ->
  InstallResult` — unpacks ``pkg_path`` into ``packages_root / <id>``.
- :func:`uninstall_package(package_id, packages_root) ->
  UninstallResult` — recursively removes the install dir, defending
  against path-escape via malformed ``package_id``.

Both raise typed exceptions for the caller to format:

- :class:`PackageAlreadyInstalledError` — install target exists and
  ``force`` is False.
- :class:`PackageNotInstalledError` — uninstall target does not exist.
- :class:`PackageEscapedRootError` — uninstall target resolves outside
  ``packages_root`` (path-escape defence).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from workbench.io.package_io import read_manifest_from_package, unpack_package
from workbench.sdk.manifest import PackageManifest


@dataclass(frozen=True, slots=True)
class InstallResult:
    """Result of a successful :func:`install_package` call.

    Attributes:
        manifest: Parsed :class:`PackageManifest` from the source
            archive. Saves callers a duplicate read.
        target_dir: Absolute path the package was extracted into.
        force: Whether ``force=True`` caused an existing target to be
            overwritten. ``False`` means the target was created fresh.
    """

    manifest: PackageManifest
    target_dir: Path
    force: bool


@dataclass(frozen=True, slots=True)
class UninstallResult:
    """Result of a successful :func:`uninstall_package` call."""

    package_id: str
    removed_dir: Path


class PackageAlreadyInstalledError(FileExistsError):
    """Raised when :func:`install_package` finds an existing target
    directory and ``force`` is False.
    """


class PackageNotInstalledError(FileNotFoundError):
    """Raised when :func:`uninstall_package` cannot find the target."""


class PackageEscapedRootError(ValueError):
    """Raised when a malformed ``package_id`` resolves outside
    ``packages_root`` — defends against ``../../etc/passwd`` style
    arguments.
    """


def _default_packages_root() -> Path:
    """Default install location (``~/.trsim/packages``)."""
    return (Path.home() / ".trsim" / "packages").resolve()


def install_package(
    pkg_path: Path | str,
    packages_root: Path | str | None = None,
    *,
    force: bool = False,
) -> InstallResult:
    """Install ``pkg_path`` into ``packages_root / <package_id>``.

    Args:
        pkg_path: ``.trsim-pkg`` archive to install.
        packages_root: Directory under which the package's
            ``<id>/`` subdirectory will be created. Defaults to
            ``~/.trsim/packages``.
        force: When True, an existing ``<id>/`` is removed (recursive)
            before extraction — same UX as ``pip install
            --force-reinstall``. When False, an existing target
            raises :class:`PackageAlreadyInstalledError`.

    Returns:
        :class:`InstallResult` with the parsed manifest, target dir,
        and whether ``force`` overwrote a previous install.

    Raises:
        FileNotFoundError: Source archive does not exist.
        ValueError: Archive is malformed or manifest is invalid
            (propagated from :func:`read_manifest_from_package` /
            :func:`unpack_package`).
        PackageAlreadyInstalledError: Target exists and ``force`` is False.
    """
    pkg = Path(pkg_path).expanduser()
    manifest = read_manifest_from_package(pkg)

    root = (
        Path(packages_root).expanduser().resolve()
        if packages_root is not None
        else _default_packages_root()
    )
    target = root / manifest.package.package_id

    existed = target.exists()
    if existed and not force:
        msg = f"{target} already exists. Use force=True to overwrite."
        raise PackageAlreadyInstalledError(msg)
    if existed:
        shutil.rmtree(target)

    root.mkdir(parents=True, exist_ok=True)
    unpack_package(pkg, target)
    return InstallResult(manifest=manifest, target_dir=target, force=existed)


def uninstall_package(
    package_id: str,
    packages_root: Path | str | None = None,
) -> UninstallResult:
    """Remove ``packages_root / <package_id>`` recursively.

    Args:
        package_id: Package identifier (manifest ``[package].id``).
        packages_root: Install root. Defaults to
            ``~/.trsim/packages``.

    Returns:
        :class:`UninstallResult` capturing the removed directory.

    Raises:
        PackageEscapedRootError: ``package_id`` (e.g. ``"../etc/passwd"``)
            resolves outside ``packages_root``.
        PackageNotInstalledError: Target directory does not exist.
    """
    root = (
        Path(packages_root).expanduser().resolve()
        if packages_root is not None
        else _default_packages_root()
    )
    target = (root / package_id).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        msg = f"package_id {package_id!r} resolves outside packages_root {root}"
        raise PackageEscapedRootError(msg) from exc
    if not target.exists():
        msg = f"no package installed at {target}"
        raise PackageNotInstalledError(msg)
    shutil.rmtree(target)
    return UninstallResult(package_id=package_id, removed_dir=target)
