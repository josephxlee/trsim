"""Generic Validation Bench runner for :class:`PhysicsModelProtocol`.

plan/19 § 19.7.5+ "Validation Bench 일반화" — the cycle-M1 layer that
lets the Physics Lab score *any* registered physics-model plugin
against a measured dataset, not just the hard-coded Bouncing Ball.

The original PL-9.2c implementation (in
:mod:`workbench.ui.physics_lab.bouncing_ball_demo`) ran a fresh
:class:`BouncingBallSimulator` for each validation pass. This module
generalises that path: the runner only needs a
:class:`PhysicsModelProtocol`, the current slider values, and a
measured ``(x, y)`` pair. It dispatches on ``model.time_mode``:

- ``"dynamic"`` — repeatedly call ``model.compute(state, params, dt_s)``,
  starting from ``initial_state`` (defaulting to ``{}``), and sample
  ``(state[x_field], state[y_field])`` after each step.
- ``"static"`` — sweep ``x_values`` (defaulting to ``measured_x``):
  for each value, call ``model.compute({}, params_with_x, None)`` with
  ``params[x_field]`` overridden, then read ``out_state[y_field]``.

The result is a :class:`ValidationRun` containing the metrics and the
simulated curve, so UI callers can install overlays without running
the model twice.

This module is intentionally **pure** (no Qt, no plot dependency) so
the existing BouncingBall validation flow (PL-9.2c) can adopt it in a
follow-up sub-step without touching UI layout.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
from numpy.typing import NDArray

from workbench.domain.physics_lab.validation import (
    ValidationRun,
    compute_validation_metrics,
)
from workbench.sdk.protocols import PhysicsModelProtocol


def simulate_dynamic_for_validation(
    model: PhysicsModelProtocol,
    params: Mapping[str, float],
    *,
    initial_state: Mapping[str, Any] | None = None,
    dt_s: float,
    t_end_s: float,
    x_field: str = "time_s",
    y_field: str,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Step a dynamic model from ``t=0`` to ``t_end_s`` and sample.

    Returns ``(sim_x, sim_y)`` where ``sim_x[i]`` is the value of
    ``state[x_field]`` and ``sim_y[i]`` is ``state[y_field]`` after
    step ``i``. The first entry is the initial state itself, so
    ``len(sim_x) == n_steps + 1``.

    Raises:
        ValueError: For ``dt_s <= 0``, ``t_end_s <= 0``, or when the
            first output state is missing either field.
    """
    if dt_s <= 0.0:
        msg = f"simulate_dynamic_for_validation: dt_s must be positive (got {dt_s})"
        raise ValueError(msg)
    if t_end_s <= 0.0:
        msg = f"simulate_dynamic_for_validation: t_end_s must be positive (got {t_end_s})"
        raise ValueError(msg)

    state: dict[str, Any] = dict(initial_state) if initial_state else {}
    state.setdefault(x_field, 0.0)

    n_steps = int(np.ceil(t_end_s / dt_s))
    xs: list[float] = [float(state[x_field])]
    ys: list[float] = [float(state.get(y_field, 0.0))]
    for i in range(n_steps):
        new_state = dict(model.compute(state, params, dt_s))
        if x_field not in new_state:
            msg = (
                f"simulate_dynamic_for_validation: model {model.name!r} did not "
                f"return x_field {x_field!r} on step {i}; got keys {sorted(new_state)}"
            )
            raise ValueError(msg)
        if y_field not in new_state:
            msg = (
                f"simulate_dynamic_for_validation: model {model.name!r} did not "
                f"return y_field {y_field!r} on step {i}; got keys {sorted(new_state)}"
            )
            raise ValueError(msg)
        xs.append(float(new_state[x_field]))
        ys.append(float(new_state[y_field]))
        state = new_state

    return np.asarray(xs, dtype=np.float64), np.asarray(ys, dtype=np.float64)


def sweep_static_for_validation(
    model: PhysicsModelProtocol,
    params: Mapping[str, float],
    *,
    x_values: NDArray[np.float64],
    x_field: str,
    y_field: str,
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Sweep a static model over ``x_values`` and collect ``y_field``.

    For each ``x`` in ``x_values``, overrides ``params[x_field]`` with
    ``x``, calls ``model.compute({}, params_with_x, None)``, and reads
    ``out_state[y_field]``.

    Returns ``(x_values, sim_y)`` so the returned ``sim_x`` is exactly
    the input grid.

    Raises:
        ValueError: For empty ``x_values`` or when the first output
            state is missing ``y_field``.
    """
    if x_values.ndim != 1:
        msg = f"sweep_static_for_validation: x_values must be 1-D (got shape {x_values.shape})"
        raise ValueError(msg)
    if x_values.size == 0:
        msg = "sweep_static_for_validation: x_values is empty"
        raise ValueError(msg)

    ys = np.empty(x_values.size, dtype=np.float64)
    for i, x in enumerate(x_values):
        sweep_params: dict[str, float] = dict(params)
        sweep_params[x_field] = float(x)
        out = model.compute({}, sweep_params, None)
        if y_field not in out:
            msg = (
                f"sweep_static_for_validation: model {model.name!r} did not "
                f"return y_field {y_field!r} for x={x}; got keys {sorted(out)}"
            )
            raise ValueError(msg)
        ys[i] = float(out[y_field])

    return x_values.astype(np.float64, copy=False), ys


def run_validation_for_model(
    model: PhysicsModelProtocol,
    *,
    params: Mapping[str, float],
    measured_x: NDArray[np.float64],
    measured_y: NDArray[np.float64],
    y_field: str,
    x_field: str | None = None,
    initial_state: Mapping[str, Any] | None = None,
    dt_s: float | None = None,
) -> ValidationRun:
    """Validate ``model`` against measured data, dispatching on time mode.

    ``x_field`` defaults differ per time mode:

    - ``"dynamic"``: ``"time_s"`` (the runner samples the simulator's
      time axis to align with ``measured_x``).
    - ``"static"``: caller must supply ``x_field`` (the parameter being
      swept — e.g. ``"range_m"``).

    Args:
        model: Any object satisfying :class:`PhysicsModelProtocol`.
        params: Slider values keyed by :attr:`PhysicsParam.name`.
        measured_x: Measured independent axis (sorted ascending
            recommended; not required by the metrics).
        measured_y: Measured dependent axis (same shape as
            ``measured_x``).
        y_field: Output state key the model writes the simulated y into.
        x_field: For ``"static"`` models, the parameter / state key the
            runner sweeps. Optional for ``"dynamic"`` (defaults to
            ``"time_s"``).
        initial_state: ``"dynamic"`` only — starting state dict.
        dt_s: ``"dynamic"`` only — step size.

    Raises:
        ValueError: For missing dynamic-mode args, unknown ``time_mode``,
            or shape/empty issues bubbling up from helpers.
    """
    if measured_x.shape != measured_y.shape:
        msg = (
            f"run_validation_for_model: measured_x {measured_x.shape} != "
            f"measured_y {measured_y.shape}"
        )
        raise ValueError(msg)
    if measured_x.ndim != 1:
        msg = (
            f"run_validation_for_model: measured arrays must be 1-D (got shape {measured_x.shape})"
        )
        raise ValueError(msg)
    if measured_x.size == 0:
        msg = "run_validation_for_model: measured arrays are empty"
        raise ValueError(msg)

    time_mode = model.time_mode
    if time_mode == "dynamic":
        if dt_s is None:
            msg = "run_validation_for_model: dt_s required when model.time_mode == 'dynamic'"
            raise ValueError(msg)
        resolved_x_field = x_field or "time_s"
        t_end_s = float(np.max(measured_x))
        if t_end_s <= 0.0:
            msg = (
                "run_validation_for_model: dynamic measured_x must include a "
                f"positive value (max={t_end_s})"
            )
            raise ValueError(msg)
        sim_x, sim_y = simulate_dynamic_for_validation(
            model,
            params,
            initial_state=initial_state,
            dt_s=dt_s,
            t_end_s=t_end_s,
            x_field=resolved_x_field,
            y_field=y_field,
        )
    elif time_mode == "static":
        if x_field is None:
            msg = "run_validation_for_model: x_field required when model.time_mode == 'static'"
            raise ValueError(msg)
        sim_x, sim_y = sweep_static_for_validation(
            model,
            params,
            x_values=measured_x,
            x_field=x_field,
            y_field=y_field,
        )
    else:
        msg = (
            f"run_validation_for_model: unsupported model.time_mode "
            f"{time_mode!r} (expected 'dynamic' or 'static')"
        )
        raise ValueError(msg)

    metrics = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
    return ValidationRun(metrics=metrics, sim_x=sim_x, sim_y=sim_y)
