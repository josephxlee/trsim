"""Parameter Studio fitter tests (PL-9.2d, plan/19 § 19.9.3)."""

from __future__ import annotations

import numpy as np
import pytest

from workbench.app.physics_lab import (
    BouncingBallSimulator,
    FitConfig,
    FitResult,
    fit_bouncing_ball,
)


def _generate_trajectory(
    *,
    gravity: float = 9.81,
    restitution: float = 0.5,
    drag: float = 0.0,
    height: float = 5.0,
    velocity: float = 0.0,
    duration_s: float = 3.0,
    dt_s: float = 0.005,
) -> tuple[np.ndarray, np.ndarray]:
    """Run a Bouncing Ball trajectory and return ``(t, y)`` arrays.

    Used both as the synthetic "measurement" for the fit + as the
    ground-truth comparison.
    """
    sim = BouncingBallSimulator(
        gravity_m_s2=gravity,
        restitution=restitution,
        initial_height_m=height,
        initial_velocity_m_s=velocity,
        drag_coefficient_k=drag,
    )
    n_steps = max(2, int(np.ceil(duration_s / dt_s)) + 1)
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
# FitConfig
# ---------------------------------------------------------------------


def test_fit_config_default_only_restitution() -> None:
    cfg = FitConfig()
    assert cfg.fit_restitution is True
    assert cfg.fit_drag_coefficient_k is False
    assert cfg.fit_gravity_m_s2 is False
    assert cfg.fit_initial_height_m is False
    assert cfg.free_count() == 1


def test_fit_config_all_off_count_zero() -> None:
    cfg = FitConfig(
        fit_restitution=False,
        fit_drag_coefficient_k=False,
        fit_gravity_m_s2=False,
        fit_initial_height_m=False,
    )
    assert cfg.free_count() == 0


# ---------------------------------------------------------------------
# Error paths
# ---------------------------------------------------------------------


def test_empty_measurement_rejected() -> None:
    with pytest.raises(ValueError, match=r"empty measured"):
        fit_bouncing_ball(
            measured_x=np.array([]),
            measured_y=np.array([]),
            initial_gravity_m_s2=9.81,
            initial_restitution=0.7,
            initial_drag_coefficient_k=0.0,
            initial_height_m=5.0,
            initial_velocity_m_s=0.0,
        )


def test_all_off_config_rejected() -> None:
    with pytest.raises(ValueError, match=r"at least one FitConfig"):
        fit_bouncing_ball(
            measured_x=np.array([0.0, 1.0]),
            measured_y=np.array([5.0, 0.0]),
            initial_gravity_m_s2=9.81,
            initial_restitution=0.7,
            initial_drag_coefficient_k=0.0,
            initial_height_m=5.0,
            initial_velocity_m_s=0.0,
            config=FitConfig(fit_restitution=False),
        )


def test_non_positive_duration_rejected() -> None:
    with pytest.raises(ValueError, match=r"positive values"):
        fit_bouncing_ball(
            measured_x=np.array([0.0, 0.0]),
            measured_y=np.array([5.0, 5.0]),
            initial_gravity_m_s2=9.81,
            initial_restitution=0.7,
            initial_drag_coefficient_k=0.0,
            initial_height_m=5.0,
            initial_velocity_m_s=0.0,
        )


# ---------------------------------------------------------------------
# Convergence (synthetic data)
# ---------------------------------------------------------------------


def test_recovers_restitution_from_synthetic_measurement() -> None:
    """Generate a known-restitution trajectory, then fit from a
    biased starting point. The optimiser should walk back to within
    ~5 % of the true value.
    """
    true_r = 0.5
    measured_t, measured_y = _generate_trajectory(restitution=true_r)
    result = fit_bouncing_ball(
        measured_x=measured_t,
        measured_y=measured_y,
        initial_gravity_m_s2=9.81,
        initial_restitution=0.85,  # biased
        initial_drag_coefficient_k=0.0,
        initial_height_m=5.0,
        initial_velocity_m_s=0.0,
        dt_s=0.005,
        max_iter=200,
    )
    assert result.success
    assert result.fitted_restitution == pytest.approx(true_r, abs=0.05)
    assert result.final_rmse < 0.1


def test_recovers_two_parameters_when_both_free() -> None:
    """Fit restitution + drag simultaneously. Synthetic trajectory uses
    moderate drag + moderate restitution; starting point is biased
    on both axes.
    """
    measured_t, measured_y = _generate_trajectory(restitution=0.6, drag=0.05, duration_s=2.0)
    result = fit_bouncing_ball(
        measured_x=measured_t,
        measured_y=measured_y,
        initial_gravity_m_s2=9.81,
        initial_restitution=0.85,
        initial_drag_coefficient_k=0.0,
        initial_height_m=5.0,
        initial_velocity_m_s=0.0,
        config=FitConfig(fit_restitution=True, fit_drag_coefficient_k=True),
        max_iter=400,
    )
    assert result.final_rmse < 0.2
    # The combined fit may not hit the exact ground truth (drag +
    # restitution have a degeneracy), but the RMSE must improve well
    # beyond the initial mismatch.


def test_zero_initial_drag_unchanged_when_drag_not_free() -> None:
    """drag stays at the initial value when only restitution is
    free."""
    measured_t, measured_y = _generate_trajectory(restitution=0.5, drag=0.0)
    result = fit_bouncing_ball(
        measured_x=measured_t,
        measured_y=measured_y,
        initial_gravity_m_s2=9.81,
        initial_restitution=0.7,
        initial_drag_coefficient_k=0.42,  # off-axis initial
        initial_height_m=5.0,
        initial_velocity_m_s=0.0,
    )
    assert result.fitted_drag_coefficient_k == pytest.approx(0.42)


def test_result_is_frozen_dataclass() -> None:
    result = fit_bouncing_ball(
        measured_x=np.array([0.0, 1.0, 2.0]),
        measured_y=np.array([5.0, 0.0, 1.0]),
        initial_gravity_m_s2=9.81,
        initial_restitution=0.7,
        initial_drag_coefficient_k=0.0,
        initial_height_m=5.0,
        initial_velocity_m_s=0.0,
        max_iter=10,
    )
    assert isinstance(result, FitResult)
    with pytest.raises(Exception):  # noqa: B017 — frozen attribute set
        result.success = False  # type: ignore[misc]
