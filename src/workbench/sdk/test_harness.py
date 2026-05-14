"""DLC test harness (Phase 7 C3, plan/17 § 17.2.6).

A ``trsim sdk test`` check before publishing a ``.trsim-pkg``:

1. The file exists and is a valid zip archive.
2. The zip contains a root ``manifest.toml`` that parses.
3. The manifest's compatibility section is non-empty (trsim_min
   version present).

This is intentionally conservative — it catches the common
"obviously broken" cases without trying to import plugin source
(which would require dependency installation). Plugin import is
a runtime concern handled by :mod:`workbench.app.dlc.plugin_loader`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PackageTestResult:
    """Outcome of :func:`test_package`.

    Attributes:
        package_id: Echo of the manifest's ``[package].id``.
        package_name: Echo of the manifest's ``[package].name``.
        package_version: Echo of ``[package].version``.
        trsim_min_version: ``[compatibility].trsim_min_version`` value.
        issues: Tuple of non-fatal warnings (e.g. empty description).
            Empty tuple = clean run.
    """

    package_id: str
    package_name: str
    package_version: str
    trsim_min_version: str
    issues: tuple[str, ...] = ()


def test_package(pkg_path: Path | str) -> PackageTestResult:
    """Lightweight sanity check on a ``.trsim-pkg``.

    Args:
        pkg_path: Archive to inspect.

    Returns:
        :class:`PackageTestResult` summarising the manifest +
        non-fatal issues found. Empty ``issues`` tuple = clean.

    Raises:
        FileNotFoundError: ``pkg_path`` does not exist.
        ValueError: Archive is missing ``manifest.toml`` or the
            manifest fails to parse / validate.
    """
    # Lazy import — see :mod:`workbench.sdk.package_builder` for the
    # same defence: sdk/__init__.py eagerly imports this module, and
    # package_io now imports :mod:`workbench.sdk.manifest`, so a
    # top-level import would create a circular load.
    from workbench.io.package_io import read_manifest_from_package

    manifest = read_manifest_from_package(pkg_path)
    issues: list[str] = []
    if not manifest.package.description:
        issues.append("[package].description is empty (recommended for marketplace listing)")
    if not manifest.package.author:
        issues.append("[package].author is empty (recommended for attribution)")
    return PackageTestResult(
        package_id=manifest.package.package_id,
        package_name=manifest.package.name,
        package_version=manifest.package.version,
        trsim_min_version=manifest.compatibility.trsim_min_version,
        issues=tuple(issues),
    )
