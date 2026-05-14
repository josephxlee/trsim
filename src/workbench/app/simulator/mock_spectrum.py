"""Mock FMCW beat-spectrum generator for the Simulator FFT panel.

Phase 4 L2 wires the Simulator's :class:`FFTPanel` to a deterministic,
sim-time-driven spectrum generator while the full Phase 3 ``Pipeline``
remains unwired. The generator is intentionally synthetic — it does
NOT call into ``workbench.physics.fmcw``; instead it produces a
plausible-looking up/down sweep beat spectrum so the UI can be
verified without booting a scenario.

Behaviour:

- ``freqs_hz`` is a fixed monotonically increasing axis from
  ``freq_min_hz`` to ``freq_max_hz`` with ``n_bins`` samples.
- The target beat frequency oscillates sinusoidally with period
  ``sweep_period_s`` so the user sees a clear moving peak.
- The up-sweep peak rises, the down-sweep peak falls (the FMCW
  triangle convention used elsewhere in the codebase).
- Gaussian noise is added with a sim-time-derived seed so the same
  ``sim_t_s`` always produces the same arrays — the panel can be
  diffed in tests without flake.

This module sits in the App layer; it depends only on numpy and on
:mod:`workbench.domain` is not touched. The UI controller in
:mod:`workbench.ui.simulator.fft_controller` consumes the
:class:`MockSpectrumFrame` and pushes it into the FFT panel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

DEFAULT_FREQ_MIN_HZ: float = 0.0
DEFAULT_FREQ_MAX_HZ: float = 2.0e6
DEFAULT_N_BINS: int = 512
_DEFAULT_PEAK_BASE_HZ: float = 7.5e5
_DEFAULT_PEAK_SWEEP_HZ: float = 3.0e5
_DEFAULT_SWEEP_PERIOD_S: float = 4.0
_DEFAULT_PEAK_WIDTH_HZ: float = 2.5e4
_DEFAULT_PEAK_HEIGHT_DB: float = 0.0
_DEFAULT_NOISE_FLOOR_DB: float = -60.0
_DEFAULT_NOISE_STD_DB: float = 3.0
_DEFAULT_SEED: int = 20260513


@dataclass(frozen=True, slots=True)
class MockSpectrumFrame:
    """One generated spectrum frame.

    Attributes:
        freqs_hz: 1-D monotonically increasing frequency axis [Hz].
        up_mag_db: Up-sweep magnitude [dB], same length as ``freqs_hz``.
        down_mag_db: Down-sweep magnitude [dB], same length as ``freqs_hz``.
        up_peak_freq_hz: Centre frequency of the synthetic up-sweep peak [Hz].
        down_peak_freq_hz: Centre frequency of the synthetic down-sweep peak [Hz].
        sim_t_s: Simulation time the frame was generated at [s].
    """

    freqs_hz: NDArray[np.float64]
    up_mag_db: NDArray[np.float64]
    down_mag_db: NDArray[np.float64]
    up_peak_freq_hz: float
    down_peak_freq_hz: float
    sim_t_s: float


class MockSpectrumGenerator:
    """Deterministic synthetic FMCW beat-spectrum generator.

    All angles are interpreted via the FMCW triangle convention used
    elsewhere in the codebase: the up-sweep peak rises with target
    range, the down-sweep peak falls.

    Args:
        freq_min_hz: Lower bound of the frequency axis [Hz], >= 0.
        freq_max_hz: Upper bound of the frequency axis [Hz], strictly
            greater than ``freq_min_hz``.
        n_bins: Number of frequency samples, >= 8.
        peak_base_hz: Centre of the peak's oscillation [Hz]. Must lie
            inside ``[freq_min_hz, freq_max_hz]``.
        peak_sweep_hz: Half-amplitude of the peak's sinusoidal motion
            [Hz], >= 0. Capped so the peak never escapes the axis.
        sweep_period_s: Period of the peak's sinusoidal motion [s], > 0.
        peak_width_hz: Standard deviation of the Gaussian peak [Hz], > 0.
        peak_height_db: Peak amplitude above the noise floor [dB].
        noise_floor_db: Baseline magnitude before noise [dB].
        noise_std_db: Standard deviation of the additive Gaussian noise
            [dB], >= 0.
        rng_seed: Base seed for the per-frame RNG. The actual seed used
            for ``spectrum_for(sim_t_s)`` is derived from this plus a
            quantised version of ``sim_t_s`` so the same time always
            yields the same arrays.

    Raises:
        ValueError: On any out-of-range constructor argument.
    """

    def __init__(
        self,
        *,
        freq_min_hz: float = DEFAULT_FREQ_MIN_HZ,
        freq_max_hz: float = DEFAULT_FREQ_MAX_HZ,
        n_bins: int = DEFAULT_N_BINS,
        peak_base_hz: float = _DEFAULT_PEAK_BASE_HZ,
        peak_sweep_hz: float = _DEFAULT_PEAK_SWEEP_HZ,
        sweep_period_s: float = _DEFAULT_SWEEP_PERIOD_S,
        peak_width_hz: float = _DEFAULT_PEAK_WIDTH_HZ,
        peak_height_db: float = _DEFAULT_PEAK_HEIGHT_DB,
        noise_floor_db: float = _DEFAULT_NOISE_FLOOR_DB,
        noise_std_db: float = _DEFAULT_NOISE_STD_DB,
        rng_seed: int = _DEFAULT_SEED,
    ) -> None:
        if freq_min_hz < 0.0:
            msg = f"freq_min_hz must be >= 0, got {freq_min_hz}"
            raise ValueError(msg)
        if freq_max_hz <= freq_min_hz:
            msg = f"freq_max_hz ({freq_max_hz}) must exceed freq_min_hz ({freq_min_hz})"
            raise ValueError(msg)
        if n_bins < 8:
            msg = f"n_bins must be >= 8, got {n_bins}"
            raise ValueError(msg)
        if not (freq_min_hz <= peak_base_hz <= freq_max_hz):
            msg = (
                f"peak_base_hz ({peak_base_hz}) must lie in "
                f"[freq_min_hz, freq_max_hz] = [{freq_min_hz}, {freq_max_hz}]"
            )
            raise ValueError(msg)
        if peak_sweep_hz < 0.0:
            msg = f"peak_sweep_hz must be >= 0, got {peak_sweep_hz}"
            raise ValueError(msg)
        if sweep_period_s <= 0.0:
            msg = f"sweep_period_s must be > 0, got {sweep_period_s}"
            raise ValueError(msg)
        if peak_width_hz <= 0.0:
            msg = f"peak_width_hz must be > 0, got {peak_width_hz}"
            raise ValueError(msg)
        if noise_std_db < 0.0:
            msg = f"noise_std_db must be >= 0, got {noise_std_db}"
            raise ValueError(msg)

        self._freqs_hz: NDArray[np.float64] = np.linspace(
            freq_min_hz, freq_max_hz, n_bins, dtype=np.float64
        )
        self._freq_min_hz = freq_min_hz
        self._freq_max_hz = freq_max_hz
        self._peak_base_hz = peak_base_hz
        # Cap the sweep amplitude so the peak never escapes the axis.
        max_amp = min(peak_base_hz - freq_min_hz, freq_max_hz - peak_base_hz)
        self._peak_sweep_hz = float(min(peak_sweep_hz, max(max_amp, 0.0)))
        self._sweep_period_s = sweep_period_s
        self._peak_width_hz = peak_width_hz
        self._peak_height_db = peak_height_db
        self._noise_floor_db = noise_floor_db
        self._noise_std_db = noise_std_db
        self._rng_seed = rng_seed

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def freqs_hz(self) -> NDArray[np.float64]:
        """Read-only frequency axis (a fresh copy)."""
        return self._freqs_hz.copy()

    @property
    def n_bins(self) -> int:
        return int(self._freqs_hz.size)

    def peak_freq_at(self, sim_t_s: float) -> tuple[float, float]:
        """Return ``(up_peak_hz, down_peak_hz)`` for the given sim-time.

        The up-sweep peak moves sinusoidally upward from
        ``peak_base_hz``; the down-sweep peak mirrors it about the
        base so that, on the FMCW triangle, ``(up + down) / 2`` stays
        constant (no Doppler in this mock).
        """
        phase = 2.0 * math.pi * sim_t_s / self._sweep_period_s
        offset = self._peak_sweep_hz * math.sin(phase)
        up_peak = self._peak_base_hz + offset
        down_peak = self._peak_base_hz - offset
        return up_peak, down_peak

    def spectrum_for(self, sim_t_s: float) -> MockSpectrumFrame:
        """Generate one :class:`MockSpectrumFrame` at the given sim-time.

        ``sim_t_s`` must be non-negative. The same ``sim_t_s`` value
        (within 1 us) always produces the same arrays so a paused
        controller can re-paint without flicker.
        """
        if sim_t_s < 0.0:
            msg = f"sim_t_s must be non-negative, got {sim_t_s}"
            raise ValueError(msg)
        up_peak, down_peak = self.peak_freq_at(sim_t_s)
        # Quantise sim_t_s to 1 us so noise is reproducible per tick.
        time_seed = round(sim_t_s * 1.0e6)
        rng_up = np.random.default_rng(self._rng_seed ^ time_seed ^ 0xA1A1A1)
        rng_down = np.random.default_rng(self._rng_seed ^ time_seed ^ 0xB2B2B2)

        up_mag = self._compose_spectrum(up_peak, rng_up)
        down_mag = self._compose_spectrum(down_peak, rng_down)
        return MockSpectrumFrame(
            freqs_hz=self._freqs_hz.copy(),
            up_mag_db=up_mag,
            down_mag_db=down_mag,
            up_peak_freq_hz=up_peak,
            down_peak_freq_hz=down_peak,
            sim_t_s=sim_t_s,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _compose_spectrum(
        self,
        peak_freq_hz: float,
        rng: np.random.Generator,
    ) -> NDArray[np.float64]:
        """Gaussian peak in dB + noise floor + Gaussian noise."""
        delta = self._freqs_hz - peak_freq_hz
        gauss = np.exp(-0.5 * (delta / self._peak_width_hz) ** 2)
        # Peak rises ``peak_height_db`` dB above the floor at the centre,
        # decays smoothly back to the floor in the wings.
        peak_component = self._peak_height_db * gauss
        noise = rng.normal(0.0, self._noise_std_db, size=self._freqs_hz.size)
        return self._noise_floor_db + peak_component + noise
