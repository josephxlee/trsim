"""PhysicsClock tests (PL-D, plan/19 § 19.6.5)."""

from __future__ import annotations

import pytest

from workbench.app.physics_lab import ClockTick, PhysicsClock


def test_default_clock_starts_paused_at_zero() -> None:
    clock = PhysicsClock()
    assert clock.dt_s == pytest.approx(0.02)
    assert clock.time_s == 0.0
    assert clock.frame_id == 0
    assert not clock.is_running


def test_constructor_rejects_non_positive_dt() -> None:
    with pytest.raises(ValueError, match=r"dt_s"):
        PhysicsClock(dt_s=0.0)


def test_tick_returns_none_when_paused() -> None:
    clock = PhysicsClock()
    assert clock.tick() is None


def test_tick_advances_time_and_frame_after_start() -> None:
    clock = PhysicsClock(dt_s=0.05)
    clock.start()
    ev = clock.tick()
    assert isinstance(ev, ClockTick)
    assert ev.dt_s == pytest.approx(0.05)
    assert ev.time_s == pytest.approx(0.05)
    assert ev.frame_id == 1
    ev2 = clock.tick()
    assert ev2 is not None
    assert ev2.frame_id == 2
    assert ev2.time_s == pytest.approx(0.10)


def test_pause_preserves_state_resume_continues() -> None:
    clock = PhysicsClock(dt_s=0.1)
    clock.start()
    clock.tick()
    clock.pause()
    assert clock.tick() is None
    assert clock.time_s == pytest.approx(0.1)
    clock.start()
    ev = clock.tick()
    assert ev is not None
    assert ev.time_s == pytest.approx(0.2)
    assert ev.frame_id == 2


def test_stop_resets_time_and_frame() -> None:
    clock = PhysicsClock()
    clock.start()
    for _ in range(5):
        clock.tick()
    clock.stop()
    assert clock.time_s == 0.0
    assert clock.frame_id == 0
    assert not clock.is_running


def test_run_for_emits_exactly_n_ticks() -> None:
    clock = PhysicsClock(dt_s=0.01)
    received: list[ClockTick] = []
    n = clock.run_for(7, received.append)
    assert n == 7
    assert len(received) == 7
    assert received[-1].frame_id == 7
    assert received[-1].time_s == pytest.approx(0.07)


def test_run_for_rejects_negative_n() -> None:
    clock = PhysicsClock()
    with pytest.raises(ValueError, match=r"n_frames"):
        clock.run_for(-1, lambda _ev: None)
