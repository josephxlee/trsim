"""NN sample-spec schema tests (Phase 6.1)."""

from __future__ import annotations

import pytest

from workbench.domain.nn import (
    DatasetMeta,
    DatasetVariant,
    FieldSpec,
    SampleSpec,
)


def _pairing_spec() -> SampleSpec:
    """Build a Pairing-shaped SampleSpec matching plan/07 § 7.4.5b."""
    return SampleSpec(
        spec_id="pairing",
        probe_stage="pairing",
        inputs=(
            FieldSpec("up_beats", (16,), "complex64", "Up-sweep beat list"),
            FieldSpec("down_beats", (16,), "complex64", "Down-sweep beat list"),
        ),
        labels=(FieldSpec("pair_indices", (16,), "int32", "GT pair index per up beat"),),
    )


# ---------------------------------------------------------------------
# FieldSpec
# ---------------------------------------------------------------------


def test_field_spec_construction() -> None:
    f = FieldSpec("phases", (4,), "complex64", "4-channel sum/delta")
    assert f.name == "phases"
    assert f.shape == (4,)
    assert f.dtype == "complex64"


def test_field_spec_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match=r"name"):
        FieldSpec("", (4,), "float32")


def test_field_spec_rejects_zero_shape_dim() -> None:
    with pytest.raises(ValueError, match=r"shape"):
        FieldSpec("x", (4, 0), "float32")


def test_field_spec_rejects_negative_shape_dim() -> None:
    with pytest.raises(ValueError, match=r"shape"):
        FieldSpec("x", (-1,), "float32")


def test_field_spec_rejects_unknown_dtype() -> None:
    with pytest.raises(ValueError, match=r"dtype"):
        FieldSpec("x", (4,), "float128")


def test_field_spec_is_frozen() -> None:
    f = FieldSpec("phases", (4,), "complex64")
    with pytest.raises(Exception):  # noqa: B017
        f.name = "renamed"  # type: ignore[misc]


# ---------------------------------------------------------------------
# SampleSpec
# ---------------------------------------------------------------------


def test_sample_spec_pairing_template_round_trip() -> None:
    spec = _pairing_spec()
    assert spec.spec_id == "pairing"
    assert spec.probe_stage == "pairing"
    assert len(spec.inputs) == 2
    assert len(spec.labels) == 1
    # Order preserved (HDF5 write order is stable).
    assert spec.inputs[0].name == "up_beats"
    assert spec.inputs[1].name == "down_beats"


def test_sample_spec_rejects_empty_spec_id() -> None:
    with pytest.raises(ValueError, match=r"spec_id"):
        SampleSpec(
            spec_id="",
            probe_stage="pairing",
            inputs=(FieldSpec("x", (1,), "float32"),),
            labels=(FieldSpec("y", (1,), "float32"),),
        )


def test_sample_spec_rejects_empty_probe_stage() -> None:
    with pytest.raises(ValueError, match=r"probe_stage"):
        SampleSpec(
            spec_id="x",
            probe_stage="",
            inputs=(FieldSpec("a", (1,), "float32"),),
            labels=(FieldSpec("b", (1,), "float32"),),
        )


def test_sample_spec_rejects_empty_inputs() -> None:
    with pytest.raises(ValueError, match=r"inputs"):
        SampleSpec(
            spec_id="x",
            probe_stage="pairing",
            inputs=(),
            labels=(FieldSpec("y", (1,), "float32"),),
        )


def test_sample_spec_rejects_empty_labels() -> None:
    with pytest.raises(ValueError, match=r"labels"):
        SampleSpec(
            spec_id="x",
            probe_stage="pairing",
            inputs=(FieldSpec("a", (1,), "float32"),),
            labels=(),
        )


def test_sample_spec_rejects_duplicate_field_name_across_input_and_label() -> None:
    """HDF5 paths /inputs/<name> and /labels/<name> must not collide."""
    with pytest.raises(ValueError, match=r"duplicate"):
        SampleSpec(
            spec_id="x",
            probe_stage="pairing",
            inputs=(FieldSpec("shared", (1,), "float32"),),
            labels=(FieldSpec("shared", (1,), "float32"),),
        )


# ---------------------------------------------------------------------
# DatasetVariant
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("variant_id", "sea_state", "attitude_on", "sidelobe_on"),
    [
        ("A", 0, False, False),
        ("B", 3, True, False),
        ("C", 0, False, True),
        ("D", 3, True, True),
    ],
)
def test_pairing_variant_standard_4_constructs(
    variant_id: str, sea_state: int, attitude_on: bool, sidelobe_on: bool
) -> None:
    v = DatasetVariant(
        variant_id=variant_id,
        sea_state=sea_state,
        attitude_on=attitude_on,
        sidelobe_on=sidelobe_on,
    )
    assert v.variant_id == variant_id
    assert v.sea_state == sea_state


def test_dataset_variant_rejects_empty_variant_id() -> None:
    with pytest.raises(ValueError, match=r"variant_id"):
        DatasetVariant(variant_id="")


@pytest.mark.parametrize("bad_sea_state", [-1, 10, 100])
def test_dataset_variant_rejects_out_of_range_sea_state(bad_sea_state: int) -> None:
    with pytest.raises(ValueError, match=r"sea_state"):
        DatasetVariant(variant_id="A", sea_state=bad_sea_state)


# ---------------------------------------------------------------------
# DatasetMeta
# ---------------------------------------------------------------------


def test_dataset_meta_default_total_samples_zero() -> None:
    meta = DatasetMeta(
        dataset_id="empty_pairing_A",
        spec=_pairing_spec(),
        variant=DatasetVariant(variant_id="A"),
    )
    assert meta.total_samples == 0
    assert meta.scenarios == ()
    assert dict(meta.extra) == {}


def test_dataset_meta_rejects_empty_dataset_id() -> None:
    with pytest.raises(ValueError, match=r"dataset_id"):
        DatasetMeta(
            dataset_id="",
            spec=_pairing_spec(),
            variant=DatasetVariant(variant_id="A"),
        )


def test_dataset_meta_rejects_negative_total_samples() -> None:
    with pytest.raises(ValueError, match=r"total_samples"):
        DatasetMeta(
            dataset_id="x",
            spec=_pairing_spec(),
            variant=DatasetVariant(variant_id="A"),
            total_samples=-1,
        )


def test_dataset_meta_preserves_scenarios_and_extra() -> None:
    meta = DatasetMeta(
        dataset_id="pairing_variant_A_2026-05-11",
        spec=_pairing_spec(),
        variant=DatasetVariant(variant_id="A"),
        total_samples=1024,
        created_at_iso="2026-05-11T12:00:00Z",
        scenarios=("baseline_sea_0",),
        extra={"job_id": "job_001", "git_hash": "9d12a6e"},
    )
    assert meta.total_samples == 1024
    assert meta.scenarios == ("baseline_sea_0",)
    assert dict(meta.extra) == {"job_id": "job_001", "git_hash": "9d12a6e"}
