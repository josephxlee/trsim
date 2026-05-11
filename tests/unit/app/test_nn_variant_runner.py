"""VariantBuildRunner tests (Task B, plan/07 § 7.4.5a)."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.app.nn import (
    PairingScenarioSpec,
    VariantBuildPlan,
    VariantBuildRunner,
    default_pairing_scenario,
    read_dataset,
    standard_pairing_build_plans,
)
from workbench.domain.nn import DatasetVariant, FieldSpec, SampleSpec
from workbench.domain.nn.variant_manifest import load_variants_manifest


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


def _plan(
    variant_id: str = "A",
    frames: int = 2,
    filename: str | None = None,
    *,
    description: str = "ideal",
) -> VariantBuildPlan:
    return VariantBuildPlan(
        variant=DatasetVariant(
            variant_id=variant_id,
            sea_state=0,
            attitude_on=False,
            sidelobe_on=False,
            description=description,
        ),
        dataset_filename=filename or f"pairing_variant_{variant_id}.h5",
        scenario=default_pairing_scenario(target_count=2),
        frames=frames,
    )


# ---------------------------------------------------------------------
# VariantBuildPlan validation
# ---------------------------------------------------------------------


def test_plan_rejects_empty_filename() -> None:
    with pytest.raises(ValueError, match=r"dataset_filename"):
        VariantBuildPlan(
            variant=DatasetVariant(variant_id="A"),
            dataset_filename="",
            scenario=default_pairing_scenario(),
            frames=1,
        )


def test_plan_rejects_negative_frames() -> None:
    with pytest.raises(ValueError, match=r"frames must be >= 0"):
        VariantBuildPlan(
            variant=DatasetVariant(variant_id="A"),
            dataset_filename="a.h5",
            scenario=default_pairing_scenario(),
            frames=-1,
        )


def test_plan_zero_frames_is_allowed() -> None:
    plan = VariantBuildPlan(
        variant=DatasetVariant(variant_id="A"),
        dataset_filename="a.h5",
        scenario=default_pairing_scenario(),
        frames=0,
    )
    assert plan.frames == 0


# ---------------------------------------------------------------------
# standard_pairing_build_plans
# ---------------------------------------------------------------------


def test_standard_pairing_plans_is_4_tier() -> None:
    plans = standard_pairing_build_plans()
    assert tuple(p.variant.variant_id for p in plans) == ("A", "B", "C", "D")
    assert all(p.frames == 100 for p in plans)
    assert plans[0].variant.description == "ideal"
    assert plans[3].variant.description == "full realistic"


def test_standard_pairing_plans_respect_frames_per_variant() -> None:
    plans = standard_pairing_build_plans(frames_per_variant=5)
    assert all(p.frames == 5 for p in plans)


def test_standard_pairing_plans_rejects_negative_frames() -> None:
    with pytest.raises(ValueError, match=r"frames_per_variant must be >= 0"):
        standard_pairing_build_plans(frames_per_variant=-1)


def test_standard_pairing_plans_accepts_external_scenario() -> None:
    scenario = PairingScenarioSpec(targets_initial_state=((1234.0, -50.0),))
    plans = standard_pairing_build_plans(frames_per_variant=1, scenario=scenario)
    assert all(p.scenario is scenario for p in plans)


# ---------------------------------------------------------------------
# VariantBuildRunner — validation
# ---------------------------------------------------------------------


def test_runner_rejects_empty_plans(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"at least one plan"):
        VariantBuildRunner(spec=_spec(), plans=(), output_root=tmp_path)


def test_runner_rejects_duplicate_variant_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"duplicate variant_id"):
        VariantBuildRunner(
            spec=_spec(),
            plans=(_plan("A"), _plan("A")),
            output_root=tmp_path,
        )


# ---------------------------------------------------------------------
# VariantBuildRunner — happy path
# ---------------------------------------------------------------------


def test_runner_writes_one_h5_per_variant(tmp_path: Path) -> None:
    plans = (_plan("A", frames=2), _plan("B", frames=3, description="attitude"))
    runner = VariantBuildRunner(spec=_spec(), plans=plans, output_root=tmp_path)
    manifest, results = runner.run()

    assert manifest is not None
    assert manifest.spec_id == "pairing"
    assert tuple(e.variant.variant_id for e in manifest.entries) == ("A", "B")

    assert len(results) == 2
    assert results[0].frames_executed == 2
    assert results[1].frames_executed == 3
    for r in results:
        assert r.dataset_path.is_file()
        assert not r.cancelled


def test_runner_writes_manifest_at_expected_path(tmp_path: Path) -> None:
    runner = VariantBuildRunner(spec=_spec(), plans=(_plan("A", frames=1),), output_root=tmp_path)
    manifest, _ = runner.run()
    assert manifest is not None
    assert runner.manifest_path.is_file()
    assert runner.manifest_path == tmp_path / "pairing_variants_manifest.toml"


def test_runner_manifest_roundtrips_through_toml(tmp_path: Path) -> None:
    plans = standard_pairing_build_plans(frames_per_variant=1, target_count=1)
    runner = VariantBuildRunner(spec=_spec(), plans=plans, output_root=tmp_path)
    manifest, _ = runner.run()
    assert manifest is not None

    loaded = load_variants_manifest(runner.manifest_path)
    assert loaded.spec_id == "pairing"
    assert tuple(e.variant.variant_id for e in loaded.entries) == ("A", "B", "C", "D")
    assert loaded.entries[0].dataset_path == Path("pairing_variant_A.h5")


def test_runner_h5_round_trips_via_read_dataset(tmp_path: Path) -> None:
    runner = VariantBuildRunner(spec=_spec(), plans=(_plan("A", frames=2),), output_root=tmp_path)
    _, results = runner.run()

    meta, inputs, labels = read_dataset(results[0].dataset_path)
    assert meta.dataset_id == "pairing_A"
    assert meta.variant.variant_id == "A"
    assert inputs["up_beats"].shape == (2, 16)
    assert labels["pair_indices"].shape == (2, 16)
    # First two slots carry the active targets; the rest is the -1 pad.
    assert labels["pair_indices"][0, 0] == 0
    assert labels["pair_indices"][0, 1] == 1
    assert labels["pair_indices"][0, 2] == -1


def test_runner_progress_callback_fires_per_frame(tmp_path: Path) -> None:
    calls: list[tuple[int, str, int, int]] = []

    def _on_progress(index: int, plan: VariantBuildPlan, n: int, target: int) -> None:
        calls.append((index, plan.variant.variant_id, n, target))

    runner = VariantBuildRunner(
        spec=_spec(),
        plans=(_plan("A", frames=2), _plan("B", frames=1)),
        output_root=tmp_path,
        progress_callback=_on_progress,
    )
    manifest, _ = runner.run()
    assert manifest is not None
    assert calls == [
        (0, "A", 1, 2),
        (0, "A", 2, 2),
        (1, "B", 1, 1),
    ]


def test_runner_dataset_id_prefix_overrides_default(tmp_path: Path) -> None:
    runner = VariantBuildRunner(
        spec=_spec(),
        plans=(_plan("A", frames=1),),
        output_root=tmp_path,
        dataset_id_prefix="custom_",
    )
    _, results = runner.run()
    meta, _, _ = read_dataset(results[0].dataset_path)
    assert meta.dataset_id == "custom_A"


# ---------------------------------------------------------------------
# VariantBuildRunner — cancellation
# ---------------------------------------------------------------------


def test_runner_cancel_before_run_returns_none_manifest(tmp_path: Path) -> None:
    runner = VariantBuildRunner(spec=_spec(), plans=(_plan("A"),), output_root=tmp_path)
    runner.cancel()
    manifest, results = runner.run()
    assert manifest is None
    assert results == ()
    assert not runner.manifest_path.exists()


def test_runner_cancel_between_plans_writes_partial_manifest(tmp_path: Path) -> None:
    calls: list[str] = []

    def _on_progress(_index: int, plan: VariantBuildPlan, _n: int, _target: int) -> None:
        calls.append(plan.variant.variant_id)
        # Cancel after the first frame of plan A so plan B never starts.
        if plan.variant.variant_id == "A":
            runner.cancel()

    runner = VariantBuildRunner(
        spec=_spec(),
        plans=(_plan("A", frames=5), _plan("B", frames=5)),
        output_root=tmp_path,
        progress_callback=_on_progress,
    )
    manifest, results = runner.run()
    assert manifest is not None
    assert tuple(e.variant.variant_id for e in manifest.entries) == ("A",)
    assert len(results) == 1
    assert results[0].cancelled
    assert results[0].frames_executed == 1
    assert calls == ["A"]


def test_runner_manifest_path_independent_of_run(tmp_path: Path) -> None:
    runner = VariantBuildRunner(
        spec=_spec(),
        plans=(_plan("A", frames=1),),
        output_root=tmp_path,
        manifest_filename="custom_manifest.toml",
    )
    assert runner.manifest_path == tmp_path / "custom_manifest.toml"
    runner.run()
    assert (tmp_path / "custom_manifest.toml").is_file()
