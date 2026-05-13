"""Physics-model plug-in discovery (Phase 9 I2).

Bridges :mod:`workbench.app.dlc.plugin_loader` (which resolves
``trsim.physics_model`` entry points to Python classes) and
:mod:`workbench.app.physics_lab.model_registry` (which owns the
runtime PhysicsModel registry the Library widget consumes).

The discovery is split into two pure functions so callers can drive
it without touching globals:

- :func:`physics_models_from_loaded_plugins` — pure transform
  ``LoadedPlugin → PhysicsModelProtocol``. Skips entries that do not
  satisfy the protocol and reports them as :class:`DiscoveryError`
  rather than raising, so one broken DLC cannot stop the others.
- :func:`register_discovered_physics_models` — calls the pure
  transform and pushes each model through
  :func:`register_physics_model`. Returns the count of newly
  registered models + the discovery errors.

The PhysicsLabWorkspace consumes the *result* of these functions; this
module never imports Qt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from workbench.app.dlc.plugin_loader import LoadedPlugin
from workbench.app.physics_lab.model_registry import (
    register_physics_model,
    registered_physics_models,
)
from workbench.sdk.protocols import PhysicsModelProtocol

PHYSICS_MODEL_SLOT = "trsim.physics_model"
"""Singleton entry-point slot the plugin_loader maps onto a Python class."""


@dataclass(frozen=True, slots=True)
class DiscoveryError:
    """One non-fatal failure while turning a LoadedPlugin into a model.

    Attributes:
        package_id: Owning DLC package id.
        target: Original entry-point string from the manifest.
        message: English failure reason (does not include the package
            id — callers prepend it when logging).
    """

    package_id: str
    target: str
    message: str


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Outcome of one discovery pass.

    Attributes:
        models: Tuple of newly *or* previously registered models that
            came from the discovered set. Order matches the loader
            order.
        errors: Tuple of :class:`DiscoveryError` for plug-ins that
            failed to instantiate or didn't satisfy the protocol.
        registered_count: How many of ``models`` were *newly*
            registered by this pass (i.e. weren't already in the
            module-level registry).
    """

    models: tuple[PhysicsModelProtocol, ...]
    errors: tuple[DiscoveryError, ...]
    registered_count: int


def physics_models_from_loaded_plugins(
    loaded: Mapping[str, tuple[LoadedPlugin, ...]],
) -> tuple[tuple[PhysicsModelProtocol, ...], tuple[DiscoveryError, ...]]:
    """Materialise PhysicsModelProtocol instances from PluginLoader output.

    Each :attr:`LoadedPlugin.attribute` is expected to be a *class* (the
    entry point ``module:Klass``); we instantiate it with no arguments
    so the manifest never has to declare constructor args. If the class
    or instance fails the ``runtime_checkable`` protocol check the
    entry is reported but not raised.

    Args:
        loaded: The mapping returned by :meth:`PluginLoader.load_all`.

    Returns:
        ``(models, errors)``. ``models`` preserves loader order;
        ``errors`` lists each non-fatal failure.
    """
    models: list[PhysicsModelProtocol] = []
    errors: list[DiscoveryError] = []
    for plugin in loaded.get(PHYSICS_MODEL_SLOT, ()):
        klass = plugin.attribute
        if klass is None:
            errors.append(
                DiscoveryError(
                    package_id=plugin.package_id,
                    target=plugin.target,
                    message="entry-point resolved to None",
                )
            )
            continue
        try:
            instance = klass()  # type: ignore[operator]
        except Exception as exc:
            errors.append(
                DiscoveryError(
                    package_id=plugin.package_id,
                    target=plugin.target,
                    message=f"instantiation failed: {exc}",
                )
            )
            continue
        if not isinstance(instance, PhysicsModelProtocol):
            errors.append(
                DiscoveryError(
                    package_id=plugin.package_id,
                    target=plugin.target,
                    message="instance does not satisfy PhysicsModelProtocol",
                )
            )
            continue
        models.append(instance)
    return tuple(models), tuple(errors)


def register_discovered_physics_models(
    loaded: Mapping[str, tuple[LoadedPlugin, ...]],
) -> DiscoveryResult:
    """Push every discovered model into the module-level registry.

    Models whose ``name`` collides with a built-in or with a previous
    registration are silently dropped from the *register* step but
    still appear in :attr:`DiscoveryResult.models` — the workspace can
    decide whether to surface a warning. ``registered_count`` reflects
    only the new additions.
    """
    models, errors = physics_models_from_loaded_plugins(loaded)
    already = {m.name for m in registered_physics_models()}
    registered_count = 0
    for model in models:
        if model.name in already:
            continue
        try:
            register_physics_model(model)
        except ValueError:
            # Built-in name collision — surface via models[] but skip
            # the side-effect.
            continue
        already.add(model.name)
        registered_count += 1
    return DiscoveryResult(models=models, errors=errors, registered_count=registered_count)
