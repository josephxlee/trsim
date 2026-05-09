"""ScenarioService — minimum-viable Scenario lookup + summary (Phase 3.3).

Phase 3.3 MVP — wraps the :class:`workbench.app.resource_library.ResourceLibrary`
and :class:`workbench.app.resource_cache.ResourceCache` into a single
service the App / CLI use to resolve a scenario by id.

Full TOML <-> Scenario conversion (plan/10 § 10.9.3 [refs] /
[composition] / [platform_install]) is deferred to Phase 3.x — the
App-side serialiser depends on too many in-flight format decisions.
At MVP the service answers "do I have this scenario id" and "what
hashes does it pin its resources to", which is enough for the CLI to
print a manifest and the unit tests to round-trip a synthetic library.
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.app.resource_cache import ResourceCache
from workbench.app.resource_library import ResourceLibrary


@dataclass(frozen=True, slots=True)
class ScenarioSummary:
    """Lightweight summary returned by :meth:`ScenarioService.describe`.

    Attributes:
        scenario_id: Identifier requested.
        map_id / radar_id / target_ids: Resources the scenario refers
            to (all empty strings / empty tuple at MVP — populated
            once full TOML parsing lands).
        map_hash / radar_hash / target_hashes: Content hashes of those
            resources, looked up via the library.
    """

    scenario_id: str
    map_id: str
    radar_id: str
    target_ids: tuple[str, ...]
    map_hash: str
    radar_hash: str
    target_hashes: tuple[str, ...]


@dataclass(slots=True)
class ScenarioService:
    """Resource-library-aware scenario resolver.

    Attributes:
        library: Source of resource entries.
        cache: Optional cache for already-loaded resources. Created
            empty if not supplied.
    """

    library: ResourceLibrary
    cache: ResourceCache | None = None

    def __post_init__(self) -> None:
        if self.cache is None:
            self.cache = ResourceCache()

    def describe(
        self,
        scenario_id: str,
        *,
        map_id: str,
        radar_id: str,
        target_ids: tuple[str, ...] = (),
    ) -> ScenarioSummary:
        """Build a :class:`ScenarioSummary` by resolving every reference.

        Args:
            scenario_id: Scenario identifier (informational; not looked
                up because Scenario TOML loading is deferred).
            map_id: Map resource id (must be indexed in ``library``).
            radar_id: Radar resource id.
            target_ids: Tuple of target resource ids.

        Returns:
            :class:`ScenarioSummary` with the looked-up content hashes.

        Raises:
            KeyError: If any referenced resource is missing.
            ValueError: If ``scenario_id`` is empty.
        """
        if not scenario_id:
            msg = "scenario_id must be a non-empty string"
            raise ValueError(msg)
        map_hash = self.library.get("maps", map_id).content_hash
        radar_hash = self.library.get("radars", radar_id).content_hash
        target_hashes = tuple(self.library.get("targets", tid).content_hash for tid in target_ids)
        return ScenarioSummary(
            scenario_id=scenario_id,
            map_id=map_id,
            radar_id=radar_id,
            target_ids=tuple(target_ids),
            map_hash=map_hash,
            radar_hash=radar_hash,
            target_hashes=target_hashes,
        )
