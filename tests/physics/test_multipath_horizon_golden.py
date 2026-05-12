"""Two-ray multipath + refractive horizon golden regression (Phase 5.19 + 5.20 + 5.19c/5.20c).

The existing physics suite (`tests/physics/test_two_ray_multipath.py`,
`tests/physics/test_horizon.py`) already covers structural invariants
of these modules. This file adds a GoldenDataset reference layer:
bit-for-bit (rtol=1e-12) regression against pre-computed values stored
in ``tests/physics/golden/multipath_horizon.json``.

Categories verified (plan/14 § 14.5 + plan/16 § 16.3 + Skolnik /
Mahafza closed-form):

5.19 / 5.20 (X-band + standard 4/3 refraction):
- two-ray phase / path difference at X-band geometry;
- one-way (F^2) and round-trip (F^4) power factors for free space,
  flat-sea (rho=-0.95), and perfect conductor (rho=-1);
- last-null / first-peak lobing landmarks (Skolnik ch.2);
- effective earth radius at the standard 4/3 refraction factor;
- single-point geometric horizon distance (k=1);
- two-point radio horizon at the 4/3 factor.

5.19c / 5.20c (multi-band + multi-refraction):
- S-band (3 GHz) at the same h1=25/h2=50/R=10km geometry — produces
  constructive interference (F^2 ~ 4) where X-band was destructive,
  pinning the frequency-dependent phase rotation.
- Ku-band (14 GHz) lobing landmarks at h1=10/h2=100 — shorter lambda
  pushes both landmarks past 90 km.
- k=1 baseline (no refraction) geometric horizon at h=100 m.
- k=1 baseline two-point radio horizon at h1=10/h2=50.
- k=1.5 super-refraction geometric horizon at h=10 m — sigma stretch
  beyond the standard 4/3 case.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Final

import pytest

from tests.physics.golden_dataset import GoldenDataset
from workbench.physics.propagation.multipath import (
    RHO_FLAT_SEA_SMOOTH,
    RHO_PERFECT_CONDUCTOR,
    first_lobing_peak_distance_m,
    last_lobing_null_distance_m,
    two_ray_phase_difference_rad,
    two_ray_power_factor,
    two_ray_round_trip_factor,
)
from workbench.physics.propagation.ray_tracing import (
    effective_earth_radius_m,
    horizon_distance_m,
    radio_horizon_distance_m,
    two_ray_path_difference_m,
)

_C_LIGHT_M_S: Final[float] = 299_792_458.0
_GOLDEN_PATH: Final[Path] = Path(__file__).parent / "golden" / "multipath_horizon.json"
_DATASET: Final[GoldenDataset] = GoldenDataset.load(_GOLDEN_PATH)
_RTOL: Final[float] = _DATASET.meta.rtol


# ---------------------------------------------------------------------
# Two-ray geometry + power factors (case A)
# ---------------------------------------------------------------------


def _case_a() -> dict[str, float]:
    sample = _DATASET.case("two_ray_h1_25_h2_50_R_10km_xband")
    return {
        "h1_m": float(sample.inputs["h1_m"]),
        "h2_m": float(sample.inputs["h2_m"]),
        "ground_distance_m": float(sample.inputs["ground_distance_m"]),
        "frequency_hz": float(sample.inputs["frequency_hz"]),
        **{k: float(v) for k, v in sample.expected.items()},
    }


def test_path_difference_matches_golden() -> None:
    c = _case_a()
    delta = two_ray_path_difference_m(c["h1_m"], c["h2_m"], c["ground_distance_m"])
    assert delta == pytest.approx(c["delta_m"], rel=_RTOL)


def test_phase_difference_matches_golden() -> None:
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    phi = two_ray_phase_difference_rad(c["h1_m"], c["h2_m"], c["ground_distance_m"], lam)
    assert phi == pytest.approx(c["phi_rad"], rel=_RTOL)


def test_power_factor_free_space_matches_golden() -> None:
    """rho = 0 -> F^2 = 1 exactly (free-space, no surface reflection)."""
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, 0.0)
    assert f2 == pytest.approx(c["F2_free"], rel=_RTOL)


def test_power_factor_perfect_conductor_matches_golden() -> None:
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f2 == pytest.approx(c["F2_pec"], rel=_RTOL)


def test_power_factor_flat_sea_matches_golden() -> None:
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_FLAT_SEA_SMOOTH
    )
    assert f2 == pytest.approx(c["F2_sea"], rel=_RTOL)


def test_round_trip_factor_perfect_conductor_matches_golden() -> None:
    """F^4 = (F^2)^2 — round-trip multipath factor for the radar equation."""
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f4 == pytest.approx(c["F4_pec"], rel=_RTOL)


def test_round_trip_factor_flat_sea_matches_golden() -> None:
    c = _case_a()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_FLAT_SEA_SMOOTH
    )
    assert f4 == pytest.approx(c["F4_sea"], rel=_RTOL)


# ---------------------------------------------------------------------
# Lobing landmarks (case B)
# ---------------------------------------------------------------------


def test_last_null_distance_matches_golden() -> None:
    sample = _DATASET.case("lobing_landmarks_h1_10_h2_100_xband")
    lam = _C_LIGHT_M_S / float(sample.inputs["frequency_hz"])
    got = last_lobing_null_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        lam,
    )
    assert got == pytest.approx(float(sample.expected["last_null_m"]), rel=_RTOL)


def test_first_peak_distance_matches_golden() -> None:
    sample = _DATASET.case("lobing_landmarks_h1_10_h2_100_xband")
    lam = _C_LIGHT_M_S / float(sample.inputs["frequency_hz"])
    got = first_lobing_peak_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        lam,
    )
    assert got == pytest.approx(float(sample.expected["first_peak_m"]), rel=_RTOL)


def test_first_peak_is_exactly_twice_last_null() -> None:
    """d_peak_0 = 4 h1 h2 / lambda = 2 * d_null_1 — closed-form ratio."""
    sample = _DATASET.case("lobing_landmarks_h1_10_h2_100_xband")
    lam = _C_LIGHT_M_S / float(sample.inputs["frequency_hz"])
    h1 = float(sample.inputs["h1_m"])
    h2 = float(sample.inputs["h2_m"])
    assert first_lobing_peak_distance_m(h1, h2, lam) == pytest.approx(
        2.0 * last_lobing_null_distance_m(h1, h2, lam), rel=_RTOL
    )


# ---------------------------------------------------------------------
# Horizon — refraction & geometry
# ---------------------------------------------------------------------


def test_effective_earth_radius_4_over_3_matches_golden() -> None:
    sample = _DATASET.case("horizon_effective_earth_4_over_3")
    got = effective_earth_radius_m(float(sample.inputs["k_factor"]))
    assert got == pytest.approx(float(sample.expected["Re_eff_m"]), rel=_RTOL)


def test_geometric_horizon_h_10m_matches_golden() -> None:
    sample = _DATASET.case("horizon_geometric_h_10m")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_radio_horizon_two_point_4_over_3_matches_golden() -> None:
    sample = _DATASET.case("horizon_radio_two_point_10_50_4over3")
    got = radio_horizon_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        k_factor=float(sample.inputs["k_factor"]),
    )
    assert got == pytest.approx(float(sample.expected["d_radio_m"]), rel=_RTOL)


def test_radio_horizon_is_sum_of_single_horizons() -> None:
    """radio_horizon_distance_m(h1, h2, k) = horizon_distance_m(h1, k)
    + horizon_distance_m(h2, k) — invariant from the definition.
    """
    h1, h2, k = 10.0, 50.0, 4.0 / 3.0
    total = radio_horizon_distance_m(h1, h2, k_factor=k)
    expected = horizon_distance_m(h1, k_factor=k) + horizon_distance_m(h2, k_factor=k)
    assert total == pytest.approx(expected, rel=_RTOL)


# ---------------------------------------------------------------------
# 5.19c — S-band two-ray (same geometry, different lambda)
# ---------------------------------------------------------------------


def _case_sband() -> dict[str, float]:
    sample = _DATASET.case("two_ray_h1_25_h2_50_R_10km_sband")
    return {
        "h1_m": float(sample.inputs["h1_m"]),
        "h2_m": float(sample.inputs["h2_m"]),
        "ground_distance_m": float(sample.inputs["ground_distance_m"]),
        "frequency_hz": float(sample.inputs["frequency_hz"]),
        **{k: float(v) for k, v in sample.expected.items()},
    }


def test_sband_path_difference_matches_xband_geometry() -> None:
    """Path difference depends only on geometry, not lambda — the
    S-band case must hit the same delta_m as the X-band case.
    """
    s = _case_sband()
    delta = two_ray_path_difference_m(s["h1_m"], s["h2_m"], s["ground_distance_m"])
    assert delta == pytest.approx(s["delta_m"], rel=_RTOL)


def test_sband_phase_difference_matches_golden() -> None:
    """Phase scales as 2 pi delta / lambda — at f=3 GHz the same delta
    produces a phi about 3x smaller (mod 2 pi) than X-band.
    """
    s = _case_sband()
    lam = _C_LIGHT_M_S / s["frequency_hz"]
    phi = two_ray_phase_difference_rad(s["h1_m"], s["h2_m"], s["ground_distance_m"], lam)
    assert phi == pytest.approx(s["phi_rad"], rel=_RTOL)


def test_sband_power_factor_perfect_conductor_is_constructive() -> None:
    """At S-band the same geometry sits near a constructive lobe peak —
    F^2 (PEC) approaches 4 (the maximum possible). Golden lock and
    sanity check (> 3.5).
    """
    s = _case_sband()
    lam = _C_LIGHT_M_S / s["frequency_hz"]
    f2 = two_ray_power_factor(
        s["h1_m"], s["h2_m"], s["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f2 == pytest.approx(s["F2_pec"], rel=_RTOL)
    assert f2 > 3.5


def test_sband_round_trip_factor_pec_matches_golden() -> None:
    s = _case_sband()
    lam = _C_LIGHT_M_S / s["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        s["h1_m"], s["h2_m"], s["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f4 == pytest.approx(s["F4_pec"], rel=_RTOL)


def test_sband_round_trip_factor_sea_matches_golden() -> None:
    s = _case_sband()
    lam = _C_LIGHT_M_S / s["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        s["h1_m"], s["h2_m"], s["ground_distance_m"], lam, RHO_FLAT_SEA_SMOOTH
    )
    assert f4 == pytest.approx(s["F4_sea"], rel=_RTOL)


# ---------------------------------------------------------------------
# 5.19c — Ku-band lobing landmarks (shorter lambda)
# ---------------------------------------------------------------------


def test_kuband_last_null_distance_matches_golden() -> None:
    sample = _DATASET.case("lobing_landmarks_h1_10_h2_100_kuband")
    lam = _C_LIGHT_M_S / float(sample.inputs["frequency_hz"])
    got = last_lobing_null_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        lam,
    )
    assert got == pytest.approx(float(sample.expected["last_null_m"]), rel=_RTOL)


def test_kuband_first_peak_distance_matches_golden() -> None:
    sample = _DATASET.case("lobing_landmarks_h1_10_h2_100_kuband")
    lam = _C_LIGHT_M_S / float(sample.inputs["frequency_hz"])
    got = first_lobing_peak_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        lam,
    )
    assert got == pytest.approx(float(sample.expected["first_peak_m"]), rel=_RTOL)


def test_lobing_landmarks_scale_inversely_with_lambda() -> None:
    """Both landmarks scale as 1/lambda. Ku-band (14 GHz, lambda ~ 0.0214 m)
    pushes them ~50% further than X-band (9.4 GHz, lambda ~ 0.0319 m).
    Ratio must equal f_ku / f_x to rtol 1e-12.
    """
    f_x = 9.4e9
    f_ku = 14.0e9
    lam_x = _C_LIGHT_M_S / f_x
    lam_ku = _C_LIGHT_M_S / f_ku
    peak_x = first_lobing_peak_distance_m(10.0, 100.0, lam_x)
    peak_ku = first_lobing_peak_distance_m(10.0, 100.0, lam_ku)
    assert peak_ku / peak_x == pytest.approx(f_ku / f_x, rel=_RTOL)


# ---------------------------------------------------------------------
# 5.20c — additional horizon cases (k=1 baseline + k=1.5 super-refraction)
# ---------------------------------------------------------------------


def test_geometric_horizon_h_100m_k_1_matches_golden() -> None:
    sample = _DATASET.case("horizon_geometric_h_100m_k_1")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_radio_horizon_two_point_k_1_matches_golden() -> None:
    """k=1 baseline (no refraction) — sanity-check the un-refracted
    sum-of-singles result against the golden."""
    sample = _DATASET.case("horizon_radio_two_point_10_50_k_1")
    got = radio_horizon_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        k_factor=float(sample.inputs["k_factor"]),
    )
    assert got == pytest.approx(float(sample.expected["d_radio_m"]), rel=_RTOL)


def test_geometric_horizon_super_refraction_k_1_5_matches_golden() -> None:
    """k=1.5 (super-refraction beyond the standard 4/3): horizon
    stretches by sqrt(1.5) ~ 1.225x over the geometric case at h=10 m.
    """
    sample = _DATASET.case("horizon_geometric_h_10m_k_1_5")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_horizon_scales_as_sqrt_k_at_fixed_height() -> None:
    """d ~ sqrt(2 k R_E h) -> d(k1) / d(k2) = sqrt(k1 / k2). Verify at
    h=10 m between k=1 and k=1.5.
    """
    d_1 = horizon_distance_m(10.0, k_factor=1.0)
    d_1_5 = horizon_distance_m(10.0, k_factor=1.5)
    assert d_1_5 / d_1 == pytest.approx(math.sqrt(1.5), rel=_RTOL)
