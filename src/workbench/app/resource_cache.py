"""ResourceCache — content-hash keyed in-memory cache (plan/04 § 4.3, v0.20).

Phase 3.3 — caches loaded resource objects (a parsed Map, RadarPlatform,
TargetEntity, ...) keyed on their content hash so repeated loads cost
nothing. The cache is intentionally typed as ``object`` because the
cache itself doesn't care what it stores; the loader supplies a
typed wrapper.

Eviction policy: simple LRU with a ``max_entries`` cap. Default cap
is generous (256) — enough for a Workspace with hundreds of resources
without eviction in normal use.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Final

DEFAULT_CACHE_CAPACITY: Final[int] = 256


@dataclass(slots=True)
class ResourceCache:
    """LRU cache keyed on resource content hash.

    Attributes:
        max_entries: Maximum cached items before LRU eviction. Must
            be >= 1.
    """

    max_entries: int = DEFAULT_CACHE_CAPACITY
    _store: OrderedDict[str, object] = field(default_factory=OrderedDict)

    def __post_init__(self) -> None:
        if self.max_entries < 1:
            msg = f"max_entries must be >= 1, got {self.max_entries}"
            raise ValueError(msg)

    def put(self, content_hash: str, value: object) -> None:
        """Insert ``value`` under ``content_hash`` (refresh LRU).

        Raises:
            ValueError: If ``content_hash`` is empty.
        """
        if not content_hash:
            msg = "content_hash must be a non-empty string"
            raise ValueError(msg)
        if content_hash in self._store:
            self._store.move_to_end(content_hash)
        self._store[content_hash] = value
        if len(self._store) > self.max_entries:
            # Drop the least-recently-used entry.
            self._store.popitem(last=False)

    def get(self, content_hash: str) -> object:
        """Retrieve cached value (refresh LRU).

        Raises:
            KeyError: If ``content_hash`` isn't cached.
        """
        try:
            value = self._store[content_hash]
        except KeyError as exc:
            msg = f"no cached value for {content_hash!r}"
            raise KeyError(msg) from exc
        self._store.move_to_end(content_hash)
        return value

    def has(self, content_hash: str) -> bool:
        """Whether ``content_hash`` is currently cached."""
        return content_hash in self._store

    def __contains__(self, content_hash: object) -> bool:
        return isinstance(content_hash, str) and content_hash in self._store

    def __len__(self) -> int:
        return len(self._store)

    def clear(self) -> None:
        """Drop every cached value."""
        self._store.clear()
