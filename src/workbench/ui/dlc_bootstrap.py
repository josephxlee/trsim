"""UI-layer DLC bootstrap (plan/17 § 17.4 finale).

Phase 7.6 — bridges the three App-layer DLC services
(:class:`workbench.app.dlc_runtime.DLCAppRuntime`) to the UI layer:

1. Build the :class:`workbench.ui.panel_registry.PanelRegistry` and
   register every ``trsim.ui.panels`` plugin that the
   :class:`workbench.app.dlc.PluginLoader` resolved.
2. Provide :func:`populate_resource_browser_from_library` so the
   Editor's Resource Browser sidebar (Phase 4.4) can be filled from
   :class:`workbench.app.resources.ResourceLibrary`.

The bootstrap is a one-way data feed — re-running it is the easy
way to refresh after an install / uninstall (the registry is cleared
first).

References:

- plan/17 § 17.4.4 — Panel Registry consumes ``trsim.ui.panels``.
- plan/13 § 13.2.3 — Resource Browser sidebar data shape.
- plan/04 § 4.3 Phase 7 통합 — three integration check-boxes.
"""

from __future__ import annotations

from dataclasses import dataclass

from workbench.app.dlc_runtime import (
    DLCAppRuntime,
    DLCPaths,
    build_dlc_app_runtime,
    default_dlc_paths,
)
from workbench.app.resources import (
    RESOURCE_CATEGORIES,
    ResourceEntry,
    ResourceLibrary,
    ResourceSource,
)
from workbench.app.resources import (
    ResourceCategory as AppResourceCategory,
)
from workbench.ui.editor.resource_browser import ResourceBrowserSidebar
from workbench.ui.editor.resource_browser.types import (
    ResourceCategory as UICategory,
)
from workbench.ui.editor.resource_browser.types import (
    ResourceItem,
    ResourceStatus,
)
from workbench.ui.panel_registry import PanelRegistry

_UI_PANEL_SLOT: str = "trsim.ui.panels"

_APP_TO_UI_CATEGORY: dict[AppResourceCategory, UICategory] = {
    AppResourceCategory.SCENARIOS: UICategory.SCENARIO,
    AppResourceCategory.MAPS: UICategory.MAP,
    AppResourceCategory.RADARS: UICategory.RADAR,
    AppResourceCategory.TARGETS: UICategory.TARGETS,
}

_SOURCE_TO_STATUS: dict[ResourceSource, ResourceStatus] = {
    ResourceSource.USER: ResourceStatus.NORMAL,
    ResourceSource.PACKAGE: ResourceStatus.NORMAL,
    ResourceSource.BUILTIN: ResourceStatus.BUILTIN,
}


@dataclass(frozen=True, slots=True)
class DLCRuntime:
    """Workbench-wide DLC bundle (App services + UI panel registry).

    Attributes:
        app: The three App-layer services (PackageManager,
            PluginLoader, ResourceLibrary) plus their paths.
        panel_registry: :class:`PanelRegistry` pre-populated with
            every ``trsim.ui.panels`` plugin discovered by the
            loader. Built-in panel registrations happen in the host
            code (Editor / Simulator workspaces own that today).
    """

    app: DLCAppRuntime
    panel_registry: PanelRegistry


def build_dlc_runtime(
    *,
    paths: DLCPaths | None = None,
    app_runtime: DLCAppRuntime | None = None,
    panel_registry: PanelRegistry | None = None,
) -> DLCRuntime:
    """Assemble the full UI-layer DLC bundle.

    Either ``paths`` or ``app_runtime`` can be supplied:

    - When both are ``None``, the defaults from
      :func:`workbench.app.dlc_runtime.default_dlc_paths` are used —
      this is what the CLI entry point calls.
    - When only ``paths`` is supplied, a fresh
      :class:`DLCAppRuntime` is built from it.
    - When ``app_runtime`` is supplied, it is reused (tests inject
      a pre-built one).

    ``panel_registry`` defaults to a brand-new empty one. Pass a
    pre-existing instance to add DLC plugins to a registry that
    already contains built-in panels.
    """
    if app_runtime is None:
        resolved_paths = paths if paths is not None else default_dlc_paths()
        app_runtime = build_dlc_app_runtime(resolved_paths)

    registry = panel_registry if panel_registry is not None else PanelRegistry()
    ui_plugins = app_runtime.plugin_loader.plugins_for_slot(_UI_PANEL_SLOT)
    registry.register_dlc_plugins(ui_plugins)
    return DLCRuntime(app=app_runtime, panel_registry=registry)


def populate_resource_browser_from_library(
    sidebar: ResourceBrowserSidebar,
    library: ResourceLibrary,
) -> int:
    """Feed every visible :class:`ResourceEntry` into the sidebar.

    The sidebar is cleared first so re-running the bootstrap after a
    package install / uninstall produces a fresh tree.

    Args:
        sidebar: Editor :class:`ResourceBrowserSidebar` to fill.
        library: :class:`ResourceLibrary` returning entries via
            :meth:`ResourceLibrary.list_resources`.

    Returns:
        Total number of leaves added across all four categories.

    Notes:
        The :data:`workbench.app.resources.ResourceCategory` enum is
        plural (``MAPS`` / ``RADARS`` / ...) and the UI enum is
        singular (``MAP`` / ``RADAR`` / ...). The mapping is local
        to this module.
    """
    sidebar.clear()
    added = 0
    for app_cat in RESOURCE_CATEGORIES:
        ui_cat = _APP_TO_UI_CATEGORY[app_cat]
        entries = library.list_resources(app_cat)
        for entry in entries:
            sidebar.add_item(_entry_to_item(entry, ui_cat))
            added += 1
    return added


def _entry_to_item(entry: ResourceEntry, ui_category: UICategory) -> ResourceItem:
    """Project an App :class:`ResourceEntry` into a UI :class:`ResourceItem`.

    The UI sidebar only needs a name, a category, and a status
    badge — the on-disk path travels via the library, not the
    sidebar.
    """
    return ResourceItem(
        name=entry.resource_id,
        category=ui_category,
        status=_SOURCE_TO_STATUS[entry.source],
    )


def populate_composer_options_from_library(
    composer: object,
    library: ResourceLibrary,
) -> tuple[int, int, int]:
    r"""Feed Map / Radar / Target resource ids into the ScenarioComposer dropdowns.

    The Composer widget already exposes
    :meth:`set_map_options(names)` / :meth:`set_radar_options(names)` /
    :meth:`set_targets_options(names)` (Phase 4.5 + 4 G4) — this
    bootstrap pulls the matching :class:`ResourceLibrary` entries and
    forwards their ``resource_id``\s.

    Args:
        composer: Any object that exposes the three setters listed
            above. Typed as ``object`` because dlc_bootstrap must not
            import :mod:`workbench.ui.editor.composer` directly
            (Editor / Simulator workspace isolation is enforced by
            Contract 2; the bootstrap is the join point).
        library: :class:`ResourceLibrary` containing the entries.

    Returns:
        ``(n_maps, n_radars, n_targets)`` — how many ids were pushed
        into each dropdown. Useful for status / log surfaces.
    """
    maps = [e.resource_id for e in library.list_resources(AppResourceCategory.MAPS)]
    radars = [e.resource_id for e in library.list_resources(AppResourceCategory.RADARS)]
    targets = [e.resource_id for e in library.list_resources(AppResourceCategory.TARGETS)]
    # Composer's public surface is duck-typed; calling each setter
    # explicitly keeps the contract loose so test doubles can stub one
    # method at a time.
    composer.set_map_options(maps)  # type: ignore[attr-defined]
    composer.set_radar_options(radars)  # type: ignore[attr-defined]
    composer.set_targets_options(targets)  # type: ignore[attr-defined]
    return (len(maps), len(radars), len(targets))
