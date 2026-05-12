"""Reusable Qt widget primitives shared across workspaces.

The widgets here are workspace-agnostic — Editor and Simulator both
import from here when they need composite behaviour (detachable tabs,
status banners, etc.) that is too small to deserve its own subpackage.

Phase 4.2d's DockManager covers the QMainWindow-level dock layout;
this module covers the more granular "promote a single tab to a
floating top-level window" interaction.
"""

from __future__ import annotations

from workbench.ui.widgets.detachable_tab import DetachableTabWidget, FloatingPanel

__all__ = ["DetachableTabWidget", "FloatingPanel"]
