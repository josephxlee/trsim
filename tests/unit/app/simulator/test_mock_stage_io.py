"""MockStageIOGenerator unit tests (Phase 4 L5)."""

from __future__ import annotations

import pytest

from workbench.app.simulator import (
    DEFAULT_PLUGIN_NAMES,
    PIPELINE_STAGE_BOXES,
    MockStageIOFrame,
    MockStageIOGenerator,
)

# ---------------------------------------------------------------------
# Constructor validation
# ---------------------------------------------------------------------


def test_constructor_rejects_nonpositive_base_pulses() -> None:
    with pytest.raises(ValueError, match=r"base_pulses must be > 0"):
        MockStageIOGenerator(base_pulses=0)


def test_constructor_rejects_nonpositive_peak_reflections() -> None:
    with pytest.raises(ValueError, match=r"peak_reflections must be > 0"):
        MockStageIOGenerator(peak_reflections=0)


def test_constructor_rejects_nonpositive_peak_detections() -> None:
    with pytest.raises(ValueError, match=r"peak_detections must be > 0"):
        MockStageIOGenerator(peak_detections=0)


def test_constructor_rejects_nonpositive_peak_pairs() -> None:
    with pytest.raises(ValueError, match=r"peak_pairs must be > 0"):
        MockStageIOGenerator(peak_pairs=0)


def test_constructor_rejects_nonpositive_peak_tracks() -> None:
    with pytest.raises(ValueError, match=r"peak_tracks must be > 0"):
        MockStageIOGenerator(peak_tracks=0)


def test_constructor_rejects_zero_sweep_period() -> None:
    with pytest.raises(ValueError, match=r"sweep_period_s must be > 0"):
        MockStageIOGenerator(sweep_period_s=0.0)


# ---------------------------------------------------------------------
# io_for
# ---------------------------------------------------------------------


def test_io_for_rejects_negative_sim_t_s() -> None:
    gen = MockStageIOGenerator()
    with pytest.raises(ValueError, match=r"sim_t_s must be non-negative"):
        gen.io_for(-0.1)


def test_io_for_contains_every_pipeline_stage_in_order() -> None:
    gen = MockStageIOGenerator()
    frame = gen.io_for(0.0)
    assert isinstance(frame, MockStageIOFrame)
    assert tuple(frame.stage_io.keys()) == PIPELINE_STAGE_BOXES
    for stage in PIPELINE_STAGE_BOXES:
        in_text, out_text = frame.stage_io[stage]
        assert isinstance(in_text, str)
        assert isinstance(out_text, str)


def test_transmitter_io_echoes_sim_t_s() -> None:
    gen = MockStageIOGenerator(base_pulses=100)
    frame = gen.io_for(0.250)
    in_text, out_text = frame.stage_io["Transmitter"]
    assert "0.250" in in_text
    assert "100 pulses" in out_text


def test_environment_pipe_consumes_transmitter_output() -> None:
    """Environment.IN == Transmitter.OUT (pipeline pass-through)."""
    gen = MockStageIOGenerator(base_pulses=42)
    frame = gen.io_for(0.5)
    tx_out = frame.stage_io["Transmitter"][1]
    env_in = frame.stage_io["Environment"][0]
    assert tx_out == env_in


def test_io_for_is_deterministic() -> None:
    gen = MockStageIOGenerator()
    a = gen.io_for(1.0)
    b = gen.io_for(1.0)
    assert a.stage_io == b.stage_io


def test_io_for_modulates_counts_over_time() -> None:
    """sin(0) and sin(pi/2) differ -> reflections counts differ."""
    gen = MockStageIOGenerator(sweep_period_s=4.0, peak_reflections=100)
    a = gen.io_for(0.0)
    b = gen.io_for(1.0)
    assert a.stage_io["Environment"][1] != b.stage_io["Environment"][1]


def test_io_for_peak_reflections_dominates_at_quarter_period() -> None:
    """sin(pi/2) = 1 -> reflections ~ peak."""
    gen = MockStageIOGenerator(sweep_period_s=4.0, peak_reflections=64)
    frame = gen.io_for(1.0)  # quarter period
    _in_text, out_text = frame.stage_io["Environment"]
    assert "64 reflections" in out_text


# ---------------------------------------------------------------------
# DEFAULT_PLUGIN_NAMES
# ---------------------------------------------------------------------


def test_default_plugin_names_covers_pipeline_stages() -> None:
    """Every plan/02 pipeline stage has at least one default plugin name."""
    assert set(DEFAULT_PLUGIN_NAMES) >= {
        "Detector",
        "Pairing",
        "Tracker",
        "Predictor",
        "Classifier",
    }


def test_default_plugin_names_values_are_nonempty_strings() -> None:
    for names in DEFAULT_PLUGIN_NAMES.values():
        assert len(names) >= 1
        for n in names:
            assert isinstance(n, str)
            assert n
