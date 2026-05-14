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
from workbench.app.physics_lab.discovery import (
    PHYSICS_MODEL_SLOT,
    DiscoveryError,
    DiscoveryResult,
    physics_models_from_loaded_plugins,
    register_discovered_physics_models,
)
from workbench.app.physics_lab.learning_models import (
    NumpyNNPhysicsModel,
    PolynomialFitModel,
)
from workbench.app.physics_lab.model_registry import (
    builtin_physics_models,
    default_physics_models,
    physics_models_from,
    register_physics_model,
    registered_physics_models,
    unregister_all_physics_models,
)
from workbench.app.physics_lab.models import (
    BouncingBallModel,
    FreeSpaceLossModel,
    GravityOnlyModel,
)
from workbench.app.physics_lab.parameter_fitter import (
    FitConfig,
    FitResult,
    fit_bouncing_ball,
)
from workbench.app.physics_lab.validation_bench import (
    ValidationBench,
    ValidationConfig,
)

__all__ = [
    "PHYSICS_MODEL_SLOT",
    "BouncingBallModel",
    "BouncingBallSimulator",
    "BouncingBallState",
    "ClockTick",
    "DiscoveryError",
    "DiscoveryResult",
    "FitConfig",
    "FitResult",
    "FreeSpaceLossModel",
    "GravityOnlyModel",
    "NumpyNNPhysicsModel",
    "PhysicsClock",
    "PolynomialFitModel",
    "ValidationBench",
    "ValidationConfig",
    "analytic_peak_height_m",
    "builtin_physics_models",
    "default_physics_models",
    "fit_bouncing_ball",
    "physics_models_from",
    "physics_models_from_loaded_plugins",
    "register_discovered_physics_models",
    "register_physics_model",
    "registered_physics_models",
    "unregister_all_physics_models",
]
