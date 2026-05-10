"""Resource Browser value types (Phase 4.4).

Light-weight UI-side types that describe what the sidebar renders.
The real :mod:`workbench.app.resource_library` (Phase 5+) will own
the canonical data; the sidebar only needs the projection defined
here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ResourceCategory(StrEnum):
    """Top-level grouping in the resource browser tree.

    Order matters - it drives the on-screen tree order via
    :data:`CATEGORY_ORDER`.
    """

    SCENARIO = "scenario"
    MAP = "map"
    RADAR = "radar"
    TARGETS = "targets"


CATEGORY_ORDER: tuple[ResourceCategory, ...] = (
    ResourceCategory.SCENARIO,
    ResourceCategory.MAP,
    ResourceCategory.RADAR,
    ResourceCategory.TARGETS,
)
"""Display order in the sidebar tree (plan/13 section 13.2.3)."""


CATEGORY_LABELS: dict[ResourceCategory, str] = {
    ResourceCategory.SCENARIO: "Scenarios",
    ResourceCategory.MAP: "Maps",
    ResourceCategory.RADAR: "Radars",
    ResourceCategory.TARGETS: "Targets",
}
"""Human plural labels (Scenarios / Maps / Radars / Targets)."""


class ResourceStatus(StrEnum):
    """Per-item status badge shown in the sidebar.

    - :attr:`ACTIVE` - referenced by the current Scenario, hashes ok.
    - :attr:`STALE` - referenced but the resource's hash diverged from
      what the Scenario remembers (resource was edited externally).
    - :attr:`BUILTIN` - shipped with the package, read-only.
    - :attr:`NORMAL` - everything else.
    """

    ACTIVE = "active"
    STALE = "stale"
    BUILTIN = "builtin"
    NORMAL = "normal"


_STATUS_PREFIX: dict[ResourceStatus, str] = {
    ResourceStatus.ACTIVE: "[active] ",
    ResourceStatus.STALE: "[stale] ",
    ResourceStatus.BUILTIN: "[builtin] ",
    ResourceStatus.NORMAL: "",
}


def status_prefix(status: ResourceStatus) -> str:
    """Return the ASCII prefix shown in front of an item's name."""
    return _STATUS_PREFIX[status]


@dataclass(frozen=True, slots=True)
class ResourceItem:
    """One leaf entry in the resource browser tree.

    Attributes:
        name: Human display name (``"B_Conflict"``, ``"fmcw_corvette"``).
        category: Which top-level grouping this item belongs to.
        status: Visual badge - :class:`ResourceStatus`.

    Raises:
        ValueError: If ``name`` is empty.
    """

    name: str
    category: ResourceCategory
    status: ResourceStatus = ResourceStatus.NORMAL

    def __post_init__(self) -> None:
        if not self.name:
            msg = "ResourceItem.name must be a non-empty string"
            raise ValueError(msg)

    def display_text(self) -> str:
        """Return the prefix-decorated name for the tree row."""
        return f"{status_prefix(self.status)}{self.name}"
