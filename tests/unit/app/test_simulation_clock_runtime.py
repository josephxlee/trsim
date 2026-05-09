"""Unit tests for App-layer runtime: SimulationClock + InputBuffer +
RunManager + ProbeRecorder (Phase 3.2)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workbench.app.input_buffer import InputBuffer
from workbench.app.probe_recorder import ProbeRecorder, ProbeRow
from workbench.app.run_manager import RunManager
from workbench.app.simulation_clock import SimulationClock
from workbench.domain.types import (
    CommandSource,
    RunState,
    RunTerminationReason,
    SimulationState,
    SpeedMultiplier,
)

# ---------------------------------------------------------------------
# SimulationClock
# ---------------------------------------------------------------------


def test_clock_initial_state() -> None:
    c = SimulationClock()
    assert c.state is SimulationState.STOPPED
    assert c.sim_t_s == 0.0
    assert c.speed is SpeedMultiplier.X1


def test_clock_start_resets_sim_t_s() -> None:
    c = SimulationClock(state=SimulationState.STOPPED, sim_t_s=99.0)
    c.start()
    assert c.state is SimulationState.RUNNING
    assert c.sim_t_s == 0.0


def test_clock_start_from_paused_keeps_sim_t_s() -> None:
    c = SimulationClock(state=SimulationState.PAUSED, sim_t_s=12.5)
    c.start()
    assert c.state is SimulationState.RUNNING
    assert c.sim_t_s == 12.5


def test_clock_start_when_running_raises() -> None:
    c = SimulationClock(state=SimulationState.RUNNING)
    with pytest.raises(RuntimeError, match=r"already RUNNING"):
        c.start()


def test_clock_pause_only_from_running() -> None:
    c = SimulationClock(state=SimulationState.RUNNING)
    c.pause()
    assert c.state is SimulationState.PAUSED
    with pytest.raises(RuntimeError):
        c.pause()


def test_clock_stop_resets_sim_t_s() -> None:
    c = SimulationClock(state=SimulationState.RUNNING, sim_t_s=5.0)
    c.stop()
    assert c.state is SimulationState.STOPPED
    assert c.sim_t_s == 0.0


def test_clock_advance_only_when_running() -> None:
    c = SimulationClock(state=SimulationState.RUNNING)
    sim_dt = c.advance(0.5)
    assert sim_dt == pytest.approx(0.5, abs=1e-12)
    assert c.sim_t_s == pytest.approx(0.5, abs=1e-12)


def test_clock_advance_with_speed_multiplier() -> None:
    c = SimulationClock(state=SimulationState.RUNNING, speed=SpeedMultiplier.X4)
    sim_dt = c.advance(0.25)
    assert sim_dt == pytest.approx(1.0, abs=1e-12)


def test_clock_advance_paused_returns_zero() -> None:
    c = SimulationClock(state=SimulationState.PAUSED, sim_t_s=3.0)
    sim_dt = c.advance(0.5)
    assert sim_dt == 0.0
    assert c.sim_t_s == 3.0


def test_clock_advance_negative_dt_rejected() -> None:
    c = SimulationClock(state=SimulationState.RUNNING)
    with pytest.raises(ValueError, match=r"wall_dt_s"):
        c.advance(-0.1)


def test_clock_state_helpers() -> None:
    c = SimulationClock(state=SimulationState.RUNNING)
    assert c.is_running and not c.is_paused and not c.is_stopped
    c.pause()
    assert c.is_paused and not c.is_running


# ---------------------------------------------------------------------
# InputBuffer
# ---------------------------------------------------------------------


def test_input_buffer_initial_empty() -> None:
    b = InputBuffer()
    assert len(b) == 0


def test_input_buffer_enqueue_and_pending() -> None:
    b = InputBuffer()
    b.enqueue("sim.start", CommandSource.MANUAL_USER)
    b.enqueue("target.run", CommandSource.MANUAL_USER, {"id": "t1"})
    assert len(b) == 2
    assert b.pending[0] == ("sim.start", CommandSource.MANUAL_USER, {})
    assert b.pending[1][2] == {"id": "t1"}


def test_input_buffer_flush_dispatches_in_order() -> None:
    b = InputBuffer()
    b.enqueue("a", CommandSource.MANUAL_USER)
    b.enqueue("b", CommandSource.MANUAL_USER)
    log: list[str] = []
    n = b.flush(lambda name, _src, _args: log.append(name))
    assert n == 2
    assert log == ["a", "b"]
    assert len(b) == 0


def test_input_buffer_clear() -> None:
    b = InputBuffer()
    b.enqueue("x", CommandSource.MANUAL_USER)
    b.clear()
    assert len(b) == 0


def test_input_buffer_empty_name_rejected() -> None:
    b = InputBuffer()
    with pytest.raises(ValueError, match=r"name"):
        b.enqueue("", CommandSource.MANUAL_USER)


# ---------------------------------------------------------------------
# RunManager
# ---------------------------------------------------------------------


def test_run_manager_initial_idle() -> None:
    r = RunManager()
    assert r.state is RunState.IDLE
    assert r.termination_reason is None
    assert not r.is_active


def test_run_manager_start_and_pause() -> None:
    r = RunManager()
    r.start("run_001")
    assert r.state is RunState.RUNNING
    assert r.run_id == "run_001"
    r.pause()
    assert r.state is RunState.PAUSED
    assert r.is_active


def test_run_manager_resume() -> None:
    r = RunManager()
    r.start("x")
    r.pause()
    r.resume()
    assert r.state is RunState.RUNNING


def test_run_manager_end_records_reason() -> None:
    r = RunManager()
    r.start("x")
    r.end(RunTerminationReason.COMPLETED)
    assert r.state is RunState.ENDED
    assert r.termination_reason is RunTerminationReason.COMPLETED


def test_run_manager_end_idempotent() -> None:
    r = RunManager()
    r.start("x")
    r.end(RunTerminationReason.USER_STOPPED)
    r.end(RunTerminationReason.SIM_STOPPED)  # second call no-op
    assert r.termination_reason is RunTerminationReason.USER_STOPPED


def test_run_manager_reset() -> None:
    r = RunManager()
    r.start("x")
    r.end(RunTerminationReason.COMPLETED)
    r.reset()
    assert r.state is RunState.IDLE
    assert r.run_id == ""
    assert r.termination_reason is None


def test_run_manager_invalid_transitions() -> None:
    r = RunManager()
    with pytest.raises(RuntimeError):
        r.pause()  # IDLE -> pause
    with pytest.raises(RuntimeError):
        r.resume()  # IDLE -> resume
    with pytest.raises(RuntimeError):
        r.end(RunTerminationReason.COMPLETED)  # IDLE -> end


def test_run_manager_start_empty_id_rejected() -> None:
    r = RunManager()
    with pytest.raises(ValueError, match=r"run_id"):
        r.start("")


# ---------------------------------------------------------------------
# ProbeRecorder
# ---------------------------------------------------------------------


def test_probe_recorder_record_and_len() -> None:
    p = ProbeRecorder()
    p.record(0.0, {"x": 1})
    p.record(0.05, {"y": 2})
    assert len(p) == 2


def test_probe_recorder_negative_sim_t_rejected() -> None:
    p = ProbeRecorder()
    with pytest.raises(ValueError, match=r"sim_t_s"):
        p.record(-0.1, {})


def test_probe_recorder_to_csv_empty_returns_empty() -> None:
    assert ProbeRecorder().to_csv_string() == ""


def test_probe_recorder_csv_header_and_row_order() -> None:
    p = ProbeRecorder()
    p.record(0.0, {"a": 1, "b": 2})
    p.record(0.05, {"b": 4, "c": 5})
    csv_text = p.to_csv_string()
    lines = csv_text.strip().split("\n")
    assert lines[0] == "sim_t_s,a,b,c"
    # Row 1: a=1, b=2, c missing
    assert lines[1] == "0.000000000,1,2,"
    # Row 2: a missing, b=4, c=5
    assert lines[2] == "0.050000000,,4,5"


def test_probe_recorder_write_csv_to_file() -> None:
    p = ProbeRecorder()
    p.record(0.0, {"v": 7})
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "probe.csv"
        n = p.write_csv(out)
        assert n == 1
        text = out.read_text(encoding="utf-8")
        assert "sim_t_s,v" in text
        assert "0.000000000,7" in text


def test_probe_recorder_clear() -> None:
    p = ProbeRecorder()
    p.record(0.0, {})
    p.clear()
    assert len(p) == 0


def test_probe_row_dataclass() -> None:
    r = ProbeRow(sim_t_s=1.5, payload={"k": "v"})
    assert r.sim_t_s == 1.5
    assert r.payload["k"] == "v"
