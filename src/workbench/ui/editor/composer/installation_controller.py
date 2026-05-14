"""ComposerInstallationController — Phase 4 M2 live binding.

Bridges :class:`workbench.ui.editor.composer.ScenarioComposer`'s
``position_changed(east, north, az, el)`` signal to its own
``set_terrain_altitude`` / ``set_coverage_stats`` API via a small
mock probe. Real DEM-sampling + visibility-fan logic lands later
when the Scenario service starts driving the Composer end-to-end;
this controller exists so the Installation block stops feeling
static while the rest of Phase 4 lights up.

The probe is intentionally synthetic:

- ``terrain_altitude_m`` follows a smooth sinusoid in the east axis
  so panning the radar around the placeholder map updates the
  Composer readout deterministically.
- ``CoverageStats`` reports a max_range_km that decays with
  elevation (lower beams reach farther over the horizon), an
  obstructed-sector fraction that drops as elevation rises, and a
  small set of blind bearings at the cardinal directions the radar
  has been pointed *away* from.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QObject

from workbench.ui.editor.composer.widget import CoverageStats, ScenarioComposer

_DEFAULT_TOTAL_SECTORS: int = 36  # one sector per 10 deg of azimuth


class ComposerInstallationController(QObject):
    """Drive Installation block readouts from ``position_changed`` ticks.

    Args:
        composer: The :class:`ScenarioComposer` to drive.
        terrain_altitude_amplitude_m: Half-amplitude of the synthetic
            terrain sinusoid [m], >= 0.
        terrain_altitude_period_m: Spatial period of the synthetic
            terrain sinusoid in the east axis [m], > 0.
        max_range_km_at_horizon: Maximum reported range when the
            radar elevation is zero degrees [km], > 0.
        total_sectors: Number of sector buckets the Coverage Stats
            block summarises, > 0.
        parent: Standard QObject parent.

    Raises:
        ValueError: On out-of-range constructor arguments.
    """

    def __init__(
        self,
        *,
        composer: ScenarioComposer,
        terrain_altitude_amplitude_m: float = 25.0,
        terrain_altitude_period_m: float = 2_000.0,
        max_range_km_at_horizon: float = 60.0,
        total_sectors: int = _DEFAULT_TOTAL_SECTORS,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        if terrain_altitude_amplitude_m < 0.0:
            msg = f"terrain_altitude_amplitude_m must be >= 0, got {terrain_altitude_amplitude_m}"
            raise ValueError(msg)
        if terrain_altitude_period_m <= 0.0:
            msg = f"terrain_altitude_period_m must be > 0, got {terrain_altitude_period_m}"
            raise ValueError(msg)
        if max_range_km_at_horizon <= 0.0:
            msg = f"max_range_km_at_horizon must be > 0, got {max_range_km_at_horizon}"
            raise ValueError(msg)
        if total_sectors <= 0:
            msg = f"total_sectors must be > 0, got {total_sectors}"
            raise ValueError(msg)
        self._composer = composer
        self._terrain_amp_m = terrain_altitude_amplitude_m
        self._terrain_period_m = terrain_altitude_period_m
        self._max_range_km = max_range_km_at_horizon
        self._total_sectors = total_sectors
        composer.position_changed.connect(self._on_position_changed)

    # ------------------------------------------------------------------
    # Public API (test helpers)
    # ------------------------------------------------------------------
    def probe(
        self, east_m: float, north_m: float, az_deg: float, el_deg: float
    ) -> tuple[float, CoverageStats]:
        """Return the ``(altitude_m, coverage_stats)`` pair without painting."""
        # Terrain altitude: smooth sinusoid in the east axis. Add a
        # small linear north-axis term so both axes move the readout.
        phase = 2.0 * math.pi * east_m / self._terrain_period_m
        altitude = self._terrain_amp_m * math.sin(phase) + 0.001 * north_m

        # Max range shrinks with elevation cosine (mostly horizon-grazing
        # beams reach farther). Clamp elevation to a sensible band.
        el_clamped = max(-30.0, min(60.0, el_deg))
        el_rad = math.radians(el_clamped)
        cos_term = max(0.1, math.cos(el_rad))
        max_range = self._max_range_km * cos_term

        # Obstructed sectors: ~half the band-of-view at the horizon,
        # tapering to a quarter at 60 deg elevation. Always integer.
        obstructed_frac = max(0.0, min(1.0, 0.5 - 0.5 * math.sin(el_rad)))
        obstructed_sectors = round(obstructed_frac * self._total_sectors)

        # Blind bearings: the opposite of the radar's heading + 90 deg.
        # The "obstacle" is in the rear hemisphere of the antenna.
        rear = (az_deg + 180.0) % 360.0
        blind = (
            (rear - 10.0) % 360.0,
            rear % 360.0,
            (rear + 10.0) % 360.0,
        )
        stats = CoverageStats(
            max_range_km=max_range,
            obstructed_sectors=obstructed_sectors,
            total_sectors=self._total_sectors,
            blind_bearings_deg=blind,
        )
        return altitude, stats

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_position_changed(
        self, east_m: float, north_m: float, az_deg: float, el_deg: float
    ) -> None:
        altitude, stats = self.probe(east_m, north_m, az_deg, el_deg)
        self._composer.set_terrain_altitude(altitude)
        self._composer.set_coverage_stats(stats)
