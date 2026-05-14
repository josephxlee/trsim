"""Mock Range-Doppler heatmap generator for the Simulator RD panel.

Phase 4 L3 wires the Simulator's :class:`RangeDopplerPanel` to a
deterministic, sim-time-driven 2-D heatmap generator while the full
Phase 3 ``Pipeline`` remains unwired. The generator is intentionally
synthetic — it does NOT call into ``workbench.physics`` for range or
Doppler returns; instead it paints a 2-D Gaussian blob that moves
along both axes so the user sees a clear target track.

Behaviour:

- ``range_axis_m`` is a fixed monotonically increasing axis from
  ``range_min_m`` to ``range_max_m`` with ``n_range_bins`` samples.
- ``doppler_axis_mps`` is a fixed monotonically increasing axis from
  ``doppler_min_mps`` to ``doppler_max_mps`` with ``n_doppler_bins``
  samples.
- The synthetic target moves: range tracks
  ``range_base_m + range_sweep_m * sin(omega_r * t)``; doppler tracks
  ``doppler_base_mps + doppler_sweep_mps * cos(omega_d * t)``. The
  two periods are independent so the blob traces a Lissajous-like
  figure across the heatmap.
- Gaussian noise is added with a sim-time-derived seed (the same
  pattern used by :mod:`workbench.app.simulator.mock_spectrum`).

The returned heatmap is in dB so it can be passed straight to a
pyqtgraph ``ImageItem`` with sensible levels.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

DEFAULT_RANGE_MIN_M: float = 0.0
DEFAULT_RANGE_MAX_M: float = 10_000.0
DEFAULT_DOPPLER_MIN_MPS: float = -50.0
DEFAULT_DOPPLER_MAX_MPS: float = 50.0
DEFAULT_N_RANGE_BINS: int = 64
DEFAULT_N_DOPPLER_BINS: int = 64
_DEFAULT_RANGE_BASE_M: float = 5_000.0
_DEFAULT_RANGE_SWEEP_M: float = 2_500.0
_DEFAULT_RANGE_PERIOD_S: float = 6.0
_DEFAULT_DOPPLER_BASE_MPS: float = 0.0
_DEFAULT_DOPPLER_SWEEP_MPS: float = 30.0
_DEFAULT_DOPPLER_PERIOD_S: float = 4.0
_DEFAULT_PEAK_WIDTH_RANGE_M: float = 350.0
_DEFAULT_PEAK_WIDTH_DOPPLER_MPS: float = 6.0
_DEFAULT_PEAK_HEIGHT_DB: float = 25.0
_DEFAULT_NOISE_FLOOR_DB: float = -60.0
_DEFAULT_NOISE_STD_DB: float = 2.0
_DEFAULT_SEED: int = 20260514


@dataclass(frozen=True, slots=True)
class MockRangeDopplerFrame:
    """One generated Range-Doppler frame.

    Attributes:
        heatmap_db: 2-D array of shape ``(n_range_bins, n_doppler_bins)``
            with magnitudes in dB.
        range_axis_m: 1-D range axis [m], length ``n_range_bins``.
        doppler_axis_mps: 1-D doppler axis [m/s], length
            ``n_doppler_bins``.
        peak_range_m: Range coordinate of the synthetic target [m].
        peak_doppler_mps: Doppler coordinate of the synthetic
            target [m/s].
        sim_t_s: Simulation time the frame was generated at [s].
    """

    heatmap_db: NDArray[np.float64]
    range_axis_m: NDArray[np.float64]
    doppler_axis_mps: NDArray[np.float64]
    peak_range_m: float
    peak_doppler_mps: float
    sim_t_s: float


class MockRangeDopplerGenerator:
    """Deterministic synthetic Range-Doppler heatmap generator.

    The synthetic target traces an independent sinusoid on each axis;
    the resulting cell is a 2-D Gaussian. The same ``sim_t_s`` always
    yields the same heatmap so a paused controller can re-paint
    without flicker.

    Args:
        range_min_m: Lower bound of the range axis [m], >= 0.
        range_max_m: Upper bound of the range axis [m], strictly
            greater than ``range_min_m``.
        doppler_min_mps: Lower bound of the doppler axis [m/s].
        doppler_max_mps: Upper bound of the doppler axis [m/s],
            strictly greater than ``doppler_min_mps``.
        n_range_bins: Number of range samples, >= 8.
        n_doppler_bins: Number of doppler samples, >= 8.
        range_base_m: Centre of the target's range oscillation [m]; must
            lie inside ``[range_min_m, range_max_m]``.
        range_sweep_m: Half-amplitude of the target's range sinusoid
            [m], >= 0. Capped so the target never escapes the axis.
        range_period_s: Period of the range sinusoid [s], > 0.
        doppler_base_mps: Centre of the target's doppler oscillation
            [m/s]; must lie inside the doppler axis.
        doppler_sweep_mps: Half-amplitude of the target's doppler
            sinusoid [m/s], >= 0. Capped so the target never escapes.
        doppler_period_s: Period of the doppler sinusoid [s], > 0.
        peak_width_range_m: Gaussian sigma along the range axis [m],
            > 0.
        peak_width_doppler_mps: Gaussian sigma along the doppler axis
            [m/s], > 0.
        peak_height_db: Peak amplitude above the noise floor [dB].
        noise_floor_db: Baseline magnitude before noise [dB].
        noise_std_db: Standard deviation of the additive Gaussian
            noise [dB], >= 0.
        rng_seed: Base seed; the actual seed for ``heatmap_for(t)`` is
            ``rng_seed ^ round(t * 1e6)``.
    """

    def __init__(
        self,
        *,
        range_min_m: float = DEFAULT_RANGE_MIN_M,
        range_max_m: float = DEFAULT_RANGE_MAX_M,
        doppler_min_mps: float = DEFAULT_DOPPLER_MIN_MPS,
        doppler_max_mps: float = DEFAULT_DOPPLER_MAX_MPS,
        n_range_bins: int = DEFAULT_N_RANGE_BINS,
        n_doppler_bins: int = DEFAULT_N_DOPPLER_BINS,
        range_base_m: float = _DEFAULT_RANGE_BASE_M,
        range_sweep_m: float = _DEFAULT_RANGE_SWEEP_M,
        range_period_s: float = _DEFAULT_RANGE_PERIOD_S,
        doppler_base_mps: float = _DEFAULT_DOPPLER_BASE_MPS,
        doppler_sweep_mps: float = _DEFAULT_DOPPLER_SWEEP_MPS,
        doppler_period_s: float = _DEFAULT_DOPPLER_PERIOD_S,
        peak_width_range_m: float = _DEFAULT_PEAK_WIDTH_RANGE_M,
        peak_width_doppler_mps: float = _DEFAULT_PEAK_WIDTH_DOPPLER_MPS,
        peak_height_db: float = _DEFAULT_PEAK_HEIGHT_DB,
        noise_floor_db: float = _DEFAULT_NOISE_FLOOR_DB,
        noise_std_db: float = _DEFAULT_NOISE_STD_DB,
        rng_seed: int = _DEFAULT_SEED,
    ) -> None:
        if range_min_m < 0.0:
            msg = f"range_min_m must be >= 0, got {range_min_m}"
            raise ValueError(msg)
        if range_max_m <= range_min_m:
            msg = f"range_max_m ({range_max_m}) must exceed range_min_m ({range_min_m})"
            raise ValueError(msg)
        if doppler_max_mps <= doppler_min_mps:
            msg = (
                f"doppler_max_mps ({doppler_max_mps}) must exceed "
                f"doppler_min_mps ({doppler_min_mps})"
            )
            raise ValueError(msg)
        if n_range_bins < 8:
            msg = f"n_range_bins must be >= 8, got {n_range_bins}"
            raise ValueError(msg)
        if n_doppler_bins < 8:
            msg = f"n_doppler_bins must be >= 8, got {n_doppler_bins}"
            raise ValueError(msg)
        if not (range_min_m <= range_base_m <= range_max_m):
            msg = (
                f"range_base_m ({range_base_m}) must lie in "
                f"[range_min_m, range_max_m] = [{range_min_m}, {range_max_m}]"
            )
            raise ValueError(msg)
        if not (doppler_min_mps <= doppler_base_mps <= doppler_max_mps):
            msg = (
                f"doppler_base_mps ({doppler_base_mps}) must lie in "
                f"[doppler_min_mps, doppler_max_mps] = "
                f"[{doppler_min_mps}, {doppler_max_mps}]"
            )
            raise ValueError(msg)
        if range_sweep_m < 0.0:
            msg = f"range_sweep_m must be >= 0, got {range_sweep_m}"
            raise ValueError(msg)
        if doppler_sweep_mps < 0.0:
            msg = f"doppler_sweep_mps must be >= 0, got {doppler_sweep_mps}"
            raise ValueError(msg)
        if range_period_s <= 0.0:
            msg = f"range_period_s must be > 0, got {range_period_s}"
            raise ValueError(msg)
        if doppler_period_s <= 0.0:
            msg = f"doppler_period_s must be > 0, got {doppler_period_s}"
            raise ValueError(msg)
        if peak_width_range_m <= 0.0:
            msg = f"peak_width_range_m must be > 0, got {peak_width_range_m}"
            raise ValueError(msg)
        if peak_width_doppler_mps <= 0.0:
            msg = f"peak_width_doppler_mps must be > 0, got {peak_width_doppler_mps}"
            raise ValueError(msg)
        if noise_std_db < 0.0:
            msg = f"noise_std_db must be >= 0, got {noise_std_db}"
            raise ValueError(msg)

        self._range_axis_m: NDArray[np.float64] = np.linspace(
            range_min_m, range_max_m, n_range_bins, dtype=np.float64
        )
        self._doppler_axis_mps: NDArray[np.float64] = np.linspace(
            doppler_min_mps, doppler_max_mps, n_doppler_bins, dtype=np.float64
        )
        self._range_min_m = range_min_m
        self._range_max_m = range_max_m
        self._doppler_min_mps = doppler_min_mps
        self._doppler_max_mps = doppler_max_mps
        self._range_base_m = range_base_m
        self._doppler_base_mps = doppler_base_mps
        # Cap sweeps so the target never escapes the axis.
        max_range_amp = min(range_base_m - range_min_m, range_max_m - range_base_m)
        max_doppler_amp = min(
            doppler_base_mps - doppler_min_mps, doppler_max_mps - doppler_base_mps
        )
        self._range_sweep_m = float(min(range_sweep_m, max(max_range_amp, 0.0)))
        self._doppler_sweep_mps = float(min(doppler_sweep_mps, max(max_doppler_amp, 0.0)))
        self._range_period_s = range_period_s
        self._doppler_period_s = doppler_period_s
        self._peak_width_range_m = peak_width_range_m
        self._peak_width_doppler_mps = peak_width_doppler_mps
        self._peak_height_db = peak_height_db
        self._noise_floor_db = noise_floor_db
        self._noise_std_db = noise_std_db
        self._rng_seed = rng_seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def range_axis_m(self) -> NDArray[np.float64]:
        """Read-only range axis (a fresh copy)."""
        return self._range_axis_m.copy()

    def doppler_axis_mps(self) -> NDArray[np.float64]:
        """Read-only doppler axis (a fresh copy)."""
        return self._doppler_axis_mps.copy()

    @property
    def n_range_bins(self) -> int:
        return int(self._range_axis_m.size)

    @property
    def n_doppler_bins(self) -> int:
        return int(self._doppler_axis_mps.size)

    def peak_position_at(self, sim_t_s: float) -> tuple[float, float]:
        """Return ``(peak_range_m, peak_doppler_mps)`` at ``sim_t_s``."""
        r_phase = 2.0 * math.pi * sim_t_s / self._range_period_s
        d_phase = 2.0 * math.pi * sim_t_s / self._doppler_period_s
        peak_r = self._range_base_m + self._range_sweep_m * math.sin(r_phase)
        peak_d = self._doppler_base_mps + self._doppler_sweep_mps * math.cos(d_phase)
        return peak_r, peak_d

    def heatmap_for(self, sim_t_s: float) -> MockRangeDopplerFrame:
        """Generate one :class:`MockRangeDopplerFrame` at ``sim_t_s``.

        ``sim_t_s`` must be non-negative. The same ``sim_t_s`` value
        (within 1 us) always produces the same arrays.
        """
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        peak_r, peak_d = self.peak_position_at(sim_t_s)
        time_seed = round(sim_t_s * 1.0e6)
        rng = np.random.default_rng(self._rng_seed ^ time_seed)
        heatmap = self._compose_heatmap(peak_r, peak_d, rng)
        return MockRangeDopplerFrame(
            heatmap_db=heatmap,
            range_axis_m=self._range_axis_m.copy(),
            doppler_axis_mps=self._doppler_axis_mps.copy(),
            peak_range_m=peak_r,
            peak_doppler_mps=peak_d,
            sim_t_s=sim_t_s,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _compose_heatmap(
        self,
        peak_range_m: float,
        peak_doppler_mps: float,
        rng: np.random.Generator,
    ) -> NDArray[np.float64]:
        """2-D Gaussian peak in dB + noise floor + Gaussian noise."""
        delta_r = (self._range_axis_m - peak_range_m) / self._peak_width_range_m
        delta_d = (self._doppler_axis_mps - peak_doppler_mps) / self._peak_width_doppler_mps
        # Outer-product Gaussian — shape (n_range, n_doppler).
        gauss_r = np.exp(-0.5 * delta_r**2)
        gauss_d = np.exp(-0.5 * delta_d**2)
        peak = self._peak_height_db * np.outer(gauss_r, gauss_d)
        noise = rng.normal(
            0.0,
            self._noise_std_db,
            size=(self._range_axis_m.size, self._doppler_axis_mps.size),
        )
        return self._noise_floor_db + peak + noise
