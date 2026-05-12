"""Physics Lab Workspace UI — 3-pane (Code / Visualization / Parameters).

plan/19 §§ 19.5 + 19.6 + 19.7. PL-A ships the shell, PL-D wires the
first interactive demo (Bouncing Ball + restitution slider) on top of
this scaffold. Editor / Simulator workspaces stay isolated from this
module per Contract 2 (workspace-isolation).
"""

from __future__ import annotations

from workbench.ui.physics_lab.bouncing_ball_demo import (
    BouncingBallController,
    BouncingBallPlot,
    CodePreview,
    LibraryWidget,
    ParametersWidget,
)
from workbench.ui.physics_lab.workspace import PhysicsLabWorkspace

__all__ = [
    "BouncingBallController",
    "BouncingBallPlot",
    "CodePreview",
    "LibraryWidget",
    "ParametersWidget",
    "PhysicsLabWorkspace",
]
