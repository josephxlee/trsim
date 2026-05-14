"""Mock primary-target snapshot generator (Phase 4 L6).

Drives :class:`workbench.ui.simulator.panels.ScopePOVPanel` and
:class:`workbench.ui.simulator.panels.PropertiesPanel` with a
deterministic per-sim-time view of the "primary target": its
spherical coordinates relative to the radar, the radar's commanded
vs actual azimuth (with a small servo lag), and a few summary
properties (RCS, speed, lock status). Real
``Pipeline`` + ``Tracker`` binding lands later.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MockPrimaryTargetSnapshot:
    """One per-tick snapshot of the primary target.

    Attributes:
        sim_t_s: Simulation time the snapshot was generated at [s].
        range_m: Slant range from radar to target [m], >= 0.
        azimuth_deg: True target azimuth from radar [deg], -180..180.
        elevation_deg: True target elevation from radar [deg], -90..90.
        rcs_dbsm: Mock radar cross-section [dBsm].
        speed_mps: Tangential speed of the target along its orbit [m/s].
        commanded_az_deg: Latest commanded antenna azimuth [deg].
        actual_az_deg: Achieved antenna azimuth (commanded + servo lag) [deg].
        cross_hair_norm: ``(x, y)`` offset of the target inside the
            radar's scope window, both in ``[-1, 1]`` (0 = boresight).
        is_locked: Whether the tracker says the primary target is locked.
    """

    sim_t_s: float
    range_m: float
    azimuth_deg: float
    elevation_deg: float
    rcs_dbsm: float
    speed_mps: float
    commanded_az_deg: float
    actual_az_deg: float
    cross_hair_norm: tuple[float, float]
    is_locked: bool


class MockPrimaryTargetGenerator:
    """Deterministic per-tick primary-target snapshot.

    Models a target on a horizontal circular orbit at fixed altitude
    (the same family as :class:`MockSceneGenerator`). The radar's
    commanded azimuth tracks the target perfectly while the actual
    azimuth has a small constant servo lag so the
    :class:`ScopePOVPanel` shows a non-zero AZ lag in production.

    Args:
        orbit_radius_m: Horizontal orbit radius from the radar [m], > 0.
        orbit_period_s: Orbit period [s], > 0.
        target_altitude_m: Constant altitude of the target [m], can be
            negative (below radar).
        rcs_dbsm: Constant RCS reported on every tick [dBsm].
        servo_lag_deg: Small constant azimuth lag of the actual
            antenna behind the commanded heading [deg].
        scope_window_deg: Half-span of the Scope POV window in azimuth/
            elevation [deg], > 0. Targets outside the window clamp to
            the edge of the cross-hair display.
        lock_after_s: Time after which the tracker reports the target
            as locked [s], >= 0.

    Raises:
        ValueError: On any out-of-range constructor argument.
    """

    def __init__(
        self,
        *,
        orbit_radius_m: float = 4_000.0,
        orbit_period_s: float = 30.0,
        target_altitude_m: float = 500.0,
        rcs_dbsm: float = 5.0,
        servo_lag_deg: float = 0.35,
        scope_window_deg: float = 10.0,
        lock_after_s: float = 0.5,
    ) -> None:
        if orbit_radius_m <= 0.0:
            msg = f"orbit_radius_m must be > 0, got {orbit_radius_m}"
            raise ValueError(msg)
        if orbit_period_s <= 0.0:
            msg = f"orbit_period_s must be > 0, got {orbit_period_s}"
            raise ValueError(msg)
        if scope_window_deg <= 0.0:
            msg = f"scope_window_deg must be > 0, got {scope_window_deg}"
            raise ValueError(msg)
        if lock_after_s < 0.0:
            msg = f"lock_after_s must be >= 0, got {lock_after_s}"
            raise ValueError(msg)
        self._orbit_radius_m = orbit_radius_m
        self._orbit_period_s = orbit_period_s
        self._target_altitude_m = target_altitude_m
        self._rcs_dbsm = rcs_dbsm
        self._servo_lag_deg = servo_lag_deg
        self._scope_window_deg = scope_window_deg
        self._lock_after_s = lock_after_s
        # Tangential speed = 2*pi*R / T, constant for a circular orbit.
        self._speed_mps = (2.0 * math.pi * orbit_radius_m) / orbit_period_s

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def snapshot_for(self, sim_t_s: float) -> MockPrimaryTargetSnapshot:
        """Return the primary-target snapshot at ``sim_t_s``."""
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        phase = 2.0 * math.pi * sim_t_s / self._orbit_period_s
        east = self._orbit_radius_m * math.cos(phase)
        north = self._orbit_radius_m * math.sin(phase)
        up = self._target_altitude_m
        slant = math.sqrt(east * east + north * north + up * up)
        az_deg = math.degrees(math.atan2(east, north))
        el_deg = math.degrees(math.asin(up / slant)) if slant > 0.0 else 0.0
        cmd_az = az_deg
        actual_az = az_deg - self._servo_lag_deg
        # Cross-hair offset: az_lag / scope_window mapped to [-1, 1] (X)
        # and an artificial vertical bob via elevation tracking. Saturate
        # at the edges.
        x_offset = self._servo_lag_deg / self._scope_window_deg
        y_offset = 0.5 * math.sin(phase)  # mild vertical oscillation
        cross_hair = (
            max(-1.0, min(1.0, x_offset)),
            max(-1.0, min(1.0, y_offset)),
        )
        return MockPrimaryTargetSnapshot(
            sim_t_s=sim_t_s,
            range_m=slant,
            azimuth_deg=az_deg,
            elevation_deg=el_deg,
            rcs_dbsm=self._rcs_dbsm,
            speed_mps=self._speed_mps,
            commanded_az_deg=cmd_az,
            actual_az_deg=actual_az,
            cross_hair_norm=cross_hair,
            is_locked=sim_t_s >= self._lock_after_s,
        )

    @property
    def servo_lag_deg(self) -> float:
        return self._servo_lag_deg

    @property
    def scope_window_deg(self) -> float:
        return self._scope_window_deg
