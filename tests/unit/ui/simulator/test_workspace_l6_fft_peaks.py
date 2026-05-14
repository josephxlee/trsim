"""Phase 4 L6 — FFT panel peak count fan-out + synthetic generator."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.ui.simulator.workspace import SimulatorWorkspace, synthetic_peak_counts

pytestmark = pytest.mark.qt


def _ws(qtbot) -> SimulatorWorkspace:  # type: ignore[no-untyped-def]
    ws = SimulatorWorkspace(nn_datasets_root=None, autostart_run_timer=False)
    qtbot.addWidget(ws)
    return ws


# ---------------------------------------------------------------------
# synthetic_peak_counts pure helper
# ---------------------------------------------------------------------


def test_synthetic_peak_counts_deterministic() -> None:
    """Same frame_id -> same (up, down) counts every call."""
    for frame_id in (0, 1, 5, 17, 100):
        first = synthetic_peak_counts(frame_id)
        second = synthetic_peak_counts(frame_id)
        assert first == second


def test_synthetic_peak_counts_non_negative() -> None:
    for frame_id in range(50):
        up, down = synthetic_peak_counts(frame_id)
        assert up >= 0
        assert down >= 0


def test_synthetic_peak_counts_negative_frame_rejected() -> None:
    with pytest.raises(ValueError, match=r"frame_id must be non-negative"):
        synthetic_peak_counts(-1)


def test_synthetic_peak_counts_pattern_period() -> None:
    """Pattern repeats every 6 frames (the helper's internal cycle)."""
    base = [synthetic_peak_counts(i) for i in range(6)]
    cycled = [synthetic_peak_counts(i + 6) for i in range(6)]
    assert base == cycled


# ---------------------------------------------------------------------
# Workspace fan-out: tick handler -> FFTPanel.set_peak_counts
# ---------------------------------------------------------------------


def test_fft_peaks_label_default(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    assert "0 up / 0 down" in ws.fft_panel().peaks_label().text()


def test_tick_pushes_peaks_into_fft_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)  # frame_id -> 1
    expected_up, expected_down = synthetic_peak_counts(1)
    text = ws.fft_panel().peaks_label().text()
    assert f"{expected_up} up" in text
    assert f"{expected_down} down" in text


def test_paused_tick_freezes_peaks(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    controller.tick(0.020)
    frozen_text = ws.fft_panel().peaks_label().text()
    controller.pause()
    controller.tick(0.020)
    assert ws.fft_panel().peaks_label().text() == frozen_text


def test_three_consecutive_ticks_match_pattern(qtbot) -> None:  # type: ignore[no-untyped-def]
    ws = _ws(qtbot)
    controller = ws.run_controller()
    controller.play()
    for expected_frame in range(1, 4):
        controller.tick(0.020)
        expected_up, expected_down = synthetic_peak_counts(expected_frame)
        text = ws.fft_panel().peaks_label().text()
        assert f"{expected_up} up" in text
        assert f"{expected_down} down" in text
