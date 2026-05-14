"""Test configuration for the Simulator UI suite (Phase 4 L4).

Phase 4 L4 added a live PyVista QtInteractor inside
:class:`workbench.ui.simulator.panels.Scene3DPanel` whenever its
``enable_3d_viewer`` kwarg is ``True`` (the production default).
Constructing the QtInteractor needs a usable OpenGL context, which
headless CI sandboxes lack.

Setting ``pyvista.OFF_SCREEN = True`` before the Simulator workspace
module is imported swaps in PyVista's off-screen VTK renderer, which
does not need a display. Production code paths (``python -m
workbench ui``) leave the flag at its default ``False`` so the real
QtInteractor stays attached to the user's display.

This mirrors :mod:`tests.unit.ui.physics_lab.conftest`.
"""

from __future__ import annotations

import pyvista as pv

pv.OFF_SCREEN = True
