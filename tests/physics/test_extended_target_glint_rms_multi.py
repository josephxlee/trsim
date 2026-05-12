"""ExtendedTarget glint Monte Carlo regression — additional N/L cases (Phase 5.21+).

Companion to ``test_extended_target_glint_rms.py`` (Phase 5.21). The
original 5.21 file fixed a single 5-scatterer 12 m aircraft cloud at
X-band. This file widens coverage on the Skolnik rule-of-thumb

    sigma_glint ~ L / (2 * sqrt(N))

by sweeping:

- scatterer count ``N`` (3 / 5 / 9 points);
- physical span ``L`` (small drone 2 m, fighter 12 m, transport 30 m);
- carrier frequency band (S / X / Ku);

and checking that

- per-axis glint std grows with ``L`` and shrinks with ``sqrt(N)`` in
  the expected direction (the rule-of-thumb is a soft upper bound,
  not a target — the test asserts directional invariants, not the
  scalar value);
- |glint| stays inside the convex-hull bound ``L`` for every sample;
- determinism holds across the wider parameter envelope (same seed
  -> bit-for-bit same Monte-Carlo array).
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

_N_SAMPLES: Final[int] = 400
_RNG_SEED: Final[int] = 1729


# ---------------------------------------------------------------------
# Target factories — three (N, L) regimes
# ---------------------------------------------------------------------


def _drone_3pt() -> ExtendedTarget:
    """Tiny drone-style 3-scatterer cloud: L_x ~ 2 m, N = 3."""
    return ExtendedTarget(
        target_id="drone_3pt",
        scatterers=(
            Scatterer(offset_body_m=(1.0, 0.0, 0.0), rcs_dbsm=-10.0, label="nose"),
            Scatterer(offset_body_m=(-1.0, 0.5, 0.0), rcs_dbsm=-12.0, label="right_arm"),
            Scatterer(offset_body_m=(-1.0, -0.5, 0.0), rcs_dbsm=-12.0, label="left_arm"),
        ),
    )


def _fighter_5pt() -> ExtendedTarget:
    """Reuse of the 5.21 baseline 5-point fighter (L ~ 12 m)."""
    return ExtendedTarget(
        target_id="fighter_5pt",
        scatterers=(
            Scatterer(offset_body_m=(7.0, 0.0, 0.0), rcs_dbsm=5.0, label="nose"),
            Scatterer(offset_body_m=(0.0, 6.0, 0.0), rcs_dbsm=8.0, label="wing_R"),
            Scatterer(offset_body_m=(0.0, -6.0, 0.0), rcs_dbsm=8.0, label="wing_L"),
            Scatterer(offset_body_m=(-5.0, 0.0, 0.5), rcs_dbsm=4.0, label="tail"),
            Scatterer(offset_body_m=(1.0, 0.0, 0.5), rcs_dbsm=10.0, label="engine"),
        ),
    )


def _transport_9pt() -> ExtendedTarget:
    """Large transport-style 9-point cloud: L ~ 30 m, N = 9."""
    return ExtendedTarget(
        target_id="transport_9pt",
        scatterers=(
            Scatterer(offset_body_m=(15.0, 0.0, 0.0), rcs_dbsm=10.0, label="nose"),
            Scatterer(offset_body_m=(-15.0, 0.0, 0.0), rcs_dbsm=8.0, label="tail"),
            Scatterer(offset_body_m=(0.0, 14.0, 0.0), rcs_dbsm=12.0, label="wingtip_R"),
            Scatterer(offset_body_m=(0.0, -14.0, 0.0), rcs_dbsm=12.0, label="wingtip_L"),
            Scatterer(offset_body_m=(2.0, 7.0, 1.0), rcs_dbsm=9.0, label="engine_R"),
            Scatterer(offset_body_m=(2.0, -7.0, 1.0), rcs_dbsm=9.0, label="engine_L"),
            Scatterer(offset_body_m=(-5.0, 0.0, 2.0), rcs_dbsm=7.0, label="vstab"),
            Scatterer(offset_body_m=(5.0, 0.0, -1.0), rcs_dbsm=6.0, label="belly"),
            Scatterer(offset_body_m=(8.0, 0.0, 1.5), rcs_dbsm=8.0, label="cockpit"),
        ),
    )


def _glint_sweep(
    target: ExtendedTarget,
    freq_low_hz: float,
    freq_high_hz: float,
    *,
    seed: int = _RNG_SEED,
    n_samples: int = _N_SAMPLES,
) -> np.ndarray:
    """Run a yaw/pitch/roll/frequency Monte Carlo and return (N, 3) glints."""
    rng = np.random.default_rng(seed=seed)
    glints: list[tuple[float, float, float]] = []
    for _ in range(n_samples):
        yaw = float(rng.uniform(-math.pi, math.pi))
        pitch = float(rng.uniform(-math.pi / 6, math.pi / 6))
        roll = float(rng.uniform(-math.pi / 6, math.pi / 6))
        freq = float(rng.uniform(freq_low_hz, freq_high_hz))
        result = compute_extended_target_return(
            radar_position_enu_m=(0.0, 0.0, 0.0),
            target=target,
            target_position_enu_m=(0.0, 30_000.0, 5000.0),
            target_attitude_rad=(yaw, pitch, roll),
            frequency_hz=freq,
        )
        glints.append(result.glint_offset_m)
    return np.asarray(glints, dtype=np.float64)


def _bounding_span_m(target: ExtendedTarget) -> float:
    """Body-frame max-extent in any single axis — proxy for L in the
    Skolnik rule. Picks the largest span across (x, y, z) to be
    conservative on the upper bound check."""
    offsets = np.asarray([s.offset_body_m for s in target.scatterers], dtype=np.float64)
    spans = offsets.max(axis=0) - offsets.min(axis=0)
    return float(spans.max())


# ---------------------------------------------------------------------
# Rule-of-thumb upper bound across multiple targets
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("target_factory", "n_scatterers"),
    [
        (_drone_3pt, 3),
        (_fighter_5pt, 5),
        (_transport_9pt, 9),
    ],
)
def test_per_axis_glint_std_under_skolnik_bound(
    target_factory: object,
    n_scatterers: int,
) -> None:
    """Each axis std must stay below L / (2*sqrt(N)) for all three
    (N, L) regimes — the rule-of-thumb is a soft upper bound.
    """
    target = target_factory()  # type: ignore[operator]
    glints = _glint_sweep(target, 9.0e9, 10.0e9)
    per_axis_std = glints.std(axis=0)
    sigma_rule = _bounding_span_m(target) / (2.0 * math.sqrt(n_scatterers))
    for axis in range(3):
        assert float(per_axis_std[axis]) < sigma_rule, (
            f"axis {axis} std {per_axis_std[axis]} exceeds rule {sigma_rule} for {target.target_id}"
        )


@pytest.mark.parametrize(
    "target_factory",
    [_drone_3pt, _fighter_5pt, _transport_9pt],
)
def test_glint_norm_within_convex_hull(target_factory: object) -> None:
    """|glint| <= L (max single-axis body span). Holds independently of
    N — pure convex-combination consequence of amplitude weighting.
    """
    target = target_factory()  # type: ignore[operator]
    glints = _glint_sweep(target, 9.0e9, 10.0e9)
    norms = np.linalg.norm(glints, axis=1)
    assert float(norms.max()) < _bounding_span_m(target)


# ---------------------------------------------------------------------
# Directional invariant: bigger L -> bigger glint (same N attempted)
# ---------------------------------------------------------------------


def test_larger_span_produces_larger_glint_std() -> None:
    """L_transport (30 m) >> L_fighter (12 m). The transport cloud has
    more scatterers (N=9 vs 5) which damps sigma_glint by sqrt(N/5)
    only ~1.34x, while L grows 2.5x. Net per-axis std must increase.
    """
    g_fighter = _glint_sweep(_fighter_5pt(), 9.0e9, 10.0e9)
    g_transport = _glint_sweep(_transport_9pt(), 9.0e9, 10.0e9)
    # Use mean of per-axis std as a scalar summary.
    std_fighter = float(g_fighter.std(axis=0).mean())
    std_transport = float(g_transport.std(axis=0).mean())
    assert std_transport > std_fighter


def test_smaller_span_produces_smaller_glint_std() -> None:
    """L_drone (2 m) << L_fighter (12 m). Even though the drone has
    fewer scatterers (N=3 vs 5, modestly easier to glint), L is 6x
    smaller — net std must drop.
    """
    g_drone = _glint_sweep(_drone_3pt(), 9.0e9, 10.0e9)
    g_fighter = _glint_sweep(_fighter_5pt(), 9.0e9, 10.0e9)
    std_drone = float(g_drone.std(axis=0).mean())
    std_fighter = float(g_fighter.std(axis=0).mean())
    assert std_drone < std_fighter


# ---------------------------------------------------------------------
# Frequency-band invariants — std envelope is band-independent
# ---------------------------------------------------------------------


def test_glint_norm_bounded_across_s_band() -> None:
    """S-band 3 GHz - 3.5 GHz sweep — |glint| stays inside the body
    bounding span. Long wavelength regime smooths some interference
    structure but the convex-hull invariant holds.
    """
    target = _fighter_5pt()
    glints = _glint_sweep(target, 3.0e9, 3.5e9, seed=2024)
    assert float(np.linalg.norm(glints, axis=1).max()) < _bounding_span_m(target)


def test_glint_norm_bounded_across_ku_band() -> None:
    """Ku-band 15 - 18 GHz sweep — short wavelength gives much more
    rapid phase rotation; same convex-hull bound still holds.
    """
    target = _fighter_5pt()
    glints = _glint_sweep(target, 15.0e9, 18.0e9, seed=2025)
    assert float(np.linalg.norm(glints, axis=1).max()) < _bounding_span_m(target)


# ---------------------------------------------------------------------
# Determinism across the wider envelope
# ---------------------------------------------------------------------


def test_multi_regime_sweep_is_deterministic() -> None:
    """All three regimes + Ku band must reproduce bit-for-bit on
    repeated runs with identical seeds.
    """
    for factory, seed in (
        (_drone_3pt, 7),
        (_fighter_5pt, 11),
        (_transport_9pt, 13),
    ):
        target = factory()
        a = _glint_sweep(target, 15.0e9, 18.0e9, seed=seed, n_samples=32)
        b = _glint_sweep(target, 15.0e9, 18.0e9, seed=seed, n_samples=32)
        np.testing.assert_array_equal(a, b)
