"""SimulatorRunController + RunPanel live sim_time/frame_id tests (Phase 4 L1)."""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from workbench.app.simulation_clock import SimulationClock
from workbench.domain.types import SimulationState, SpeedMultiplier
from workbench.ui.simulator.panels import RunPanel
from workbench.ui.simulator.run_controller import SimulatorRunController

pytestmark = pytest.mark.qt


# ---------------------------------------------------------------------
# RunPanel sim_time readout
# ---------------------------------------------------------------------


def _panel(qtbot) -> RunPanel:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    return panel


def test_run_panel_default_sim_time_readouts(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    assert p.sim_time_label().text() == "0.000 s"
    assert p.frame_id_label().text() == "0"
    assert p.sim_state_label().text() == "stopped"
    assert p.sim_speed_label().text() == "x1"


def test_set_sim_time_formats_seconds(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_sim_time(1.23456789, 42)
    assert p.sim_time_label().text() == "1.235 s"
    assert p.frame_id_label().text() == "42"


def test_set_sim_time_rejects_negative(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        p.set_sim_time(-0.1, 0)


def test_set_sim_time_rejects_negative_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    with pytest.raises(ValueError, match=r"frame_id must be non-negative"):
        p.set_sim_time(0.0, -1)


def test_set_sim_state_uses_enum_value(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_sim_state(SimulationState.RUNNING)
    assert p.sim_state_label().text() == "running"
    p.set_sim_state(SimulationState.PAUSED)
    assert p.sim_state_label().text() == "paused"


def test_set_sim_speed_formats(qtbot) -> None:  # type: ignore[no-untyped-def]
    p = _panel(qtbot)
    p.set_sim_speed(SpeedMultiplier.X4)
    assert p.sim_speed_label().text() == "x4"


# ---------------------------------------------------------------------
# SimulatorRunController transport
# ---------------------------------------------------------------------


def _controller(qtbot) -> SimulatorRunController:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    return SimulatorRunController(run_panel=panel, autostart_timer=False)


def test_controller_default_state_stopped(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    assert ctl.clock.state is SimulationState.STOPPED
    assert ctl.frame_id == 0
    assert ctl.clock.sim_t_s == 0.0


def test_play_transitions_to_running_and_paints_panel(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    assert ctl.clock.state is SimulationState.RUNNING
    panel = ctl._panel  # type: ignore[attr-defined]
    assert panel.sim_state_label().text() == "running"


def test_tick_advances_sim_time_and_frame_id(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    sim_dt = ctl.tick(0.020)
    assert sim_dt == pytest.approx(0.020)
    assert ctl.frame_id == 1
    assert ctl.clock.sim_t_s == pytest.approx(0.020)
    panel = ctl._panel  # type: ignore[attr-defined]
    assert panel.sim_time_label().text() == "0.020 s"
    assert panel.frame_id_label().text() == "1"


def test_tick_while_stopped_does_not_advance(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    sim_dt = ctl.tick(0.020)
    assert sim_dt == 0.0
    assert ctl.frame_id == 0


def test_pause_freezes_frame_id(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    ctl.tick(0.020)
    ctl.tick(0.020)
    assert ctl.frame_id == 2
    ctl.pause()
    ctl.tick(0.020)
    # No advance while paused.
    assert ctl.frame_id == 2
    assert ctl.clock.sim_t_s == pytest.approx(0.040)


def test_stop_resets_sim_time_and_frame(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    ctl.tick(0.020)
    ctl.tick(0.020)
    ctl.stop()
    assert ctl.clock.sim_t_s == 0.0
    assert ctl.frame_id == 0
    panel = ctl._panel  # type: ignore[attr-defined]
    assert panel.sim_time_label().text() == "0.000 s"
    assert panel.sim_state_label().text() == "stopped"


def test_set_speed_multiplies_advance(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.set_speed(SpeedMultiplier.X4)
    ctl.play()
    ctl.tick(0.010)
    # 10 ms wall * x4 = 40 ms sim
    assert ctl.clock.sim_t_s == pytest.approx(0.040)
    panel = ctl._panel  # type: ignore[attr-defined]
    assert panel.sim_speed_label().text() == "x4"


def test_tick_emits_tick_completed_signal(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    received: list[tuple[float, int]] = []
    ctl.tick_completed.connect(lambda t, f: received.append((t, f)))
    ctl.tick(0.010)
    ctl.tick(0.010)
    assert len(received) == 2
    assert received[1][1] == 2
    assert received[1][0] == pytest.approx(0.020)


def test_tick_rejects_negative_wall_dt(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    with pytest.raises(ValueError, match=r"wall_dt_s must be non-negative"):
        ctl.tick(-1.0)


def test_controller_rejects_zero_tick_interval(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    with pytest.raises(ValueError, match=r"tick_interval_ms must be > 0"):
        SimulatorRunController(run_panel=panel, tick_interval_ms=0, autostart_timer=False)


def test_play_after_stop_restarts_at_zero(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    ctl.tick(0.020)
    ctl.tick(0.020)
    ctl.stop()
    ctl.play()
    assert ctl.frame_id == 0
    assert ctl.clock.sim_t_s == 0.0


def test_play_after_pause_resumes_without_reset(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    ctl.play()
    ctl.tick(0.020)
    ctl.pause()
    ctl.play()
    assert ctl.frame_id == 1  # unchanged
    assert ctl.clock.sim_t_s == pytest.approx(0.020)


def test_external_clock_injection(qtbot) -> None:  # type: ignore[no-untyped-def]
    panel = RunPanel()
    qtbot.addWidget(panel)
    external = SimulationClock()
    ctl = SimulatorRunController(run_panel=panel, clock=external, autostart_timer=False)
    assert ctl.clock is external
    ctl.play()
    ctl.tick(0.020)
    assert external.sim_t_s == pytest.approx(0.020)


def test_controller_owns_qtimer(qtbot) -> None:  # type: ignore[no-untyped-def]
    ctl = _controller(qtbot)
    timer = ctl.timer()
    assert timer.interval() == ctl.tick_interval_ms
    assert timer.isActive() is False  # autostart_timer=False in tests
