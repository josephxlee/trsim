"""Track / Detection / status dataclasses (plan/03 § 3.2.1k).

Phase 2.8 — minimum viable track + measurement record consumed by the
EKF / UKF filters and GNN data associator.

State convention (constant-velocity 3D):

- ``mean`` is a 6-vector ``[e_m, n_m, u_m, vE_mps, vN_mps, vU_mps]``
  in Map ENU.
- ``covariance`` is a ``6 x 6`` symmetric positive-definite matrix.

Measurement convention (spherical from radar):

- ``range_m`` along the radar line of sight.
- ``az_rad`` clockwise from North (matches project heading convention,
  plan/12 § 12.4).
- ``el_rad`` above horizon (positive nose-up).
- ``doppler_mps`` is the line-of-sight rate; positive = receding.
  Optional — set to NaN when the radar can't measure Doppler.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

import numpy as np
from numpy.typing import NDArray

STATE_DIM: int = 6
"""Constant-velocity ENU state dimension. Used for cov shape checks."""

MEASUREMENT_DIM: int = 3
"""(range, az, el) measurement dimension."""


class TrackStatus(Enum):
    """Lifecycle stage of a track (plan/03 § 3.2.1k)."""

    TENTATIVE = "tentative"
    """Newly initiated — not yet confirmed by ``M`` of ``N`` updates."""

    CONFIRMED = "confirmed"
    """Actively maintained with recent updates."""

    COASTING = "coasting"
    """No association last frame; predictions only, awaiting update."""

    LOST = "lost"
    """Removed from active set after too many coasting frames."""


@dataclass(frozen=True, slots=True)
class Detection:
    """Single radar measurement at one frame.

    Attributes:
        range_m: Slant range to the target [m]. Must be > 0.
        az_rad: Azimuth (CW from North) [rad].
        el_rad: Elevation above horizon [rad].
        doppler_mps: Line-of-sight rate [m/s], positive = receding.
            NaN if the radar didn't measure Doppler this frame.
        sim_t_s: Simulation time [s]. Must be >= 0.
        snr_db: Optional SNR for diagnostics. NaN when not available.

    Raises:
        ValueError: If range_m <= 0 or sim_t_s < 0.
    """

    range_m: float
    az_rad: float
    el_rad: float
    sim_t_s: float
    doppler_mps: float = float("nan")
    snr_db: float = float("nan")

    def __post_init__(self) -> None:
        if self.range_m <= 0.0:
            msg = f"range_m must be > 0, got {self.range_m}"
            raise ValueError(msg)
        if self.sim_t_s < 0.0:
            msg = f"sim_t_s must be >= 0, got {self.sim_t_s}"
            raise ValueError(msg)

    def to_enu(self) -> tuple[float, float, float]:
        """Return ``(east, north, up)`` Cartesian position [m].

        Reverse of the spherical measurement function used by EKF/UKF:
        ``e = R * sin(az) * cos(el)``,
        ``n = R * cos(az) * cos(el)``,
        ``u = R * sin(el)``.
        """
        ce = math.cos(self.el_rad)
        return (
            self.range_m * math.sin(self.az_rad) * ce,
            self.range_m * math.cos(self.az_rad) * ce,
            self.range_m * math.sin(self.el_rad),
        )


@dataclass(frozen=True, slots=True)
class TrackState:
    """Active track state (plan/03 § 3.2.1k).

    Attributes:
        track_id: Stable integer identifier within the run.
        mean: Length-6 ENU constant-velocity state ``[e, n, u, vE, vN, vU]``.
        covariance: ``6 x 6`` covariance matrix. Must be symmetric and
            positive-definite (we check shape only — PD is the
            filter's job).
        sim_t_s: Simulation time at which the state was sampled [s].
        status: Lifecycle stage.
        consecutive_misses: Frames since last successful update. Used
            by the lifecycle policy to escalate COASTING -> LOST.

    Raises:
        ValueError: If shapes are wrong, ``track_id < 0``, or
            ``consecutive_misses < 0``.
    """

    track_id: int
    mean: NDArray[np.float64]
    covariance: NDArray[np.float64]
    sim_t_s: float
    status: TrackStatus = TrackStatus.TENTATIVE
    consecutive_misses: int = 0

    def __post_init__(self) -> None:
        if self.track_id < 0:
            msg = f"track_id must be >= 0, got {self.track_id}"
            raise ValueError(msg)
        if self.mean.shape != (STATE_DIM,):
            msg = f"mean must be shape ({STATE_DIM},), got {self.mean.shape}"
            raise ValueError(msg)
        if self.covariance.shape != (STATE_DIM, STATE_DIM):
            msg = (
                f"covariance must be shape ({STATE_DIM}, {STATE_DIM}), got {self.covariance.shape}"
            )
            raise ValueError(msg)
        if self.consecutive_misses < 0:
            msg = f"consecutive_misses must be >= 0, got {self.consecutive_misses}"
            raise ValueError(msg)

    @property
    def position_enu_m(self) -> tuple[float, float, float]:
        """Position 3-tuple ``(east, north, up)`` [m]."""
        return (float(self.mean[0]), float(self.mean[1]), float(self.mean[2]))

    @property
    def velocity_enu_mps(self) -> tuple[float, float, float]:
        """Velocity 3-tuple ``(vE, vN, vU)`` [m/s]."""
        return (float(self.mean[3]), float(self.mean[4]), float(self.mean[5]))
