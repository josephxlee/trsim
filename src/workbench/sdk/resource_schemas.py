"""DLC resource TOML schemas (Phase 7 C8, plan/17 § 17.2.4).

Minimal schema check for the Map / Radar / Targets / Scenario
resource TOML files a DLC ships under ``resources/<category>/``.
The MVP only enforces the **required keys** — full per-category
validation (numeric ranges, cross-field invariants) lands when
the rich Editor activities (plan/13) wire schema-aware forms.

The package validator (:mod:`workbench.sdk.package_validator`) calls
:func:`validate_resource_toml_blob` to produce soft issues for
DLC authors before publication.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

ResourceCategory = Literal["maps", "radars", "targets", "scenarios"]
"""Categories handled by the resource TOML schema check.

Mirrors :class:`workbench.app.resources.library.ResourceCategory`
but lives in the SDK layer (no app/ import allowed)."""


MAP_REQUIRED_KEYS: frozenset[str] = frozenset({"id"})
"""Minimum keys for a ``resources/maps/<id>.toml`` (plan/13 § 13.4)."""

RADAR_REQUIRED_KEYS: frozenset[str] = frozenset({"id"})
"""Minimum keys for a ``resources/radars/<id>.toml`` (plan/13 § 13.5)."""

TARGETS_REQUIRED_KEYS: frozenset[str] = frozenset({"id"})
"""Minimum keys for a ``resources/targets/<id>.toml`` (plan/13 § 13.6)."""

SCENARIO_REQUIRED_KEYS: frozenset[str] = frozenset({"id"})
"""Minimum keys for a ``scenarios/<id>.toml`` (plan/13 § 13.3)."""


_REQUIRED_KEYS_BY_CATEGORY: dict[str, frozenset[str]] = {
    "maps": MAP_REQUIRED_KEYS,
    "radars": RADAR_REQUIRED_KEYS,
    "targets": TARGETS_REQUIRED_KEYS,
    "scenarios": SCENARIO_REQUIRED_KEYS,
}


def validate_resource_toml_blob(
    category: ResourceCategory, blob: Mapping[str, object]
) -> tuple[str, ...]:
    """Check ``blob`` against the required keys for ``category``.

    Args:
        category: ``"maps"`` / ``"radars"`` / ``"targets"`` / ``"scenarios"``.
        blob: Parsed TOML dict.

    Returns:
        Tuple of issue strings. Empty = no problems found.

    Raises:
        ValueError: ``category`` is not a known resource category.
    """
    if category not in _REQUIRED_KEYS_BY_CATEGORY:
        msg = (
            f"unknown resource category {category!r}; expected one of "
            f"{sorted(_REQUIRED_KEYS_BY_CATEGORY)}"
        )
        raise ValueError(msg)
    required = _REQUIRED_KEYS_BY_CATEGORY[category]
    missing = sorted(required - blob.keys())
    return tuple(f"missing required key {key!r}" for key in missing)


def known_resource_categories() -> tuple[ResourceCategory, ...]:
    """List of categories the schema check recognises."""
    return ("maps", "radars", "targets", "scenarios")
