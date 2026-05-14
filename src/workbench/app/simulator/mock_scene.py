"""Mock 3D scene generator for the Simulator Scene3D panel.

Phase 4 L4 wires the Simulator's :class:`Scene3DPanel` to a
deterministic, sim-time-driven 3-D scene generator while the full
Phase 3 ``Pipeline`` remains unwired. The generator paints a tiny
synthetic world: one fixed radar position at the origin plus a
single target that traces a horizontal circular orbit at a fixed
altitude. The user sees a slow, predictable orbit so the camera
preset toolbar and layer-visibility checks are exercisable.

The generator does NOT depend on PyVista — it returns plain numpy
ENU coordinates and a frozen :class:`MockSceneFrame`. The UI panel
(:class:`workbench.ui.simulator.panels.Scene3DPanel`) is responsible
for turning the frame into PyVista actors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

_DEFAULT_RADAR_ENU_M: tuple[float, float, float] = (0.0, 0.0, 0.0)
_DEFAULT_TARGET_ORBIT_RADIUS_M: float = 4_000.0
_DEFAULT_TARGET_ORBIT_PERIOD_S: float = 30.0
_DEFAULT_TARGET_ALTITUDE_M: float = 500.0
_DEFAULT_TERRAIN_HALFSPAN_M: float = 8_000.0


@dataclass(frozen=True, slots=True)
class MockSceneFrame:
    """One generated 3-D scene frame.

    Attributes:
        radar_position_enu_m: Radar position in Map ENU [m], length 3.
        target_position_enu_m: Target position in Map ENU [m], length 3.
        terrain_halfspan_m: Half-span of the synthetic flat-terrain
            placeholder centred at the origin [m]. The Scene3DPanel
            uses this to size a low-altitude reference plane.
        sim_t_s: Simulation time the frame was generated at [s].
    """

    radar_position_enu_m: NDArray[np.float64]
    target_position_enu_m: NDArray[np.float64]
    terrain_halfspan_m: float
    sim_t_s: float


class MockSceneGenerator:
    """Deterministic synthetic 3-D scene generator.

    A fixed radar plus a single target on a horizontal circular orbit
    at constant altitude. The orbit angle is a linear function of
    ``sim_t_s`` so the same time always yields the same target
    position (paused scenes do not flicker).

    Args:
        radar_position_enu_m: Tuple of (E, N, U) radar position [m].
        target_orbit_radius_m: Horizontal orbit radius of the target
            relative to the radar [m], >= 0.
        target_orbit_period_s: Period of the circular orbit [s], > 0.
        target_altitude_m: Constant Up coordinate of the target [m].
        terrain_halfspan_m: Half-span of the placeholder terrain
            plane [m], > 0.

    Raises:
        ValueError: On any out-of-range constructor argument.
    """

    def __init__(
        self,
        *,
        radar_position_enu_m: tuple[float, float, float] = _DEFAULT_RADAR_ENU_M,
        target_orbit_radius_m: float = _DEFAULT_TARGET_ORBIT_RADIUS_M,
        target_orbit_period_s: float = _DEFAULT_TARGET_ORBIT_PERIOD_S,
        target_altitude_m: float = _DEFAULT_TARGET_ALTITUDE_M,
        terrain_halfspan_m: float = _DEFAULT_TERRAIN_HALFSPAN_M,
    ) -> None:
        if target_orbit_radius_m < 0.0:
            msg = f"target_orbit_radius_m must be >= 0, got {target_orbit_radius_m}"
            raise ValueError(msg)
        if target_orbit_period_s <= 0.0:
            msg = f"target_orbit_period_s must be > 0, got {target_orbit_period_s}"
            raise ValueError(msg)
        if terrain_halfspan_m <= 0.0:
            msg = f"terrain_halfspan_m must be > 0, got {terrain_halfspan_m}"
            raise ValueError(msg)
        self._radar_enu = np.asarray(radar_position_enu_m, dtype=np.float64)
        if self._radar_enu.shape != (3,):
            msg = f"radar_position_enu_m must be a 3-tuple, got shape {self._radar_enu.shape}"
            raise ValueError(msg)
        self._target_orbit_radius_m = target_orbit_radius_m
        self._target_orbit_period_s = target_orbit_period_s
        self._target_altitude_m = target_altitude_m
        self._terrain_halfspan_m = terrain_halfspan_m

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def terrain_halfspan_m(self) -> float:
        return self._terrain_halfspan_m

    def radar_position_enu_m(self) -> NDArray[np.float64]:
        """Read-only radar position (a fresh copy)."""
        return self._radar_enu.copy()

    def target_position_at(self, sim_t_s: float) -> NDArray[np.float64]:
        """Return the target ENU position [m] at ``sim_t_s``."""
        phase = 2.0 * math.pi * sim_t_s / self._target_orbit_period_s
        east = self._radar_enu[0] + self._target_orbit_radius_m * math.cos(phase)
        north = self._radar_enu[1] + self._target_orbit_radius_m * math.sin(phase)
        up = self._target_altitude_m
        return np.array([east, north, up], dtype=np.float64)

    def scene_for(self, sim_t_s: float) -> MockSceneFrame:
        """Generate one :class:`MockSceneFrame` at the given sim-time."""
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        return MockSceneFrame(
            radar_position_enu_m=self._radar_enu.copy(),
            target_position_enu_m=self.target_position_at(sim_t_s),
            terrain_halfspan_m=self._terrain_halfspan_m,
            sim_t_s=sim_t_s,
        )
