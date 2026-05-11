"""DLC manifest.toml schema + parser (plan/17 § 17.2.4).

Phase 7.1 — read-only schema. The TOML file lives at the root of a
``.trsim-pkg`` and declares every entry point the PackageManager
(Phase 7.2) needs to register the package's plugins / resources / UI
panels.

Validation rules (plan/17 § 17.2.4):

- ``package.id`` — non-empty, kebab-case (lowercase letters, digits,
  hyphens). Used as the on-disk directory name under
  ``~/.trsim/packages/``.
- ``package.version`` — SemVer ``MAJOR.MINOR.PATCH`` (extra
  pre-release / build metadata accepted but not parsed).
- ``package.license`` — non-empty. DLC authors must declare one.
- ``compatibility.trsim_min_version`` — required SemVer.
- ``compatibility.trsim_max_version`` — optional; ``"1.x"`` (any
  string) is allowed for "supports 1.X line".

Out of scope at this layer:

- Plugin loading / import-by-string (Phase 7.2 PluginLoader).
- Marketplace metadata (license matrix, signatures, etc.).
- TOML write — manifests are authored externally.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

_PACKAGE_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")
"""Kebab-case: lowercase + digits + hyphen, no leading/trailing hyphen."""

_SEMVER_RE = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def _validate_semver(value: str, field_name: str) -> None:
    if not _SEMVER_RE.match(value):
        msg = f"{field_name} must be SemVer 'MAJOR.MINOR.PATCH', got {value!r}"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class PackageMeta:
    """``[package]`` block — top-level identification.

    Attributes:
        package_id: Globally-unique kebab-case identifier.
        name: Human-readable display name (free-form).
        version: SemVer string.
        author: ``"Name <email>"`` free-form.
        description: One-line description shown in the install dialog.
        license: SPDX identifier ("MIT", "Apache-2.0", "GPL-3.0", etc.).
        homepage: Optional URL.

    Raises:
        ValueError: For empty package_id / name / version / license,
            non-kebab-case package_id, non-SemVer version.
    """

    package_id: str
    name: str
    version: str
    author: str = ""
    description: str = ""
    license: str = ""
    homepage: str = ""

    def __post_init__(self) -> None:
        if not self.package_id:
            msg = "PackageMeta.package_id must be a non-empty string"
            raise ValueError(msg)
        if not _PACKAGE_ID_RE.match(self.package_id):
            msg = (
                f"PackageMeta.package_id must be kebab-case (lowercase, "
                f"digits, hyphens), got {self.package_id!r}"
            )
            raise ValueError(msg)
        if not self.name:
            msg = "PackageMeta.name must be a non-empty string"
            raise ValueError(msg)
        if not self.version:
            msg = "PackageMeta.version must be a non-empty string"
            raise ValueError(msg)
        _validate_semver(self.version, "PackageMeta.version")
        if not self.license:
            msg = (
                "PackageMeta.license must be a non-empty string (DLC "
                "authors must declare a licence, plan/17 § 17.2.4)"
            )
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class CompatibilitySpec:
    """``[compatibility]`` block — TRsim version requirements.

    Attributes:
        trsim_min_version: Required SemVer string.
        trsim_max_version: Optional cap. Empty string means "no cap".
            Free-form strings like ``"1.x"`` are accepted (plan/17
            example) — the workbench resolves them at install time.

    Raises:
        ValueError: For empty / non-SemVer ``trsim_min_version``.
    """

    trsim_min_version: str
    trsim_max_version: str = ""

    def __post_init__(self) -> None:
        if not self.trsim_min_version:
            msg = "CompatibilitySpec.trsim_min_version must be non-empty"
            raise ValueError(msg)
        _validate_semver(self.trsim_min_version, "CompatibilitySpec.trsim_min_version")


@dataclass(frozen=True, slots=True)
class PythonDeps:
    """``[python]`` block — extra Python requirements.

    Attributes:
        extra_requires: Tuple of pip-style requirement strings
            (``"torch>=2.0"`` etc.). The workbench resolves these
            against the active environment at install time.
    """

    extra_requires: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PackageManifest:
    """Full manifest.toml (plan/17 § 17.2.4).

    Attributes:
        package: ``[package]`` block.
        compatibility: ``[compatibility]`` block.
        dependencies: ``[dependencies]`` mapping
            ``other_package_id -> version_constraint``.
        entry_points: ``[entry_points]`` mapping
            ``slot_name -> "module:attr"`` or ``"path/"``.
        python: ``[python]`` block.
    """

    package: PackageMeta
    compatibility: CompatibilitySpec
    dependencies: Mapping[str, str] = field(default_factory=dict)
    entry_points: Mapping[str, str] = field(default_factory=dict)
    python: PythonDeps = field(default_factory=PythonDeps)


def load_manifest_from_toml(path: Path | str) -> PackageManifest:
    """Read + validate a manifest.toml.

    Args:
        path: ``.trsim-pkg`` 의 ``manifest.toml`` 경로.

    Returns:
        Parsed :class:`PackageManifest`.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: For missing top-level sections, schema violations
            (covered by the dataclass __post_init__ rules), or invalid
            TOML.
    """
    path_obj = Path(path)
    with path_obj.open("rb") as handle:
        blob = tomllib.load(handle)
    return _manifest_from_blob(blob, source=str(path_obj))


def _manifest_from_blob(blob: Mapping[str, object], *, source: str = "<memory>") -> PackageManifest:
    pkg_blob = blob.get("package")
    if not isinstance(pkg_blob, Mapping):
        msg = f"{source}: [package] section missing or not a table"
        raise ValueError(msg)
    compat_blob = blob.get("compatibility")
    if not isinstance(compat_blob, Mapping):
        msg = f"{source}: [compatibility] section missing or not a table"
        raise ValueError(msg)

    package = PackageMeta(
        package_id=str(pkg_blob["id"]),
        name=str(pkg_blob["name"]),
        version=str(pkg_blob["version"]),
        author=str(pkg_blob.get("author", "")),
        description=str(pkg_blob.get("description", "")),
        license=str(pkg_blob.get("license", "")),
        homepage=str(pkg_blob.get("homepage", "")),
    )
    compatibility = CompatibilitySpec(
        trsim_min_version=str(compat_blob["trsim_min_version"]),
        trsim_max_version=str(compat_blob.get("trsim_max_version", "")),
    )

    deps_blob = blob.get("dependencies", {})
    if not isinstance(deps_blob, Mapping):
        msg = f"{source}: [dependencies] must be a table"
        raise ValueError(msg)
    dependencies = {str(k): str(v) for k, v in deps_blob.items()}

    ep_blob = blob.get("entry_points", {})
    if not isinstance(ep_blob, Mapping):
        msg = f"{source}: [entry_points] must be a table"
        raise ValueError(msg)
    entry_points = {str(k): str(v) for k, v in ep_blob.items()}

    py_blob = blob.get("python", {})
    if not isinstance(py_blob, Mapping):
        msg = f"{source}: [python] must be a table"
        raise ValueError(msg)
    extra_raw = py_blob.get("extra_requires", [])
    if not isinstance(extra_raw, list):
        msg = f"{source}: [python].extra_requires must be a list"
        raise ValueError(msg)
    python = PythonDeps(extra_requires=tuple(str(x) for x in extra_raw))

    return PackageManifest(
        package=package,
        compatibility=compatibility,
        dependencies=dependencies,
        entry_points=entry_points,
        python=python,
    )
