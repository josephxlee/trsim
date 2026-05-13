"""Validation Bench metrics (PL-9.2c, plan/19 § 19.9.4).

Compares a measurement curve ``(x_meas, y_meas)`` against a simulated
curve ``(x_sim, y_sim)`` by interpolating the simulation onto the
measured x-grid and reducing the residuals to three scalar metrics:

================== =====================================================
metric             definition
================== =====================================================
``rmse``           ``sqrt(mean((y_sim_interp - y_meas)**2))``
``max_abs_error``  ``max(|y_sim_interp - y_meas|)``
``pearson_corr``   sample Pearson correlation between ``y_meas`` and
                   ``y_sim_interp`` (``0.0`` when either has zero
                   variance — avoids ``NaN`` propagation).
================== =====================================================

The function deliberately stays in the domain layer (no Qt, no
pyqtgraph) so the App-layer validation controller can call it from
any context. PL-9.2d (Parameter Studio) reuses it as the loss
function during ``scipy.optimize`` fitting.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class ValidationMetrics:
    """Three scalar metrics characterising the measurement-vs-sim fit.

    Attributes:
        n_samples: Number of points used (== ``len(measured_y)`` once
            measured points outside the simulation x-range are dropped).
        rmse: Root-mean-square error.
        max_abs_error: Largest absolute residual.
        pearson_correlation: ``[-1, 1]``. ``0.0`` for degenerate
            zero-variance inputs.
    """

    n_samples: int
    rmse: float
    max_abs_error: float
    pearson_correlation: float


@dataclass(frozen=True, slots=True)
class ValidationRun:
    """Bundle of metrics + simulated curve from a Validation Bench run.

    Wraps :class:`ValidationMetrics` together with the simulated
    ``(sim_x, sim_y)`` arrays the runner produced, so UI callers can
    score *and* render the overlay from a single object without doing a
    second simulation pass.

    Attributes:
        metrics: Scalar comparison metrics.
        sim_x: Simulation x-axis samples (e.g. ``time_s``, ``range_m``).
        sim_y: Simulation y-axis samples (output state key per spec).
    """

    metrics: ValidationMetrics
    sim_x: NDArray[np.float64]
    sim_y: NDArray[np.float64]


def compute_validation_metrics(
    measured_x: NDArray[np.float64],
    measured_y: NDArray[np.float64],
    sim_x: NDArray[np.float64],
    sim_y: NDArray[np.float64],
) -> ValidationMetrics:
    """Interpolate ``(sim_x, sim_y)`` onto ``measured_x`` and reduce.

    Drops measurement points that fall outside ``[sim_x[0], sim_x[-1]]``
    so the comparison stays within the simulated time / parameter range.
    Raises :class:`ValueError` for mis-shaped inputs or empty arrays.
    """
    if measured_x.shape != measured_y.shape:
        msg = (
            f"compute_validation_metrics: measured_x {measured_x.shape} != "
            f"measured_y {measured_y.shape}"
        )
        raise ValueError(msg)
    if sim_x.shape != sim_y.shape:
        msg = f"compute_validation_metrics: sim_x {sim_x.shape} != sim_y {sim_y.shape}"
        raise ValueError(msg)
    if measured_x.size == 0 or sim_x.size == 0:
        msg = "compute_validation_metrics: empty input arrays"
        raise ValueError(msg)
    if measured_x.ndim != 1 or sim_x.ndim != 1:
        msg = "compute_validation_metrics: inputs must be 1-D"
        raise ValueError(msg)

    # numpy.interp expects xp to be sorted ascending. Sort once.
    sim_order = np.argsort(sim_x)
    sim_x_sorted = sim_x[sim_order]
    sim_y_sorted = sim_y[sim_order]

    # Restrict measured points to the simulation x-range.
    x_lo = float(sim_x_sorted[0])
    x_hi = float(sim_x_sorted[-1])
    mask = (measured_x >= x_lo) & (measured_x <= x_hi)
    mx = measured_x[mask]
    my = measured_y[mask]
    if mx.size == 0:
        msg = (
            "compute_validation_metrics: no measured points fall inside the "
            f"simulated x-range [{x_lo}, {x_hi}]"
        )
        raise ValueError(msg)

    sim_interp = np.interp(mx, sim_x_sorted, sim_y_sorted)
    residuals = sim_interp - my
    rmse = float(np.sqrt(np.mean(residuals * residuals)))
    max_abs = float(np.max(np.abs(residuals)))

    if my.std() == 0.0 or sim_interp.std() == 0.0:
        corr = 0.0
    else:
        corr = float(np.corrcoef(my, sim_interp)[0, 1])

    return ValidationMetrics(
        n_samples=int(mx.size),
        rmse=rmse,
        max_abs_error=max_abs,
        pearson_correlation=corr,
    )
