"""ResourceLibrary App layer (plan/17 § 17.4.3).

Phase 7.4 — exposes the merged Built-in + Package + User resource
roots through :class:`ResourceLibrary`. The Editor's Resource Browser
sidebar (Phase 4.4) consumes the resulting :class:`ResourceEntry`
records to populate its tree.
"""

from __future__ import annotations

from workbench.app.resources.library import (
    RESOURCE_CATEGORIES,
    ResourceCategory,
    ResourceEntry,
    ResourceLibrary,
    ResourceSource,
)

__all__ = [
    "RESOURCE_CATEGORIES",
    "ResourceCategory",
    "ResourceEntry",
    "ResourceLibrary",
    "ResourceSource",
]
