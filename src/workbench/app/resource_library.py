"""ResourceLibrary — directory-scan index of saved resources (plan/04 § 4.3, v0.20).

Phase 3.3 — scans a Workspace's ``resources/`` tree (``maps/``,
``radars/``, ``targets/``, ...) and returns an index keyed by
``(kind, id)``. Each entry carries a content hash (sha256 of the
TOML manifest) so the run-bundle export (plan/10 § 10.9.3) can
record resource_refs that pin a Run to exact resource bytes.

MVP layout assumption (plan/10 § 10.5):

- ``resources/maps/<id>.toml``
- ``resources/radars/<id>.toml``
- ``resources/targets/<id>.toml``

Each TOML carries at minimum ``id`` (matches the file stem at MVP).
Full schema validation belongs to Phase 3 ScenarioService /
EditorValidator (deferred).
"""

from __future__ import annotations

import hashlib
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# Recognised top-level resource kinds. Adding a new kind requires a
# matching subdirectory under resources/.
RESOURCE_KINDS: Final[tuple[str, ...]] = ("maps", "radars", "targets")


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    """One entry in the :class:`ResourceLibrary` index.

    Attributes:
        kind: Resource kind (``"maps"`` / ``"radars"`` / ``"targets"``).
        resource_id: Stable identifier (file stem; matches ``id`` in
            the TOML). Empty if the manifest doesn't declare it.
        path: Absolute path to the manifest file.
        content_hash: ``sha256:<hex>`` of the manifest bytes.
    """

    kind: str
    resource_id: str
    path: Path
    content_hash: str


def compute_content_hash(file_path: Path | str) -> str:
    """Return ``sha256:<hex>`` for the file's raw bytes."""
    digest = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _read_resource_id(toml_path: Path) -> str:
    """Best-effort ``id`` lookup from a resource TOML.

    Falls back to the file stem if the TOML doesn't declare an ``id``.
    """
    try:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)
    except tomllib.TOMLDecodeError:
        return toml_path.stem
    rid = data.get("id")
    if isinstance(rid, str) and rid:
        return rid
    return toml_path.stem


@dataclass(slots=True)
class ResourceLibrary:
    """Scan + index a ``resources/`` directory tree.

    Construct via :meth:`scan` to populate the index from disk; the
    constructor leaves it empty so tests can assemble a synthetic
    library.
    """

    root: Path
    _entries: dict[tuple[str, str], ResourceEntry] = field(default_factory=dict)

    @classmethod
    def scan(cls, root: Path | str) -> ResourceLibrary:
        """Build a library by scanning ``root`` for resource TOMLs.

        Args:
            root: Directory containing the ``maps/`` / ``radars/`` /
                ``targets/`` subdirs. Missing subdirs are silently
                skipped (a Workspace may not have every kind yet).

        Returns:
            A populated :class:`ResourceLibrary`.

        Raises:
            FileNotFoundError: If ``root`` doesn't exist.
        """
        root = Path(root)
        if not root.exists():
            msg = f"resource root does not exist: {root}"
            raise FileNotFoundError(msg)
        lib = cls(root=root)
        for kind in RESOURCE_KINDS:
            sub = root / kind
            if not sub.is_dir():
                continue
            for toml_path in sorted(sub.glob("*.toml")):
                rid = _read_resource_id(toml_path)
                content_hash = compute_content_hash(toml_path)
                lib._entries[(kind, rid)] = ResourceEntry(
                    kind=kind,
                    resource_id=rid,
                    path=toml_path.resolve(),
                    content_hash=content_hash,
                )
        return lib

    def add(self, entry: ResourceEntry) -> None:
        """Insert / replace a single entry."""
        self._entries[(entry.kind, entry.resource_id)] = entry

    def get(self, kind: str, resource_id: str) -> ResourceEntry:
        """Retrieve an indexed entry.

        Raises:
            KeyError: If no entry matches ``(kind, resource_id)``.
        """
        try:
            return self._entries[(kind, resource_id)]
        except KeyError as exc:
            msg = f"no resource {resource_id!r} of kind {kind!r}"
            raise KeyError(msg) from exc

    def has(self, kind: str, resource_id: str) -> bool:
        """Whether ``(kind, resource_id)`` is indexed."""
        return (kind, resource_id) in self._entries

    def list(self, kind: str | None = None) -> tuple[ResourceEntry, ...]:
        """All entries, optionally filtered by ``kind``.

        Order is stable: alphabetical by ``(kind, resource_id)``.
        """
        items: Iterable[ResourceEntry] = self._entries.values()
        if kind is not None:
            items = (e for e in items if e.kind == kind)
        return tuple(sorted(items, key=lambda e: (e.kind, e.resource_id)))

    def __len__(self) -> int:
        return len(self._entries)
