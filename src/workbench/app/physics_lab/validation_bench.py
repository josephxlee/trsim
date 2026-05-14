"""Generalized Validation Bench (Phase 9 § 19.7.5+ P2).

The PL-9.2c
:meth:`workbench.ui.physics_lab.bouncing_ball_demo.BouncingBallController.run_validation_from_dataset`
ties the Validation Bench to the Bouncing Ball simulator. Phase 9 §
19.7.5+ generalises the bench to **any**
:class:`workbench.sdk.protocols.PhysicsModelProtocol` instance —
dynamic models (state propagated forward by ``dt_s``) and static
models (single-shot evaluation per measured ``x`` value).

The bench is a pure-Python + numpy helper; the UI controller picks up
the resulting ``(sim_x, sim_y, ValidationMetrics)`` triple and paints
overlay curves itself.

Usage — dynamic model::

    bench = ValidationBench(model=bouncing_ball_model)
    sim_x, sim_y, metrics = bench.evaluate(
        measured_x=measured_t,
        measured_y=measured_y,
        params={"gravity_m_s2": 9.81, "restitution": 0.7,
                "initial_height_m": 5.0, "initial_velocity_m_s": 0.0,
                "drag_coefficient_k": 0.0},
        config=ValidationConfig(
            output_field="position_m",
            initial_state={"time_s": 0.0, "position_m": 5.0,
                           "velocity_m_s": 0.0, "bounces": 0},
            dt_s=0.005,
        ),
    )

Usage — static model::

    bench = ValidationBench(model=free_space_loss_model)
    sim_x, sim_y, metrics = bench.evaluate(
        measured_x=measured_range_m,
        measured_y=measured_loss_db,
        params={"freq_hz": 9.4e9},  # range_m overridden per-sample
        config=ValidationConfig(
            output_field="loss_db",
            input_field="range_m",       # static models map x -> params[input_field]
        ),
    )
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from workbench.domain.physics_lab.validation import (
    ValidationMetrics,
    compute_validation_metrics,
)
from workbench.sdk.protocols import PhysicsModelProtocol


@dataclass(frozen=True, slots=True)
class ValidationConfig:
    """How to drive the model from a measured ``(x, y)`` pair.

    Attributes:
        output_field: Key in the ``compute(...)`` return mapping whose
            value is the model's prediction at the current step / x
            value. Must be present in every ``compute`` output, otherwise
            :meth:`ValidationBench.evaluate` raises ``KeyError``.
        initial_state: Starting state mapping handed to a **dynamic**
            model's first ``compute`` call. Ignored for static models.
        input_field: For **static** models, the parameter name that is
            overridden with each measured x value (e.g. ``"range_m"``).
            Ignored for dynamic models.
        dt_s: Integration step size used by **dynamic** models. Ignored
            for static models. Must be > 0.
        n_samples: Number of equally-spaced sim points sampled across
            the measured x-range for **static** models. Ignored for
            dynamic models. Must be >= 2.

    Raises:
        ValueError: For ``dt_s <= 0`` or ``n_samples < 2``.
    """

    output_field: str
    initial_state: Mapping[str, Any] = field(default_factory=dict)
    input_field: str | None = None
    dt_s: float = 0.005
    n_samples: int = 256

    def __post_init__(self) -> None:
        if self.dt_s <= 0.0:
            msg = f"ValidationConfig: dt_s must be > 0, got {self.dt_s}"
            raise ValueError(msg)
        if self.n_samples < 2:
            msg = f"ValidationConfig: n_samples must be >= 2, got {self.n_samples}"
            raise ValueError(msg)


class ValidationBench:
    """Run any :class:`PhysicsModelProtocol` against a measured curve.

    Args:
        model: The PhysicsModelProtocol instance to validate. Its
            ``time_mode`` decides whether :meth:`evaluate` integrates
            forward (``"dynamic"``) or sweeps the input axis (``"static"``).

    Raises:
        ValueError: If ``model.time_mode`` is neither ``"dynamic"`` nor
            ``"static"``.
    """

    def __init__(self, *, model: PhysicsModelProtocol) -> None:
        self._model = model
        if model.time_mode not in ("dynamic", "static"):
            msg = (
                f"ValidationBench: unsupported time_mode {model.time_mode!r} "
                f"(expected 'dynamic' or 'static')"
            )
            raise ValueError(msg)

    @property
    def model(self) -> PhysicsModelProtocol:
        return self._model

    def evaluate(
        self,
        *,
        measured_x: NDArray[np.float64],
        measured_y: NDArray[np.float64],
        params: Mapping[str, float],
        config: ValidationConfig,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], ValidationMetrics]:
        """Run the model and score it against ``(measured_x, measured_y)``.

        Returns:
            A 3-tuple ``(sim_x, sim_y, metrics)`` where ``sim_x`` /
            ``sim_y`` are the simulated curve (so callers can overlay
            it) and ``metrics`` is a :class:`ValidationMetrics`.
        """
        if measured_x.ndim != 1 or measured_y.ndim != 1:
            msg = "ValidationBench.evaluate: measured arrays must be 1-D"
            raise ValueError(msg)
        if measured_x.size == 0:
            msg = "ValidationBench.evaluate: measured arrays must be non-empty"
            raise ValueError(msg)
        if measured_x.shape != measured_y.shape:
            msg = (
                f"ValidationBench.evaluate: measured_x {measured_x.shape} != "
                f"measured_y {measured_y.shape}"
            )
            raise ValueError(msg)

        if self._model.time_mode == "dynamic":
            sim_x, sim_y = self._simulate_dynamic(measured_x, params, config)
        else:
            sim_x, sim_y = self._simulate_static(measured_x, params, config)

        metrics = compute_validation_metrics(measured_x, measured_y, sim_x, sim_y)
        return sim_x, sim_y, metrics

    # ------------------------------------------------------------------
    # Dynamic-model integration loop
    # ------------------------------------------------------------------
    def _simulate_dynamic(
        self,
        measured_x: NDArray[np.float64],
        params: Mapping[str, float],
        config: ValidationConfig,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        end_t = float(measured_x.max())
        if end_t <= 0.0:
            msg = (
                "ValidationBench.evaluate: dynamic mode requires measured_x to "
                "include positive values (interpreted as time)"
            )
            raise ValueError(msg)
        n_steps = max(2, int(np.ceil(end_t / config.dt_s)) + 1)
        xs = np.empty(n_steps, dtype=np.float64)
        ys = np.empty(n_steps, dtype=np.float64)
        # Seed the time + initial output value from ``initial_state`` so
        # the very first sim sample matches whatever the model expects.
        state: Mapping[str, Any] = dict(config.initial_state)
        xs[0] = float(state.get("time_s", 0.0))
        ys[0] = self._extract_output(state, config.output_field, allow_missing=True)
        for i in range(1, n_steps):
            new_state = self._model.compute(state, params, config.dt_s)
            xs[i] = float(new_state.get("time_s", xs[i - 1] + config.dt_s))
            ys[i] = self._extract_output(new_state, config.output_field)
            state = new_state
        return xs, ys

    # ------------------------------------------------------------------
    # Static-model axis-sweep loop
    # ------------------------------------------------------------------
    def _simulate_static(
        self,
        measured_x: NDArray[np.float64],
        params: Mapping[str, float],
        config: ValidationConfig,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        if config.input_field is None:
            msg = "ValidationBench.evaluate: static models require ValidationConfig.input_field"
            raise ValueError(msg)
        x_lo = float(measured_x.min())
        x_hi = float(measured_x.max())
        if x_hi <= x_lo:
            msg = "ValidationBench.evaluate: static measured_x must span a non-zero range"
            raise ValueError(msg)
        sim_x = np.linspace(x_lo, x_hi, config.n_samples, dtype=np.float64)
        sim_y = np.empty_like(sim_x)
        merged = dict(params)
        for i, x_val in enumerate(sim_x):
            merged[config.input_field] = float(x_val)
            out = self._model.compute({}, merged, None)
            sim_y[i] = self._extract_output(out, config.output_field)
        return sim_x, sim_y

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_output(
        state: Mapping[str, Any],
        field_name: str,
        *,
        allow_missing: bool = False,
    ) -> float:
        if field_name not in state:
            if allow_missing:
                return 0.0
            msg = (
                f"ValidationBench: output_field {field_name!r} missing from "
                f"compute() return — keys = {sorted(state.keys())}"
            )
            raise KeyError(msg)
        return float(state[field_name])
