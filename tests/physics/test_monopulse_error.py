"""Monopulse error regression (Phase 5.6).

Plan/08 § 8.5a.4: ``error_axis = slope_axis * Re(delta_axis / sigma)``.
"""

from __future__ import annotations

import math

import pytest

from workbench.physics.monopulse import monopulse_error_from_channels

_RTOL = 1e-12


def test_pure_real_channels_recover_slope_times_ratio() -> None:
    err = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.1, 0.0),
        delta_el=complex(0.05, 0.0),
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == pytest.approx(1.4 * 0.1, rel=_RTOL)
    assert err.error_el_rad == pytest.approx(1.4 * 0.05, rel=_RTOL)
    assert err.sum_amplitude == pytest.approx(1.0, rel=_RTOL)


def test_purely_imaginary_delta_yields_zero_error() -> None:
    """Re(j x / 1) = 0 - amplitude-comparison monopulse ignores quadrature."""
    err = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.0, 0.1),
        delta_el=complex(0.0, 0.1),
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_az_rad == pytest.approx(0.0, abs=1e-14)
    assert err.error_el_rad == pytest.approx(0.0, abs=1e-14)


def test_sigma_phase_does_not_change_real_ratio_magnitude() -> None:
    """Rotating sigma + delta by the same phase preserves Re(delta/sigma)."""
    phase = math.radians(37.0)
    rot = complex(math.cos(phase), math.sin(phase))
    base_err = monopulse_error_from_channels(
        sigma=complex(2.0, 0.0),
        delta_az=complex(0.2, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    rot_err = monopulse_error_from_channels(
        sigma=complex(2.0, 0.0) * rot,
        delta_az=complex(0.2, 0.0) * rot,
        delta_el=complex(0.0, 0.0) * rot,
        slope_az=1.0,
        slope_el=1.0,
    )
    assert rot_err.error_az_rad == pytest.approx(base_err.error_az_rad, rel=_RTOL)


def test_doubling_slope_doubles_error() -> None:
    base = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.07, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    doubled = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.07, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=2.0,
        slope_el=1.0,
    )
    assert doubled.error_az_rad == pytest.approx(2.0 * base.error_az_rad, rel=_RTOL)


@pytest.mark.parametrize("bad_slope", [0.0, -0.1, -1.4])
def test_non_positive_slope_az_rejected(bad_slope: float) -> None:
    with pytest.raises(ValueError, match=r"slope_az"):
        monopulse_error_from_channels(
            sigma=complex(1.0, 0.0),
            delta_az=complex(0.0, 0.0),
            delta_el=complex(0.0, 0.0),
            slope_az=bad_slope,
            slope_el=1.0,
        )


def test_zero_sigma_rejected() -> None:
    with pytest.raises(ValueError, match=r"sigma channel"):
        monopulse_error_from_channels(
            sigma=complex(0.0, 0.0),
            delta_az=complex(0.0, 0.0),
            delta_el=complex(0.0, 0.0),
            slope_az=1.0,
            slope_el=1.0,
        )


def test_sum_amplitude_equals_abs_sigma() -> None:
    sigma = complex(3.0, 4.0)  # |sigma| = 5
    err = monopulse_error_from_channels(
        sigma=sigma,
        delta_az=complex(0.0, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    assert err.sum_amplitude == pytest.approx(5.0, rel=_RTOL)


# ---------- 5.6b — axis separation + sign + sigma scaling ----------


def test_delta_el_zero_keeps_error_el_zero_regardless_of_delta_az() -> None:
    """Axis decoupling: a non-zero delta_az with zero delta_el must
    leave error_el untouched (= 0). The two axes are independent in
    the amplitude-comparison monopulse closed form.
    """
    err = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.3, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.4,
        slope_el=1.4,
    )
    assert err.error_el_rad == 0.0
    assert err.error_az_rad == pytest.approx(1.4 * 0.3, rel=_RTOL)


def test_error_az_antisymmetric_in_delta_az_sign() -> None:
    """error_az is linear in delta_az -> flipping the sign of the
    delta_az channel flips the sign of the angle error exactly.
    """
    base = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.12, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    flipped = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(-0.12, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    assert flipped.error_az_rad == pytest.approx(-base.error_az_rad, rel=_RTOL)


def test_error_linear_in_delta_magnitude() -> None:
    """Doubling |delta_az| doubles the angle error (matching the
    doubling-slope invariant, but on the delta axis instead).
    """
    base = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.05, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.4,
        slope_el=1.4,
    )
    doubled = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.10, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.4,
        slope_el=1.4,
    )
    assert doubled.error_az_rad == pytest.approx(2.0 * base.error_az_rad, rel=_RTOL)


def test_error_inversely_proportional_to_sigma_magnitude() -> None:
    """error_axis = slope * Re(delta / sigma) -> doubling |sigma|
    halves the error at fixed delta. Locks the denominator scaling.
    """
    base = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.20, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    doubled_sigma = monopulse_error_from_channels(
        sigma=complex(2.0, 0.0),
        delta_az=complex(0.20, 0.0),
        delta_el=complex(0.0, 0.0),
        slope_az=1.0,
        slope_el=1.0,
    )
    assert doubled_sigma.error_az_rad == pytest.approx(base.error_az_rad / 2.0, rel=_RTOL)


def test_slope_az_change_does_not_affect_error_el() -> None:
    """The two slopes scale their own axis only. Bumping slope_az
    must leave error_el untouched at fixed delta_el (independent
    knobs in the closed form).
    """
    base = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.05, 0.0),
        delta_el=complex(0.07, 0.0),
        slope_az=1.0,
        slope_el=1.2,
    )
    bumped = monopulse_error_from_channels(
        sigma=complex(1.0, 0.0),
        delta_az=complex(0.05, 0.0),
        delta_el=complex(0.07, 0.0),
        slope_az=3.5,  # bumped from 1.0
        slope_el=1.2,
    )
    assert bumped.error_el_rad == pytest.approx(base.error_el_rad, rel=_RTOL)
