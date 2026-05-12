"""Physics Lab Application Layer (PL-D, plan/19 § 19.6 + § 19.12.1).

PL-D ships the first interactive demo backing the Physics Lab
workspace:

- :class:`PhysicsClock` — single-source time stepper for the Run mode.
- :class:`BouncingBallSimulator` — 1-D vertical dynamics with
  configurable restitution; the canonical first example from
  plan/19 § 19.12.1.
- :func:`analytic_peak_height_m` — closed-form reference the Compare
  mode (Phase 9.1) will overlay on the simulated peaks.
"""

from __future__ import annotations

from workbench.app.physics_lab.bouncing_ball import (
    BouncingBallSimulator,
    BouncingBallState,
    analytic_peak_height_m,
)
from workbench.app.physics_lab.clock import ClockTick, PhysicsClock
from workbench.app.physics_lab.parameter_fitter import (
    FitConfig,
    FitResult,
    fit_bouncing_ball,
)

__all__ = [
    "BouncingBallSimulator",
    "BouncingBallState",
    "ClockTick",
    "FitConfig",
    "FitResult",
    "PhysicsClock",
    "analytic_peak_height_m",
    "fit_bouncing_ball",
]
