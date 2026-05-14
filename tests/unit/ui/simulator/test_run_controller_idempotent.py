"""SimulatorRunController.play / pause idempotent tests (P5d-fix).

User-reported during MVP_GUIDE rev11 hand-test: clicking the toolbar
Play button twice produced ``RuntimeError: SimulationClock.start:
already RUNNING``. The domain layer keeps the strict double-start
guard, but the UI controller absorbs it so toolbar / palette / hotkey
calls are safe to re-trigger.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.domain.types import SimulationState
from workbench.ui.simulator.panels import RunPanel
from workbench.ui.simulator.run_controller import SimulatorRunController

pytestmark = pytest.mark.qt


def _ctl(qtbot) -> SimulatorRunController:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    return SimulatorRunController(run_panel=panel, autostart_timer=False)


def test_play_twice_does_not_raise(qtbot) -> None:  # type: ignore[no-untyped-def]
    """The second Play press is a no-op (toolbar idempotency)."""
    ctl = _ctl(qtbot)
    ctl.play()
    assert ctl.clock.state is SimulationState.RUNNING
    # Second click must not raise.
    ctl.play()
    assert ctl.clock.state is SimulationState.RUNNING


def test_play_three_times_stays_running(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _ctl(qtbot)
    for _ in range(3):
        ctl.play()
    assert ctl.clock.state is SimulationState.RUNNING


def test_pause_twice_stays_paused(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _ctl(qtbot)
    ctl.play()
    ctl.pause()
    assert ctl.clock.state is SimulationState.PAUSED
    ctl.pause()
    assert ctl.clock.state is SimulationState.PAUSED


def test_pause_when_stopped_is_noop(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _ctl(qtbot)
    # STOPPED -> PAUSED via Pause click. No-op (only RUNNING -> PAUSED is real).
    ctl.pause()
    assert ctl.clock.state is SimulationState.STOPPED


def test_stop_when_already_stopped_is_noop(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _ctl(qtbot)
    ctl.stop()
    ctl.stop()
    assert ctl.clock.state is SimulationState.STOPPED
    assert ctl.frame_id == 0


def test_play_resume_from_pause(qtbot) -> None:  # type: ignore[no-untyped-def]
    """PAUSED -> RUNNING preserves frame_id (not a fresh start)."""
    ctl = _ctl(qtbot)
    ctl.play()
    ctl.tick(0.033)
    ctl.tick(0.033)
    assert ctl.frame_id == 2
    ctl.pause()
    ctl.play()  # Resume.
    assert ctl.clock.state is SimulationState.RUNNING
    assert ctl.frame_id == 2  # Unchanged.


def test_play_after_stop_resets_frame_id(qtbot) -> None:  # type: ignore[no-untyped-def]
    """STOPPED -> RUNNING resets frame_id (cold start)."""
    ctl = _ctl(qtbot)
    ctl.play()
    ctl.tick(0.033)
    ctl.stop()
    ctl.play()
    assert ctl.frame_id == 0
