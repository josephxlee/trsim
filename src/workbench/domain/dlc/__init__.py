"""DLC (.trsim-pkg) packaging schema (plan/17 § 17.2.4).

Phase 7.1 — frozen dataclasses for the manifest.toml header that
every ``.trsim-pkg`` ships at its root. The PackageManager (Phase 7.2)
reads these records to register plugins / resources / UI panels into
the workbench. The schema is read-only at this layer — manifest files
are authored by DLC creators, not the workbench.

Schema layout (plan/17 § 17.2.4):

::

    manifest.toml
    ├── [package]          PackageMeta — id / name / version / etc.
    ├── [compatibility]    CompatibilitySpec — trsim_min/max_version
    ├── [dependencies]     dict[str, str] — pkg_id -> version_constraint
    ├── [entry_points]     dict[str, str] — slot_name -> target
    └── [python]           PythonDeps — extra_requires tuple

References:

- plan/17 § 17.2.4 — DLC format definition.
- plan/17 § 17.4.2 — Plugin Loader (reads manifest.toml).
- plan/17 § 17.4.3 — Resource Library 3-source split.
"""

from __future__ import annotations

from workbench.domain.dlc.manifest import (
    CompatibilitySpec,
    PackageManifest,
    PackageMeta,
    PythonDeps,
    load_manifest_from_toml,
)

__all__ = [
    "CompatibilitySpec",
    "PackageManifest",
    "PackageMeta",
    "PythonDeps",
    "load_manifest_from_toml",
]
