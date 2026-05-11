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
