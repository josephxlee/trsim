"""ExtendedTarget glint RMS Monte Carlo regression (Phase 5.21).

Companion to ``tests/physics/test_extended_target_glint.py`` (Phase
5.14). 5.14 verified the closed-form 2-scatterer reference and the
Skolnik glint *bounds* (apparent in scatterer convex hull, |sum| <=
sum amp). This file verifies the *statistical* characterisation in
plan/14 § 14.10.6:

- Skolnik rule-of-thumb: sigma_glint ~ L / (2*sqrt(N)), where L is the
  target physical span and N the scatterer count.
- For a 5-point aircraft cloud (L ~ 12 m, N = 5), the per-axis glint
  standard deviation across a uniform attitude / frequency sweep
  stays below the rule-of-thumb upper bound and the |glint| stays
  inside the convex-hull bound L.
- The Monte-Carlo loop is deterministic (numpy default_rng seed
  fixed) so the same seed reproduces the same sample-statistic
  bit-for-bit on every run.
"""

from __future__ import annotations

import math
from typing import Final

import numpy as np
import pytest

from workbench.physics.reflection.extended_target import (
    ExtendedTarget,
    Scatterer,
    compute_extended_target_return,
)

_L_TARGET_M: Final[float] = 12.0
"""Physical span of the 5-scatterer aircraft cloud below
(body x range -5..+7 m + y range -6..+6 m). Used as the L in the
Skolnik rule-of-thumb."""

_N_SCATTERERS: Final[int] = 5

_N_SAMPLES: Final[int] = 500
"""Monte-Carlo sample count — enough for std to stabilise on the
order-of-magnitude check without making the test slow."""

_RNG_SEED: Final[int] = 42


def _aircraft_target() -> ExtendedTarget:
    return ExtendedTarget(
        target_id="aircraft_5pt",
        scatterers=(
            Scatterer(offset_body_m=(7.0, 0.0, 0.0), rcs_dbsm=5.0, label="nose"),
            Scatterer(offset_body_m=(0.0, 6.0, 0.0), rcs_dbsm=8.0, label="wing_R"),
            Scatterer(offset_body_m=(0.0, -6.0, 0.0), rcs_dbsm=8.0, label="wing_L"),
            Scatterer(offset_body_m=(-5.0, 0.0, 0.5), rcs_dbsm=4.0, label="tail"),
            Scatterer(offset_body_m=(1.0, 0.0, 0.5), rcs_dbsm=10.0, label="engine"),
        ),
    )


def _glint_sweep(seed: int = _RNG_SEED, n_samples: int = _N_SAMPLES) -> np.ndarray:
    """Run a Monte-Carlo attitude / frequency sweep and return an (N, 3)
    array of (E, N, U) glint offsets in metres.
    """
    target = _aircraft_target()
    rng = np.random.default_rng(seed=seed)
    glints: list[tuple[float, float, float]] = []
    for _ in range(n_samples):
        yaw = float(rng.uniform(-math.pi, math.pi))
        pitch = float(rng.uniform(-math.pi / 6, math.pi / 6))
        roll = float(rng.uniform(-math.pi / 6, math.pi / 6))
        freq = float(rng.uniform(9.0e9, 10.0e9))
        result = compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(0.0, 30_000.0, 5000.0),
            target_attitude_rad=(yaw, pitch, roll),
            frequency_hz=freq,
        )
        glints.append(result.glint_offset_m)
    return np.asarray(glints, dtype=np.float64)


# ---------------------------------------------------------------------
# Skolnik rule-of-thumb (plan/14 § 14.10.6)
# ---------------------------------------------------------------------


def test_skolnik_rule_of_thumb_formula() -> None:
    """sigma_glint ~ L / (2 sqrt(N)) — closed-form sanity-lock of the
    rule. 12 / (2 sqrt(5)) ~ 2.683 m for the aircraft cloud.
    """
    sigma_rule = _L_TARGET_M / (2.0 * math.sqrt(_N_SCATTERERS))
    assert sigma_rule == pytest.approx(2.6832815729997477, rel=1e-12)


def test_glint_per_axis_std_within_rule_of_thumb_upper_bound() -> None:
    """Each axis std of the Monte-Carlo glint distribution must stay
    below the Skolnik rule-of-thumb. The rule is a rough upper bound,
    not a target — a realistic non-uniform scatterer cloud should
    sit well inside it (our case yields ~0.45 m vs the 2.68 m bound).
    """
    glints = _glint_sweep()
    per_axis_std = glints.std(axis=0)
    sigma_rule = _L_TARGET_M / (2.0 * math.sqrt(_N_SCATTERERS))
    assert float(per_axis_std[0]) < sigma_rule
    assert float(per_axis_std[1]) < sigma_rule
    assert float(per_axis_std[2]) < sigma_rule


def test_glint_norm_within_convex_hull_bound() -> None:
    """|glint| must stay inside L for every sample — the apparent
    centroid cannot leave the scatterer convex hull (Skolnik glint
    definition, also covered structurally in 5.14).
    """
    glints = _glint_sweep()
    norms = np.linalg.norm(glints, axis=1)
    assert float(norms.max()) < _L_TARGET_M


def test_symmetric_body_glint_east_mean_near_zero() -> None:
    """The aircraft cloud is L/R symmetric in body y (wings, tail,
    engine sit on the body x-z plane). Averaged over uniform yaw, the
    E-axis glint must wash out to within a small fraction of the
    per-axis std.
    """
    glints = _glint_sweep()
    e_mean = float(glints[:, 0].mean())
    e_std = float(glints[:, 0].std())
    # Mean must be tiny compared to std (no DC bias along E).
    assert abs(e_mean) < 0.2 * e_std


# ---------------------------------------------------------------------
# Determinism (same seed -> same statistic, bit-for-bit)
# ---------------------------------------------------------------------


def test_monte_carlo_glint_is_deterministic_under_fixed_seed() -> None:
    """Two sweeps with the same seed must return numerically identical
    arrays — no hidden non-determinism in compute_extended_target_return.
    """
    glints_a = _glint_sweep(seed=42, n_samples=64)
    glints_b = _glint_sweep(seed=42, n_samples=64)
    np.testing.assert_array_equal(glints_a, glints_b)


def test_different_seed_produces_different_samples() -> None:
    """Sanity check the other direction — different seeds should not
    accidentally collide.
    """
    glints_a = _glint_sweep(seed=42, n_samples=64)
    glints_b = _glint_sweep(seed=43, n_samples=64)
    assert not np.array_equal(glints_a, glints_b)
