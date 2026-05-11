"""UI Panel Registry — DLC + built-in panel index (plan/17 § 17.4.4).

Phase 7.5 — collects panel classes that the workbench can dock into a
workspace. Two sources:

1. Built-in: the workbench's own panel classes are registered at
   startup (Editor / Simulator workspaces own this in the host code).
2. DLC: every :class:`workbench.app.dlc.LoadedPlugin` for the
   ``trsim.ui.panels`` slot is registered automatically via
   :meth:`register_dlc_plugins`.

The registry does not instantiate panels — it stores the class
reference and the workspace / dock-area tag so the main_window can
build the panel lazily when its workspace becomes active.

Workspace tags follow the Phase 4 :class:`workbench.ui.workspace_
selector.Workspace` enum (``"editor"`` / ``"simulator"``); dock
areas are free-form strings (``"left"`` / ``"right"`` / ``"bottom"``
/ ``"center"`` — main_window resolves them to Qt dock zones).

References:

- plan/17 § 17.4.4 — Panel Registry.
- plan/13 § 13.2 — Editor workspace dock layout.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from workbench.app.dlc import LoadedPlugin


@dataclass(frozen=True, slots=True)
class PanelRegistration:
    """One registered panel.

    Attributes:
        panel_class: The panel's class object. The main_window calls
            ``panel_class(parent)`` when the panel is shown.
        workspace: Workspace tag (``"editor"`` / ``"simulator"``).
        dock_area: Dock-area tag (``"left"`` / ``"right"`` /
            ``"bottom"`` / ``"center"``).
        source_package_id: ``""`` for built-in panels; the owning
            DLC package id for plugin panels.
    """

    panel_class: type
    workspace: str
    dock_area: str
    source_package_id: str = ""


_DEFAULT_DLC_WORKSPACE: str = "simulator"
_DEFAULT_DLC_DOCK_AREA: str = "right"


class PanelRegistry:
    """Pluggable index of UI panels per workspace.

    Attributes:
        _entries: Internal list of :class:`PanelRegistration`.
            Insertion order is preserved.
    """

    def __init__(self) -> None:
        self._entries: list[PanelRegistration] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        panel_class: type,
        *,
        workspace: str,
        dock_area: str,
        source_package_id: str = "",
    ) -> None:
        """Register a single panel class.

        Args:
            panel_class: The panel's class object.
            workspace: ``"editor"`` / ``"simulator"``. Anything goes,
                but only known workspaces will surface the panel.
            dock_area: ``"left"`` / ``"right"`` / ``"bottom"`` /
                ``"center"``. Free-form; main_window resolves.
            source_package_id: DLC package id; empty for built-in.

        Raises:
            ValueError: For empty ``workspace`` or ``dock_area``.
        """
        if not workspace:
            msg = "workspace must be a non-empty string"
            raise ValueError(msg)
        if not dock_area:
            msg = "dock_area must be a non-empty string"
            raise ValueError(msg)
        self._entries.append(
            PanelRegistration(
                panel_class=panel_class,
                workspace=workspace,
                dock_area=dock_area,
                source_package_id=source_package_id,
            )
        )

    def register_dlc_plugins(
        self,
        plugins: Iterable[LoadedPlugin],
        *,
        default_workspace: str = _DEFAULT_DLC_WORKSPACE,
        default_dock_area: str = _DEFAULT_DLC_DOCK_AREA,
    ) -> int:
        """Register every ``trsim.ui.panels`` plugin from the loader.

        DLC manifests do not yet ship workspace / dock_area metadata
        (plan/17 § 17.4.4 leaves that for a later schema bump). The
        MVP places every DLC panel under ``default_workspace`` +
        ``default_dock_area``; main_window can override via the
        per-panel ``configure_layout`` hook in a future sub-step.

        Args:
            plugins: Iterable of :class:`LoadedPlugin` records,
                typically from
                :meth:`workbench.app.dlc.PluginLoader.plugins_for_slot`
                (``"trsim.ui.panels"``).
            default_workspace: Workspace tag for every panel.
            default_dock_area: Dock-area tag for every panel.

        Returns:
            Number of panels registered. Plugins whose ``attribute``
            is ``None`` (path-slot mistakes) are skipped silently;
            the loader already logged their error.
        """
        n = 0
        for plugin in plugins:
            if plugin.attribute is None:
                continue
            if not isinstance(plugin.attribute, type):
                # Plugin attribute is a function / instance, not a
                # class — accept but defer the type check to
                # main_window. For the MVP we only accept classes.
                continue
            self.register(
                panel_class=plugin.attribute,
                workspace=default_workspace,
                dock_area=default_dock_area,
                source_package_id=plugin.package_id,
            )
            n += 1
        return n

    def clear(self) -> None:
        """Remove every registration. Useful for tests + DLC re-install."""
        self._entries = []

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_panels_for_workspace(self, workspace: str) -> tuple[PanelRegistration, ...]:
        """Return every registration whose workspace tag matches."""
        return tuple(e for e in self._entries if e.workspace == workspace)

    def all_registrations(self) -> tuple[PanelRegistration, ...]:
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)
