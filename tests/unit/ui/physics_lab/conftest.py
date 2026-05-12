"""Test configuration for the Physics Lab UI suite (PL-9.1d).

The :class:`TestObject3DPanel` wraps a ``pyvistaqt.QtInteractor``
which by default creates a real OpenGL render window. Headless CI
sandboxes do not have a usable display + GL context, so without
intervention the interactor crashes with a Windows access violation
the moment :class:`PhysicsLabWorkspace` is constructed.

Setting ``pyvista.OFF_SCREEN = True`` before the workspace module is
imported swaps in PyVista's off-screen renderer (VTK GenericOpenGL),
which does not need a display. Production code paths (``python -m
workbench ui``) leave the flag at its default ``False`` so the real
QtInteractor stays attached to the user's display.

This conftest runs at test collection time, before any
``test_workspace.py`` / ``test_bouncing_ball_demo.py`` module is
imported, so the workspace module's eager construction of
``TestObject3DPanel`` succeeds.
"""

from __future__ import annotations

import pyvista as pv

pv.OFF_SCREEN = True
