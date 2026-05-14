"""ComposerInstallationController tests (Phase 4 M2)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.editor.composer import (
    ComposerInstallationController,
    CoverageStats,
    ScenarioComposer,
)

pytestmark = pytest.mark.qt


def _composer(qtbot) -> ScenarioComposer:  # type: ignore[no-untyped-def]
    c = ScenarioComposer()
    qtbot.addWidget(c)
    return c


# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_constructor_rejects_negative_terrain_amplitude(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    with pytest.raises(ValueError, match=r"terrain_altitude_amplitude_m must be >= 0"):
        ComposerInstallationController(composer=c, terrain_altitude_amplitude_m=-1.0)


def test_constructor_rejects_zero_terrain_period(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    with pytest.raises(ValueError, match=r"terrain_altitude_period_m must be > 0"):
        ComposerInstallationController(composer=c, terrain_altitude_period_m=0.0)


def test_constructor_rejects_nonpositive_max_range(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    with pytest.raises(ValueError, match=r"max_range_km_at_horizon must be > 0"):
        ComposerInstallationController(composer=c, max_range_km_at_horizon=0.0)


def test_constructor_rejects_nonpositive_total_sectors(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    with pytest.raises(ValueError, match=r"total_sectors must be > 0"):
        ComposerInstallationController(composer=c, total_sectors=0)


# ---------------------------------------------------------------------
# Probe behaviour
# ---------------------------------------------------------------------


def test_probe_returns_terrain_altitude_and_coverage_stats(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    _altitude, stats = ctl.probe(0.0, 0.0, 0.0, 0.0)
    assert isinstance(stats, CoverageStats)
    assert stats.max_range_km > 0.0
    assert 0 <= stats.obstructed_sectors <= stats.total_sectors


def test_probe_altitude_moves_with_east_axis(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    a, _ = ctl.probe(0.0, 0.0, 0.0, 0.0)
    b, _ = ctl.probe(500.0, 0.0, 0.0, 0.0)
    assert a != pytest.approx(b)


def test_probe_max_range_decays_with_elevation(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c, max_range_km_at_horizon=100.0)
    _, horizon_stats = ctl.probe(0.0, 0.0, 0.0, 0.0)
    _, sky_stats = ctl.probe(0.0, 0.0, 0.0, 45.0)
    assert horizon_stats.max_range_km > sky_stats.max_range_km


def test_probe_obstructed_fraction_shrinks_with_elevation(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c, total_sectors=36)
    _, horizon_stats = ctl.probe(0.0, 0.0, 0.0, 0.0)
    _, sky_stats = ctl.probe(0.0, 0.0, 0.0, 45.0)
    assert horizon_stats.obstructed_sectors >= sky_stats.obstructed_sectors


def test_probe_blind_bearings_lie_in_unit_circle(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    _, stats = ctl.probe(0.0, 0.0, 45.0, 0.0)
    for bearing in stats.blind_bearings_deg:
        assert 0.0 <= bearing < 360.0


def test_probe_is_deterministic(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    a_alt, a_stats = ctl.probe(123.0, 456.0, 78.0, 9.0)
    b_alt, b_stats = ctl.probe(123.0, 456.0, 78.0, 9.0)
    assert a_alt == pytest.approx(b_alt)
    assert a_stats == b_stats


# ---------------------------------------------------------------------
# Signal wiring
# ---------------------------------------------------------------------


def test_position_changed_signal_paints_terrain_altitude(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    expected_altitude, _ = ctl.probe(200.0, 0.0, 0.0, 0.0)
    c.position_changed.emit(200.0, 0.0, 0.0, 0.0)
    # The Composer's altitude label now shows the probed value
    # (rounded to 2 decimals).
    assert f"{expected_altitude:.2f}" in c.altitude_label().text()


def test_position_changed_signal_paints_coverage_stats(qtbot) -> None:  # type: ignore[no-untyped-def]
    c = _composer(qtbot)
    ctl = ComposerInstallationController(composer=c)
    _, stats = ctl.probe(0.0, 0.0, 30.0, 5.0)
    c.position_changed.emit(0.0, 0.0, 30.0, 5.0)
    # Verify the max-range readout shows the probed value.
    assert f"{stats.max_range_km:.1f}" in c.max_range_label().text()
