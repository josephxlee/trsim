"""ExtendedTarget glint RMS Monte Carlo regression (Phase 5.21 + 5.21b).

Companion to ``tests/physics/test_extended_target_glint.py`` (Phase
5.14). 5.14 verified the closed-form 2-scatterer reference and the
Skolnik glint *bounds* (apparent in scatterer convex hull, |sum| <=
sum amp). This file verifies the *statistical* characterisation in
plan/14 § 14.10.6:

5.21 (existing) — single 5-point aircraft cloud (L ~ 12 m, N = 5):
- Skolnik rule-of-thumb: sigma_glint ~ L / (2*sqrt(N)).
- Per-axis glint std stays below the rule bound.
- |glint| stays inside the convex-hull bound L.
- Deterministic under fixed seed.

5.21b (this revision) — N-scaling / L-scaling invariants across a
parametric uniform-line target (body x-axis evenly spaced points):
- Holding L fixed and growing N from 2 -> 5 -> 10, the per-axis std
  decays monotonically (1/sqrt(N) trend).
- Holding N fixed and growing L from 4 -> 12 -> 40 m, the per-axis
  std grows monotonically (linear-in-L trend).
- Every (L, N) pair stays inside the rule-of-thumb upper bound.
- Closed-form sigma_rule reference values match plan/14 § 14.10.6
  examples (missile L=5/N=3 -> 1.443 m, aircraft L=15/N=5 -> 3.354 m,
  ship L=100/N=5 -> 22.361 m).
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


# ---------------------------------------------------------------------
# 5.21b — N-scaling / L-scaling invariants (plan/14 § 14.10.6)
# ---------------------------------------------------------------------


def _uniform_line_target(*, length_m: float, n_scatterers: int) -> ExtendedTarget:
    """Build a target with N scatterers uniformly spaced on body x-axis.

    Used by the 5.21b scaling tests to vary L (span) and N (count)
    independently while keeping the body-y/z layout trivial. The
    per-scatterer RCS is fixed at 0 dBsm (1 m^2) so amplitude weights
    are equal — the closest geometric match to the Skolnik rule
    sigma ~ L / (2 sqrt(N)) which assumes uniform reflectivity.
    """
    if length_m <= 0.0:
        msg = f"length_m must be > 0, got {length_m}"
        raise ValueError(msg)
    if n_scatterers < 2:
        msg = f"n_scatterers must be >= 2, got {n_scatterers}"
        raise ValueError(msg)
    half = length_m / 2.0
    positions = np.linspace(-half, half, n_scatterers)
    scatterers = tuple(
        Scatterer(offset_body_m=(float(pos), 0.0, 0.0), rcs_dbsm=0.0, label=f"pt_{i}")
        for i, pos in enumerate(positions)
    )
    return ExtendedTarget(
        target_id=f"uniform_L{int(length_m)}_N{n_scatterers}",
        scatterers=scatterers,
    )


def _glint_sweep_target(
    target: ExtendedTarget,
    *,
    seed: int = _RNG_SEED,
    n_samples: int = _N_SAMPLES,
) -> np.ndarray:
    """Run a Monte-Carlo attitude / frequency sweep on ``target``.

    Generalisation of :func:`_glint_sweep`; same RNG distribution but
    parameterised by target so we can sweep multiple (L, N) cases.
    """
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


def _sigma_rule(*, length_m: float, n_scatterers: int) -> float:
    """Skolnik rule-of-thumb upper bound sigma ~ L / (2 sqrt(N))."""
    return length_m / (2.0 * math.sqrt(n_scatterers))


def test_plan_14_10_6_aircraft_example_value() -> None:
    """plan/14 § 14.10.6 example: aircraft L=15 m, N=5 -> sigma ~ 3.354 m.

    The plan rounds to 3.4 m; we lock the exact closed-form value here.
    """
    assert _sigma_rule(length_m=15.0, n_scatterers=5) == pytest.approx(3.354101966249685, rel=1e-12)


def test_plan_14_10_6_ship_example_value() -> None:
    """plan/14 § 14.10.6 example: ship L=100 m, N=5 -> sigma ~ 22.361 m
    (plan rounds to 22 m).
    """
    assert _sigma_rule(length_m=100.0, n_scatterers=5) == pytest.approx(
        22.360679774997898, rel=1e-12
    )


def test_plan_14_10_6_missile_example_value() -> None:
    """plan/14 § 14.10.6 example: missile L=5 m, N=3 -> sigma ~ 1.443 m
    (plan rounds to 1.4 m).
    """
    assert _sigma_rule(length_m=5.0, n_scatterers=3) == pytest.approx(1.4433756729740645, rel=1e-12)


def test_uniform_line_target_construction_rejects_bad_inputs() -> None:
    """Helper validation — keeps the parametric fixture honest."""
    with pytest.raises(ValueError, match=r"length_m must be > 0"):
        _uniform_line_target(length_m=0.0, n_scatterers=3)
    with pytest.raises(ValueError, match=r"length_m must be > 0"):
        _uniform_line_target(length_m=-1.0, n_scatterers=3)
    with pytest.raises(ValueError, match=r"n_scatterers must be >= 2"):
        _uniform_line_target(length_m=10.0, n_scatterers=1)


def test_n_scaling_per_axis_std_monotonic_decay_fixed_l() -> None:
    """Holding L = 12 m fixed and growing N from 2 -> 5 -> 10, the per-
    axis glint std must decay monotonically (Skolnik 1/sqrt(N) trend).
    """
    length_m = 12.0
    stds_per_axis: list[float] = []
    for n in (2, 5, 10):
        target = _uniform_line_target(length_m=length_m, n_scatterers=n)
        glints = _glint_sweep_target(target)
        # Use the max-axis std as a single scalar — robust to which
        # axis the body x-axis happens to project onto after rotation.
        stds_per_axis.append(float(glints.std(axis=0).max()))
    assert stds_per_axis[0] > stds_per_axis[1] > stds_per_axis[2], (
        f"std should decay with N; got {stds_per_axis}"
    )


def test_l_scaling_per_axis_std_monotonic_growth_fixed_n() -> None:
    """Holding N = 5 fixed and growing L from 4 -> 12 -> 40 m, the per-
    axis glint std must grow monotonically (rule sigma is linear in L).
    """
    n_scatterers = 5
    stds_per_axis: list[float] = []
    for length_m in (4.0, 12.0, 40.0):
        target = _uniform_line_target(length_m=length_m, n_scatterers=n_scatterers)
        glints = _glint_sweep_target(target)
        stds_per_axis.append(float(glints.std(axis=0).max()))
    assert stds_per_axis[0] < stds_per_axis[1] < stds_per_axis[2], (
        f"std should grow with L; got {stds_per_axis}"
    )


def test_rule_of_thumb_bound_holds_across_n_variants() -> None:
    """For uniform-line targets with L = 12 m, every N in {2, 5, 10}
    must keep per-axis std <= rule sigma. The rule is an *upper* bound;
    actual std is typically a fraction of it.
    """
    length_m = 12.0
    for n in (2, 5, 10):
        target = _uniform_line_target(length_m=length_m, n_scatterers=n)
        glints = _glint_sweep_target(target)
        per_axis_std = glints.std(axis=0)
        bound = _sigma_rule(length_m=length_m, n_scatterers=n)
        max_std = float(per_axis_std.max())
        assert max_std <= bound, f"N={n}: max_std={max_std:.4f} > rule bound={bound:.4f}"


def test_rule_of_thumb_bound_holds_across_l_variants() -> None:
    """For uniform-line targets with N = 5, every L in {4, 12, 40} m
    must keep per-axis std <= rule sigma.
    """
    n_scatterers = 5
    for length_m in (4.0, 12.0, 40.0):
        target = _uniform_line_target(length_m=length_m, n_scatterers=n_scatterers)
        glints = _glint_sweep_target(target)
        per_axis_std = glints.std(axis=0)
        bound = _sigma_rule(length_m=length_m, n_scatterers=n_scatterers)
        max_std = float(per_axis_std.max())
        assert max_std <= bound, f"L={length_m}: max_std={max_std:.4f} > rule bound={bound:.4f}"


def test_glint_norm_within_l_bound_for_extreme_aspect_ratios() -> None:
    """For any uniform-line target, |glint| must stay strictly within L
    (apparent centroid cannot exceed scatterer convex-hull span). Verify
    at the small-N edge (N=2 dumbbell) and large-N edge (N=10).
    """
    for n in (2, 10):
        target = _uniform_line_target(length_m=12.0, n_scatterers=n)
        glints = _glint_sweep_target(target)
        norms = np.linalg.norm(glints, axis=1)
        assert float(norms.max()) < 12.0, f"N={n}: norm exceeded L"
