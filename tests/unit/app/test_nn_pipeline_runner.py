"""PipelineRunner + PairingScenarioSpec tests (Phase 6 후속, task 2)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from workbench.app.nn import (
    DatasetBuilder,
    PairingScenarioSpec,
    PipelineRunner,
    default_pairing_scenario,
    read_dataset,
)
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec
from workbench.physics.propagation.fmcw import fmcw_triangle_beats


def _spec(buffer_size: int = 16) -> SampleSpec:
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (buffer_size,), "complex64"),
            FieldSpec("down_beats", (buffer_size,), "complex64"),
        ),
        labels=(FieldSpec("pair_indices", (buffer_size,), "int32"),),
    )


def _builder(tmp_path: Path, buffer_size: int = 16) -> DatasetBuilder:
    return DatasetBuilder(
        spec=_spec(buffer_size),
        variant=DatasetVariant(variant_id="A"),
        dataset_id="pairing_demo",
        output_path=tmp_path / "demo.h5",
    )


# ---------------------------------------------------------------------
# PairingScenarioSpec validation
# ---------------------------------------------------------------------


def test_default_scenario_constructs_with_3_targets() -> None:
    scenario = default_pairing_scenario()
    assert len(scenario.targets_initial_state) == 3
    assert scenario.carrier_freq_hz == 9.4e9


def test_default_scenario_clamps_to_3_max() -> None:
    assert len(default_pairing_scenario(target_count=10).targets_initial_state) == 3


def test_default_scenario_at_least_one_target() -> None:
    assert len(default_pairing_scenario(target_count=0).targets_initial_state) == 1


def test_empty_targets_rejected() -> None:
    with pytest.raises(ValueError, match=r"targets_initial_state"):
        PairingScenarioSpec(targets_initial_state=())


def test_non_positive_range_rejected() -> None:
    with pytest.raises(ValueError, match=r"range_m"):
        PairingScenarioSpec(targets_initial_state=((0.0, 0.0),))


@pytest.mark.parametrize(
    "field_name",
    ["dt_s", "carrier_freq_hz", "bandwidth_hz", "sweep_period_s"],
)
def test_non_positive_numeric_rejected(field_name: str) -> None:
    kwargs: dict[str, Any] = {"targets_initial_state": ((1000.0, 0.0),)}
    kwargs[field_name] = 0.0
    with pytest.raises(ValueError, match=field_name):
        PairingScenarioSpec(**kwargs)


# ---------------------------------------------------------------------
# PipelineRunner — basic build
# ---------------------------------------------------------------------


def test_run_appends_one_record_per_frame(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    scenario = default_pairing_scenario(3)
    runner = PipelineRunner(builder=builder, scenario=scenario)
    n_done = runner.run_pairing_dataset(n_frames=5)
    assert n_done == 5
    assert builder.n_appended == 5


def test_zero_frames_is_noop(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    runner = PipelineRunner(builder=builder, scenario=default_pairing_scenario())
    assert runner.run_pairing_dataset(n_frames=0) == 0
    assert builder.n_appended == 0


def test_negative_n_frames_rejected(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    runner = PipelineRunner(builder=builder, scenario=default_pairing_scenario())
    with pytest.raises(ValueError, match=r"n_frames"):
        runner.run_pairing_dataset(n_frames=-1)


def test_buffer_too_small_rejected_at_construction(tmp_path: Path) -> None:
    """SampleSpec buffer (5) < target count (3 in default scenario clamp 10 -> 3)
    — wait, default is 3 -> 3 fits in 5. Make 4 targets / buffer 3 to trigger.
    """
    builder = _builder(tmp_path, buffer_size=2)
    scenario = PairingScenarioSpec(
        targets_initial_state=((1000.0, 0.0), (2000.0, 0.0), (3000.0, 0.0)),
    )
    with pytest.raises(ValueError, match=r"buffer size"):
        PipelineRunner(builder=builder, scenario=scenario)


# ---------------------------------------------------------------------
# Beat / GT correctness
# ---------------------------------------------------------------------


def test_beats_match_fmcw_triangle_closed_form(tmp_path: Path) -> None:
    """The runner's per-target beats must equal fmcw_triangle_beats()
    on the propagated range.
    """
    builder = _builder(tmp_path)
    scenario = PairingScenarioSpec(
        targets_initial_state=((5000.0, 30.0),),
        dt_s=0.1,
    )
    runner = PipelineRunner(builder=builder, scenario=scenario)
    runner.run_pairing_dataset(n_frames=3)
    builder.finalize()

    _meta, inputs, _labels = read_dataset(tmp_path / "demo.h5")
    # Frame 2 -> range = 5000 - 30 * 0.2 = 4994.0
    expected_up, expected_down = fmcw_triangle_beats(
        range_m=4994.0,
        v_radial_m_s=30.0,
        bandwidth_hz=scenario.bandwidth_hz,
        sweep_period_s=scenario.sweep_period_s,
        carrier_freq_hz=scenario.carrier_freq_hz,
    )
    assert complex(inputs["up_beats"][2, 0]).real == pytest.approx(expected_up, rel=1e-5)
    assert complex(inputs["down_beats"][2, 0]).real == pytest.approx(expected_down, rel=1e-5)


def test_gt_pair_indices_diagonal_for_active_targets_padding_negative_one(
    tmp_path: Path,
) -> None:
    builder = _builder(tmp_path, buffer_size=16)
    scenario = default_pairing_scenario(3)
    runner = PipelineRunner(builder=builder, scenario=scenario)
    runner.run_pairing_dataset(n_frames=2)
    builder.finalize()

    _meta, _inputs, labels = read_dataset(tmp_path / "demo.h5")
    gt = labels["pair_indices"][0]
    assert gt[0] == 0
    assert gt[1] == 1
    assert gt[2] == 2
    # Slots 3..15 are padding -> -1
    assert int(gt[3]) == -1
    assert int(gt[15]) == -1


def test_padding_beats_are_zero(tmp_path: Path) -> None:
    builder = _builder(tmp_path, buffer_size=16)
    scenario = default_pairing_scenario(2)
    runner = PipelineRunner(builder=builder, scenario=scenario)
    runner.run_pairing_dataset(n_frames=1)
    builder.finalize()

    _meta, inputs, _labels = read_dataset(tmp_path / "demo.h5")
    # Targets 0..1 -> non-zero; slots 2..15 -> zero
    for j in range(2, 16):
        assert complex(inputs["up_beats"][0, j]) == 0j
        assert complex(inputs["down_beats"][0, j]) == 0j


# ---------------------------------------------------------------------
# Probe callback
# ---------------------------------------------------------------------


def test_probe_callback_fires_once_per_frame_with_stage_pairing(tmp_path: Path) -> None:
    builder = _builder(tmp_path)
    scenario = default_pairing_scenario(2)
    seen: list[tuple[str, int]] = []

    def cb(stage: str, payload: Mapping[str, Any]) -> None:
        seen.append((stage, int(payload["frame_index"])))

    runner = PipelineRunner(builder=builder, scenario=scenario, probe_callback=cb)
    runner.run_pairing_dataset(n_frames=4)
    assert seen == [("pairing", 0), ("pairing", 1), ("pairing", 2), ("pairing", 3)]


# ---------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------


def test_run_breaks_immediately_when_builder_cancelled(tmp_path: Path) -> None:
    """A probe callback can trip builder.cancel() — the next iteration
    must see is_cancelled and break before appending.
    """
    builder = _builder(tmp_path)
    scenario = default_pairing_scenario(2)

    def cancel_after_two(_stage: str, payload: Mapping[str, Any]) -> None:
        if int(payload["frame_index"]) == 1:
            builder.cancel()

    runner = PipelineRunner(builder=builder, scenario=scenario, probe_callback=cancel_after_two)
    n_done = runner.run_pairing_dataset(n_frames=10)
    # Frame 0 appends fully. Frame 1's probe trips cancel BEFORE the
    # append in the same iteration -> append skipped, loop breaks.
    # Net: 1 frame appended.
    assert n_done == 1
    assert builder.n_appended == 1
