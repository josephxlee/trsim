"""Two-ray multipath + refractive horizon golden regression (Phase 5.19 + 5.20).

The existing physics suite (`tests/physics/test_two_ray_multipath.py`,
`tests/physics/test_horizon.py`) already covers structural invariants
of these modules. This file adds a GoldenDataset reference layer:
bit-for-bit (rtol=1e-12) regression against pre-computed values stored
in ``tests/physics/golden/multipath_horizon.json``.

Categories verified (plan/14 § 14.5 + plan/16 § 16.3 + Skolnik /
Mahafza closed-form):

- two-ray phase / path difference at X-band geometry;
- one-way (F^2) and round-trip (F^4) power factors for free space,
  flat-sea (rho=-0.95), and perfect conductor (rho=-1);
- last-null / first-peak lobing landmarks (Skolnik ch.2);
- effective earth radius at the standard 4/3 refraction factor;
- single-point geometric horizon distance (k=1);
- two-point radio horizon at the 4/3 factor.
"""

from __future__ import annotations

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
    earth_bulge_m,
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
# Phase 5.19+ : Multi-band two-ray power factors (case B + C)
# ---------------------------------------------------------------------


def _case_b_sband() -> dict[str, float]:
    sample = _DATASET.case("two_ray_h1_10_h2_200_R_20km_sband")
    return {
        "h1_m": float(sample.inputs["h1_m"]),
        "h2_m": float(sample.inputs["h2_m"]),
        "ground_distance_m": float(sample.inputs["ground_distance_m"]),
        "frequency_hz": float(sample.inputs["frequency_hz"]),
        **{k: float(v) for k, v in sample.expected.items()},
    }


def _case_c_kuband() -> dict[str, float]:
    sample = _DATASET.case("two_ray_h1_15_h2_80_R_15km_kuband")
    return {
        "h1_m": float(sample.inputs["h1_m"]),
        "h2_m": float(sample.inputs["h2_m"]),
        "ground_distance_m": float(sample.inputs["ground_distance_m"]),
        "frequency_hz": float(sample.inputs["frequency_hz"]),
        **{k: float(v) for k, v in sample.expected.items()},
    }


def test_path_difference_sband_matches_golden() -> None:
    """S-band 3 GHz geometry — path difference is a wavelength-independent
    function of geometry (closed-form ``sqrt(d^2 + (h1+h2)^2) -
    sqrt(d^2 + (h2-h1)^2)``)."""
    c = _case_b_sband()
    delta = two_ray_path_difference_m(c["h1_m"], c["h2_m"], c["ground_distance_m"])
    assert delta == pytest.approx(c["delta_m"], rel=_RTOL)


def test_phase_difference_sband_matches_golden() -> None:
    """S-band phi = 2*pi*delta/lambda; longer lambda (3 GHz vs X-band)
    shrinks phi for the same geometry."""
    c = _case_b_sband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    phi = two_ray_phase_difference_rad(c["h1_m"], c["h2_m"], c["ground_distance_m"], lam)
    assert phi == pytest.approx(c["phi_rad"], rel=_RTOL)


def test_power_factor_sband_perfect_conductor_matches_golden() -> None:
    """S-band F^2 near a null — the 4.4 rad phase puts cos(phi) very
    close to +1 so 1 + rho^2 + 2*rho*cos(phi) collapses for rho=-1."""
    c = _case_b_sband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f2 == pytest.approx(c["F2_pec"], rel=_RTOL)


def test_power_factor_sband_flat_sea_matches_golden() -> None:
    """S-band sea-bounce F^2 — non-ideal rho=-0.95 lifts the deep null
    by an order of magnitude versus PEC."""
    c = _case_b_sband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_FLAT_SEA_SMOOTH
    )
    assert f2 == pytest.approx(c["F2_sea"], rel=_RTOL)


def test_round_trip_factor_sband_perfect_conductor_matches_golden() -> None:
    """S-band F^4 — deep-null geometry pushes round-trip multipath
    factor below 1e-8 (the classic two-way nulling)."""
    c = _case_b_sband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f4 == pytest.approx(c["F4_pec"], rel=_RTOL)


def test_round_trip_factor_sband_flat_sea_matches_golden() -> None:
    """S-band F^4 with realistic sea rho=-0.95 — null is much shallower
    than PEC but still ~5 orders of magnitude below free space."""
    c = _case_b_sband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_FLAT_SEA_SMOOTH
    )
    assert f4 == pytest.approx(c["F4_sea"], rel=_RTOL)


def test_path_difference_kuband_matches_golden() -> None:
    """Ku-band 16 GHz geometry — same closed-form delta independent of
    frequency."""
    c = _case_c_kuband()
    delta = two_ray_path_difference_m(c["h1_m"], c["h2_m"], c["ground_distance_m"])
    assert delta == pytest.approx(c["delta_m"], rel=_RTOL)


def test_power_factor_kuband_perfect_conductor_matches_golden() -> None:
    """Ku-band F^2 near a peak — short wavelength puts phi at an odd
    multiple of pi, driving 1 + rho^2 + 2*rho*cos(phi) close to 4."""
    c = _case_c_kuband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f2 = two_ray_power_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f2 == pytest.approx(c["F2_pec"], rel=_RTOL)


def test_round_trip_factor_kuband_perfect_conductor_matches_golden() -> None:
    """Ku-band F^4 ~16 — the peak gives the +12 dB round-trip
    enhancement above the radar equation free-space level."""
    c = _case_c_kuband()
    lam = _C_LIGHT_M_S / c["frequency_hz"]
    f4 = two_ray_round_trip_factor(
        c["h1_m"], c["h2_m"], c["ground_distance_m"], lam, RHO_PERFECT_CONDUCTOR
    )
    assert f4 == pytest.approx(c["F4_pec"], rel=_RTOL)


def test_delta_is_frequency_invariant_across_bands() -> None:
    """Two-ray path difference depends only on geometry — same geometry
    at S/X/Ku must yield bit-for-bit identical delta. (Sanity-lock
    that the goldens themselves don't drift across bands.)
    """
    # X-band geometry (case A) vs same-geometry sweep across bands.
    h1, h2, d = 25.0, 50.0, 10_000.0
    delta_x = two_ray_path_difference_m(h1, h2, d)
    delta_s = two_ray_path_difference_m(h1, h2, d)
    delta_ku = two_ray_path_difference_m(h1, h2, d)
    assert delta_x == delta_s == delta_ku


def test_lobing_peak_distance_scales_inversely_with_lambda() -> None:
    """d_peak_0 = 4*h1*h2/lambda — doubling the frequency (halving
    lambda) doubles the far-field peak distance. Closed-form invariant
    tested across two bands using the existing 5.20 fixture geometry.
    """
    h1, h2 = 10.0, 100.0
    lam_x = _C_LIGHT_M_S / 9.4e9
    lam_ku = _C_LIGHT_M_S / 18.8e9
    peak_x = first_lobing_peak_distance_m(h1, h2, lam_x)
    peak_ku = first_lobing_peak_distance_m(h1, h2, lam_ku)
    # Ku is exactly 2x X frequency -> Ku peak is at 2x X peak distance.
    assert peak_ku == pytest.approx(2.0 * peak_x, rel=_RTOL)


# ---------------------------------------------------------------------
# Phase 5.20+ : Multi-refraction-factor horizon (cases D / E / F / G)
# ---------------------------------------------------------------------


def test_geometric_horizon_h_1000m_matches_golden() -> None:
    """k=1 (no refraction) horizon at h=1000m — 112.88 km. Scales as
    sqrt(h) so 10x height -> sqrt(10) ~ 3.16x distance.
    """
    sample = _DATASET.case("horizon_geometric_h_1000m")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_horizon_height_scales_as_sqrt() -> None:
    """horizon(100*h) / horizon(h) = sqrt(100) = 10 exactly (k cancels).
    Closed-form invariant from sqrt(2 k R_E h).
    """
    h_low = horizon_distance_m(10.0)
    h_high = horizon_distance_m(1000.0)
    assert h_high / h_low == pytest.approx(10.0, rel=_RTOL)


def test_sub_refraction_horizon_h_100m_matches_golden() -> None:
    """Sub-refraction (k=2/3) — colder than ISA, rays bend up. Effective
    Earth shrinks, horizon shortens to 29.15 km (vs 41.2 km at k=4/3).
    """
    sample = _DATASET.case("horizon_sub_refraction_k_2_3_h_100m")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_sub_refraction_effective_earth_matches_golden() -> None:
    sample = _DATASET.case("horizon_sub_refraction_k_2_3_h_100m")
    got = effective_earth_radius_m(float(sample.inputs["k_factor"]))
    assert got == pytest.approx(float(sample.expected["Re_eff_m"]), rel=_RTOL)


def test_super_refraction_horizon_h_100m_matches_golden() -> None:
    """Super-refraction / ducting limit (k=2). Effective Earth doubles,
    horizon extends to 50.5 km."""
    sample = _DATASET.case("horizon_super_refraction_k_2_h_100m")
    got = horizon_distance_m(
        float(sample.inputs["height_m"]), k_factor=float(sample.inputs["k_factor"])
    )
    assert got == pytest.approx(float(sample.expected["horizon_m"]), rel=_RTOL)


def test_super_refraction_effective_earth_matches_golden() -> None:
    sample = _DATASET.case("horizon_super_refraction_k_2_h_100m")
    got = effective_earth_radius_m(float(sample.inputs["k_factor"]))
    assert got == pytest.approx(float(sample.expected["Re_eff_m"]), rel=_RTOL)


def test_horizon_is_strictly_monotonic_in_k_factor() -> None:
    """Larger k -> larger effective Earth -> longer horizon. Monotonic
    invariant across realistic atmosphere regimes (sub -> std -> super).
    """
    h = 100.0
    d_sub = horizon_distance_m(h, k_factor=2.0 / 3.0)
    d_std = horizon_distance_m(h, k_factor=4.0 / 3.0)
    d_super = horizon_distance_m(h, k_factor=2.0)
    assert d_sub < d_std < d_super


def test_radio_horizon_sub_refraction_matches_golden() -> None:
    """Two-point radio horizon at k=2/3 — same h1/h2 as case A but
    sub-refractive atmosphere collapses LOS from 42.2 km to 29.8 km."""
    sample = _DATASET.case("horizon_radio_two_point_sub_refraction_10_50_k_2_3")
    got = radio_horizon_distance_m(
        float(sample.inputs["h1_m"]),
        float(sample.inputs["h2_m"]),
        k_factor=float(sample.inputs["k_factor"]),
    )
    assert got == pytest.approx(float(sample.expected["d_radio_m"]), rel=_RTOL)


# ---------------------------------------------------------------------
# Phase 5.20+ : Earth bulge midpoint (case G)
# ---------------------------------------------------------------------


def test_earth_bulge_midpoint_50km_matches_golden() -> None:
    """50 km segment midpoint, k=4/3 -> 36.79 m bulge. From the closed
    form ``h_bulge(midpoint) = d_total^2 / (8 k R_E)``."""
    sample = _DATASET.case("earth_bulge_midpoint_50km_k_4_3")
    got = earth_bulge_m(
        float(sample.inputs["distance_from_a_m"]),
        float(sample.inputs["distance_from_b_m"]),
        k_factor=float(sample.inputs["k_factor"]),
    )
    assert got == pytest.approx(float(sample.expected["bulge_m"]), rel=_RTOL)


def test_earth_bulge_max_at_midpoint_closed_form() -> None:
    """For a chord of length D split at midpoint x=D/2:

        h_max = (D/2)^2 / (2 k R_E) = D^2 / (8 k R_E).

    Sanity check via the formula form expected by Skolnik Ch.2.
    """
    sample = _DATASET.case("earth_bulge_midpoint_50km_k_4_3")
    d_total = float(sample.inputs["distance_from_a_m"]) + float(sample.inputs["distance_from_b_m"])
    from workbench.physics.propagation.ray_tracing import R_EARTH_MEAN_M

    closed = (d_total * d_total) / (8.0 * float(sample.inputs["k_factor"]) * R_EARTH_MEAN_M)
    assert closed == pytest.approx(float(sample.expected["bulge_m"]), rel=_RTOL)
