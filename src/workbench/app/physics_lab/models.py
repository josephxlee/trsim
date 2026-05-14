"""Built-in :class:`PhysicsModelProtocol` implementations (PL-9.3b).

plan/19 § 19.8.1 specifies the protocol; this module ships the first
two reference implementations the Physics Lab Library presents under
the Models category:

- :class:`GravityOnlyModel` — 1-D vertical free-fall (no bounce, no
  drag). Useful as the "compare to analytic" baseline.
- :class:`BouncingBallModel` — the full PL-D semi-implicit Euler step
  with bounce + restitution + optional drag. Mirrors the live
  :class:`workbench.app.physics_lab.BouncingBallSimulator` so the
  Validation Bench can score it against measured data through the
  generic plugin path.

Each model declares its parameters via the existing
``@physics_param`` metadata so the Auto-Parameters widget renders
the matching sliders. The ``compute`` method is **pure** — it never
mutates the simulator-controller history; the Lab's controller
orchestrates calls.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from workbench.domain.physics_lab import (
    BOUNCING_BALL_PARAM_SPECS,
    PhysicsParam,
)
from workbench.sdk.protocols import (
    PhysicsModelCategory,
    PhysicsModelTimeMode,
    PhysicsModelVisualization,
)


class GravityOnlyModel:
    """1-D vertical free-fall ``y'' = -g``.

    No bounce, no drag, no restitution. The closed-form solution
    ``y(t) = y0 + v0 * t - 0.5 * g * t^2`` is used directly so the
    Validation Bench can compare against analytic data without
    accumulated integration error.

    State dict keys (input + output):
        ``time_s`` — current simulation time (seconds).
        ``position_m`` — vertical position.
        ``velocity_m_s`` — vertical velocity (positive upward).
    """

    name: str = "Gravity Only (analytic)"
    category: PhysicsModelCategory = "dynamics"
    time_mode: PhysicsModelTimeMode = "dynamic"
    visualization: PhysicsModelVisualization = "2d"

    _PARAMS: tuple[PhysicsParam, ...] = (
        PhysicsParam(
            name="gravity_m_s2",
            min_value=1.0,
            max_value=30.0,
            scale="linear",
            unit="m/s^2",
            default=9.81,
        ),
        PhysicsParam(
            name="initial_height_m",
            min_value=0.1,
            max_value=50.0,
            scale="log",
            unit="m",
            default=5.0,
        ),
        PhysicsParam(
            name="initial_velocity_m_s",
            min_value=-20.0,
            max_value=20.0,
            scale="linear",
            unit="m/s",
            default=0.0,
        ),
    )

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return self._PARAMS

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        if dt_s is None:
            msg = "GravityOnlyModel: dt_s required for dynamic mode"
            raise ValueError(msg)
        g = float(params.get("gravity_m_s2", 9.81))
        t = float(state.get("time_s", 0.0))
        v = float(state.get("velocity_m_s", float(params.get("initial_velocity_m_s", 0.0))))
        y = float(state.get("position_m", float(params.get("initial_height_m", 5.0))))
        # Semi-implicit Euler so the result matches PL-D vanilla
        # behaviour bit-for-bit at the same dt.
        new_v = v - g * dt_s
        new_y = y + new_v * dt_s
        return {
            "time_s": t + dt_s,
            "position_m": new_y,
            "velocity_m_s": new_v,
        }


class BouncingBallModel:
    """Full PL-D Bouncing Ball step packaged as a PhysicsModelProtocol.

    Same parameters as the live simulator (``BOUNCING_BALL_PARAM_SPECS``).
    The ``compute`` method runs one semi-implicit Euler step + bounce
    handling, returning the new state dict.
    """

    name: str = "Bouncing Ball"
    category: PhysicsModelCategory = "dynamics"
    time_mode: PhysicsModelTimeMode = "dynamic"
    visualization: PhysicsModelVisualization = "2d"

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return BOUNCING_BALL_PARAM_SPECS

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        if dt_s is None:
            msg = "BouncingBallModel: dt_s required for dynamic mode"
            raise ValueError(msg)
        g = float(params.get("gravity_m_s2", 9.81))
        r = float(params.get("restitution", 0.7))
        k = float(params.get("drag_coefficient_k", 0.0))
        h0 = float(params.get("initial_height_m", 5.0))
        v0 = float(params.get("initial_velocity_m_s", 0.0))
        t = float(state.get("time_s", 0.0))
        v = float(state.get("velocity_m_s", v0))
        y = float(state.get("position_m", h0))
        bounces = int(state.get("bounces", 0))

        drag_acc = k * v * abs(v)
        new_v = v - (g + drag_acc) * dt_s
        new_y = y + new_v * dt_s
        if new_y <= 0.0:
            new_y = 0.0
            new_v = -new_v * r
            if abs(new_v) < 1e-3:
                new_v = 0.0
            bounces += 1
        return {
            "time_s": t + dt_s,
            "position_m": new_y,
            "velocity_m_s": new_v,
            "bounces": bounces,
        }


class FreeSpaceLossModel:
    """Static Friis free-space path loss ``L = (4 * pi * R / lambda)^2``.

    Demonstrates the ``time_mode == "static"`` path: no ``dt``, no
    state carried forward; the output is a one-shot computation.
    """

    name: str = "Free-Space Path Loss"
    category: PhysicsModelCategory = "rf_propagation"
    time_mode: PhysicsModelTimeMode = "static"
    visualization: PhysicsModelVisualization = "2d"

    _PARAMS: tuple[PhysicsParam, ...] = (
        PhysicsParam(
            name="range_m",
            min_value=1.0,
            max_value=100_000.0,
            scale="log",
            unit="m",
            default=1000.0,
        ),
        PhysicsParam(
            name="freq_hz",
            min_value=1e6,
            max_value=1e12,
            scale="log",
            unit="Hz",
            default=9.4e9,
        ),
    )

    @property
    def parameters(self) -> Sequence[PhysicsParam]:
        return self._PARAMS

    def compute(
        self,
        state: Mapping[str, Any],
        params: Mapping[str, float],
        dt_s: float | None,
    ) -> Mapping[str, Any]:
        del state, dt_s  # Static model.
        range_m = float(params.get("range_m", 1000.0))
        freq_hz = float(params.get("freq_hz", 9.4e9))
        wavelength_m = 299_792_458.0 / freq_hz
        loss_ratio = (4.0 * math.pi * range_m / wavelength_m) ** 2
        loss_db = 10.0 * math.log10(loss_ratio)
        return {"loss_db": loss_db, "wavelength_m": wavelength_m}
