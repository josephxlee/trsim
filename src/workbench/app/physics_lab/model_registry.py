"""Physics-model registry for the Physics Lab Library (Phase 9 H2).

plan/19 § 19.7.5+ "Library Models 동적 채우기" 의 backbone. The Library
widget (H1) accepts a tuple of ``PhysicsModelProtocol`` instances; this
module owns *which* instances ship out-of-the-box and provides a global
registry hook for DLC / user plugins so future cycles can teach the Lab
about new models without touching the widget.

Three public surfaces:

- :data:`builtin_physics_models()` — the three references shipped by
  Phase 9.3b/c/d (Gravity Only / Bouncing Ball / Free-Space Loss).
- :func:`register_physics_model(model)` — plugin hook. Adds a model to
  a module-level :data:`_REGISTERED_MODELS` tuple that
  :func:`default_physics_models` then concatenates with the built-ins.
- :func:`default_physics_models()` — final list the workspace consumes.
  Order: built-ins first, registrations in insertion order. The function
  also enforces name-uniqueness across the merged list so a workspace
  never receives a list the LibraryWidget would reject as duplicate.

Mirrors the test-object plugin pattern at
:func:`workbench.ui.physics_lab.test_object_view.register_visual_kind_builder`,
so adopting plug-in discovery (PluginLoader, future cycle) just means
calling :func:`register_physics_model` for each discovered model.
"""

from __future__ import annotations

from collections.abc import Iterable

from workbench.app.physics_lab.models import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
)
from workbench.sdk.protocols import PhysicsModelProtocol

_BUILTINS: tuple[type, ...] = (
    GravityOnlyModel,
    BouncingBallModel,
    FreeSpaceLossModel,
)

_REGISTERED_MODELS: list[PhysicsModelProtocol] = []


def builtin_physics_models() -> tuple[PhysicsModelProtocol, ...]:
    """Fresh instances of the three Phase 9.3 reference models.

    Returned in a fixed user-facing order: Gravity Only → Bouncing
    Ball → Free-Space Loss. Each call returns *new* instances so the
    workspace can hold one set and a Validation Bench can hold another
    without state cross-talk.
    """
    return tuple(cls() for cls in _BUILTINS)


def register_physics_model(model: PhysicsModelProtocol) -> None:
    """Add a model to the module-level plug-in registry.

    Args:
        model: An object implementing :class:`PhysicsModelProtocol`.
            ``isinstance(model, PhysicsModelProtocol)`` is the only gate
            (cheap because the protocol is ``runtime_checkable``).

    Raises:
        TypeError: If ``model`` does not satisfy the protocol.
        ValueError: If a model with the same ``name`` is already in the
            built-in set or has been previously registered.
    """
    if not isinstance(model, PhysicsModelProtocol):
        msg = (
            "register_physics_model() requires an object implementing "
            f"PhysicsModelProtocol; got {type(model).__name__}"
        )
        raise TypeError(msg)
    existing = {m.name for m in builtin_physics_models()} | {m.name for m in _REGISTERED_MODELS}
    if model.name in existing:
        msg = f"Physics model name {model.name!r} already registered"
        raise ValueError(msg)
    _REGISTERED_MODELS.append(model)


def unregister_all_physics_models() -> None:
    """Clear the plug-in registry (built-ins are untouched).

    Test helper — production code never calls this; tests use it to
    keep modules isolated across cases.
    """
    _REGISTERED_MODELS.clear()


def registered_physics_models() -> tuple[PhysicsModelProtocol, ...]:
    """Snapshot of the plug-in-only registry (no built-ins)."""
    return tuple(_REGISTERED_MODELS)


def default_physics_models() -> tuple[PhysicsModelProtocol, ...]:
    """Final list the workspace ships into LibraryWidget.set_physics_models.

    Order: built-ins (Gravity / BouncingBall / FreeSpaceLoss) followed
    by registered plug-ins in insertion order. Duplicate names — across
    built-ins and registrations — raise ``ValueError`` so the workspace
    never silently drops a model.
    """
    merged: list[PhysicsModelProtocol] = list(builtin_physics_models())
    merged.extend(_REGISTERED_MODELS)
    names = [m.name for m in merged]
    if len(names) != len(set(names)):
        seen: set[str] = set()
        dupes: list[str] = []
        for n in names:
            if n in seen:
                dupes.append(n)
            seen.add(n)
        msg = f"Duplicate physics-model names in default registry: {dupes!r}"
        raise ValueError(msg)
    return tuple(merged)


def physics_models_from(
    *, include_builtins: bool, extra: Iterable[PhysicsModelProtocol] = ()
) -> tuple[PhysicsModelProtocol, ...]:
    """Custom assembly path for advanced callers.

    Tests and the Validation Bench occasionally want a curated subset
    (e.g. built-ins only, or built-ins + one custom mock). This helper
    builds a deterministic tuple without mutating module state.
    """
    merged: list[PhysicsModelProtocol] = []
    if include_builtins:
        merged.extend(builtin_physics_models())
    merged.extend(extra)
    names = [m.name for m in merged]
    if len(names) != len(set(names)):
        msg = "Duplicate physics-model names in custom assembly"
        raise ValueError(msg)
    return tuple(merged)
