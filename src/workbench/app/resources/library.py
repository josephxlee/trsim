"""ResourceLibrary — 3-source merged index (plan/17 § 17.4.3).

Phase 7.4 — the Editor's Resource Browser sidebar (Phase 4.4) gets
its data through this library. Three source tiers, in priority order
**User > Package > Built-in**:

1. **User**: ``<user_root>/resources/<category>/``. Editor writes here.
2. **Package**: ``<package_root>/resources/<category>/`` for every
   installed :class:`workbench.app.dlc.LoadedPackage`.
3. **Built-in**: ``<builtin_root>/<category>/`` shipped with the
   workbench.

The library treats every immediate child entry (file or directory)
under ``<root>/<category>/`` as one resource. The entry name is the
file / directory's stem; collisions across sources are resolved by
priority — User wins over Package wins over Built-in. The library
records "shadowed" entries so the Editor can show a tooltip ("from
User; Built-in version available").

The MVP discovers entries lazily on every :meth:`list_resources`
call — re-indexing on demand keeps the code simple and lets the
Editor see file-system changes without an explicit refresh. The
typical resource counts (~10 maps, ~20 radars, ~30 targets) make
the IO cost negligible.

References:

- plan/17 § 17.4.3 — Resource Library 3-source split.
- plan/13 § 13.2.3 — Resource Browser sidebar consumes this output.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from workbench.app.dlc.package_manager import LoadedPackage


class ResourceCategory(Enum):
    """Top-level resource categories (plan/13 § 13.2)."""

    MAPS = "maps"
    RADARS = "radars"
    TARGETS = "targets"
    SCENARIOS = "scenarios"


RESOURCE_CATEGORIES: tuple[ResourceCategory, ...] = tuple(ResourceCategory)


class ResourceSource(Enum):
    """Which tier a :class:`ResourceEntry` came from (plan/17 § 17.4.3)."""

    USER = "user"
    PACKAGE = "package"
    BUILTIN = "builtin"


_PRIORITY: dict[ResourceSource, int] = {
    ResourceSource.USER: 0,
    ResourceSource.PACKAGE: 1,
    ResourceSource.BUILTIN: 2,
}


@dataclass(frozen=True, slots=True)
class ResourceEntry:
    """One resolved resource visible to the Editor.

    Attributes:
        resource_id: File or directory stem (``"east_coast_50km"``).
        category: Top-level category.
        source: Which tier the entry came from.
        path: Absolute path to the resource on disk.
        package_id: Owning package id when ``source = PACKAGE``;
            empty string otherwise.
        shadowed_by_source: Tuple of sources that shadow this entry
            (``USER > PACKAGE > BUILTIN``). Empty if no shadowing.
            For example a Built-in resource with the same id as a
            User one carries ``shadowed_by_source = (USER,)``.
    """

    resource_id: str
    category: ResourceCategory
    source: ResourceSource
    path: Path
    package_id: str = ""
    shadowed_by_source: tuple[ResourceSource, ...] = ()


class ResourceLibrary:
    """Three-source resource index.

    Attributes:
        user_root: ``<user>/resources/`` (the Editor's writeable
            workspace). ``None`` disables the user tier.
        builtin_root: ``<workbench>/resources/`` (read-only built-in
            presets). ``None`` disables the built-in tier.
        packages: Iterable of installed :class:`LoadedPackage`. Each
            contributes ``<root>/resources/<category>/``.
    """

    def __init__(
        self,
        *,
        user_root: Path | None = None,
        packages: Iterable[LoadedPackage] = (),
        builtin_root: Path | None = None,
    ) -> None:
        self.user_root = user_root
        self.builtin_root = builtin_root
        self._packages: tuple[LoadedPackage, ...] = tuple(packages)

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def list_resources(self, category: ResourceCategory) -> tuple[ResourceEntry, ...]:
        """Return every visible resource under ``category``.

        Visible = the winning entry per ``resource_id`` after applying
        the User > Package > Built-in priority. Shadowed entries are
        recorded on the visible entry's ``shadowed_by_source``.

        The result is sorted by ``resource_id`` for deterministic UI
        rendering.
        """
        # Collect candidates per (resource_id) keeping all sources.
        candidates: dict[str, list[ResourceEntry]] = {}

        for entry in self._scan_user(category):
            candidates.setdefault(entry.resource_id, []).append(entry)
        for entry in self._scan_packages(category):
            candidates.setdefault(entry.resource_id, []).append(entry)
        for entry in self._scan_builtin(category):
            candidates.setdefault(entry.resource_id, []).append(entry)

        winners: list[ResourceEntry] = []
        for entries in candidates.values():
            entries.sort(key=lambda e: _PRIORITY[e.source])
            winner = entries[0]
            shadowed_by = tuple(e.source for e in entries[1:])
            # Reconstruct so the shadowed_by_source field is populated;
            # frozen dataclasses cannot be mutated in place.
            winners.append(
                ResourceEntry(
                    resource_id=winner.resource_id,
                    category=winner.category,
                    source=winner.source,
                    path=winner.path,
                    package_id=winner.package_id,
                    shadowed_by_source=shadowed_by if entries[1:] else (),
                )
            )

        winners.sort(key=lambda e: e.resource_id)
        return tuple(winners)

    def all_categories(self) -> Sequence[ResourceCategory]:
        return RESOURCE_CATEGORIES

    def installed_packages(self) -> tuple[LoadedPackage, ...]:
        return self._packages

    # ------------------------------------------------------------------
    # Source scans
    # ------------------------------------------------------------------

    def _scan_user(self, category: ResourceCategory) -> Iterable[ResourceEntry]:
        if self.user_root is None:
            return ()
        category_dir = self.user_root / "resources" / category.value
        return _scan_category_dir(category_dir, category=category, source=ResourceSource.USER)

    def _scan_packages(self, category: ResourceCategory) -> Iterable[ResourceEntry]:
        out: list[ResourceEntry] = []
        for pkg in self._packages:
            category_dir = pkg.root / "resources" / category.value
            for entry in _scan_category_dir(
                category_dir,
                category=category,
                source=ResourceSource.PACKAGE,
                package_id=pkg.package_id,
            ):
                out.append(entry)
        return out

    def _scan_builtin(self, category: ResourceCategory) -> Iterable[ResourceEntry]:
        if self.builtin_root is None:
            return ()
        category_dir = self.builtin_root / category.value
        return _scan_category_dir(category_dir, category=category, source=ResourceSource.BUILTIN)


def _scan_category_dir(
    category_dir: Path,
    *,
    category: ResourceCategory,
    source: ResourceSource,
    package_id: str = "",
) -> tuple[ResourceEntry, ...]:
    """List ``category_dir`` 's immediate children as ResourceEntry.

    Hidden files (``.``-prefixed) and macOS metadata are skipped.
    Returns an empty tuple when the directory does not exist; an empty
    workbench install / package without that category is normal.
    """
    if not category_dir.is_dir():
        return ()
    entries: list[ResourceEntry] = []
    for child in sorted(category_dir.iterdir()):
        if child.name.startswith("."):
            continue
        entries.append(
            ResourceEntry(
                resource_id=child.stem,
                category=category,
                source=source,
                path=child.resolve(),
                package_id=package_id,
            )
        )
    return tuple(entries)
