"""Parameter Studio fitter (PL-9.2d, plan/19 § 19.9.3 form 1).

Wraps ``scipy.optimize.minimize`` (Nelder-Mead) around the
:class:`workbench.domain.physics_lab.compute_validation_metrics` RMSE
loss so the Physics Lab can solve for ``restitution`` / ``drag`` /
other Bouncing Ball parameters that minimise the residual against a
measured ``(t, y)`` trajectory.

Nelder-Mead is gradient-free, so the ground-bounce discontinuity in
:class:`BouncingBallSimulator.step` is fine. Bounds are enforced
inside the loss function by clamping the active vector — Nelder-Mead
does not natively support box constraints in older scipy, and adding
a penalty term blurs the surface near the minimum.

Inputs / outputs:

- :class:`FitConfig` selects which Bouncing Ball parameters are free.
  ``restitution`` is on by default; the other three are off so the
  default call is a one-parameter fit.
- :class:`FitResult` reports the fitted scalars, the final RMSE,
  iteration count, and a free-form ``message`` (``scipy`` reason
  string).

The fitter does not mutate the live simulator — it returns the
result as a frozen dataclass and lets the controller decide whether
to push the values onto the live state.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import scipy.optimize
from numpy.typing import NDArray

from workbench.app.physics_lab.bouncing_ball import BouncingBallSimulator
from workbench.domain.physics_lab.validation import compute_validation_metrics

# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FitConfig:
    """Which Bouncing Ball parameters are free during the fit.

    All ``False`` would leave nothing to optimise — the fitter rejects
    that combination.
    """

    fit_restitution: bool = True
    fit_drag_coefficient_k: bool = False
    fit_gravity_m_s2: bool = False
    fit_initial_height_m: bool = False

    def free_count(self) -> int:
        return sum(
            (
                self.fit_restitution,
                self.fit_drag_coefficient_k,
                self.fit_gravity_m_s2,
                self.fit_initial_height_m,
            )
        )


@dataclass(frozen=True, slots=True)
class FitResult:
    """Outcome of one :func:`fit_bouncing_ball` call.

    Attributes:
        success: ``True`` if scipy converged within the iteration
            budget.
        fitted_gravity_m_s2: Final gravity. Equal to the input when
            ``fit_gravity_m_s2 = False``.
        fitted_restitution: Final restitution.
        fitted_drag_coefficient_k: Final drag.
        fitted_initial_height_m: Final initial height.
        final_rmse: RMSE between measured + simulated at convergence.
        n_iterations: ``scipy`` ``nit`` count.
        message: ``scipy`` termination message.
    """

    success: bool
    fitted_gravity_m_s2: float
    fitted_restitution: float
    fitted_drag_coefficient_k: float
    fitted_initial_height_m: float
    final_rmse: float
    n_iterations: int
    message: str


# ---------------------------------------------------------------------
# Bounds (mirror BOUNCING_BALL_PARAM_SPECS)
# ---------------------------------------------------------------------

_BOUNDS = {
    "restitution": (0.0, 1.0),
    "drag_coefficient_k": (0.0, 1.0),
    "gravity_m_s2": (1.0, 30.0),
    "initial_height_m": (0.1, 50.0),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


# ---------------------------------------------------------------------
# Simulation helper (mirrors BouncingBallController._simulate_for_validation)
# ---------------------------------------------------------------------


def _simulate(
    gravity: float,
    restitution: float,
    drag: float,
    height: float,
    velocity: float,
    end_t: float,
    dt_s: float,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    sim = BouncingBallSimulator(
        gravity_m_s2=gravity,
        restitution=restitution,
        initial_height_m=height,
        initial_velocity_m_s=velocity,
        drag_coefficient_k=drag,
    )
    n_steps = max(2, int(np.ceil(end_t / dt_s)) + 1)
    times = np.empty(n_steps, dtype=np.float64)
    ys = np.empty(n_steps, dtype=np.float64)
    times[0] = sim.state.time_s
    ys[0] = sim.state.position_m
    for i in range(1, n_steps):
        state = sim.step(dt_s)
        times[i] = state.time_s
        ys[i] = state.position_m
    return times, ys


# ---------------------------------------------------------------------
# Fit entry point
# ---------------------------------------------------------------------


def fit_bouncing_ball(
    *,
    measured_x: NDArray[np.float64],
    measured_y: NDArray[np.float64],
    initial_gravity_m_s2: float,
    initial_restitution: float,
    initial_drag_coefficient_k: float,
    initial_height_m: float,
    initial_velocity_m_s: float,
    config: FitConfig | None = None,
    dt_s: float = 0.01,
    max_iter: int = 200,
) -> FitResult:
    """Minimise the RMSE between simulated and measured trajectories.

    Returns the :class:`FitResult` regardless of convergence — the
    caller can inspect ``success`` + ``message`` for diagnostics. The
    initial-velocity parameter stays fixed; only the four parameters
    listed in :class:`FitConfig` may be free.

    Raises:
        ValueError: For empty inputs, all-``False`` config, or a
            non-positive measured max time.
    """
    cfg = config if config is not None else FitConfig()
    if cfg.free_count() == 0:
        msg = "fit_bouncing_ball: at least one FitConfig flag must be True"
        raise ValueError(msg)
    if measured_x.size == 0 or measured_y.size == 0:
        msg = "fit_bouncing_ball: empty measured arrays"
        raise ValueError(msg)
    end_t = float(measured_x.max())
    if end_t <= 0.0:
        msg = "fit_bouncing_ball: measured x-range must include positive values"
        raise ValueError(msg)

    # Active parameter ordering: restitution, drag, gravity, height.
    active_names: list[str] = []
    x0: list[float] = []
    if cfg.fit_restitution:
        active_names.append("restitution")
        x0.append(initial_restitution)
    if cfg.fit_drag_coefficient_k:
        active_names.append("drag_coefficient_k")
        x0.append(initial_drag_coefficient_k)
    if cfg.fit_gravity_m_s2:
        active_names.append("gravity_m_s2")
        x0.append(initial_gravity_m_s2)
    if cfg.fit_initial_height_m:
        active_names.append("initial_height_m")
        x0.append(initial_height_m)

    def loss(vector: NDArray[np.float64]) -> float:
        params = {
            "restitution": initial_restitution,
            "drag_coefficient_k": initial_drag_coefficient_k,
            "gravity_m_s2": initial_gravity_m_s2,
            "initial_height_m": initial_height_m,
        }
        for name, value in zip(active_names, vector, strict=True):
            low, high = _BOUNDS[name]
            params[name] = _clamp(float(value), low, high)
        sim_x, sim_y = _simulate(
            gravity=params["gravity_m_s2"],
            restitution=params["restitution"],
            drag=params["drag_coefficient_k"],
            height=params["initial_height_m"],
            velocity=initial_velocity_m_s,
            end_t=end_t,
            dt_s=dt_s,
        )
        try:
            metrics = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
        except ValueError:
            # Degenerate trajectory (no overlap, etc.) -> huge penalty.
            return 1e9
        return metrics.rmse

    result = scipy.optimize.minimize(
        loss,
        x0=np.asarray(x0, dtype=np.float64),
        method="Nelder-Mead",
        options={"maxiter": max_iter, "xatol": 1e-4, "fatol": 1e-4},
    )

    # Assemble fitted parameter set.
    fitted = {
        "restitution": initial_restitution,
        "drag_coefficient_k": initial_drag_coefficient_k,
        "gravity_m_s2": initial_gravity_m_s2,
        "initial_height_m": initial_height_m,
    }
    for name, value in zip(active_names, result.x, strict=True):
        low, high = _BOUNDS[name]
        fitted[name] = _clamp(float(value), low, high)

    return FitResult(
        success=bool(result.success),
        fitted_gravity_m_s2=fitted["gravity_m_s2"],
        fitted_restitution=fitted["restitution"],
        fitted_drag_coefficient_k=fitted["drag_coefficient_k"],
        fitted_initial_height_m=fitted["initial_height_m"],
        final_rmse=float(result.fun),
        n_iterations=int(result.nit),
        message=str(result.message),
    )
